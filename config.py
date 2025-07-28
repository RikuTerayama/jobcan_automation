import os

# Flask設定
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
UPLOAD_FOLDER = 'uploads'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

# Jobcan設定
JOBCAN_LOGIN_URL = "https://id.jobcan.jp/users/sign_in?app_key=atd"
JOBCAN_EMPLOYEE_URL = "https://ssl.jobcan.jp/employee"

# Playwright設定
BROWSER_ARGS = [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-dev-shm-usage',
    '--disable-accelerated-2d-canvas',
    '--no-first-run',
    '--no-zygote',
    '--disable-gpu',
    '--disable-background-timer-throttling',
    '--disable-backgrounding-occluded-windows',
    '--disable-renderer-backgrounding',
    '--disable-features=TranslateUI',
    '--disable-ipc-flooding-protection',
    '--disable-background-networking',
    '--disable-default-apps',
    '--disable-sync',
    '--disable-translate',
    '--hide-scrollbars',
    '--mute-audio',
    '--no-first-run',
    '--safebrowsing-disable-auto-update',
    '--disable-client-side-phishing-detection',
    '--disable-component-update',
    '--disable-domain-reliability',
    '--disable-features=TranslateUI',
    '--disable-ipc-flooding-protection'
]

# ユーザーエージェント設定
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# HTTPヘッダー設定
HTTP_HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'ja-JP,ja;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

# ファイル拡張子設定
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

# ログ設定
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

# 開発環境設定
DEBUG = os.environ.get('FLASK_ENV') == 'development'
HOST = '0.0.0.0'
PORT = int(os.environ.get('PORT', 5000)) 
