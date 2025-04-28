# 匯入 subprocess 模組，用於執行子程序
import subprocess
import time
import webbrowser
import requests

# 啟動 Analysis.py 的 Flask 伺服器
def start_analysis_server():
    print("🚀 Starting Analysis.py Flask server...")
    process = subprocess.Popen([
        r"C:\Users\a-timmylin\MicrosoftCode\InternEnv\Scripts\python.exe", "Analysis.py"
    ])

    # 等待伺服器啟動（最多等 10 秒）
    for i in range(60):
        try:
            res = requests.get("http://127.0.0.1:5000/ping")
            if res.status_code == 200:
                print("✅ Flask server is up!")
                break
        except:
            time.sleep(0.5)
    else:
        print("❌ Flask server did not start in time.")
        return None

    webbrowser.open("http://127.0.0.1:5000")
    return process

# 發送 POST 請求以執行動作
def start_analysis_action():
    data = {"action": "start"}
    try:
        response = requests.post('http://127.0.0.1:5000/perform-action', json=data)
        if response.status_code == 200:
            print("🎉 Response from server:", response.json())
        else:
            print(f"⚠️ Server responded with status code: {response.status_code}")
    except Exception as e:
        print(f"❌ Error while contacting server: {e}")

# 主程式
if __name__ == '__main__':
    process = start_analysis_server()
    if process:
        start_analysis_action()