# 匯入 Flask 框架及相關模組
from flask import Flask, request, jsonify, render_template, session, send_file
# 匯入數學運算模組
import math
import json
# 匯入 pandas 用於處理 Excel 資料
import pandas as pd
# 匯入 os 模組處理檔案與路徑
import os
# 匯入正則表達式模組
import re
# 匯入 webbrowser 用於開啟網頁
import webbrowser
# 匯入 traceback 用於錯誤追蹤
import traceback
# 匯入 Werkzeug 的工具函數確保檔案名稱安全
from werkzeug.utils import secure_filename

# ✅ 匯入語意分析模組
from SmartScoring import is_high_risk, is_escalated, is_multi_user, extract_keywords, recommend_solution
# ✅ 預先 encode 一筆資料以加速首次請求
from SmartScoring import bert_model  # 確保你有從 SmartScoring 載入模型
from tqdm import tqdm
from sentence_transformers import util
# ✅ 匯入關鍵字抽取模組
from datetime import datetime


print("🔥 預熱語意模型中...")
bert_model.encode("warmup")  # 預熱一次，避免第一次使用太慢
print("✅ 模型已預熱完成")

# 建立 Flask 應用
app = Flask(__name__)
# 設定應用的密鑰，用於 session 加密
app.secret_key = 'gwegweqgt22e'
# 設定 session 儲存方式為檔案系統
app.config['SESSION_TYPE'] = 'filesystem'

# ------------------------------------------------------------------------------
# 設定上傳資料夾與大小限制（10MB）
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 限制檔案大小為 10MB
ALLOWED_EXTENSIONS = {'xlsx'}  # 僅允許上傳 xlsx 檔案


basedir = os.path.abspath(os.path.dirname(__file__))  # 取得當前 app.py 的絕對目錄


# 確保上傳資料夾存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(basedir, 'json_data'), exist_ok=True)
os.makedirs(os.path.join(basedir, 'excel_result'), exist_ok=True)


# 判斷是否允許的檔案格式
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ------------------------------------------------------------------------------

# 定義函數：處理特殊值（如 NaN、None 等）
def safe_value(val):
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return 0
    elif val is None:
        return None
    elif isinstance(val, str):
        return val
    else:
        return val

# ------------------------------------------------------------------------------

