from SmartScoring import is_actionable_resolution
import aiohttp
import asyncio
import hashlib
import json
import os
from datetime import datetime
from sentence_transformers import SentenceTransformer, util
import numpy as np
import re
import time


POWERAUTOMATEANALYSIS_URL = "https://prod-68.southeastasia.logic.azure.com:443/workflows/de1c05e9860c4296873b019585edcb7f/triggers/manual/paths/invoke?api-version=2016-06-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=TlEzbTE_tkcvnKUuiziBXthKuvW7ONK6VP4bxi_-_bY"  # 🔁 請換成你的實際網址


MAX_CONCURRENCY = 10
CHAR_LIMIT_OLLAMA_RESOLUTION = 16000  # 或你想要的字數限制
CHAR_LIMIT_OLLAMA_SUMMARY = 16000  # 或你想要的字數限制
CHAR_LIMIT_AIBUILDER_RESOLUTION = 128000  # 或你想要的字數限制
CHAR_LIMIT_AIBUILDER_SUMMARY = 128000  # 或你想要的字數限制

DEFAULT_MODEL_SOLUTION = "command-r7b:latest"
DEFAULT_MODEL_SUMMARY = "command-r7b:latest"

cache_hit_count_resolution = 0
cache_total_queries_resolution = 0
cache_hit_count_summary = 0
cache_total_queries_summary = 0



PA_MAX_CONCURRENCY = 50  # 你想要同時送幾筆 request
pa_semaphore = asyncio.Semaphore(PA_MAX_CONCURRENCY)
semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

# ✅ 快取儲存位置
CACHE_DIR = "cache"
CACHE_FILE_RESOLUTION = os.path.join(CACHE_DIR, "semantic_cache_resolution.json")
CACHE_FILE_SUMMARY = os.path.join(CACHE_DIR, "semantic_cache_summary.json") 
# ✅ 快取大小限制
MAX_CACHE_SIZE = 3000

# 統計用變數
cache_hit_count = 0
cache_total_queries = 0

# ✅ 確保資料夾存在
os.makedirs(CACHE_DIR, exist_ok=True)

# ✅ 載入語意模型
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# ✅ 載入快取資料
if os.path.exists(CACHE_FILE_RESOLUTION):
    with open(CACHE_FILE_RESOLUTION, "r", encoding="utf-8") as f:
        semantic_cache_resolution = json.load(f)
else:
    semantic_cache_resolution = []

if os.path.exists(CACHE_FILE_SUMMARY):
    with open(CACHE_FILE_SUMMARY, "r", encoding="utf-8") as f:
        semantic_cache_summary = json.load(f)
else:
    semantic_cache_summary = []


def clean_text(text):
    return re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)  # 去除控制符號（emoji 可保留）

# ✅ 產生 hash key 用於完全比對
def make_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()



# ✅ 語意快取查詢（含文字 hash + cosine）
def find_semantic_cache(text, kind="resolution", threshold=0.9, source_id=""):
    global cache_hit_count_resolution, cache_total_queries_resolution
    global cache_hit_count_summary, cache_total_queries_summary

    key = make_hash(text)

    if kind == "resolution":
        cache = semantic_cache_resolution
        cache_total_queries_resolution += 1
    elif kind == "summary":
        cache = semantic_cache_summary
        cache_total_queries_summary += 1
    else:
        raise ValueError("Unknown cache kind: must be 'resolution' or 'summary'")

    print(f"🔍 [Cache:{kind}] 查找快取中... {source_id} hash={key[:8]} text='{text[:30]}'")

    for item in cache:
        if item.get("hash") == key:
            if item["response"] == "（AI 擷取失敗）":
                print(f"🚫 [Cache:{kind}] 命中但為失敗快取（{source_id}），需送 GPT 再分析")
                return None
            if kind == "resolution":
                cache_hit_count_resolution += 1
            elif kind == "summary":
                cache_hit_count_summary += 1
            print(f"🎯 [Cache:{kind}] 完整命中！（{source_id}）")
            return item["response"]

    if len(cache) == 0:
        print(f"📭 [Cache:{kind}] 無任何快取可比對（cache 空）（{source_id}）")
        return None

    try:
        query_vec = embedding_model.encode(text).astype(np.float32)
        all_vecs = np.array([item['embedding'] for item in cache], dtype=np.float32)
        sims = util.cos_sim(query_vec, all_vecs).flatten()
    except Exception as e:
        print(f"❌ [Cache:{kind}] 語意比對時發生錯誤（{source_id}）：{e}")
        return None

    best_idx = int(np.argmax(sims))
    if sims[best_idx] > threshold:
        response = cache[best_idx]["response"]
        if response == "（AI 擷取失敗）":
            print(f"🚫 [Cache:{kind}] 語意相似命中但為失敗快取（{sims[best_idx]:.3f}）（{source_id}）")
            return None
        if kind == "resolution":
            cache_hit_count_resolution += 1
        elif kind == "summary":
            cache_hit_count_summary += 1
        print(f"🎯 [Cache:{kind}] 語意相似命中！相似度={sims[best_idx]:.3f}（{source_id}）")
        return response

    print(f"❌ [Cache:{kind}] 無命中，將送 GPT 擷取新資料（{source_id}）")
    return None



