@echo off
echo Jobcan勤怠打刻自動申請ツール - セットアップスクリプト
echo ================================================

echo.
echo 1. Pythonのインストール確認...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Pythonがインストールされていません。
    echo Python 3.8以上をインストールしてください。
    echo ダウンロード: https://www.python.org/downloads/
    echo.
    echo インストール後、このスクリプトを再実行してください。
    pause
    exit /b 1
)

echo Pythonがインストールされています。
python --version

echo.
echo 2. 依存関係のインストール...
pip install -r requirements.txt

echo.
echo 3. Playwrightブラウザのインストール...
playwright install chromium

echo.
echo 4. サンプルデータの作成...
python sample_data.py

echo.
echo セットアップが完了しました！
echo.
echo 使用方法:
echo   python jobcan_bot.py sample_attendance.xlsx
echo.
echo 初回ログイン時:
echo   python jobcan_bot.py sample_attendance.xlsx --email your-email@example.com --password your-password --save-credentials
echo.
pause 