# 分析 Excel 資料的主邏輯
def analyze_excel(filepath):
    print(f"\n📂 讀取 Excel：{filepath}")
    df = pd.read_excel(filepath)  # 讀取 Excel 檔案
    print(f"📊 共讀取 {len(df)} 筆資料\n")
    component_counts = df['Role/Component'].value_counts()  # 計算每個角色/元件的出現次數
    df['Opened'] = pd.to_datetime(df['Opened'], errors='coerce')  # 將 'Opened' 欄位轉為日期格式
    results = []  # 儲存分析結果
    configuration_item_counts = df['Configuration item'].value_counts()  # 計算每個配置項的出現次數
    configuration_item_max = configuration_item_counts.max()  # 找出配置項的最大出現次數
    analysis_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"📅 分析時間：{analysis_time}")

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="📊 分析進度"):
        print(f"\n🔍 第 {idx + 1} 筆分析中...")
        description_text = row.get('Description', 'not filled')  # 取得描述文字
        short_description_text = row.get('Short description', 'not filled') # 取得簡短描述文字
        close_note_text = row.get('Close notes', 'not filled')  # 取得關閉註解文字
        print(f"📄 描述：{description_text}")
        print(f"🔑 簡短描述：{short_description_text}")
        print(f"🔒 關閉註解：{close_note_text}")
        # 這裡可以加入對描述文字的預處理，例如去除多餘空格、轉為小寫等
        # description_text = normalize_text(description_text)  # 標準化文字    


        #這裡要改成使用語意分析模型

        keyword_score = is_high_risk(short_description_text)  # 計算關鍵字分數
        print(f"⚠️ 高風險語意分數（keyword_score）：{keyword_score}")
        user_impact_score = is_multi_user(description_text)  # 計算使用者影響分數
        print(f"👥 多人影響分數（user_impact_score）：{user_impact_score}")
        escalation_score = is_escalated(close_note_text)  # 計算升級處理分數
        print(f"📈 升級處理分數（escalation_score）：{escalation_score}")



        config_raw = configuration_item_counts.get(row.get('Configuration item'), 0)  # 取得配置項的出現次數
        configuration_item_freq = config_raw / configuration_item_max if configuration_item_max > 0 else 0  # 計算配置項頻率

        role_comp = row.get('Role/Component', 'not filled')  # 取得角色/元件
        count = component_counts.get(role_comp, 0)  # 取得角色/元件的出現次數
        if count >= 5:
            role_component_freq = 3
        elif count >= 3:
            role_component_freq = 2
        elif count == 2:
            role_component_freq = 1
        else:
            role_component_freq = 0

        this_time = row.get('Opened', 'not filled')  # 取得開啟時間
        if pd.isnull(this_time):  # 如果開啟時間為空
            time_cluster_score = 1
        else:
            others = df[df['Role/Component'] == role_comp]  # 篩選相同角色/元件的資料
            close_events = others[(others['Opened'] >= this_time - pd.Timedelta(hours=24)) &
                                  (others['Opened'] <= this_time + pd.Timedelta(hours=24))]  # 找出 24 小時內的事件
            count_cluster = len(close_events)  # 計算事件數量
            if count_cluster >= 3:
                time_cluster_score = 3
            elif count_cluster == 2:
                time_cluster_score = 2
            else:
                time_cluster_score = 1

        # 計算嚴重性分數
        severity_score = round(keyword_score * 5 + user_impact_score * 3.0 + escalation_score * 2, 2)
        # 計算頻率分數
        frequency_score = round(configuration_item_freq * 5.0 + role_component_freq * 3.0 + time_cluster_score * 2.0, 2)
        print("🧠 頻率分數細項：")
        print(f"🔸 配置項（Configuration Item）出現比例：{configuration_item_freq:.2f}，乘以權重後得 {configuration_item_freq * 5:.2f} 分")
        print(f"🔸 元件或角色（Role/Component）在整體中出現 {count} 次 → 給 {role_component_freq * 3:.2f} 分")
        print(f"🔸 在 24 小時內有 {count_cluster} 筆同元件事件 → 群聚加分 {time_cluster_score * 2:.2f} 分")
        print(f"📊 頻率總分 = {frequency_score}\n")

        # 計算影響分數
        impact_score = round(severity_score + frequency_score, 2)
        risk_level = get_risk_level(impact_score)
        print(f"📉 嚴重性：{severity_score}, 頻率：{frequency_score}, 總分：{impact_score} → 分級：{risk_level}")

        # 儲存分析結果
        results.append({
            'id': safe_value(row.get('Incident') or row.get('Number')),
            'configurationItem': safe_value(row.get('Configuration item')),
            'severityScore': safe_value(severity_score),
            'frequencyScore': safe_value(frequency_score),
            'impactScore': safe_value(impact_score),
            'riskLevel': safe_value(get_risk_level(impact_score)),
            'solution': safe_value(row.get('Close notes') or '無提供解法'),
            'location': safe_value(row.get('Location')),
            'analysisTime': analysis_time
        })
        solution_text = row.get('Close notes') or '無提供解法'
        recommended = recommend_solution(short_description_text)
        keywords = extract_keywords(short_description_text)

        print(f"💡 建議解法：{recommended}")
        print(f"🔑 抽取關鍵字：{keywords}")
        print("—" * 250)  # 分隔線


    print("\n✅ 所有資料分析完成！")
    return results

# 根據分數判斷風險等級
def get_risk_level(score):
    level = ''
    if score >= 18:
        level = '高風險'
    elif score >= 12:
        level = '中風險'
    elif score >= 6:
        level = '低風險'
    else:
        level = '忽略'
    
    print(f"📊 impactScore: {score} → 分級：{level}")  # 印出每次分級結果
    return level

# ------------------------------------------------------------------------------

# 定義首頁路由
@app.route('/')
def index():
    return render_template('FrontEnd.html')  # 渲染首頁模板

# 定義結果頁面路由
@app.route('/result')
def result_page():
    data = session.get('analysis_data', [])  # 從 session 取得分析結果
    return render_template('result.html', data=data)  # 渲染結果頁面

# 定義歷史紀錄頁面路由
@app.route('/history')
def history_page():
    return render_template('history.html')  # 渲染歷史紀錄頁面

# ------------------------------------------------------------------------------




@app.route('/ping')
def ping():
    return "pong", 200


# 定義檔案上傳路由
@app.route('/upload', methods=['POST'])
def upload_file():
    print("📥 收到上傳請求")  # 紀錄請求

    if 'file' not in request.files:  # 檢查是否有檔案欄位
        print("❌ 沒有 file 欄位")
        return jsonify({'error': '沒有找到檔案欄位'}), 400

    file = request.files['file']  # 取得檔案
    if file.filename == '':  # 檢查檔案名稱是否為空
        print("⚠️ 檔案名稱為空")
        return jsonify({'error': '未選擇檔案'}), 400

    if not allowed_file(file.filename):  # 檢查檔案格式是否允許
        print("⚠️ 檔案類型不符")
        return jsonify({'error': '請上傳 .xlsx 檔案'}), 400
    


        # 產生時間戳記與檔名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    uid = f"result_{timestamp}" # 例如 result_20250423_152301 分析結果檔名稱
    original_filename = f"original_{timestamp}.xlsx" # 例如 original_20250423_152301.xlsx 原始黨名稱
    original_path = os.path.join('uploads', original_filename)

    try:
        file.save(original_path)  # 儲存原始檔案
        print(f" 原始檔已儲存：{original_path}")
    except Exception as e:
        return jsonify({'error': f'儲存原始檔失敗：{str(e)}'}), 500

    try:
        result = analyze_excel(original_path)  # 分析檔案

        save_analysis_files(result, uid)  # 同時儲存 JSON + Excel

        print(f"✅ 分析完成，共 {len(result)} 筆")
        session['analysis_data'] = result  # 儲存分析結果到 session

        return jsonify({'data': result, 'uid': uid}), 200
    


    except Exception as e:
        print(f"❌ 分析時發生錯誤：{e}")
        traceback.print_exc()  # 印出完整錯誤堆疊
        return jsonify({'error': str(e)}), 500
    