# ✅ 儲存新的快取紀錄
def add_to_semantic_cache(text, response, kind="resolution"):
    key = make_hash(text)
    emb = embedding_model.encode(text).tolist()

    if kind == "resolution":
        cache = semantic_cache_resolution
        cache_file = CACHE_FILE_RESOLUTION
    elif kind == "summary":
        cache = semantic_cache_summary
        cache_file = CACHE_FILE_SUMMARY
    else:
        raise ValueError("Unknown cache kind: must be 'resolution' or 'summary'")

    cache.append({
        "hash": key,
        "input": text,
        "embedding": emb,
        "response": response,
        "createdAt": datetime.now().isoformat()
    })
    if len(cache) > MAX_CACHE_SIZE:
        cache.pop(0)
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    print(f"💾 [Cache:{kind}] 已儲存快取：hash={key[:8]} text='{text[:1000]}'")


# 🧠 主功能：從段落中抽出解決建議句（含空值與快取）

def get_gpt_prompt_and_model(task="solution"):
    MAP_PATH = os.path.join("gpt_data", "gpt_prompt_map.json")
    try:
        with open(MAP_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        if config.get(task):
            prompt = config[task].get("prompt") or ""
            model = config[task].get("model") or ""
            # 檢查是否 prompt/model 缺失
            if not prompt or not model:
                print(f"⚠️ [PromptMap] {task} 的 prompt 或 model 欄位為空，已啟用預設值！")
            return prompt, model
        else:
            print(f"⚠️ [PromptMap] {task} 設定不存在，已啟用預設值！")
    except Exception as e:
        print(f"❌ [PromptMap] 讀取 {task} 設定失敗：{e}")
    # 回傳預設值
    if task == "solution":
        print("⚠️ [PromptMap] 使用 solution 預設 prompt/model")
        return "請從以下段落提取一個具體的行動建議", DEFAULT_MODEL_SOLUTION
    elif task == "ai_summary":
        print("⚠️ [PromptMap] 使用 ai_summary 預設 prompt/model")
        return "請用一句話描述事件是什麼", DEFAULT_MODEL_SUMMARY
    else:
        print(f"⚠️ [PromptMap] 未知用途 {task}，回傳空值")
        return "", ""


async def extract_resolution_suggestion(text, model=DEFAULT_MODEL_SOLUTION, source_id=""):
    if not isinstance(text, str) or not text.strip():
        return "（無原始描述）"

    ALWAYS_ANALYZE = True
    if not ALWAYS_ANALYZE and not is_actionable_resolution(text):
        print(f"⏭️ 無語意相近解法語氣，略過分析（{source_id}）：", text[:100])
        return "（未偵測到具體解法語氣，略過分析）"

    # 讀取目前的 prompt 與 model 設定
    custom_prompt, custom_model = get_gpt_prompt_and_model("solution")
    model = model or custom_model

    text_trimmed = text.strip()[:CHAR_LIMIT_OLLAMA_RESOLUTION]
    print(f"🔍 [GPT] 準備擷取解決建議：{text_trimmed[:500]}...（{source_id}）")

    # ✅ 這裡加 kind
    cached = find_semantic_cache(text_trimmed, kind="resolution", source_id=source_id)
    if cached:
        print(f"🎯 快取命中：略過 GPT 分析（{source_id}）")
        return cached

    prompt = f"{custom_prompt}\n---\n{text_trimmed}"
    print(f"📝 [GPT] 最後輸入進的prompt：{prompt[:600]}...")
    max_retry = 5
    retry_count = 0

    while retry_count < max_retry:
        try:
            result = await call_ollama_model_async(prompt, model)
            if result and "擷取失敗" not in result and "未偵測" not in result:
                print(f"✅ GPT (擷取解決建議)第 {retry_count + 1} 次呼叫成功（{source_id}）")
                # ✅ 這裡加 kind
                add_to_semantic_cache(text_trimmed, result, kind="resolution")
                return result
            else:
                print(f"⚠️ GPT 回傳內容不完整，第 {retry_count + 1} 次結果為：{result[:30]}...")
        except Exception as e:
            print(f"⚠️ GPT 呼叫失敗（第 {retry_count + 1} 次）（{source_id}）：{e}")
        retry_count += 1
        await asyncio.sleep(2)

    print(f"⛔ GPT 分析失敗（{source_id}），已達最大重試次數 {max_retry} 次")
    return "（AI (擷取解決建議)擷取失敗）"
# 🧠 主功能：擷取問題摘要（同樣支援 source_id）


async def extract_problem_with_custom_prompt(text, model=None, source_id=""):
    if not isinstance(text, str) or not text.strip():
        return "（無原始描述）"

    # 讀取目前的 prompt 與 model 設定
    custom_prompt, custom_model = get_gpt_prompt_and_model("ai_summary")
    model = model or custom_model

    text_trimmed = text.strip()[:CHAR_LIMIT_OLLAMA_SUMMARY]
    
    print(f"🔍 [GPT] 準備擷取問題摘要：{text_trimmed[:500]}...（{source_id}）")

    # ✅ 查詢 summary cache
    cached = find_semantic_cache(text_trimmed, kind="summary", source_id=source_id)
    if cached:
        print(f"🎯 快取命中：略過 GPT (擷取問題摘要) 分析（{source_id}）")
        return cached

    prompt = f"{custom_prompt}\n---\n{text_trimmed}"
    print(f"📝 [GPT] 最後輸入進的prompt：{prompt[:600]}...")
    max_retry = 5
    retry_count = 0

    while retry_count < max_retry:
        try:
            result = await call_ollama_model_async(prompt, model)
            if result and "擷取失敗" not in result and "未偵測" not in result:
                print(f"✅ GPT (擷取問題摘要) 第 {retry_count + 1} 次呼叫成功（{source_id}）")
                # ✅ 儲存進 summary cache
                add_to_semantic_cache(text_trimmed, result, kind="summary")
                return result
            else:
                print(f"⚠️ GPT 回傳內容不完整，第 {retry_count + 1} 次結果為：{result[:30]}...")
        except Exception as e:
            print(f"⚠️ GPT (擷取問題摘要) 第 {retry_count + 1} 次呼叫失敗（{source_id}）：{e}")
        retry_count += 1
        await asyncio.sleep(2)

    print(f"⛔ GPT (擷取問題摘要) 分析失敗（{source_id}），已達最大重試次數 {max_retry} 次")
    return "（AI (擷取問題摘要)擷取失敗）"



# 📊 快取命中率報告
def print_cache_report():
    print("=== Resolution Cache 命中報告 ===")
    if cache_total_queries_resolution == 0:
        print("📊 Resolution 本次未執行任何語意快取查詢。")
    else:
        ratio = cache_hit_count_resolution / cache_total_queries_resolution * 100
        print(f"📊 Resolution 快取命中 {cache_hit_count_resolution} / {cache_total_queries_resolution} 筆，命中率 {ratio:.1f}%")
    
    print("=== Summary Cache 命中報告 ===")
    if cache_total_queries_summary == 0:
        print("📊 Summary 本次未執行任何語意快取查詢。")
    else:
        ratio = cache_hit_count_summary / cache_total_queries_summary * 100
        print(f"📊 Summary 快取命中 {cache_hit_count_summary} / {cache_total_queries_summary} 筆，命中率 {ratio:.1f}%")



# 🔧 非同步呼叫本地 Ollama API
async def call_ollama_model_async(prompt, model="command-r7b:latest", timeout=600):
    async with semaphore:
        url = "http://localhost:11434/api/generate"
        headers = {"Content-Type": "application/json"}
        print(f"📝 [GPT] 使用模型 {model}")

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
            
        
# 📝 主功能：分析解決建議與問題摘要，先使用 Power Automate，再使用本地模型作為 fallback    
async def analyze_with_ai_builder_then_fallback(resolution_text, summary_input, source_id=""):
    if not resolution_text.strip() and not summary_input.strip():
        print(f"[{time.strftime('%X')}] ⛔️ 空白輸入，略過分析（{source_id}）")
        return "（無原始描述）", "（無原始描述）"

    res_trimmed = clean_text(resolution_text.strip())[:CHAR_LIMIT_AIBUILDER_RESOLUTION]
    sum_trimmed = clean_text(summary_input.strip())[:CHAR_LIMIT_AIBUILDER_SUMMARY]
    print(f"[{time.strftime('%X')}] 📝 準備分析：解決建議='{res_trimmed[:50]}' 摘要='{sum_trimmed[:50]}'（{source_id}）")
    
    # 1️⃣ 查找時分流
    cached_solution = find_semantic_cache(res_trimmed, kind="resolution", source_id=source_id + "-sol")
    cached_summary = find_semantic_cache(sum_trimmed, kind="summary", source_id=source_id + "-sum")
    if cached_solution and cached_summary:
        print(f"[{time.strftime('%X')}] 🎯 快取命中（{source_id}），略過 Power Automate 與本地分析")
        print(f"[{time.strftime('%X')}] 📝 快取解決建議：'{cached_solution}'")
        print(f"[{time.strftime('%X')}] 📝 快取問題摘要：'{cached_summary}'")
        return cached_solution, cached_summary
    
    custom_solution_prompt, custom_solution_model = get_gpt_prompt_and_model("solution")
    custom_summary_prompt, custom_summary_model = get_gpt_prompt_and_model("ai_summary")

    MAX_RETRY = 5
    for attempt in range(1, MAX_RETRY + 1):
        try:
            print(f"[{time.strftime('%X')}] ⚡️ Power Automate 嘗試第 {attempt} 次（{source_id}）...")
            async with pa_semaphore:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        POWERAUTOMATEANALYSIS_URL,
                        json={
                            "resolution": res_trimmed, 
                            "summary": sum_trimmed,
                            "solutionPrompt": custom_solution_prompt,
                            "summaryPrompt": custom_summary_prompt  
                        },
                        timeout=360
                    ) as response:
                        print(f"[{time.strftime('%X')}] ⏩ Power Automate response status: {response.status} ({source_id})")
                        response_text = await response.text()
                        print(f"[{time.strftime('%X')}] ⏪ Power Automate raw response: {response_text} ({source_id})")
                        if response.status == 200:
                            try:
                                result = json.loads(response_text)
                            except Exception as e:
                                print(f"[{time.strftime('%X')}] ❌ 回傳非 JSON 格式！({source_id}) err={e}")
                                continue
                            solution = result.get("solution", "").strip()
                            summary = result.get("aiSummary", "").strip()
                            print(f"[{time.strftime('%X')}] 📝 解析出 solution: '{solution[:50]}' summary: '{summary[:50]}' ({source_id})")

                            if solution and summary:
                                print(f"[{time.strftime('%X')}] ✅ Power Automate 成功（{source_id}）")
                                # 2️⃣ 儲存時分流
                                add_to_semantic_cache(res_trimmed, solution, kind="resolution")
                                add_to_semantic_cache(sum_trimmed, summary, kind="summary")
                                return solution, summary
                            else:
                                print(f"[{time.strftime('%X')}] ⚠️ Power Automate 回傳內容不完整（{source_id}）: {result}")
                        else:
                            print(f"[{time.strftime('%X')}] ❌ Power Automate HTTP status: {response.status} ({source_id}) | Text: {response_text}")
        except Exception as e:
            print(f"[{time.strftime('%X')}] ⚠️ Power Automate 發生錯誤（{source_id}）第 {attempt} 次：{e}")
        await asyncio.sleep(2)

    print(f"[{time.strftime('%X')}] 🔁 Power Automate 全部失敗，fallback 到本地模型（{source_id}）")
    try:
        ai_suggestion, ai_summary = await asyncio.gather(
            extract_resolution_suggestion(res_trimmed, source_id=source_id + "-sol"),
            extract_problem_with_custom_prompt(sum_trimmed, source_id=source_id + "-sum")
        )
        print(f"[{time.strftime('%X')}] 🟩 fallback 本地模型完成 solution: '{ai_suggestion[:50]}' summary: '{ai_summary[:50]}' ({source_id})")
        return ai_suggestion, ai_summary
    except Exception as e:
        print(f"[{time.strftime('%X')}] ❌ fallback 本地模型也失敗（{source_id}）：{e}")
        return "（AI 擷取失敗）", "（AI 擷取失敗）"
