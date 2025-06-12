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
from agents.sql_agent import SQLAgent  # ✅ 請確保你已經建立這個檔案並放好 class
from agents.semantic_agent import SemanticAgent  # ✅ 請確保你已經建立這個檔案並放好 class
from agents.query_classifier_agent import QueryClassifierAgent
from agents.followup_agent import FollowUpAgent  # ✅ 請確保你已經建立這個檔案並放好 class
from utils.kb_loader import load_kb  # ✅ 請確保你已經建立這個檔案並放好函式
import json
# ----------- 全域設定 -----------
DB_PATH = "resultDB.db"  # 你在 build_kb.py 裡設定的 DB 名稱
kb_model, kb_index, kb_texts = load_kb() # 載入知識庫模型、索引和文本
classifier = QueryClassifierAgent() # ✅ 初始化查詢分類代理
sql_agent = SQLAgent() # ✅ 初始化 SQLAgent
semantic_agent = SemanticAgent(kb_model=kb_model, kb_index=kb_index, kb_texts=kb_texts) # ✅ 初始化語意代理
followup_agent = FollowUpAgent()  # ✅ 初始化追問代理

# ----------- 儲存查詢上下文 -----------
def save_query_context(chat_id, query, result_type, filter_info=None, result_summary=None):
    filepath = f"chat_history/{chat_id}.json"
    print(f"📁 嘗試讀取對話記錄檔：{filepath}")

    # 嘗試讀取對話歷史
    try:
        with open(filepath, encoding="utf-8") as f:
            history = json.load(f)
        if not isinstance(history, list):
            print("⚠️ 記錄格式錯誤（非 list），重新初始化歷史")
            history = []
        else:
            print(f"📖 成功讀取歷史記錄，現有筆數：{len(history)}")
    except Exception as e:
        print(f"⚠️ 無法讀取歷史，初始化為空：{e}")
        history = []

    # 準備 context 內容
    context = {
        "type": result_type,
        "query": query,
        "filters": filter_info,
        "summary": result_summary
    }
    print(f"🧠 準備儲存的 context：{context}")

    # 若無歷史，建立佔位對話
    if not history:
        print("📌 尚無對話歷史，自動新增一則佔位訊息並附加 context。")
        history.append({
            "role": "user",
            "content": query,
            "context": context
        })
    else:
        print("🔁 已有歷史，將 context 寫入最後一則對話...")
        history[-1]["context"] = context

    # 顯示將要寫入的完整歷史
    print("📦 即將儲存的完整歷史內容預覽（最後 1 筆）：")
    print(json.dumps(history[-1], ensure_ascii=False, indent=2))

    # 儲存回 JSON 檔案
    try:
        os.makedirs("chat_history", exist_ok=True)  # 確保資料夾存在
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        print(f"✅ 已成功寫入檔案：{filepath}")
    except Exception as e:
        print(f"❌ 儲存記憶失敗：{e}")




