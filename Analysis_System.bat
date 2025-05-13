@echo off
@chcp 65001 >nul
cd /d %~dp0
color 0A
title ☁ Microsoft Analytics 啟動器

echo.
echo ╔══════════════════════════════════════════════╗
echo ║      Microsoft Analytics 系統啟動中...       ║
echo ╚══════════════════════════════════════════════╝
echo.



:: ⏳ 顯示 loading 提示視窗（5 秒自動關閉）
start powershell -NoLogo -WindowStyle Hidden -Command ^
  "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('系統正在啟動中，請稍候...','🚀 Microsoft Analytics',0,64)"

:: 🐍 設定虛擬環境 Python 執行檔
set "PYTHON_EXE=C:\Users\a-timmylin\MicrosoftCode\InternEnv\Scripts\python.exe"

:: ❌ 檢查 Python 是否存在
if not exist "%PYTHON_EXE%" (
    echo.
    echo ❌ 無法啟動：找不到虛擬環境 Python！
    echo 🔎 請確認此路徑是否正確：
    echo     %PYTHON_EXE%
    echo.
    pause
    exit /b
)

:: 🚀 啟動 Flask 系統
echo.
echo 🔄 啟動 Flask 主程式中，請稍候...
start "" "%PYTHON_EXE%" run_analysis.py

echo.
echo ✅ 系統已啟動，請稍候瀏覽器開啟頁面。
echo 🔗 預設網址： http://127.0.0.1:5000
echo.
pause
