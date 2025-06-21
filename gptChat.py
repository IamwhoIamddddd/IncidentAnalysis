

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
import hashlib
from autogen_core.tools import FunctionTool
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.ollama import OllamaChatCompletionClient
from autogen_agentchat.ui import Console
from autogen_core import ClosureAgent,ClosureContext,DefaultSubscription, MessageContext, SingleThreadedAgentRuntime
from datetime import datetime

# ----------- 全域設定 -----------
POWERAUTOMATE_URL = "https://prod-08.southeastasia.logic.azure.com:443/workflows/a9de89a708674755923e900665994521/triggers/manual/paths/invoke?api-version=2016-06-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=Eo8rgY9JHLAqYDQCYTjWYiufiHq3LYQ_kZXWmGjqLhw"  # 🔁 請換成你的實際網址

DB_PATH = "resultDB.db"  # 你在 build_kb.py 裡設定的 DB 名稱
# ✅ 載入 metadata（若不存在則為空）
metadata_path = "kb_metadata.json"

metadata_path = "kb_metadata.json"
if os.path.exists(metadata_path):
    with open(metadata_path, encoding="utf-8") as f:
        metadata = json.load(f)
    print("📦 成功載入 kb_metadata.json")
else:
    metadata = []
    print("⚠️ 找不到 kb_metadata.json，將使用空 metadata")

# ✅ 建立 FAISS ID → 原始文字句子 的對照表
faiss_id_to_text = {
    int(hashlib.sha256(item["id"].encode("utf-8")).hexdigest(), 16) % (1 << 63): item["text"]
    for item in metadata if "id" in item and "text" in item
}

kb_model, kb_index, kb_texts = load_kb() # 載入知識庫模型、索引和文本
classifier = QueryClassifierAgent() # ✅ 初始化查詢分類代理
sql_agent = SQLAgent() # ✅ 初始化 SQLAgent
semantic_agent = SemanticAgent(
    kb_model=kb_model, 
    kb_index=kb_index, 
    kb_texts=kb_texts, 
    metadata=metadata, 
    faiss_id_to_text=faiss_id_to_text
) # ✅ 初始化語意代理
followup_agent = FollowUpAgent()  # ✅ 初始化追問代理



# ----------- 以下開始嘗試用AutoGen -----------

# 全域變數（或設一個 class property）
_last_autogen_result = None


def semantic_agent_handle(message: str) -> str:
    """
    Invokes the SemanticAgent to perform semantic retrieval and synthesis based on the user's natural language question.

    This function accepts a single message as input and:
      - Encodes the question using a sentence-transformer model.
      - Searches a FAISS vector index and SQLite database for the most relevant historic case records, dynamically determining the number of matches to retrieve based on query specificity.
      - Groups and summarizes multiple retrieved records using a local LLM (with automatic model fallback and chunked/recursive summarization to handle token limits).
      - Returns a synthesized summary of key findings, typical solutions, or recurring incident patterns in plain text.

    Use this function when the user request is in natural language and requires semantic understanding, case similarity search, incident clustering, or aggregation of unstructured problem/solution experiences.

    Parameters:
        message (str): The user's question or problem statement in natural language.

    Returns:
        str: An LLM-generated summary or best-practice overview synthesized from the most relevant historic cases.

    Example:
        reply = semantic_agent_handle("What are common solutions for Teams connectivity issues in the past six months?")
        print(reply)
    """
    global _last_autogen_result
    result =  semantic_agent.handle(message)
    _last_autogen_result = result  # 儲存最後一次結果
    print(f"🔍 SemanticAgent 處理結果：{result[:1000]}{'...' if len(result) > 1000 else ''}")
    return result


def sql_agent_handle(message: str) -> str:
    """
    Invokes the SQLAgent to handle structured data requests based on a user's natural language query.

    This function:
      - Uses an LLM to decompose the user's question into a SQL query prompt and an analysis prompt.
      - Generates an appropriate SQL query to aggregate or summarize data from a SQLite database of case records.
      - Executes the SQL query and retrieves structured results as a pandas DataFrame.
      - Optionally summarizes large query results in multiple chunks using an LLM, then recursively merges these summaries for a concise overview.
      - Returns a combined human-readable summary and a model-generated insight covering statistics, trends, or patterns found in the data.

    Use this function for queries involving statistics, record counts, field-based filtering, database aggregation, or when the user's intent is to obtain structured, tabular, or quantitative information.

    Parameters:
        message (str): The user's question or command describing the data requirement in natural language.

    Returns:
        str: Combined summary and LLM-generated analysis of the queried data, suitable for direct presentation or reporting.

    Example:
        reply = sql_agent_handle("Show the number of incidents by subcategory for the past year")
        print(reply)
    """
    global _last_autogen_result
    # 呼叫 SQLAgent 處理 SQL 查詢
    result = sql_agent.handle(message)
    _last_autogen_result = result  # 儲存最後一次結果
    print(f"🔍 SQLAgent 處理結果：{result[:1000]}{'...' if len(result) > 1000 else ''}")
    return result


