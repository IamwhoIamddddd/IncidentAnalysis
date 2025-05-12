from SmartScoring import is_actionable_resolution
import aiohttp
import asyncio


# 🧠 主功能：從段落中抽出解決建議句（含空值與關鍵字檢查）
async def extract_resolution_suggestion(text, model="mistral"):
    if not isinstance(text, str) or not text.strip():
        return "（無原始描述）"

    ALWAYS_ANALYZE = True
    if not ALWAYS_ANALYZE and not is_actionable_resolution(text):
        print("⏭️ 無語意相近解法語氣，略過分析：", text[:100])
        return "（未偵測到具體解法語氣，略過分析）"

    lines = text.strip().splitlines()
    text_trimmed = "\n".join(lines[:3])

    prompt = f"""Instruction: Summarize 1 actionable solution from the following.
Reply "No recommendation" if none. Limit answer to 30 words.
---
{text_trimmed}
"""

    try:
        return await call_ollama_model_async(prompt, model)
    except Exception as e:
        print("❌ 初次呼叫失敗，嘗試重試一次...")
        await asyncio.sleep(2)
        try:
            return await call_ollama_model_async(prompt, model)
        except Exception as e2:
            print("⛔ GPT 雙次呼叫都失敗：", e2)
            return "（AI 擷取失敗）"


async def extract_problem_with_custom_prompt(text, model="phi3:mini"):
    if not isinstance(text, str) or not text.strip():
        return "（無原始描述）"

    lines = text.strip().splitlines()
    text_trimmed = "\n".join(lines[:3])

    prompt = f"""You're an assistant. Read the following incident note and summarize what issue or problem it describes, in one clear sentence.
Do not suggest a solution. Only summarize the problem.
Limit to 30 words.
---
{text_trimmed}
"""

    try:
        return await call_ollama_model_async(prompt, model)
    except Exception as e:
        print("❌ 初次呼叫失敗，嘗試重試一次...")
        await asyncio.sleep(2)
        try:
            return await call_ollama_model_async(prompt, model)
        except Exception as e2:
            print("⛔ GPT 雙次呼叫都失敗：", e2)
            return "（AI 擷取失敗）"


# 🔧 非同步呼叫本地 Ollama API
async def call_ollama_model_async(prompt, model="mistral", timeout=120):
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

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
        async with session.post(url, json=payload, headers=headers) as response:
            response.raise_for_status()
            result = await response.json()
            return result.get("response", "").strip()