# ----------- GPT 主函式 -----------
def run_offline_gpt(message, model="orca2:13b", history=[], chat_id=None):
    print("🟢 啟動 GPT 回答流程...")
    print(f"📝 使用者輸入：{message}")
    print(f"🧠 chat_id: {chat_id}")
    print("------------------------------------------------------------------開始分類---------------------------------------------------------------------------------")
    query_type = classifier.handle(message)
    print("------------------------------------------------------------------結束分類---------------------------------------------------------------------------------")
    print(f"🔍 判斷結果：{query_type}")
    # 如果是追問查詢，直接轉交處理(尚未完成) 應該要併到 classify_query_type 裡面
    # 這裡假設追問查詢會有 chat_id，否則無法找到對應的歷史記錄
    # 在 run_offline_gpt 裡面這段改寫：
    print("------------------------------------------------------------------開始判斷是否為追問查詢---------------------------------------------------------------------------------")
    if followup_agent.is_follow_up(message) and chat_id:
        print("🔁 偵測為追問查詢，轉交 FollowUpAgent 處理...")
        return followup_agent.handle(chat_id, message)
    print("------------------------------------------------------------------結束判斷是否為追問查詢---------------------------------------------------------------------------------")
    # 如果是sql 結構化查詢，走sql查詢流程
    print("------------------------------------------------------------------開始判斷是否為 SQL 結構化查詢---------------------------------------------------------------------------------")
    if query_type == "Structured SQL":        
        print("🧾 類型為 SQL 結構化查詢，改由 SQLAgent 處理...")
        sql_agent.set_model("deepseek-coder-v2:latest")  # ✅ 設定 SQLAgent 使用的模型
        print("🧠 使用 SQLAgent 處理查詢...")
        reply = sql_agent.handle(message)
        print(f"📥 SQLAgent 回覆（前 500 字）：{reply[:500]}{'...' if len(reply) > 500 else ''}")
        if not reply:
            print("⚠️ SQLAgent 回覆為空，可能是查詢語句生成失敗")
            return "⚠️ 無法生成有效的 SQL 查詢語句。請檢查您的問題描述。"
        print("------------------------------------------------------------------結束 SQL 結構化查詢處理---------------------------------------------------------------------------------")
        # ✅ 記得存回查詢紀錄
        save_query_context(chat_id, message, query_type, result_summary=reply[:500])
        return reply
    # 預設為 Semantic Query
    print("------------------------------------------------------------------開始判斷是否為語意查詢---------------------------------------------------------------------------------")
    semantic_agent.model = model  # ✅ 動態指定使用者當前選擇的模型
    print("🔄 類型為語意查詢，改由 SemanticAgent 處理...")
    kb_context = semantic_agent.handle(message)
    print("🧠 知識庫摘要處理完成")
    print(f"📚 知識庫檢索結果筆數：{len(kb_context)}")
    print(f"📚 知識庫摘要（前 300 字）：{kb_context[:300]}{'...' if len(kb_context) > 300 else ''}")
    if not kb_context:
        print("⚠️ 知識庫檢索結果為空，無法生成摘要")
        return "⚠️ 無法從知識庫檢索到相關資料。請嘗試更改您的問題描述。"
    print("📚 知識庫摘要完成")
    print("------------------------------------------------------------------結束語意查詢---------------------------------------------------------------------------------")
    


    print("------------------------------------------------------------------開始把訊息做組合---------------------------------------------------------------------------------")
    # 組合對話歷史
    context = ""
    if not isinstance(history, list):
        print("⚠️ 對話歷史格式錯誤，初始化為空 list")
        history = []
    # 僅取最後 5 筆
    # 根據前幾輪的對話紀錄 history，組合成一段文字 context，讓模型能看懂上下文脈絡（多輪對話）。
    for turn in history[-5:]:
        
        role = "User" if turn["role"] == "user" else "Assistant" # 將 role 轉為 User/Assistant
        context += f"{role}: {turn['content']}\n" # 僅取最後 5 筆

    prompt = (
        "You are a knowledgeable helpdesk assistant. "
        "You will first review some relevant case entries, then answer the user's question based on context and your reasoning.\n\n"
        
        "==== [Retrieved Knowledge Base Entries] ====\n"
        f"{kb_context.strip()}\n\n"
        
        "==== [Conversation History] ====\n"
        f"{context.strip()}\n"
        
        "==== [User's Current Question] ====\n"
        f"User: {message}\n"
        
        "==== [Your Response] ====\n"
        "Assistant:"
    )
    print("\n[Prompt Preview] 🧾 發送給模型的 Prompt 前 300 字：")
    print(prompt[:300] + ("..." if len(prompt) > 300 else ""))
    try:
        print("🚀 發送 prompt 給模型中...")
        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt.encode("utf-8"),
            capture_output=True,
            timeout=600
        )

        if result.returncode != 0:
            err = result.stderr.decode('utf-8')
            print("❌ 模型錯誤：", err)
            return f"⚠️ Ollama 錯誤：{err}"

        reply = result.stdout.decode("utf-8").strip()
        print("📥 模型回覆（前 300 字）：")
        print(reply[:300] + ("..." if len(reply) > 300 else ""))

        save_query_context(chat_id, message, query_type, result_summary=reply[:200])
        print("------------------------------------------------------------------結束處理---------------------------------------------------------------------------------")
        return reply if reply else "⚠️ 沒有收到模型回應。"

    except Exception as e:
        print(f"❌ 呼叫模型失敗：{str(e)}")
        return f"⚠️ 呼叫模型時發生錯誤：{str(e)}"
    