def get_last_autogen_result():
    return _last_autogen_result


sql_tool = FunctionTool(
    func=sql_agent_handle,
    name="SQLAgentTool",
    description="Handles requests for structured data, such as statistical summaries, filtering records by specific fields, or generating tables from the database."
)

semantic_tool = FunctionTool(
    func=semantic_agent_handle,
    name="SemanticAgentTool",
    description="Handles requests stated in natural language to retrieve similar past incidents, summarize multiple case solutions, or provide insights based on previous experience."
)


# AutoGen Agent 設定
# 這裡使用 OllamaChatCompletionClient 作為模型客戶端
ollama_client = OllamaChatCompletionClient(
    model="mistral-nemo:latest"
)

classifier_agent = AssistantAgent(
    name="Classifier",
    model_client=ollama_client,
    tools=[sql_tool, semantic_tool],
    system_message=(
            "You are a classification assistant. Your task is to analyze the user's question and classify it as one of the following two types:\n\n"
            "1. Semantic Query – The user is seeking similar past incidents, solution suggestions, or insights based on previous case knowledge.\n"
            "   Typical intents: find related issues, ask how a problem was resolved, request examples of solutions.\n\n"
            "2. Structured SQL – The user is requesting structured or statistical data, such as record counts, field value filtering, time-based trends, or aggregated summaries.\n"
            "   Typical intents: show number of records, list unique values, filter by conditions, summarize results over time.\n\n"
            "Respond with exactly one of the following labels (no explanations):\n"
            "'SemanticAgentTool' or 'SQLAgentTool'."
    )
)

# 用 UserProxy 代表人類使用者
user_proxy = UserProxyAgent(name="user_proxy")
team = RoundRobinGroupChat([classifier_agent, user_proxy], max_turns=2)


async def autogen_dispatch(message):
    # 直接丟訊息給 classifier_agent，讓他自動分類並調用工具
    stream = classifier_agent.run_stream(
        task=message,
    )
    # result.summary 就是 SQLAgent 或 SemanticAgent 的回傳內容
    await Console(stream)  # 顯示對話過程（如需要）

    return get_last_autogen_result()  # 回傳最後一次的結果

# ----------- AutoGen Agent 設定結束 -----------

# -----------------------------------------------------------------------------------------------------------
# ----------- 儲存查詢上下文 -----------

