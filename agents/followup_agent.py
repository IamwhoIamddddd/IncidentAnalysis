# agents/followup_agent.py

import json
import subprocess

class FollowUpAgent:
    def __init__(self, allowed_fields=None, metadata_path="kb_metadata.json", chat_dir="chat_history"):
        self.allowed_fields = allowed_fields or ["configurationItem", "subcategory", "roleComponent", "location"]
        self.metadata_path = metadata_path
        self.chat_dir = chat_dir

    def is_follow_up(self, message: str) -> bool:
        print("🧠 判斷是否為追問查詢...")
        keywords = ["previous", "last query", "those", "add filter", "now show", "continue", "follow up"]
        lowered = message.lower()
        for kw in keywords:
            if kw in lowered:
                print(f"✅ 命中關鍵字：'{kw}' → 判定為追問查詢")
                return True
        print("❌ 無關鍵字命中 → 非追問查詢")
        return False

    def handle(self, chat_id, message):
        filepath = f"{self.chat_dir}/{chat_id}.json"
        print(f"📂 嘗試讀取歷史記錄：{filepath}")
        try:
            with open(filepath, encoding="utf-8") as f:
                history = json.load(f)
        except Exception as e:
            return f"⚠️ 無法讀取對話記錄：{e}"

        if not history or "context" not in history[-1]:
            return "⚠️ 查無先前查詢條件，請重新描述您的需求。"

        context = history[-1]["context"]
        if context.get("type") != "Field Filter":
            return "⚠️ 目前只支援欄位篩選的延伸查詢。"

        original = context.get("filters", {})
        print(f"🔍 原始過濾條件：{original}")

        prompt = (
            "You are a filter parser. Based on this message, extract an additional field and value to add as a filter.\n"
            "Return JSON like: {\"field\": \"subcategory\", \"value\": \"Crash\"}\n"
            "The entire response must be in compact JSON format and must not exceed 500 characters."
            f"\n\nUser: {message}"
        )

        try:
            result = subprocess.run(
                ["ollama", "run", "phi3:mini"],
                input=prompt.encode("utf-8"),
                capture_output=True,
                timeout=600
            )
            raw_reply = result.stdout.decode("utf-8").strip()
            new_filter = json.loads(raw_reply)

            field = new_filter.get("field")
            value = new_filter.get("value")

            if field not in self.allowed_fields:
                return "⚠️ 無效的欄位"

            with open(self.metadata_path, encoding="utf-8") as f:
                metadata = json.load(f)

            matches = metadata
            for f in [original, new_filter]:
                matches = [m for m in matches if m.get(f["field"]) == f["value"]]

            lines = [f"- {item.get('text', '')[:500]}" for item in matches[:5]]
            return f"🔎 延伸查詢結果（共 {len(matches)} 筆）：\n" + "\n".join(lines)

        except Exception as e:
            return f"⚠️ 延伸查詢失敗：{e}"
