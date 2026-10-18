@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ===================================================
echo X(Twitter) Bot 個別ウィンドウ一括起動スクリプト
echo ===================================================
echo 5つのアカウントを独立したウィンドウで起動します...
echo.

set PYTHON_CMD="%~dp0.venv\Scripts\python.exe"

start "Bot [KEIBA]" cmd /k "%PYTHON_CMD% main.py --mode keiba"
start "Bot [FITNESS_JP]" cmd /k "%PYTHON_CMD% main.py --mode goutraining-jp"
start "Bot [FITNESS_EN]" cmd /k "%PYTHON_CMD% main.py --mode goutraining-eng"
start "Bot [RICE]" cmd /k "%PYTHON_CMD% main.py --mode rice"
start "Bot [ANIPATH]" cmd /k "%PYTHON_CMD% main.py --mode anipath"

echo すべてのBotを別ウィンドウで起動しました。
echo このウィンドウは閉じて構いません。
pause
