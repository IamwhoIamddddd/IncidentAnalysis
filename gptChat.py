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
from autogen import ConversableAgent
from agents.sql_agent import SQLAgent  # ✅ 請確保你已經建立這個檔案並放好 class
from agents.semantic_agent import SemanticAgent  # ✅ 請確保你已經建立這個檔案並放好 class
from agents.query_classifier_agent import QueryClassifierAgent
from agents.followup_agent import FollowUpAgent  # ✅ 請確保你已經建立這個檔案並放好 class
from utils.kb_loader import load_kb  # ✅ 請確保你已經建立這個檔案並放好函式
import json
# ----------- 全域設定 -----------
DB_PATH = "resultDB.db"  # 你在 build_kb.py 裡設定的 DB 名稱
kb_model, kb_index, kb_texts = load_kb() # 載入知識庫模型、索引和文本


# ----------- 初始化代理 -----------
classifier = QueryClassifierAgent() # ✅ 初始化查詢分類代理
sql_agent = SQLAgent() # ✅ 初始化 SQLAgent
semantic_agent = SemanticAgent(kb_model=kb_model, kb_index=kb_index, kb_texts=kb_texts) # ✅ 初始化語意代理
followup_agent = FollowUpAgent()  # ✅ 初始化追問代理


# ConversableAgent 包裝
classifier_agent = ConversableAgent(
    name="ClassifierAgent",
    llm_config={},  # 這裡不用給 LLM config，反正你只用 .generate_reply() 包 handle
    description="Classify the user's query as either a Semantic Query or a Structured SQL Query. Helps determine which agent should handle the request.",
    human_input_mode="NEVER",  # 不需要人工回覆
    code_execution_config=False,
    is_termination_msg=lambda x: True,  # 結果永遠只回 1 次
    function_map={
        "handle": classifier.handle
    }
)
sql_agent_wrapper = ConversableAgent(
    name="SQLAgent",
    llm_config={},
    description="Execute structured SQL queries on the incident database. Suitable for questions involving counts, trends, filters, and structured data summaries.",
    human_input_mode="NEVER",
    code_execution_config=False,
    is_termination_msg=lambda x: True,
    function_map={
        "handle": sql_agent.handle
    }
)
semantic_agent_wrapper = ConversableAgent(
    name="SemanticAgent",
    llm_config={},
    description="Perform semantic search using vector embeddings to retrieve similar historical incidents and suggest relevant solutions. Best for vague, context-based queries.",
    human_input_mode="NEVER",
    code_execution_config=False,
    is_termination_msg=lambda x: True,
    function_map={
        "handle": semantic_agent.handle
    }
)
followup_agent_wrapper = ConversableAgent(
    name="FollowUpAgent",
    llm_config={},
    description="Handle follow-up questions by leveraging previous context. Useful when the user refers to past queries like 'the previous one' or 'that issue you mentioned earlier'.",
    human_input_mode="NEVER",
    code_execution_config=False,
    is_termination_msg=lambda x: True,
    function_map={
        "handle": followup_agent.handle
    }
)

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
    print(f"🧠 使用模型：{model} / chat_id: {chat_id}")

    # 分類器 → AutoGen agent
    classify_result = classifier_agent.generate_reply(
        message,
        function_call="handle"
    )
    query_type = classify_result["content"] if isinstance(classify_result, dict) and "content" in classify_result else classify_result
    print(f"🔍 判斷結果：{query_type}")


    # 如果是追問查詢，直接轉交處理(尚未完成) 應該要併到 classify_query_type 裡面
    # 這裡假設追問查詢會有 chat_id，否則無法找到對應的歷史記錄
    # 在 run_offline_gpt 裡面這段改寫：
    # 追問查詢
    if followup_agent.is_follow_up(message) and chat_id:
        print("🔁 偵測為追問查詢，轉交 FollowUpAgent 處理...")
        result = followup_agent_wrapper.generate_reply(
            (chat_id, message),
            function_call="handle"
        )
        return result["content"] if isinstance(result, dict) and "content" in result else result


    # 如果是sql 結構化查詢，走sql查詢流程 
    if query_type == "Structured SQL":
        print("🧾 類型為 SQL 結構化查詢，改由 SQLAgent 處理...")
        sql_agent.set_model("deepseek-coder-v2:latest")
        result = sql_agent_wrapper.generate_reply(
            message,
            function_call="handle"
        )
        reply = result["content"] if isinstance(result, dict) and "content" in result else result
        print(f"📥 SQLAgent 回覆（前 500 字）：{reply[:500]}{'...' if len(reply) > 500 else ''}")
        if not reply:
            print("⚠️ SQLAgent 回覆為空，可能是查詢語句生成失敗")
            return "⚠️ 無法生成有效的 SQL 查詢語句。請檢查您的問題描述。"
        save_query_context(chat_id, message, query_type, result_summary=reply[:500])
        return reply
    


    # 預設為 Semantic Query
    semantic_agent.model = model  # ✅ 動態指定使用者當前選擇的模型
    print("🔄 類型為語意查詢，改由 SemanticAgent 處理...")
    result = semantic_agent_wrapper.generate_reply(
        message,
        function_call="handle"
    )
    kb_context = result["content"] if isinstance(result, dict) and "content" in result else result
    print("🧠 知識庫摘要處理完成")
    print(f"📚 知識庫檢索結果筆數：{len(kb_context)}")
    print(f"📚 知識庫摘要（前 300 字）：{kb_context[:300]}{'...' if len(kb_context) > 300 else ''}")
    if not kb_context:
        print("⚠️ 知識庫檢索結果為空，無法生成摘要")
        return "⚠️ 無法從知識庫檢索到相關資料。請嘗試更改您的問題描述。"
    print("📚 知識庫摘要完成")

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
        return reply if reply else "⚠️ 沒有收到模型回應。"

    except Exception as e:
        print(f"❌ 呼叫模型失敗：{str(e)}")
        return f"⚠️ 呼叫模型時發生錯誤：{str(e)}"
    
