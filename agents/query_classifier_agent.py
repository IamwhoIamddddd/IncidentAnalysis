# agents/query_classifier_agent.py

import subprocess
import re

class QueryClassifierAgent:
    def __init__(self, primary_model="command-r7b:latest", fallback_model="openchat:7b", timeout=120):
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.timeout = timeout

        self.system_prompt = (
            "You are a classification assistant. Your task is to analyze the user's question and classify it as one of the following two types:\n\n"
            "1. Semantic Query – The user is seeking similar past incidents, solution suggestions, or insights based on previous case knowledge.\n"
            "   Typical intents: find related issues, ask how a problem was resolved, request examples of solutions.\n\n"
            "2. Structured SQL – The user is requesting structured or statistical data, such as record counts, field value filtering, time-based trends, or aggregated summaries.\n"
            "   Typical intents: show number of records, list unique values, filter by conditions, summarize results over time.\n\n"
            "Respond with exactly one of the following labels (no explanations):\n"
            "'Semantic Query' or 'Structured SQL'."
        )

    def handle(self, message: str) -> str:
        prompt = f"{self.system_prompt}\n\nUser: {message}"
        print(f"📝 使用者輸入：{message}")
        def try_model(model_name):
            try:
                print(f"🧠 嘗試模型：{model_name}")
                result = subprocess.run(
                    ["ollama", "run", model_name],
                    input=prompt.encode("utf-8"),
                    capture_output=True,
                    timeout=self.timeout
                )
                if result.returncode == 0:
                    reply = result.stdout.decode("utf-8").strip()
                    print(f"[分類回覆] {reply}")
                    return reply
                else:
                    print(f"❌ 模型 {model_name} 錯誤：{result.stderr.decode('utf-8')}")
            except subprocess.TimeoutExpired:
                print(f"⏰ 模型 {model_name} 超時（{self.timeout}s）")
            except Exception as e:
                print(f"❌ 模型 {model_name} 發生例外：{e}")
            return None

        reply = try_model(self.primary_model) or try_model(self.fallback_model)
        if not reply:
            print("⚠️ 回覆為空，預設為 Semantic Query")
            return "Semantic Query"

        if "Structured SQL" in reply:
            print("✅ 類別判斷：Structured SQL")
            return "Structured SQL"
        if "Semantic Query" in reply:
            print("✅ 類別判斷：Semantic Query")
            return "Semantic Query"

        print("⚠️ 回傳內容不在允許類型中，預設為 Semantic Query")
        return "Semantic Query"