import sqlite3
import pandas as pd
import argparse
import os
import datetime
import random
import string

DB_PATH = "resultDB.db"
EXPORT_DIR = "ExportDB"

def generate_filename():
    today = datetime.datetime.now().strftime("%Y%m%d")
    rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=7))
    return f"{today}_{rand_str}.csv"

def run_sql(query):
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        print("❌ 查詢失敗：", e)
        return None

def main():
    parser = argparse.ArgumentParser(description="Query SQLite database using SQL")
    parser.add_argument("--sql", type=str, help="SQL query to execute")
    args = parser.parse_args()

    if not args.sql:
        print("⚠️ 請使用 --sql 參數指定查詢語句，例如：")
        print("   python query_sqlite.py --sql \"SELECT * FROM metadata LIMIT 5\"")
        return

    df = run_sql(args.sql)
    if df is not None:
        print(f"\n✅ 查詢結果（共 {len(df)} 筆）：")
        print(df)

        # 建立 ExportDB 資料夾
        os.makedirs(EXPORT_DIR, exist_ok=True)
        export_filename = generate_filename()
        export_path = os.path.join(EXPORT_DIR, export_filename)
        abs_export_path = os.path.abspath(export_path)

        # 輸出 CSV
        df.to_csv(export_path, index=False)
        print(f"📁 已輸出成 CSV：{abs_export_path}")

if __name__ == "__main__":
    main()