# -----------------------------------------------以下是註解--------------------------------------------------------
    
    
    
    
    
    




# ----------- 統計分析查詢 -----------
# def analyze_metadata_query(message):
#     print("📊 執行統計分析...")
#     print(f"📝 使用者輸入：{message}")

#     try:
#         with open("kb_metadata.json", encoding="utf-8") as f:
#             metadata = json.load(f)
#         print(f"📂 成功載入 metadata，總筆數：{len(metadata)}")
#     except Exception as e:
#         print("❌ metadata 載入錯誤")
#         return f"⚠️ 無法載入 metadata：{str(e)}"

#     system_prompt = (
#         "You are helping analyze a structured knowledge base.\n"
#         "From the user's question, choose ONE of the following fields to do statistical aggregation:\n"
#         " - subcategory\n - configurationItem\n - roleComponent\n - location\n"
#         "If the request is vague or unclear, respond with '__fallback__'.\n"
#         "Only return one word: the field name or '__fallback__'.\n"
#         "Do not return any explanation or code block. Just the field name."
#     )
#     prompt = f"{system_prompt}\n\nUser: {message}"
#     print(f"📤 發送給模型的 prompt：\n{prompt}")

#     try:
#         print("🚀 呼叫模型 phi3:mini 分析欄位...")
#         result = subprocess.run(
#             ["ollama", "run", "phi3:mini"],
#             input=prompt.encode("utf-8"),
#             capture_output=True,
#             timeout=600
#         )
#         print(f"🔚 模型回傳碼：{result.returncode}")
#         raw = result.stdout.decode("utf-8").strip()

#         # ✅ 移除 markdown 格式包裹
#         if raw.startswith("```"):
#             print("⚠️ 偵測到 markdown 包裹，嘗試移除...")
#             raw = raw.strip("`").strip()
#             if "\n" in raw:
#                 raw = "\n".join(raw.split("\n")[1:-1])

