from SmartScoring import is_actionable_resolution
import requests
import time

# 🧠 主功能：從段落中抽出解決建議句（含空值與關鍵字檢查）
def extract_resolution_suggestion(text, model="mistral"):
    if not isinstance(text, str) or not text.strip():
        return "（無原始描述）"

    # ✅ 使用 SmartScoring 提供的處理動作判斷（模組分工）
    ALWAYS_ANALYZE = True  # 👈 設成 True 就跳過篩選

    if not ALWAYS_ANALYZE and not is_actionable_resolution(text):
        print("⏭️ 無語意相近解法語氣，略過分析：", text[:100])
        return "（未偵測到具體解法語氣，略過分析）"



    # ✅ 限制輸入長度為前 3 行，避免 timeout
    lines = text.strip().splitlines()
    text_trimmed = "\n".join(lines[:3])

    # ✅ 英文 Prompt，固定風格讓模型加快生成
    prompt = f"""Instruction: Summarize 1 actionable solution from the following.
    Reply "No recommendation" if none. Limit answer to 30 words.
    ---
    {text_trimmed}
    """

    try:
        return call_ollama_model(prompt, model)
    except Exception as e:
        print("❌ 初次呼叫失敗，嘗試重試一次...")
        time.sleep(2)
        try:
            return call_ollama_model(prompt, model)
        except Exception as e2:
            print("⛔ GPT 雙次呼叫都失敗：", e2)
            return "（AI 擷取失敗）"
        

def extract_problem_with_custom_prompt(text, model="mistral"):
    if not isinstance(text, str) or not text.strip():
        return "（無原始描述）"

    lines = text.strip().splitlines()
    text_trimmed = "\n".join(lines[:3])

    # 🆕 使用新的 Prompt（30 字內的 actionable solution）
    prompt = f"""You're an assistant. Read the following incident note and summarize what issue or problem it describes, in one clear sentence.
Do not suggest a solution. Only summarize the problem.
Limit to 30 words.
---
{text_trimmed}
"""



    try:
        return call_ollama_model(prompt, model)
    except Exception as e:
        print("❌ 初次呼叫失敗，嘗試重試一次...")
        time.sleep(2)
        try:
            return call_ollama_model(prompt, model)
        except Exception as e2:
            print("⛔ GPT 雙次呼叫都失敗：", e2)
            return "（AI 擷取失敗）"



# 🔧 基礎函數：呼叫本地 Ollama API
def call_ollama_model(prompt, model="mistral", timeout=60):
    url = "http://localhost:11434/api/generate"
    headers = {"Content-Type": "application/json"}

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": 50,
            "temperature": 0.5
        }
    }

    response = requests.post(url, json=payload, headers=headers, timeout=timeout)
    response.raise_for_status()
    result = response.json()

    return result.get("response", "").strip()
