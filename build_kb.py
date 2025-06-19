import os
import sys
import json
import faiss
import pickle
import hashlib
import sqlite3
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
SQLITE_DB = "resultDB.db"

def id_to_int64(uid):
    return int(hashlib.sha256(uid.encode('utf-8')).hexdigest(), 16) % (1 << 63)


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


def save_to_sqlite(metadata_list):
    conn = sqlite3.connect(SQLITE_DB)
    c = conn.cursor()

    # 建表（如果不存在）
    c.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                internalId INTEGER PRIMARY KEY AUTOINCREMENT,
                id TEXT UNIQUE,
                text TEXT,
                subcategory TEXT,
                configurationItem TEXT,
                roleComponent TEXT,
                location TEXT,
                opened TEXT,
                analysisTime TEXT
            )
    """)


    # 插入資料
    for item in metadata_list:
        c.execute("""
            INSERT OR REPLACE INTO metadata (id, text, subcategory, configurationItem, roleComponent, location, opened,analysisTime)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item.get("id"),
            item["text"],
            item["subcategory"],
            item["configurationItem"],
            item["roleComponent"],
            item["location"],
            item["opened"],
            item["analysisTime"]
        ))


    conn.commit()
    conn.close()
    print(f"🗃️ 已同步儲存 {len(metadata_list)} 筆資料到 SQLite：{SQLITE_DB}")



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
            analysisTime_raw = item.get("analysisTime") or "時間未填入"
            uid = item.get("id") or "未提供"
            analysis_Time = fix_datetime(analysisTime_raw)
            open_time = fix_datetime(open_raw)
            text = f"""事件類別：{sub}｜模組：{ci}｜角色：{role}\n地點：{loc}\n問題描述：{summary}\n處理方式：{solution}"""
            kb_texts.append(text)
            metadata.append({
                "id": uid,
                "text": text,
                "subcategory": sub,
                "configurationItem": ci,
                "roleComponent": role,
                "location": loc,
                "opened": open_time,
                "analysisTime": analysis_Time,
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
        print(f"📑 處理檔案：{file}")
        new_texts, new_metadata = extract_texts_and_metadata(path)
        metadata.extend(new_metadata)
        save_processed_file(file)

    # 🔄 若有舊的 metadata，先載入並轉成 dict 以 id 為 key
    print("📂 載入舊的 metadata.json 並準備比對 ID...")
    if os.path.exists(KB_METADATA):
        with open(KB_METADATA, "r", encoding="utf-8") as f:
            old_metadata = json.load(f)
    else:
        old_metadata = []

    metadata_dict = {item["id"]: item for item in old_metadata if "id" in item}

    print(f"🔍 舊 metadata 共 {len(metadata_dict)} 筆，準備與新資料合併")

    # 🆕 更新或新增每一筆新 metadata（用新資料覆蓋同 id）
    print(f"➕ 合併新 metadata，共 {len(metadata)} 筆新資料")
    for item in metadata:
        uid = item.get("id")
        if not uid or uid == "未提供":
            continue
        metadata_dict[uid] = item

    # 💾 寫回檔案（轉回 list）
    merged_metadata = list(metadata_dict.values())
    print(f"💾 寫入合併後的 metadata，共 {len(merged_metadata)} 筆")
    with open(KB_METADATA, "w", encoding="utf-8") as f:
        json.dump(merged_metadata, f, ensure_ascii=False, indent=2)

    # ✅ 這裡改為重建 FAISS index 和文字庫
    print("📐 開始重建 FAISS 向量庫")
    texts_for_embedding = [item["text"] for item in merged_metadata]
    embeddings = model.encode(texts_for_embedding, show_progress_bar=True)

    index_flat = faiss.IndexFlatL2(embeddings.shape[1])         # 建立 base index
    index = faiss.IndexIDMap(index_flat)                        # 包成 ID map
    print("🔢 準備加入向量到 FAISS index...")
    ids = []
    for item in merged_metadata:
        uid = item["id"]
        fid = id_to_int64(uid)
        print(f"🆔 原始 ID: {uid} -> FAISS ID: {fid}")
        ids.append(fid)

    ids = np.array(ids, dtype=np.int64)
    index.add_with_ids(np.array(embeddings), ids)
    print(f"🔢 向量庫建立完成，共 {len(embeddings)} 筆向量")
    print(f"🔢 向量庫建立完成，共 {len(texts_for_embedding)} 筆文本")
    print("✅ 向量建立完成，準備儲存 FAISS index")

    faiss.write_index(index, KB_INDEX)
    with open(KB_TEXTS, "wb") as f:
        pickle.dump(texts_for_embedding, f)
    print(f"💾 向量庫與文字庫已儲存，共 {len(texts_for_embedding)} 筆")

    print("🗃️ 寫入 SQLite 資料庫中...")
    save_to_sqlite(merged_metadata)

    print(f"✅ 知識庫更新完成（總共 {len(texts_for_embedding)} 筆）")
    log(f"✅ [LOG] 成功建立知識庫，共 {len(texts_for_embedding)} 筆")


if __name__ == "__main__":
    try:
        build_kb()
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
        print("🗂️ 鎖定檔已刪除，結束建庫流程")
        log("✅ [LOG] 知識庫流程結束，lock 已清除")
        print("📜 日誌已更新，請檢查 kb_log.txt 獲取詳細資訊")