#         field = raw.strip().strip('"').strip("'").lower()  # ✅ 標準化字串
#         print(f"[欄位判斷] GPT 回覆欄位：{field}")

#         allowed_fields = {"subcategory", "configurationItem", "roleComponent", "location"}

#         if field == "__fallback__":
#             print("🔁 回傳 fallback，改為列出 subcategory 和 configurationItem 統計")
#             return "\n\n".join([
#                 summarize_field("subcategory", metadata),
#                 summarize_field("configurationItem", metadata)
#             ])

#         if field not in allowed_fields:
#             print("⚠️ 模型回傳不在允許欄位中")
#             return f"⚠️ 無法判斷要統計的欄位（回覆為：{field}）"

#         print(f"✅ 進行欄位 {field} 的統計")
#         return summarize_field(field, metadata)

#     except Exception as e:
#         print(f"❌ 呼叫模型過程發生錯誤：{str(e)}")
#         return f"⚠️ 呼叫模型分類欄位時出錯：{str(e)}"





# ----------- 統計欄位值 -----------
# def summarize_field(field, metadata):
#     print(f"📊 開始統計欄位：{field}")
#     counts = {}
#     for item in metadata:
#         key = item.get(field, "未標註")
#         counts[key] = counts.get(key, 0) + 1

#     print(f"📈 統計完成，共有 {len(counts)} 種不同值")

#     sorted_counts = sorted(counts.items(), key=lambda x: -x[1])
#     for i, (k, v) in enumerate(sorted_counts[:5]):
#         print(f"  🔢 Top{i+1}: {k} - {v} 筆")

#     result_lines = [f"{i+1}. {k}：{v} 筆" for i, (k, v) in enumerate(sorted_counts[:5])]
#     return f"📊 統計結果（依 {field}）：\n" + "\n".join(result_lines)


# ----------- 欄位值清單查詢 -----------
# def list_field_values(message):
#     print("🔍 啟動欄位值列舉任務...")
#     print(f"📝 使用者提問：{message}")

#     try:
#         with open("kb_metadata.json", encoding="utf-8") as f:
#             metadata = json.load(f)
#         print(f"📂 成功載入 metadata，筆數：{len(metadata)}")
#     except Exception as e:
#         print("❌ metadata 載入失敗")
#         return f"⚠️ Failed to load metadata: {str(e)}"

#     system_prompt = (
#         "You are a parser. The user is asking about what values are available in a certain field.\n"
#         "Please extract which field they want to list.\n"
#         "Return the field name only. Must be one of: configurationItem, subcategory, roleComponent, location"
#     )
#     prompt = f"{system_prompt}\n\nUser: {message}"
#     print(f"📤 發送給模型的 prompt：\n{prompt}")

#     try:
#         print("🧠 使用模型 phi3:mini 判斷欄位名稱...")
#         result = subprocess.run(
#             ["ollama", "run", "phi3:mini"],
#             input=prompt.encode("utf-8"),
#             capture_output=True,
#             timeout=600
#         )

#         raw_reply = result.stdout.decode("utf-8").strip()
#         print(f"[回應] GPT 回傳：{raw_reply}")

#         field = raw_reply.strip()
#         if field not in ["configurationItem", "subcategory", "roleComponent", "location"]:
#             print("⚠️ 模型回傳無效欄位")
#             return f"⚠️ Invalid field: {field}"

#         print(f"✅ 欄位判定成功：{field}")
#         values = set()
#         for item in metadata:
#             value = item.get(field)
#             if value:
#                 values.add(value)

#         print(f"📊 擷取欄位值完成，共 {len(values)} 種不同值")
#         sorted_vals = sorted(values)
#         for i, v in enumerate(sorted_vals[:5]):
#             print(f"  - Top {i+1}: {v}")

#         lines = [f"- {v}" for v in sorted_vals[:20]]
#         return f"📋 Values in '{field}' field:\n" + "\n".join(lines)

