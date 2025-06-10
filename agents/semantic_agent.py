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

# 外部程式碼
from utils.kb_loader import load_kb  # ✅ 請確保你已經建立這個檔案並放好函式

DB_PATH = "resultDB.db"  # 你在 build_kb.py 裡設定的 DB 名稱
kb_model, kb_index, kb_texts = load_kb() # 載入知識庫模型、索引和文本





class SemanticAgent:
    def __init__(self, model="orca2:13b", kb_model=None, kb_index=None, kb_texts=None):
        self.model = model
        self.kb_model = kb_model
        self.kb_index = kb_index
        self.kb_texts = kb_texts



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
            merge_prompt = "Based on the following summaries, please synthesize the main insights:\n\n"
            for j, s in enumerate(group, 1):
                merge_prompt += f"（第 {j} 段摘要）{s}\n\n"
            merge_prompt += "Please provide an overall concluding observation:"
            reply = self._run_with_fallback(merge_prompt)
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

    # 知識庫摘要處理
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
        print(f"🔍 模型 {self.model} 的 token 限制：{token_limit}")
        prompt_reserve = 500
        available_tokens = token_limit - prompt_reserve
        print(f"🧠 可用 token 數量：{available_tokens}（扣除提示詞保留 {prompt_reserve}）" )

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
        print(f"📦 共分成 {len(groups)} 組，每組平均 {token_sum / len(groups):.2f} tokens" )
        chunk_summaries = []
        for i, group in enumerate(groups, 1):
            prompt = "Please summarize the key points and handling methods based on the following knowledge entries (respond in English):\n\n"
            for j, txt in enumerate(group, 1):
                prompt += f"{j}. {txt.strip()}\n"
            prompt += "\nPlease provide a single summary paragraph:"

            reply = self._run_with_fallback(prompt)
            chunk_summaries.append(reply if reply else "❌ 本段摘要失敗")

        if len(chunk_summaries) == 1:
            return chunk_summaries[0]
        else:
            return self._recursive_merge(chunk_summaries, token_limit, prompt_reserve)



    # 主要處理函式
    def _determine_top_k(self, user_input, fallback=3, min_top_k=1, max_top_k=10):
        print("🧠 [SemanticAgent] 使用 LLM 預測合適的 top_k 數量...")
        prompt = (
            "You are a knowledge retrieval assistant. Based on the user's question, decide how many similar cases (top_k) should be retrieved from the knowledge base.\n\n"
            "Guidelines:\n"
            "- If the question is **very specific** (mentions error codes, clear symptoms, or keywords), return a **small** top_k (1–3).\n"
            "- If the question is **vague or general** (like 'why is it slow?' or 'something went wrong'), return a **larger** top_k (5–10).\n"
            "- If the user asks for a **summary, report, or trend**, use a **larger** top_k (8–10).\n"
            "- Only reply with a **single integer** between 1 and 10. Do not add explanation.\n\n"
            f"User question: {user_input}\n\nAnswer:"
        )

        def try_model(model_name):
            try:
                print(f"🧠 嘗試模型：{model_name}")
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
        print(f"⚠️ 全部模型失敗，使用 fallback {fallback}")
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
        D, I = self.kb_index.search(np.array(query_vec), top_k)
        print(f"[RAG] 🔍 查詢內容：{query}")
        print(f"[RAG] 🧠 取出知識庫資料：{[self.kb_texts[i][:50] for i in I[0]]}")
        return [self.kb_texts[i] for i in I[0]]
    
    def handle(self, query, top_k=None):
        print(f"📥 [SemanticAgent] 接收到查詢：{query}")
        retrieved = self._search_knowledge_base(query, top_k)
        summary = self._summarize_retrieved_kb(retrieved)
        return summary