def save_analysis_files(result, uid):
    # 儲存 JSON
    json_path = os.path.join(basedir, 'json_data', f"{uid}.json")
    print(f"📝 預計儲存 JSON：{json_path}")  # ✅ 加在這邊
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("✅ JSON 檔案已寫入成功")


    # 儲存分析報表 Excel
    df = pd.DataFrame(result)
    excel_path = os.path.join(basedir, 'excel_result', f"{uid}.xlsx")
    df.to_excel(excel_path, index=False)
    if os.path.exists(json_path):
        print("✅ JSON 檔案已成功儲存")
    else:
        print("❌ JSON 檔案儲存失敗！")
    print(f"✅ 分析報表已儲存：{excel_path}")  # ✅ 加在這邊

    print("📁 JSON 絕對路徑：", os.path.abspath(json_path))
    print("📁 Excel 絕對路徑：", os.path.abspath(excel_path))



@app.route('/get-results')
def get_results():
    folder = 'json_data'  # 資料夾名稱
    results = []

    if not os.path.exists(folder):
        return jsonify({'error': f'資料夾不存在：{folder}'}), 404

    for filename in os.listdir(folder):
        if filename.endswith('.json'):
            filepath = os.path.join(folder, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        results.extend(data)
                    else:
                        print(f"⚠️ {filename} 格式錯誤（非 list），已略過")
            except Exception as e:
                print(f"❌ 讀取 {filename} 時錯誤：{e}")

    return jsonify(results)




# ✅ JSON 預覽路由：提供 `/get-json?file=xxxx.json`
@app.route('/get-json', methods=['GET'])
def get_json_file():
    filename = request.args.get('file')  # e.g., result_20250423_152301.json
    if not filename:
        return jsonify({'error': '缺少 file 參數'}), 400

    json_path = os.path.join('json_data', filename)
    if os.path.exists(json_path):
        return send_file(json_path, as_attachment=False)
    else:
        return jsonify({'error': '找不到對應的 JSON 檔案'}), 404


# ✅ 分析 Excel 下載路由：提供 `/download-excel?uid=xxxx`
@app.route('/download-excel', methods=['GET'])
def download_excel_file():
    uid = request.args.get('uid')  # e.g., result_20250423_152301
    if not uid:
        return jsonify({'error': '缺少 uid 參數'}), 400

    excel_path = os.path.join('excel_result', f"{uid}.xlsx")
    if os.path.exists(excel_path):
        return send_file(excel_path, as_attachment=True)
    else:
        return jsonify({'error': '找不到對應的 Excel 檔案'}), 404

@app.route('/download-original', methods=['GET'])
def download_original_excel():
    uid = request.args.get('uid')  # uid = result_20250423_152301
    if not uid:
        return jsonify({'error': '缺少 uid 參數'}), 400

    # 取出對應的時間戳
    timestamp = uid.replace('result_', '')
    original_filename = f'original_{timestamp}.xlsx'
    original_path = os.path.join('uploads', original_filename)

    if os.path.exists(original_path):
        return send_file(original_path, as_attachment=True)
    else:
        return jsonify({'error': '找不到對應的原始檔案'}), 404


# ------------------------------------------------------------------------------

# 定義檔案列表路由
@app.route('/files', methods=['GET'])
def get_file_list():
    files = os.listdir(UPLOAD_FOLDER)  # 列出上傳資料夾中的檔案
    return jsonify({'files': files}), 200

# ------------------------------------------------------------------------------

# 定義執行動作的路由
@app.route('/perform-action', methods=['POST'])
def perform_action():
    data = request.json  # 取得 JSON 資料
    action = data.get('action')  # 取得動作名稱

    if action == 'start':  # 如果動作是 'start'
        result = "Server received 'start' action and performed the task."
        print(result)
        return jsonify({'status': 'success', 'message': result}), 200
    else:  # 如果是未知動作
        result = f"Server received unknown action: {action}"
        print(result)
        return jsonify({'status': 'error', 'message': 'Unknown action!'}), 400

# ------------------------------------------------------------------------------

# 啟動 Flask 應用
if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)