#     except Exception as e:
#         print(f"❌ 呼叫模型或解析錯誤：{str(e)}")
#         return f"⚠️ Failed to process: {str(e)}"

    


# ----------- 欄位查詢分析 -----------

# def analyze_field_query(message):
#     print("🔍 啟動多欄位條件查詢分析...")
#     print(f"📝 使用者輸入：{message}")

#     try:
#         with open("kb_metadata.json", encoding="utf-8") as f:
#             metadata = json.load(f)
#         print(f"📂 成功載入 metadata，總筆數：{len(metadata)}")
#     except Exception as e:
#         print(f"❌ metadata 載入失敗：{str(e)}")
#         return f"⚠️ Failed to load metadata: {str(e)}"

#     # ✅ 取得合法值清單（限制模型輸出）
#     allowed_fields = ["configurationItem", "subcategory", "roleComponent", "location"]
#     valid_values = {
#         field: sorted(set(str(item.get(field, "")).strip() for item in metadata if item.get(field)))
#         for field in allowed_fields
#     }
#     value_hint = "\n".join([f"{field}: {valid_values[field]}" for field in allowed_fields])

#     system_prompt = (
#         "You are a parser. Extract all field=value conditions from the user's message for filtering.\n"
#         "Only include fields: configurationItem, subcategory, roleComponent, location.\n"
#         "Use only values from these lists:\n"
#         f"{value_hint}\n"
#         "Return ONLY a raw JSON array like:\n"
#         '[{"field": "subcategory", "value": "Login/Access"}, {"field": "location", "value": "Taipei"}]\n'
#         "Do not include any explanation or markdown formatting.\n"
#         "The entire output must be a compact JSON array and must not exceed 500 characters in total."
#     )

#     prompt = f"{system_prompt}\n\nUser: {message}"
#     print(f"📤 發送給模型的 prompt：\n{prompt}")

#     try:
#         print("🧠 呼叫模型 phi3:mini 判斷過濾欄位條件...")
#         result = subprocess.run(
#             ["ollama", "run", "phi3:mini"],
#             input=prompt.encode("utf-8"),
#             capture_output=True,
#             timeout=600
#         )
#         raw = result.stdout.decode("utf-8").strip()
#         print("[🔍 多欄位查詢原始回覆]", raw)

#     # ✅ 去除 markdown 包裹與標籤干擾
#         if "```" in raw:
#             print("⚠️ 偵測到 markdown 格式，正在清理...")
#             raw = raw.split("```")[1].strip()
#         if raw.startswith("json"):
#             raw = raw[len("json"):].strip()

#         print("📥 清理後的 JSON 字串：", raw)

#         # ✅ 嘗試從原始字串中擷取合法 JSON 陣列
#         match = re.search(r'\[\s*{.*?}\s*\]', raw, re.DOTALL)
#         if not match:
#             return "⚠️ Failed to extract valid JSON array from model output."
#         json_part = match.group(0)

#         try:
#             parsed_conditions = json.loads(json_part)
#             print(f"✅ 成功解析為 JSON 陣列，共 {len(parsed_conditions)} 筆條件")
#         except Exception as e:
#             print(f"❌ JSON 解析失敗：{e}")
#             return f"⚠️ JSON decode error: {str(e)}"


#         if not isinstance(parsed_conditions, list):
#             print("❌ 解析結果非 list 格式")
#             return "⚠️ Invalid parsed result format (not a list)."

#         filters = [(c["field"], c["value"]) for c in parsed_conditions if c.get("field") in allowed_fields]

#         print("🔎 過濾後的有效條件：")
#         for f, v in filters:
#             print(f"  • {f} = {v}")

#         if not filters:
#             print("⚠️ 沒有擷取到有效條件")
#             return "⚠️ No valid filters extracted from the query."

#         # 篩選資料（符合所有條件，大小寫不敏感，空白容錯）
#         def match_all(item):
#             for field, value in filters:
#                 actual = str(item.get(field, "")).strip().lower()
#                 expected = str(value).strip().lower()
#                 if expected not in actual:  # ✅ 改為模糊比對
#                     return False
#             return True

