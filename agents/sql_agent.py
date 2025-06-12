# sql_agent.py
import subprocess
import re
import sqlite3
import pandas as pd



class SQLAgent:
    def __init__(self, model="deepseek-coder-v2:latest", db_path="resultDB.db"):
        self.model = model
        self.db_path = db_path
        print(f"🔧 [SQLAgent] 初始化，使用模型：{self.model}，資料庫路徑：{self.db_path}")
    
    def set_model(self, model_name):
        self.model = model_name
        print(f"✅ [SQLAgent] 模型已更新為：{self.model}")
        
        
        
        
        # 拆解問題並分成兩部分，並使用 LLM 處理
    def _split_user_question(self, message):
        # LLM 用來根據使用者的問題拆解為兩個部分
        prompt = (
            "You are an expert assistant. Based on the user's question, split the task into two parts:\n\n"
            "1. **SQL Query Prompt**:\n"
            "- Generate a prompt for another LLM to create a SQL query.\n"
            "- Use aggregation functions (e.g., COUNT, GROUP BY) to summarize data based on broad categories.\n"
            "- Do not include any filtering conditions (e.g., WHERE clauses), unless explicitly requested by the user.\n\n"
            "2. **Analysis Prompt**:\n"
            "- Create a prompt for another LLM to analyze the SQL query results.\n"
            "- Describe the user's intent (e.g., trends, insights, summarization).\n"
            "- Provide instructions on interpreting the results and deriving insights.\n"
            "- Suggest trends, anomalies, or patterns if applicable.\n\n"
            "Return both prompts separately, labeled as 'SQL Query Prompt' and 'Analysis Prompt'."
        )


        # 在提示語句中加入使用者問題
        print("📝 [SQLAgent] 構造拆解問題的提示語句...")
        prompt = f"{prompt}\n\nUser Question: {message}\n\n"

        # 呼叫 LLM 來拆解問題並生成兩個部分
        try:
            print("🚀 發送拆解問題的提示到 LLM...")
            result = subprocess.run(
                ["ollama", "run", self.model],
                input=prompt.encode("utf-8"),
                capture_output=True,
                timeout=600
            )
            if result.returncode == 0:
                response = result.stdout.decode("utf-8").strip()
                print("✅ LLM 回應：", response)
                # 假設 LLM 會返回兩個部分，分別是 SQL 查詢提示與分析提示
                sql_query_prompt = ""
                analysis_prompt = ""
                
                # 抽取 SQL 查詢提示與分析提示
                if "SQL Query Prompt" in response and "Analysis Prompt" in response:
                    sql_query_prompt = response.split("SQL Query Prompt")[1].split("Analysis Prompt")[0].strip()
                    analysis_prompt = response.split("Analysis Prompt")[1].strip()

                return sql_query_prompt, analysis_prompt
            else:
                print("❌ LLM 錯誤：", result.stderr.decode("utf-8"))
                return None, None
        except Exception as e:
            print(f"❌ 呼叫 LLM 發生錯誤：{str(e)}")
            return None, None

    # SQL 查詢生成與執行 
    def _build_prompt(self, user_question):
        schema_info = """
        You are an expert data analyst.

        You are working with the following SQLite table named 'metadata':

        Columns:
        - id (integer): internal ID
        - text (text): full case description, includes issue and solution
        - subcategory (text): issue type, such as 'Login', 'Teams', etc.
        - configurationItem (text): module or system component
        - roleComponent (text): affected user role or feature
        - location (text): site or region where issue occurred
        - analysisTime (text): ISO timestamp when the issue was recorded
        - solution (text): solution text or resolution for the case

        Please write an SQL query (SELECT ...) that provides aggregated information based on the columns. 
        Do not include any filtering conditions or WHERE clauses. The query should focus on summarizing data across broad categories.
        Return only the SQL query, no explanation or formatting.
        """

        
        print("📝 [SQLAgent] 構造 SQL 提示語句...")
        prompt = f"{schema_info}\n\nUser question: {user_question}\nSQL:"
        return prompt
    

    # 產生 SQL 查詢語句
    def _generate_sql(self, prompt):
        print("🧠 [SQLAgent] 嘗試使用 LLM 產生 SQL 查詢語句...")
        print(f"📝 Prompt 輸入：{prompt}")
        print("使用模型：", self.model)
        if not prompt.strip():
            print("⚠️ 提示語句為空，無法產生 SQL")
            return None
        try:
            print("🚀 呼叫模型產生 SQL 中...")
            result = subprocess.run(
                ["ollama", "run", self.model],
                input=prompt.encode("utf-8"),
                capture_output=True,
                timeout=600
            )

            if result.returncode != 0:
                err = result.stderr.decode("utf-8")
                print("❌ 模型錯誤：", err)
                return None

            output = result.stdout.decode("utf-8").strip()
            print("📥 模型產出（前 200 字）：", output[:200])
            return output

        except Exception as e:
            print(f"❌ 呼叫 LLM 失敗：{str(e)}")
            return None
        
    # 抽取 SQL 指令
    def _extract_sql(self, text):
        print("🔍 [SQLAgent] 嘗試從模型回應中萃取 SQL 指令...")

        # 嘗試抓 ```sql 區塊
        code_block_match = re.search(r"```sql\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if code_block_match:
            sql_code = code_block_match.group(1).strip()
            print("✅ 偵測到 ```sql 區塊，成功抽取 SQL。")
            return sql_code

        # 否則抓第一段 SELECT 語句
        select_match = re.search(r"(SELECT\s.+?;)", text, re.IGNORECASE | re.DOTALL)
        if select_match:
            sql_code = select_match.group(1).strip()
            print("✅ 成功抽取 SELECT 開頭的 SQL。")
            return sql_code

        # fallback：抓包含 FROM 的段落
        fallback_match = re.search(r"(SELECT.+FROM.+?)(\n|$)", text, re.IGNORECASE | re.DOTALL)
        if fallback_match:
            sql_code = fallback_match.group(1).strip()
            print("⚠️ 從 fallback 抽取 SQL 成功（但可能不完整）。")
            return sql_code

        print("⚠️ 無法抽取 SQL，原始輸出如下：")
        print(text[:300])
        return None
    


    
    # 執行 SQL 查詢
    def _run_sql(self, query):
        try:
            print("🔍 [SQLAgent] 正在連線到 SQLite 資料庫...")
            conn = sqlite3.connect(self.db_path)
            print("🔍 [SQLAgent] 正在查詢...")
            df = pd.read_sql_query(query, conn)
            conn.close()
            print(f"✅ 查詢成功，共 {len(df)} 筆結果。")
            return df
        except Exception as e:
            print("❌ 查詢失敗：", e)
            return None
        
    
    # ---------- 人類摘要 ----------
    def _summarize_sql(self, df, max_rows=5):
        if df.empty:
            return "📭 No data found."

        print("📝 [SQLAgent] 正在生成 SQL 結果摘要...")
        print(f"📊 資料筆數：{len(df)}")

        preview_df = df.head(max_rows).copy()
        for col in preview_df.columns:
            if preview_df[col].dtype == "object":
                preview_df[col] = (
                    preview_df[col]
                    .astype(str)
                    .str.replace(r'\\n', '\n')
                    .str.slice(0, 200)
                )

        summary = f"📊 Query successful. Total {len(df)} records found.<br>"
        summary += f"📋 Preview of first {min(max_rows, len(df))} records:<br>"
        preview = preview_df.to_string(index=False)

        print("DEBUG preview====>")
        print(repr(preview))
        print("<====DEBUG preview")

        return summary + "```\n" + preview + "\n```"
    

    # ----------- LLM 動態 chunk size 計算 -----------
    # 估算每行資料的 token 數量
    # 這裡假設每個 token 約等於 4 個字元（這是 OpenAI 的估算）
    # 這個函數會計算 DataFrame 的平均行長度，並估算每行的 token 數量
    # 這個估算是粗略的，實際情況可能會有所不同，但可以作為一個起點

    def _estimate_tokens_per_row(self, df):
        csv_text = df.to_csv(index=False)
        avg_len = len(csv_text) / len(df) if len(df) > 0 else 1
        return int(avg_len / 4)
    
    # 根據模型名稱和保留的提示 token 數量計算動態 chunk size
    # 這個函數會根據模型的 token 限制和保留的提示 token 數量計算出合適的 chunk size
    # 這樣可以確保在處理大型 DataFrame 時不會超過模型的 token 限制
    # 這個函數會考慮模型的 token 限制、保留的提示 token 數量以及每行資料的平均 token 數量
    # 最後返回一個合適的 chunk size，確保不會超過模型的限制
    # 如果計算出的 chunk size 大於 DataFrame 的行數，則返回 DataFrame 的行數
    # 這樣可以確保在處理小型 DataFrame 時不會出現錯誤
    # 根據模型和資料量動態計算 chunk_size
    def _calculate_dynamic_chunk_size(self, df, prompt_reserve_tokens=500):
        model_token_limits = {
            "phi4-mini": 4096,
            "phi3:mini": 4096,
            "mistral": 8192,
            "orca2": 8192,
            "orca2-13b": 8192,
            "deepseek-coder:latest": 16384,
            "deepseek-coder-v2:latest": 16384,
        }
        max_tokens = model_token_limits.get(self.model, 4096)
        tokens_per_row = self._estimate_tokens_per_row(df)
        available_tokens = max_tokens - prompt_reserve_tokens
        # 🛡️ 為了輸出品質，再減 10 筆
        chunk_size = max(5, int(available_tokens / tokens_per_row) - 10)
        return min(chunk_size, len(df))
    
    # 將多個摘要分組並合併，確保不超過 token 限制
    # 這個函數用來將多個摘要分組並合併成更大的摘要
    # 它會將摘要分成多個組，每組的 token 數量不超過可用的 token 限制
    # 然後使用指定的模型來合併每組摘要
    # 如果合併後的摘要仍然超過 token 限制，則會遞迴地再次合併
    # 最後返回合併後的摘要
    # 如果只有一個合併後的摘要，則直接返回該摘要
    # 如果合併失敗，則會嘗試使用備用模型進行合併
    # 如果所有模型都失敗，則返回一個錯誤訊息
    # 📌 固定使用 8192 token 限制切 prompt，即使 fallback 模型上限更小（如 phi3）
    def _split_and_merge_summaries(self, summaries, token_limit=8192, prompt_reserve=500, is_top_level=True):
        def estimate_token_count(text):
            return len(text) // 4

        fallback_models = ["orca2:13b", "nous-hermes2:10.7b", "phi3:mini"]
        available_tokens = token_limit - prompt_reserve
        grouped = []
        group = []
        token_count = 0

        for s in summaries:
            s_tokens = estimate_token_count(s)
            if token_count + s_tokens > available_tokens:
                grouped.append(group)
                group = [s]
                token_count = s_tokens
            else:
                group.append(s)
                token_count += s_tokens
        if group:
            grouped.append(group)

        def run_with_model(m, prompt):
            try:
                result = subprocess.run(
                    ["ollama", "run", m],
                    input=prompt.encode("utf-8"),
                    capture_output=True,
                    timeout=300
                )
                if result.returncode == 0:
                    return result.stdout.decode("utf-8").strip()
            except Exception as e:
                print(f"❌ 模型 {m} 發生錯誤：{e}")
            return None

        merged_chunks = []
        print(f"🔍 共分成 {len(grouped)} 組摘要，每組平均 {token_count / len(grouped):.2f} tokens")
        print("🧠 開始合併摘要...")
        for i, group in enumerate(grouped, 1):
            merge_prompt = f"You are a data analyst. Please summarize the key points from the following group {i} of summaries:\n\n"
            for idx, s in enumerate(group, 1):
                merge_prompt += f"（摘要 {idx}）{s}\n\n"
            merge_prompt += "Please consolidate the main observations:"

            print(f"🧠 嘗試使用主模型 {self.model} 進行合併摘要...")
            print(f"📥 Prompt Preview：{merge_prompt[:300]}{'...' if len(merge_prompt) > 300 else ''}")
            reply = run_with_model(self.model, merge_prompt)
            print(f"📥 回覆 Preview：{reply[:300]}{'...' if reply and len(reply) > 300 else ''}")

            for fallback in fallback_models:
                if reply:
                    break
                print(f"🔁 使用 fallback 模型：{fallback}")
                reply = run_with_model(fallback, merge_prompt)

            merged_chunks.append(reply if reply else "❌ 本段摘要失敗")

        if len(merged_chunks) == 1:
            result = merged_chunks[0]
            if is_top_level:
                return f"📊 GPT 整合摘要如下：\n{result}"
            else:
                return result
        else:
            return self._split_and_merge_summaries(merged_chunks, token_limit, prompt_reserve, is_top_level=False)





    # 這個函數用來使用 LLM 對 SQL 查詢結果進行摘要
    # 它會將查詢結果分成多個 chunk，然後對每個 chunk 使用 LLM 進行摘要
    # 最後將所有 chunk 的摘要合併成一個最終的摘要
    # 如果查詢結果為空，則返回一個提示訊息
    # 如果 LLM 呼叫失敗，則會嘗試使用備用模型進行摘要
    # 如果所有模型都失敗，則返回一個錯誤訊息
    # 這個函數會根據模型的 token 限制和保留的提示 token 數量計算出合適的 chunk size
    # 這樣可以確保在處理大型 DataFrame 時不會超過模型的 token 限制
    # 它還會考慮每行資料的平均 token 數量，並根據這些資訊計算出合適的 chunk size
    # 最後返回一個合適的 chunk size，確保不會超過模型的限制
    # 使用 LLM 摘要 SQL 結果
    def _summarize_sql_with_llm(self, df):
        print("🧠 [SQLAgent] 嘗試使用 LLM 進行 SQL 結果摘要...")
        print(f"🧠 使用模型：{self.model}")
        print(f"📝 資料筆數：{len(df)}")

        if df.empty:
            return "📭 查無資料結果。"

        chunk_size = self._calculate_dynamic_chunk_size(df)
        print(f"📐 預估 chunk_size = {chunk_size} 筆（模型：{self.model}）")

        chunk_summaries = []

        for i in range(0, len(df), chunk_size):
            chunk = df.iloc[i:i+chunk_size]
            sample_csv = chunk.to_csv(index=False)
            prompt = (
                f"You are a data analyst. The following is data chunk {i//chunk_size+1}. "
                f"Please summarize its characteristics and trends:\n\n{sample_csv}\n\nSummary:"
            )

            try:
                result = subprocess.run(
                    ["ollama", "run", self.model],
                    input=prompt.encode("utf-8"),
                    capture_output=True,
                    timeout=600
                )

                if result.returncode == 0:
                    reply = result.stdout.decode("utf-8").strip()
                    chunk_summaries.append(reply)
                    print(f"✅ 第 {i//chunk_size+1} 段完成摘要")
                else:
                    print(f"⚠️ 第 {i//chunk_size+1} 段摘要失敗，跳過")

            except Exception as e:
                print(f"❌ 第 {i//chunk_size+1} 段呼叫 LLM 失敗：{e}")

        if not chunk_summaries:
            return self._summarize_sql(df)

        print("🧠 開始整合所有段落摘要...")
        
        # ✅ 使用整合版摘要方法取代原本 run_with_fallback
        print("🧠 開始整合所有段落摘要（使用 _split_and_merge_summaries）...")
        final_summary = self._split_and_merge_summaries(chunk_summaries)
        print("📝 整合摘要完成，長度：", len(final_summary))
        if final_summary:
            return final_summary
        else:
            print("⚠️ 合併摘要失敗，回傳各段摘要集合")
            return "\n\n".join(chunk_summaries)


    

    def handle(self, user_question, memory=None):
        print("🧠 [SQLAgent] 啟動 SQL 查詢流程...")
        if not user_question:
            return "⚠️ 使用者問題為空，無法進行 SQL 查詢。"
        user_question_sql_prompt, user_question_analysis_prompt = self._split_user_question(user_question)
        if not user_question_sql_prompt or not user_question_analysis_prompt:
            return "⚠️ 無法從 LLM 拆解使用者問題，請檢查模型設定或輸入格式。"
        # 1. 构造 SQL 提示
        sql_prompt = self._build_prompt(user_question_sql_prompt)
        print("📝 [SQLAgent] 構造 SQL Prompt：")
        print(sql_prompt[:300])

        # 2. 產生 SQL 查詢語句
        raw_sql = self._generate_sql(sql_prompt)
        if not raw_sql:
            return "⚠️ 無法從 LLM 生成有效 SQL 查詢語句。"

        # 3. 抽取 SQL 指令
        sql_code = self._extract_sql(raw_sql)
        print("📝 [SQLAgent] 抽取的 SQL 指令：")
        if not sql_code:
            return "⚠️ 無法從回應中擷取 SQL 指令。"

        # 4. 執行查詢
        df = self._run_sql(sql_code)
        if df is None or df.empty:
            return "📭 查無資料結果，請調整條件後再試。"

        # 5. 摘要結果（人類版 + GPT 版）
        summary = self._summarize_sql(df)
        summaryByLLM = self._summarize_sql_with_llm(df)

        combined = (
            "📋 [系統摘要]\n" + summary.strip() +
            "\n\n🧠 [GPT 摘要]\n" + summaryByLLM.strip()
        )

        # 6. 如果有記憶體 agent，就存進 context
        if memory:
            memory.save("last_sql_summary", combined[:500])

        return combined