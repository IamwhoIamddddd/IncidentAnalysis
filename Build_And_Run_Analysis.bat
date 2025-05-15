@echo off
@chcp 65001 >nul
cd /d %~dp0
setlocal enabledelayedexpansion

echo 🔍 啟用虛擬環境 InternEnv...
set "PYTHON_EXE=%cd%\InternEnv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo.
    echo ❌ 找不到虛擬環境 Python 可執行檔！
    echo 🔎 請確認路徑是否正確：
    echo     %PYTHON_EXE%
    echo.
    pause
    exit /b
)

echo 🧹 清理舊的打包結果（dist/ 和 build/）...
rmdir /s /q dist
rmdir /s /q build
rmdir /s /q build_log >nul 2>nul
del Analysis.spec >nul 2>nul
mkdir build_log

echo 🛠️ 開始打包 Analysis.py 系統（OneFile 模式）...
echo ▶ 請稍候，正在處理...

:: ⏳ 執行 PyInstaller 並導出 log
"%PYTHON_EXE%" -m PyInstaller --noconfirm --onefile ^
--noupx ^
--hidden-import encodings ^
--hidden-import site ^
--hidden-import _bootlocale ^
--hidden-import flask_session ^
--add-data "%cd%\\templates;templates" ^
--add-data "%cd%\\static;static" ^
--add-data "%cd%\\cache;cache" ^
--add-data "%cd%\\uploads;uploads" ^
--add-data "%cd%\\json_data;json_data" ^
--add-data "%cd%\\cluster_excels;cluster_excels" ^
--add-data "%cd%\\excel_result_Clustered;excel_result_Clustered" ^
--add-data "%cd%\\excel_result_Unclustered;excel_result_Unclustered" ^
--add-data "%cd%\\gpt_utils.py;." ^
--add-data "%cd%\\SmartScoring.py;." ^
Analysis.py > build_log\build_log.txt 2>&1

:: ✅ 檢查結果
if exist dist\Analysis.exe (
    echo.
    echo ✅ 打包完成！
    echo 📁 執行檔已建立於 dist\Analysis.exe
    echo 🚀 正在啟動 Flask 系統...
    start cmd /k dist\Analysis.exe
) else (
    echo.
    echo ❌ 打包失敗！
    echo 🔍 請開啟 build_log\build_log.txt 查看錯誤原因...
    echo.
    notepad build_log\build_log.txt
)

pause