#         matches = [item for item in metadata if match_all(item)]

#         print(f"📊 符合條件的結果筆數：{len(matches)}")

#         if not matches:
#             print("📭 查無結果")
#             return f"🔍 No results found for: " + " AND ".join([f"{f}={v}" for f, v in filters])

#         lines = [f"- {item.get('text', '')[:500]}" for item in matches[:5]]
#         # 🔁 從 matches 中取出實際命中的原始值
#         actual_values = {field: set() for field, _ in filters}
#         for item in matches:
#             for field, _ in filters:
#                 val = item.get(field, "").strip()
#                 if val:
#                     actual_values[field].add(val)

#         summary_lines = [
#             f"• {field} = {', '.join(sorted(actual_values[field])) or 'N/A'}"
#             for field in actual_values
#         ]

#         return (
#             "🔎 Top matches for:\n" +
#             "\n".join(summary_lines) +
#             "\n\n" + "\n".join(lines)
#         )
    
#     except Exception as e:
#         print(f"❌ 呼叫模型或解析過程出錯：{str(e)}")
#         return f"⚠️ Failed to parse or search: {str(e)}"




# ----------- 時間趨勢分析 -----------
# def analyze_temporal_trend(message):
#     print("📈 啟動時間趨勢分析...")
#     print(f"📝 使用者輸入：{message}")

#     try:
#         with open("kb_metadata.json", encoding="utf-8") as f:
#             metadata = json.load(f)
#         print("📦 第一筆資料：", metadata[0])
#         print("🔍 是否有 analysisTime 欄位：", "analysisTime" in metadata[0])
#         print(f"📂 成功載入 metadata，總筆數：{len(metadata)}")
#     except Exception as e:
#         print(f"❌ metadata 載入失敗：{str(e)}")
#         return f"⚠️ 無法載入資料：{str(e)}"

#     if not metadata:
#         print("⚠️ metadata 為空")
#         return "⚠️ 無資料可分析。"

#     if "analysisTime" not in metadata[0]:
#         print("⚠️ analysisTime 欄位不存在")
#         return "⚠️ 缺少 analysisTime 欄位，無法分析趨勢。"

#     print("🧪 開始轉換為 DataFrame 並處理時間欄位...")
#     df = pd.DataFrame(metadata)
#     print(f"📊 DataFrame 欄位：{list(df.columns)}")

#     df["analysisTime"] = pd.to_datetime(df["analysisTime"], errors="coerce")
#     initial_len = len(df)
#     df = df.dropna(subset=["analysisTime"])
#     print(f"🧹 處理無效時間後，剩餘筆數：{len(df)} / 原始 {initial_len}")

#     print("📆 建立月份欄位並計算每月數量...")
#     df["month"] = df["analysisTime"].dt.to_period("M")
#     trend = df.groupby("month").size()
#     print("📊 每月統計結果：")
#     for month, count in trend.items():
#         print(f"  • {month}: {count} 筆")

#     # ✅ 用文字敘述每月趨勢
#     summary_lines = ["📊 每月案件趨勢："]
#     for month, count in trend.items():
#         summary_lines.append(f"- {month.strftime('%Y-%m')}: {count} 筆")
#     print("✅ 已轉換為純文字描述")

#     return "\n".join(summary_lines)

    
    
    
# ----------- 解法統整 -----------
# def summarize_solutions(message):
#     print("🛠️ 啟動相似案例處理方案摘要流程...")
#     print(f"📝 使用者輸入：{message}")

#     try:
#         with open("kb_metadata.json", encoding="utf-8") as f:
#             metadata = json.load(f)
#         print(f"📂 成功載入 metadata，筆數：{len(metadata)}")
#     except Exception as e:
#         print(f"❌ metadata 載入失敗：{str(e)}")
#         return f"⚠️ Failed to load metadata: {str(e)}"