def save_query_context(chat_id, query, result_type, filter_info=None, result_summary=None):
    filepath = f"chat_history/{chat_id}.json"
    print(f"📁 嘗試讀取對話記錄檔：{filepath}")

    try:
        with open(filepath, encoding="utf-8") as f:
            chat_data = json.load(f)

        if not isinstance(chat_data, dict) or "history" not in chat_data or not isinstance(chat_data["history"], list):
            print("⚠️ chat 記錄格式錯誤，重新初始化")
            chat_data = {
                "id": chat_id,
                "title": chat_id,
                "edit_title": "",
                "model": "unknown",
                "timestamp": datetime.now().isoformat(),
                "history": []
            }
        else:
            print(f"📖 成功讀取歷史記錄，現有筆數：{len(chat_data['history'])}")
    except Exception as e:
        print(f"⚠️ 無法讀取歷史，初始化為空：{e}")
        chat_data = {
            "id": chat_id,
            "title": chat_id,
            "edit_title": "",
            "model": "unknown",
            "timestamp": datetime.now().isoformat(),
            "history": []
        }

    context = {
        "type": result_type,
        "query": query,
        "filters": filter_info,
        "summary": result_summary
    }
    print(f"🧠 準備儲存的 context：{context}")

    if not chat_data["history"]:
        print("📌 尚無對話歷史，自動新增一則佔位訊息並附加 context。")
        chat_data["history"].append({
            "role": "user",
            "content": query,
            "context": context
        })
    else:
        print("🔁 已有歷史，將 context 寫入最後一則對話...")
        chat_data["history"][-1]["context"] = context

    print("📦 即將儲存的完整歷史內容預覽（最後 1 筆）：")
    print(json.dumps(chat_data["history"][-1], ensure_ascii=False, indent=2))

    try:
        os.makedirs("chat_history", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(chat_data, f, ensure_ascii=False, indent=2)
        print(f"✅ 已成功寫入檔案：{filepath}")
    except Exception as e:
        print(f"❌ 儲存記憶失敗：{e}")

# -----------------------------------------------------------------------------------------------------------

async def run_offline_gpt(message, model="orca2:13b", history=[], chat_id=None):
    print("🟢 啟動 GPT 回答流程...")
    print(f"📝 使用者輸入：{message}")
    print(f"🧠 chat_id: {chat_id}")

    if followup_agent.is_follow_up(message) and chat_id:
        print("🔁 偵測為追問查詢，轉交 FollowUpAgent 處理...")
        return followup_agent.handle(chat_id, message)

    try:
        kb_context = await autogen_dispatch(message)
    except Exception as e:
        print(f"❌ autogen_dispatch 發生錯誤：{e}")
        kb_context = ""

    print("🧠 知識庫摘要處理完成")
    print(f"📚 知識庫摘要（前 1000 字）：{kb_context[:1000]}{'...' if len(kb_context) > 1000 else ''}")

    # 整理對話歷史
    context = ""
    if not isinstance(history, list):
        print("⚠️ 對話歷史格式錯誤，初始化為空 list")
        history = []
    for turn in history[-2:]:
        role = "User" if turn["role"] == "user" else "Assistant"
        context += f"{role}: {turn['content']}\n"

    # 建立 PowerAutomate 專用 Prompt（分開 template + userInput）
    template = (
        "You are a knowledgeable helpdesk assistant. "
        "You will first review some relevant case entries, then answer the user's question based on context and your reasoning.\n\n"
        "Please limit your answer to no more than 1000 English words.\n\n"
        "==== [Retrieved Knowledge Base Entries] ====\n"
    )

    user_input_section = (
        f"{kb_context.strip()}\n\n"
        "==== [Conversation History] ====\n"
        f"{context.strip()}\n"
        "==== [User's Current Question] ====\n"
        f"User: {message}\n"
        "==== [Your Response] ====\n"
        "Assistant:"
    )

    full_prompt = template + user_input_section

    print("\n[Prompt Preview] 🧾 發送給模型的 Prompt 前 5000 字：")
    print(full_prompt[:5000] + ("..." if len(full_prompt) > 5000 else ""))
    print("testing")

    try:
        print("📡 傳送 prompt 至 Power Automate...")
        payload = {
            "template": template,
            "userInput": user_input_section
        }
        res = requests.post(POWERAUTOMATE_URL, json=payload, timeout=360)
        if res.status_code == 200:
            reply = res.json().get("response", "").strip()
            print("📥 AI Builder 回應（前 1000 字）：")
            print(reply[:1000] + ("..." if len(reply) > 1000 else ""))
            if reply:
                save_query_context(chat_id, message, "RAG-Integrated", result_summary=reply)
                return reply
            else:
                print("⚠️ AI Builder 回應為空，將進行 fallback")
        else:
            print(f"❌ AI Builder 回應錯誤，狀態碼：{res.status_code}")
    except Exception as e:
        print(f"❌ AI Builder 呼叫失敗或逾時：{e}")

    # ✅ fallback：本地 ollama 模型推論
    try:
        print("🚀 發送 prompt 給本地模型中...")
        result = subprocess.run(
            ["ollama", "run", model],
            input=full_prompt.encode("utf-8"),
            capture_output=True,
            timeout=600
        )
        if result.returncode != 0:
            err = result.stderr.decode('utf-8')
            print("❌ 模型錯誤：", err)
            return f"⚠️ Ollama 錯誤：{err}"

        reply = result.stdout.decode("utf-8").strip()
        print("📥 模型回覆（前 1000 字）：")
        print(reply[:1000] + ("..." if len(reply) > 1000 else ""))

        save_query_context(chat_id, message, "RAG-Integrated", result_summary=reply)
        print("------------------------------------------------------------------結束處理---------------------------------------------------------------------------------")
        return reply if reply else "⚠️ 沒有收到模型回應。"

    except Exception as e:
        print(f"❌ 呼叫模型失敗：{str(e)}")
        return f"⚠️ 呼叫模型時發生錯誤：{str(e)}"



