import subprocess
import sys
import os
import time
import webbrowser
import requests



# ✅ 計算 Analysis.py 的絕對路徑（支援 PyInstaller 打包）
def get_script_path(filename):
    if getattr(sys, 'frozen', False):  # 是否是打包後執行
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, filename)

# ✅ 啟動 Flask Server
def start_analysis_server():
    print("🚀 Starting Analysis.py Flask server...")
    t_start = time.time()  # ← 計時起點


    python_exe = sys.executable  # ✅ 自動抓目前 Python 執行檔
    script_path = get_script_path("Analysis.py")  # ✅ 相對路徑 → 絕對路徑

    process = subprocess.Popen([python_exe, script_path])

    # 等待 Flask 啟動
    for i in range(240):
        try:
            res = requests.get("http://127.0.0.1:5000/ping")
            if res.status_code == 200:
                t_ready = time.time()
                print(f"✅ Flask server is up! 🕒 啟動耗時：{t_ready - t_start:.2f} 秒")
                break
        except:
            time.sleep(0.5)
    else:
        print("❌ Flask server did not start in time.")
        return None

    webbrowser.open("http://127.0.0.1:5000")
    return process, t_ready - t_start

# ✅ 可選：啟動後發送初始化 POST 請求
def start_analysis_action():
    data = {"action": "start"}
    try:
        response = requests.post("http://127.0.0.1:5000/perform-action", json=data)
        if response.status_code == 200:
            print("🎉 Response from server:", response.json())
        else:
            print(f"⚠️ Server responded with status code: {response.status_code}")
    except Exception as e:
        print(f"❌ Error while contacting server: {e}")

# ✅ 主程式
if __name__ == "__main__":
    total_start = time.time()
    process, launch_time = start_analysis_server()
    if process:
        start_analysis_action()
        total_time = time.time() - total_start
        print(f"\n🟢 ✅ 網頁開啟與啟動總耗時：{total_time:.2f} 秒")