#     print("🔍 開始語意比對相關案例...")
#     related_cases = search_knowledge_base(message, top_k=5)
#     print(f"🧠 取得相似片段數量：{len(related_cases)}")
#     for i, r in enumerate(related_cases, 1):
#         print(f"  {i}. {r[:60]}{'...' if len(r) > 60 else ''}")

#     if not related_cases:
#         print("⚠️ 無相關案例")
#         return "⚠️ No similar cases found to extract solutions."

#     print("📦 擷取相關案例中的解決方案...")
#     solutions = []
#     for item in metadata:
#         text = item.get("text", "")
#         if any(snippet in text for snippet in related_cases):
#             solution = item.get("solution", "")
#             if solution:
#                 solutions.append(solution)

#     print(f"✅ 擷取到 solution 數量：{len(solutions)}")
#     if not solutions:
#         print("⚠️ 無對應解決方案欄位")
#         return "⚠️ No resolution data found for related cases."

#     print("📝 組裝 prompt 進行 GPT 統整...")
#     prompt = "Please summarize the following resolution steps into a brief, clear list:\n\n"
#     prompt += "\n---\n".join(solutions[:10])
#     prompt += "\n\nSummary:"

#     print("📤 發送 prompt 給模型（前 300 字）：")
#     print(prompt[:300] + ("..." if len(prompt) > 300 else ""))

#     try:
#         result = subprocess.run(
#             ["ollama", "run", "phi4"],
#             input=prompt.encode("utf-8"),
#             capture_output=True,
#             timeout=600
#         )
#         output = result.stdout.decode("utf-8").strip()
#         print("✅ 模型成功回應（前 200 字）：")
#         print(output[:200] + ("..." if len(output) > 200 else ""))
#         return output

#     except Exception as e:
#         print(f"❌ 模型摘要失敗：{str(e)}")
#         return f"⚠️ Failed to summarize solutions: {str(e)}"
    
    
    

    # if query_type == "Statistical Analysis":
    #     print("📊 類型為統計分析，開始處理...")
    #     reply = analyze_metadata_query(message)
    #     print("📦 統計分析完成，摘要前 200 字：", reply[:200])
    #     save_query_context(chat_id, message, query_type, result_summary=reply[:200])
    #     return reply

    # if query_type == "Field Filter":
    #     print("🔄 類型為欄位過濾，開始進行過濾...")
    #     reply = analyze_field_query(message)
    #     print("📦 過濾查詢完成，前 200 字：", reply[:200])
    #     filters = []
    #     for line in reply.splitlines():
    #         if line.strip().startswith("• "):
    #             try:
    #                 field_part = line.replace("•", "").strip()
    #                 field, value = field_part.split("=", 1)
    #                 filters.append({"field": field.strip(), "value": value.strip()})
    #             except Exception as e:
    #                 print(f"⚠️ 無法解析條件行：{line}，錯誤：{e}")
    #                 continue
    #     print("🧾 擷取到的 filters：", filters)
    #     save_query_context(chat_id, message, query_type, filter_info=filters if filters else None, result_summary=reply[:200])
    #     return reply

    # if query_type == "Field Values":
    #     print("📋 類型為欄位值清單，開始列出欄位值...")
    #     reply = list_field_values(message)
    #     print("📦 欄位值查詢完成，前 200 字：", reply[:200])
    #     save_query_context(chat_id, message, query_type, result_summary=reply[:200])
    #     return reply

    # if query_type == "Temporal Trend":
    #     print("📈 類型為時間趨勢查詢，開始繪製圖表...")
    #     reply = analyze_temporal_trend(message)
    #     print("📦 趨勢圖完成（HTML 片段）")
    #     save_query_context(chat_id, message, query_type, result_summary=reply[:200])
    #     return reply

    # if query_type == "Solution Summary":
    #     print("🛠 類型為解法統整，開始彙整處理方式...")
    #     reply = summarize_solutions(message)
    #     print("📦 解法統整完成，前 200 字：", reply[:200])
    #     save_query_context(chat_id, message, query_type, result_summary=reply[:200])
    #     return reply

