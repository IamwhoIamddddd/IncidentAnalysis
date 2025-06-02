import os
import sys
import json
import faiss
import pickle
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import numpy as np
from datetime import datetime
from dateutil.parser import parse
# ========== ✅ 檢查環境與依賴 ==========
print("✅ [DEBUG] 你有成功呼叫 build_kb.py")

# ========== ✅ 加入 log 與鎖定檢查 ==========
LOCK_FILE = "kb_building.lock"
LOG_FILE = "kb_log.txt"

KB_INDEX = "kb_index.faiss"
KB_TEXTS = "kb_texts.pkl"
KB_METADATA = "kb_metadata.json"
PROCESSED_LOG = "processed_files.json"
DATA_DIR = "json_data"
MODEL_NAME = "all-MiniLM-L6-v2"



def fix_datetime(value):
    try:
        # 嘗試轉為 datetime 物件，並轉成 ISO 格式字串
        return parse(value).isoformat()
    except Exception:
        return "時間未填入"

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

log("✅ [LOG] build_kb.py 被執行！")

if os.path.exists(LOCK_FILE):
    print("❗知識庫正在建立中，請稍候")
    log("❗ [LOG] 偵測到 lock file，已中止建立")
    sys.exit(0)

with open(LOCK_FILE, "w") as f:
    f.write("building")

def load_processed_files():
    if not os.path.exists(PROCESSED_LOG):
        return set()
    with open(PROCESSED_LOG, "r", encoding="utf-8") as f:
        data = json.load(f)
        return set(entry["file"] for entry in data)

def save_processed_file(file):
    now = datetime.now().isoformat()
    if os.path.exists(PROCESSED_LOG):
        with open(PROCESSED_LOG, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []
    data.append({"file": file, "processedAt": now})
    with open(PROCESSED_LOG, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def extract_texts_and_metadata(json_file):
    with open(json_file, encoding="utf-8") as f:
        data = json.load(f)
        items = data["data"] if isinstance(data, dict) and "data" in data else data
        if not isinstance(items, list):
            items = [items]
        kb_texts = []
        metadata = []
        for item in items:
            summary = item.get("aiSummary") or item.get("problemSummary") or "(AI 擷取失敗)"
            solution = item.get("solution") or "(AI 擷取失敗)"
            ci = item.get("configurationItem") or "未知模組"
            role = item.get("roleComponent") or "未指定元件"
            sub = item.get("subcategory") or "未分類"
            loc = item.get("location") or "未提供"
            open_raw = item.get("opened") or "時間未填入"
            open_time = fix_datetime(open_raw)
            text = f"""事件類別：{sub}｜模組：{ci}｜角色：{role}\n地點：{loc}\n問題描述：{summary}\n處理方式：{solution}"""
            kb_texts.append(text)
            metadata.append({
                "text": text,
                "subcategory": sub,
                "configurationItem": ci,
                "roleComponent": role,
                "location": loc,
                "analysisTime": open_time,
            })
        return kb_texts, metadata

def build_kb():
    processed_files = load_processed_files()
    all_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".json") and f not in processed_files]
    if not all_files:
        print("📭 沒有新檔案，跳過建庫")
        return

    print(f"📂 有 {len(all_files)} 個新 JSON 檔要加入知識庫")
    model = SentenceTransformer(MODEL_NAME)

    if os.path.exists(KB_INDEX) and os.path.exists(KB_TEXTS) and os.path.exists(KB_METADATA):
        print("🔄 載入舊有 FAISS index、文字庫與 metadata")
        index = faiss.read_index(KB_INDEX)
        with open(KB_TEXTS, "rb") as f:
            kb_texts = pickle.load(f)
        with open(KB_METADATA, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    else:
        print("🆕 建立全新知識庫")
        index = None
        kb_texts = []
        metadata = []

    for file in tqdm(all_files, desc="📥 加入新知識檔案"):
        path = os.path.join(DATA_DIR, file)
        new_texts, new_metadata = extract_texts_and_metadata(path)
        new_embeddings = model.encode(new_texts, show_progress_bar=False)
        if index is None:
            index = faiss.IndexFlatL2(new_embeddings.shape[1])
        index.add(np.array(new_embeddings))
        kb_texts.extend(new_texts)
        metadata.extend(new_metadata)
        save_processed_file(file)

    faiss.write_index(index, KB_INDEX)
    with open(KB_TEXTS, "wb") as f:
        pickle.dump(kb_texts, f)
    with open(KB_METADATA, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"✅ 知識庫更新完成（總共 {len(kb_texts)} 筆）")
    log(f"✅ [LOG] 成功建立知識庫，共 {len(kb_texts)} 筆")

if __name__ == "__main__":
    try:
        build_kb()
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
        print("🗂️ 鎖定檔已刪除，結束建庫流程")
        log("✅ [LOG] 知識庫流程結束，lock 已清除")
        print("📜 日誌已更新，請檢查 kb_log.txt 獲取詳細資訊")