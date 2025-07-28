import os
import uuid
import asyncio
import threading
from flask import Flask, request, render_template, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import pandas as pd
from datetime import datetime
import queue
import time

# カスタムモジュールをインポート
from jobcan_automation import JobcanAutomation
from async_jobcan_automation import AsyncJobcanAutomation
from utils import load_excel_data, allowed_file, ensure_playwright_browser

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# アップロードフォルダが存在しない場合は作成
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# グローバル変数
jobs = {}

def add_job_log(job_id: str, message: str):
    """ジョブログを追加"""
    if job_id not in jobs:
        jobs[job_id] = {
            'status': 'pending',
            'logs': [],
            'diagnosis': {},
            'start_time': datetime.now().isoformat()
        }
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    jobs[job_id]['logs'].append(f"[{timestamp}] {message}")
    print(f"[{job_id}] {message}")

def get_job_logs(job_id: str):
    """ジョブログを取得"""
    return jobs.get(job_id, {}).get('logs', [])

def add_job_diagnosis(job_id: str, diagnosis_data: dict):
    """ジョブ診断データを追加"""
    if job_id not in jobs:
        jobs[job_id] = {
            'status': 'pending',
            'logs': [],
            'diagnosis': {},
            'start_time': datetime.now().isoformat()
        }
    
    jobs[job_id]['diagnosis'] = diagnosis_data

def get_job_diagnosis(job_id: str):
    """ジョブ診断データを取得"""
    return jobs.get(job_id, {}).get('diagnosis', {})

def run_async_automation(job_id: str, email: str, password: str, file_path: str):
    """非同期自動化を実行"""
    try:
        # 新しいイベントループを作成
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 非同期処理を実行
        result = loop.run_until_complete(
            async_process_jobcan_automation(job_id, email, password, file_path)
        )
        
        loop.close()
        return result
        
    except Exception as e:
        error_msg = f"非同期自動化でエラー: {e}"
        add_job_log(job_id, error_msg)
        jobs[job_id]['status'] = 'error'
        return False

async def async_process_jobcan_automation(job_id: str, email: str, password: str, file_path: str):
    """非同期Jobcan自動化処理"""
    try:
        add_job_log(job_id, "Jobcan自動化を開始します")
        jobs[job_id]['status'] = 'running'
        
        # Playwrightブラウザを確保
        from async_jobcan_automation import ensure_playwright_browser
        ensure_playwright_browser()
        
        # 非同期自動化インスタンスを作成
        automation = AsyncJobcanAutomation()
        
        try:
            # ブラウザを起動
            add_job_log(job_id, "ブラウザを起動中...")
            await automation.start_browser()
            
            # Jobcanにログイン
            add_job_log(job_id, "Jobcanにログイン中...")
            login_success = await automation.login_to_jobcan(email, password)
            
            if not login_success:
                add_job_log(job_id, "ログインに失敗しました")
                jobs[job_id]['status'] = 'error'
                return False
            
            add_job_log(job_id, "ログインに成功しました")
            
            # 勤怠ページに移動
            add_job_log(job_id, "勤怠ページに移動中...")
            await automation.navigate_to_attendance()
            
            # Excelファイルを読み込み
            add_job_log(job_id, "Excelファイルを読み込み中...")
            df = pd.read_excel(file_path)
            
            # 勤怠データを処理
            add_job_log(job_id, "勤怠データを処理中...")
            await automation.process_attendance_data(df)
            
            add_job_log(job_id, "処理が完了しました")
            jobs[job_id]['status'] = 'completed'
            return True
            
        finally:
            # ブラウザを閉じる
            await automation.close()
            
    except Exception as e:
        error_msg = f"予期しないエラーが発生しました: {e}"
        add_job_log(job_id, error_msg)
        jobs[job_id]['status'] = 'error'
        return False

def process_jobcan_automation(job_id: str, email: str, password: str, file_path: str):
    """Jobcan自動化処理（同期版）"""
    try:
        add_job_log(job_id, "Jobcan自動化を開始します")
        jobs[job_id]['status'] = 'running'
        
        # Playwrightブラウザを確保
        from async_jobcan_automation import ensure_playwright_browser
        ensure_playwright_browser()
        
        # 自動化インスタンスを作成
        automation = JobcanAutomation(headless=True)
        
        try:
            # ブラウザを起動
            add_job_log(job_id, "ブラウザを起動中...")
            automation.start_browser()
            
            # Jobcanにログイン
            add_job_log(job_id, "Jobcanにログイン中...")
            login_success = automation.login_to_jobcan(email, password)
            
            if not login_success:
                add_job_log(job_id, "ログインに失敗しました")
                jobs[job_id]['status'] = 'error'
                return False
            
            add_job_log(job_id, "ログインに成功しました")
            
            # 勤怠ページに移動
            add_job_log(job_id, "勤怠ページに移動中...")
            automation.navigate_to_attendance()
            
            # Excelファイルを読み込み
            add_job_log(job_id, "Excelファイルを読み込み中...")
            data = load_excel_data(file_path)
            
            # 勤怠データを処理
            add_job_log(job_id, "勤怠データを処理中...")
            automation.process_attendance_data(data)
            
            add_job_log(job_id, "処理が完了しました")
            jobs[job_id]['status'] = 'completed'
            return True
            
        finally:
            # ブラウザを閉じる
            automation.close()
            
    except Exception as e:
        error_msg = f"予期しないエラーが発生しました: {e}"
        add_job_log(job_id, error_msg)
        jobs[job_id]['status'] = 'error'
        return False

@app.route('/')
def index():
    """メインページ"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """ファイルアップロード処理"""
    try:
        # フォームデータを取得
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        if not email or not password:
            return jsonify({
                'success': False,
                'error': 'メールアドレスとパスワードを入力してください'
            })
        
        # ファイルが存在するかチェック
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'ファイルが選択されていません'
            })
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'ファイルが選択されていません'
            })
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'Excelファイル（.xlsx）を選択してください'
            })
        
        # ファイルを保存
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # ジョブIDを生成
        job_id = str(uuid.uuid4())
        
        # ジョブを開始
        add_job_log(job_id, "アップロード処理を開始")
        
        # バックグラウンドで処理を実行
        thread = threading.Thread(
            target=run_async_automation,
            args=(job_id, email, password, file_path)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': '処理を開始しました。進捗は下記で確認できます。'
        })
        
    except Exception as e:
        error_msg = f"アップロード処理でエラーが発生しました: {e}"
        return jsonify({
            'success': False,
            'error': error_msg
        })

@app.route('/status/<job_id>')
def get_status(job_id):
    """ジョブステータスを取得"""
    try:
        job_data = jobs.get(job_id, {})
        return jsonify({
            'status': job_data.get('status', 'not_found'),
            'logs': job_data.get('logs', []),
            'diagnosis': job_data.get('diagnosis', {})
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        })

@app.route('/health')
def health_check():
    """ヘルスチェック"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    # 開発環境ではデバッグモードで実行
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=debug_mode) 
