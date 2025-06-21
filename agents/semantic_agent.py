import subprocess
import os
import pickle
import faiss
import json
import numpy as np
from sentence_transformers import SentenceTransformer
import pandas as pd
import matplotlib.pyplot as plt
import re
import io
import base64
import sqlite3
import requests
import hashlib
import openai


POWERAUTOMATE_URL = "https://prod-08.southeastasia.logic.azure.com:443/workflows/a9de89a708674755923e900665994521/triggers/manual/paths/invoke?api-version=2016-06-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=Eo8rgY9JHLAqYDQCYTjWYiufiHq3LYQ_kZXWmGjqLhw"  # 🔁 請換成你的實際網址


# 外部程式碼
from utils.kb_loader import load_kb  # ✅ 請確保你已經建立這個檔案並放好函式

DB_PATH = "resultDB.db"  # 你在 build_kb.py 裡設定的 DB 名稱
kb_model, kb_index, kb_texts = load_kb() # 載入知識庫模型、索引和文本

def id_to_int64(uid):
    return int(hashlib.sha256(uid.encode("utf-8")).hexdigest(), 16) % (1 << 63)


class SemanticAgent:
    def __init__(self, model="orca2:13b", kb_model=None, kb_index=None, kb_texts=None, metadata=None, faiss_id_to_text=None):
        self.model = model
        self.kb_model = kb_model
        self.kb_index = kb_index
        self.kb_texts = kb_texts
        self.metadata = metadata or []  # 避免 metadata=None 時出錯
        self.faiss_id_to_text = faiss_id_to_text or {}  # 避免 faiss_id_to_text=None 時出錯


        self.faiss_to_real_id = {
            id_to_int64(item["id"]): item["id"] for item in self.metadata
        }
        
    # 壓縮多段摘要
    # 將多段摘要合併成一段
    def _recursive_merge(self, summaries, token_limit, prompt_reserve):
        available_tokens = token_limit - prompt_reserve

        def estimate_token(text):
            return int(len(text) / 4)

        merged_groups = []
        group = []
        token_count = 0
        for s in summaries:
            t = estimate_token(s)
            if token_count + t > available_tokens and group:
                merged_groups.append(group)
                group = [s]
                token_count = t
            else:
                group.append(s)
                token_count += t
        if group:
            merged_groups.append(group)

        results = []

        for i, group in enumerate(merged_groups, 1):
            print(f"📡 嘗試使用 AI Builder 分析第 {i} 組合併摘要...")
            group_text = "\n\n".join([f"({j+1}) {s.strip()}" for j, s in enumerate(group)])

            payload = {
                "template": "Based on the following summaries, please synthesize the main insights:\n\nSummaries:",
                "userInput": group_text + "\n\nPlease provide an overall concluding observation:"
            }

            try:
                res = requests.post(POWERAUTOMATE_URL, json=payload, timeout=360)
                if res.status_code == 200:
                    reply = res.json().get("response", "").strip()
                    print(f"✅ AI Builder 回應合併摘要：{reply}")
                else:
                    print(f"⚠️ AI Builder 回傳狀態碼異常：{res.status_code}")
                    reply = None
            except Exception as e:
                print(f"❌ AI Builder 呼叫失敗或逾時：{e}")
                reply = None

            if not reply:
                merge_prompt = "Based on the following summaries, please synthesize the main insights:\n\n"
                for j, s in enumerate(group, 1):
                    merge_prompt += f"（第 {j} 段摘要）{s}\n\n"
                merge_prompt += "Please provide an overall concluding observation:"
                reply = self._run_with_fallback(merge_prompt)
                print(f"🔁 fallback 模型合併結果：{reply}")

            results.append(reply if reply else "❌ 合併失敗")

        return results[0] if len(results) == 1 else self._recursive_merge(results, token_limit, prompt_reserve)
    
    # 使用 ollama 執行模型
    def _run_with_fallback(self, prompt):
        try:
            result = subprocess.run(
                ["ollama", "run", self.model],
                input=prompt.encode("utf-8"),
                capture_output=True,
                timeout=600
            )
            if result.returncode == 0:
                return result.stdout.decode("utf-8").strip()
        except Exception as e:
            print(f"❌ 模型 {self.model} 發生錯誤：{e}")

        fallback_model = "nous-hermes2:10.7b"
        try:
            result = subprocess.run(
                ["ollama", "run", fallback_model],
                input=prompt.encode("utf-8"),
                capture_output=True,
                timeout=600
            )
            if result.returncode == 0:
                return result.stdout.decode("utf-8").strip()
        except Exception as e:
            print(f"❌ fallback 模型 {fallback_model} 發生錯誤：{e}")

        return None
    
    def _summarize_retrieved_kb(self, retrieved):
        if not retrieved:
            print("⚠️ 無資料可摘要（retrieved 為空）")
            return ""

        print("🧠 正在進行分段摘要處理（retrieved KB）...")
        print(f"📦 輸入筆數：{len(retrieved)}")

        model_token_limits = {
            "orca2:13b": 8192,
            "nous-hermes2:10.7b": 8192,
            "mistral": 8192,
            "phi4-mini": 4096,
            "phi3:mini": 4096,
            "command-r7b:latest": 4096,
            "openchat:7b": 4096,
            "deepseek-coder-v2:latest": 16384,
            "deepseek-coder:latest": 16384,
        }
        token_limit = model_token_limits.get(self.model, 4096)
        prompt_reserve = 500
        available_tokens = token_limit - prompt_reserve
        print(f"🔍 模型 {self.model} 的 token 限制：{token_limit}")
        print(f"🧠 可用 token 數量：{available_tokens}（扣除提示詞保留 {prompt_reserve}）")

        def estimate_token(text):
            return int(len(text) / 4)

        groups = []
        group = []
        token_sum = 0
        print("🔍 正在分組知識庫資料...")
        for text in retrieved:
            tokens = estimate_token(text)
            print(f"📦 處理文本：{text[:50]}... (估計 token: {tokens})")
            if token_sum + tokens > available_tokens and group:
                groups.append(group)
                group = [text]
                token_sum = tokens
            else:
                group.append(text)
                token_sum += tokens
        if group:
            groups.append(group)

        print(f"📦 共分成 {len(groups)} 組，每組平均 {token_sum / len(groups):.2f} tokens")
        chunk_summaries = []
        
        for i, group in enumerate(groups, 1):
            print(f"📡 嘗試使用 AI Builder 分析第 {i} 組摘要...")
            entries_text = "\n".join([f"{j+1}. {txt.strip()}" for j, txt in enumerate(group)])
            payload = {
                "template": "Please summarize the key points and handling methods based on the following knowledge entries (respond in English):",
                "userInput": entries_text + "\n\nPlease provide a single summary paragraph:"
            }

            try:
                res = requests.post(POWERAUTOMATE_URL, json=payload, timeout=360)
                if res.status_code == 200:
                    reply = res.json().get("response", "").strip()
                    print(f"✅ AI Builder 回應摘要：{reply}")
                else:
                    print(f"⚠️ AI Builder 回傳狀態碼異常：{res.status_code}")
                    reply = None
            except Exception as e:
                print(f"❌ AI Builder 呼叫失敗或逾時：{e}")
                reply = None

            if not reply:
                prompt = (
                    "Please summarize the key points and handling methods based on the following knowledge entries (respond in English):\n\n" +
                    entries_text + "\n\nPlease provide a single summary paragraph:"
                )
                reply = self._run_with_fallback(prompt)
                print(f"🔁 fallback 模型摘要結果：{reply}")

            chunk_summaries.append(reply if reply else "❌ 本段摘要失敗")

        if len(chunk_summaries) == 1:
            return chunk_summaries[0]
        else:
            return self._recursive_merge(chunk_summaries, token_limit, prompt_reserve)



    def _determine_top_k(self, user_input, fallback=3, min_top_k=1, max_top_k=10):
        print("🧠 [SemanticAgent] 使用 AI Builder 預測合適的 top_k 數量（HTTP 模式）...")
        
        # ✅ Power Automate 用：Prompt 與 user_input 分開
        powerautomate_prompt_template = (
            "You are a knowledge retrieval assistant. Based on the user's question, decide how many similar cases (top_k) should be retrieved from the knowledge base.\n\n"
            "Guidelines:\n"
            "- If the question is **very specific** (mentions error codes, clear symptoms, or keywords), return a **small** top_k (1–3).\n"
            "- If the question is **vague or general** (like 'why is it slow?' or 'something went wrong'), return a **larger** top_k (5–10).\n"
            "- If the user asks for a **summary, report, or trend**, use a **larger** top_k (8–10).\n"
            "- Only reply with a **single integer** between 1 and 10. Do not add explanation.\n\n"
            "User question: "
        )
        
        # ✅ 原本的 prompt（保留合併版本）— 用於本地模型
        prompt = (
            powerautomate_prompt_template + f"{user_input}\n\nAnswer:"
        )

        # ✅ 先嘗試透過 Power Automate 的 AI Builder 分析
        try:
            payload = {
                "template": powerautomate_prompt_template,
                "userInput": user_input,
            }
            print(f"📡 傳送 prompt 至 Power Automate...")
            res = requests.post(POWERAUTOMATE_URL, json=payload, timeout=360)
            if res.status_code == 200:
                reply = res.json().get("response", "").strip()
                print(f"📥 AI Builder 回應：{reply}")
                match = re.search(r"\b([1-9]|10)\b", reply)
                if match:
                    top_k = int(match.group(1))
                    return max(min_top_k, min(top_k, max_top_k))
                else:
                    print("⚠️ 回應中未偵測到合法數字 top_k")
            else:
                print(f"❌ AI Builder 回應錯誤，狀態碼：{res.status_code}")
        except Exception as e:
            print(f"❌ AI Builder 呼叫失敗或逾時，使用 fallback 模型：{e}")

        # ✅ 改用本地模型 fallback
        def try_model(model_name):
            try:
                print(f"🧠 嘗試本地模型：{model_name}")
                result = subprocess.run(
                    ["ollama", "run", model_name],
                    input=prompt.encode("utf-8"),
                    capture_output=True,
                    timeout=240
                )
                if result.returncode == 0:
                    reply = result.stdout.decode("utf-8").strip()
                    print(f"📥 模型回覆：{reply}")
                    match = re.search(r"\b([1-9]|10)\b", reply)
                    if match:
                        top_k = int(match.group(1))
                        return max(min_top_k, min(top_k, max_top_k))
            except Exception as e:
                print(f"❌ 模型 {model_name} 失敗：{e}")
            return None

        for model in ["command-r7b:latest", "openchat:7b", "phi4-mini"]:
            top_k = try_model(model)
            if top_k:
                return top_k

        print(f"⚠️ 所有方式皆失敗，使用預設 fallback 值 {fallback}")
        return fallback

    def _search_knowledge_base(self, query, top_k=None):
        print("🔍 [SemanticAgent] 執行語意查詢...")
        if self.kb_model is None or self.kb_index is None or self.kb_texts is None:
            print("❌ 知識庫尚未載入")
            return []

        if top_k is None:
            top_k = self._determine_top_k(query)
            print(f"🤖 動態決定 top_k = {top_k}")

        query_vec = self.kb_model.encode([query])
        D, I = self.kb_index.search(np.array(query_vec), top_k) # 執行檢索
        

        print("📂 開啟 SQLite 資料庫連線")
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
        except Exception as e:
            print(f"❌ 連線 SQLite 失敗：{e}")
            return []
        print("🔍 正在查詢相關知識庫資料...")

        results = []
        for i, distance in zip(I[0], D[0]):
            try:
                real_id = self.faiss_to_real_id.get(i, "❌ 無法對應")
                text = self.faiss_id_to_text.get(i, "❌ 找不到句子")  # ✅ 改這裡！
                print(f"📌 FAISS ID: {i} → 原始 ID: {real_id}")
                print(f"📜 原始句子內容：{text} ｜📏 距離（越小越相似）: {distance:.4f}")


                # 查資料庫
                cur.execute("SELECT * FROM metadata WHERE id = ?", (real_id,))
                row = cur.fetchone()

                if row:
                    columns = [desc[0] for desc in cur.description]
                    row_dict = dict(zip(columns, row))
                    print(f"🧾 成功查回資料庫資料：{row_dict}")
                else:
                    row_dict = None
                    print("⚠️ 查不到 SQLite 資料（可能是 ID 不存在）")

                results.append({
                    "text": text,
                    "real_id": real_id,
                    "row": row_dict
                })
            except Exception as e:
                print(f"❌ 處理 FAISS ID {i} 發生錯誤：{e}")
                
        try:
            conn.close()
            print("✅ 關閉 SQLite 連線")
        except Exception as e:
            print(f"⚠️ 關閉連線時出錯：{e}")
        print(f"📦 共找到 {len(results)} 筆相關知識庫資料")
        return results
        

    
    def handle(self, query, top_k=None):
        print(f"📥 [SemanticAgent] 接收到查詢：{query}")
        retrieved_pairs = self._search_knowledge_base(query, top_k)

        # 加入 Entry 分隔與欄位格式化
        retrieved_texts = []
        for idx, entry in enumerate(retrieved_pairs, 1):
            row = entry.get("row")
            if row:
                description = (
                    f"--- Incident Entry {idx} ---\n"
                    f"ID: {row.get('id', '')}\n"
                    f"Text: {row.get('text', '')}\n"
                    f"Subcategory: {row.get('subcategory', '')}\n"
                    f"ConfigurationItem: {row.get('configurationItem', '')}\n"
                    f"RoleComponent: {row.get('roleComponent', '')}\n"
                    f"Location: {row.get('location', '')}\n"
                    f"Opened: {row.get('opened', '')}\n"
                    f"AnalysisTime: {row.get('analysisTime', '')}"
                )
            else:
                description = f"--- Entry {idx} ---\n{entry.get('text', '❌ 無原始文字')}"

            retrieved_texts.append(description)

        # 做摘要
        summary = self._summarize_retrieved_kb(retrieved_texts)

        print("📝 [SemanticAgent] 知識庫摘要完成：")
        print(summary)

        # 額外列印 ID
        print("📋 查詢對應 ID 在 sqlite db 中：")
        for idx, entry in enumerate(retrieved_pairs, 1):
            print(f"🆔 Entry {idx} → ID: {entry['real_id']}")

        return summary

