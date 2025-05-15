@echo off
@chcp 65001 >nul
cd /d %~dp0
setlocal enabledelayedexpansion

REM === 小工具：顯示目前時間（格式 HH:MM:SS）===
set "timenow="
for /f "tokens=1-2 delims=." %%a in ("%TIME%") do set timenow=%%a

echo [%timenow%] 🔍 啟用虛擬環境 InternEnv...
set "PYTHON_EXE=%cd%\InternEnv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo.
    echo [%timenow%] ❌ 找不到虛擬環境 Python 可執行檔！
    echo [%timenow%] 🔎 請確認路徑是否正確：
    echo [%timenow%]     %PYTHON_EXE%
    echo.
    pause
    exit /b
)

echo [%timenow%] 🧹 清理舊的打包結果（dist/ 和 build/）...
rmdir /s /q dist
rmdir /s /q build
rmdir /s /q build_log >nul 2>nul
del run_analysis.spec >nul 2>nul
del Analysis.spec >nul 2>nul
mkdir build_log

echo [%timenow%] 🛠️ 開始打包 Analysis 系統（OneFile 模式）...
echo [%timenow%] ▶ 請稍候，正在處理...

REM === 關鍵指令前 echo 現在時間 ===
echo [%timenow%] ▶ 執行 PyInstaller，導出 log...

REM === 這裡改用 PowerShell Tee-Object 同步顯示＋存檔 ===
powershell -Command ^
    "& '%cd%\\InternEnv\\Scripts\\python.exe' -m PyInstaller --noconfirm --onefile --noupx --hidden-import encodings --hidden-import site --hidden-import _bootlocale --add-data '%cd%\\templates;templates' --add-data '%cd%\\static;static' --add-data '%cd%\\cache;cache' --add-data '%cd%\\uploads;uploads' --add-data '%cd%\\json_data;json_data' --add-data '%cd%\\models;models' --add-data '%cd%\\cluster_excels;cluster_excels' --add-data '%cd%\\excel_result_Clustered;excel_result_Clustered' --add-data '%cd%\\excel_result_Unclustered;excel_result_Unclustered' --add-data '%cd%\\run_analysis.py;.' --add-data '%cd%\\gpt_utils.py;.' --add-data '%cd%\\SmartScoring.py;.' --hidden-import flask_session -d all Analysis.py | Tee-Object -FilePath 'build_log\\build_log.txt'"

REM === 檢查結果並顯示進度 ===
if exist dist\Analysis.exe (
    echo.
    echo [%timenow%] ✅ 打包完成！
    echo [%timenow%] 📁 執行檔已建立於 dist\Analysis.exe
    echo [%timenow%] 🚀 正在啟動 Analysis 系統...
    start cmd /k dist\Analysis.exe
) else (
    echo.
    echo [%timenow%] ❌ 打包失敗！
    echo [%timenow%] 🔍 請開啟 build_log\build_log.txt 查看錯誤原因...
    echo.
    notepad build_log\build_log.txt
)

pause
