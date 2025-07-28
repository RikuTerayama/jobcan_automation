import os
import uuid
import threading
from flask import Flask, request, render_template, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import pandas as pd
from datetime import datetime
import time

# カスタムモジュールをインポート
from jobcan_automation import JobcanAutomation
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
            'start_time': datetime.now().isoformat(),
            'progress': {
                'current_step': 0,
                'total_steps': 0,
                'current_data': 0,
                'total_data': 0
            }
        }
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    jobs[job_id]['logs'].append(f"[{timestamp}] {message}")
    print(f"[{job_id}] {message}")
    
    # 進捗情報を更新
    if "ステップ" in message:
        if "ステップ1" in message:
            jobs[job_id]['progress']['current_step'] = 1
        elif "ステップ2" in message:
            jobs[job_id]['progress']['current_step'] = 2
        elif "ステップ3" in message:
            jobs[job_id]['progress']['current_step'] = 3
        elif "ステップ4" in message:
            jobs[job_id]['progress']['current_step'] = 4
        elif "ステップ5" in message:
            jobs[job_id]['progress']['current_step'] = 5
        elif "ステップ6" in message:
            jobs[job_id]['progress']['current_step'] = 6

def get_job_logs(job_id: str):
    """ジョブログを取得"""
    return jobs.get(job_id, {}).get('logs', [])

def get_job_progress(job_id: str):
    """ジョブ進捗を取得"""
    return jobs.get(job_id, {}).get('progress', {})

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

def run_automation(job_id: str, email: str, password: str, file_path: str):
    """自動化を実行"""
    try:
        return process_jobcan_automation(job_id, email, password, file_path)
    except Exception as e:
        error_msg = f"自動化でエラー: {e}"
        add_job_log(job_id, error_msg)
        jobs[job_id]['status'] = 'error'
        return False

def process_jobcan_automation(job_id: str, email: str, password: str, file_path: str):
    """Jobcan自動化処理（同期版）"""
    try:
        add_job_log(job_id, "=== Jobcan自動化を開始します ===")
        jobs[job_id]['status'] = 'running'
        
        # Railway環境の情報をログに出力
        add_job_log(job_id, f"🔧 実行環境: {os.environ.get('RAILWAY_ENVIRONMENT', 'local')}")
        add_job_log(job_id, f"🔧 Python バージョン: {os.sys.version}")
        
        # Playwrightブラウザを確保
        add_job_log(job_id, "🔧 Playwrightブラウザを確保中...")
        try:
            browser_result = ensure_playwright_browser()
            if browser_result:
                add_job_log(job_id, "✅ Playwrightブラウザの確保が完了しました")
            else:
                add_job_log(job_id, "⚠️ Playwrightブラウザの確保に問題がありましたが、続行します")
        except Exception as browser_error:
            add_job_log(job_id, f"⚠️ Playwrightブラウザの確保でエラー: {browser_error}")
            add_job_log(job_id, "🔄 ブラウザの確保をスキップして続行します")
        
        # Railway環境での追加情報をログに出力
        add_job_log(job_id, f"🔧 現在のディレクトリ: {os.getcwd()}")
        add_job_log(job_id, f"🔧 利用可能なメモリ: {psutil.virtual_memory().available // (1024**3)} GB")
        add_job_log(job_id, f"🔧 CPU使用率: {psutil.cpu_percent()}%")
        
        # 自動化インスタンスを作成
        add_job_log(job_id, "🤖 自動化インスタンスを作成中...")
        try:
            automation = JobcanAutomation(headless=True)
            add_job_log(job_id, "✅ 自動化インスタンスの作成が完了しました")
        except Exception as automation_error:
            add_job_log(job_id, f"❌ 自動化インスタンスの作成に失敗: {automation_error}")
            jobs[job_id]['status'] = 'error'
            return False
        
        try:
            # ブラウザを起動
            add_job_log(job_id, "🌐 ブラウザを起動中...")
            try:
                automation.start_browser()
                add_job_log(job_id, "✅ ブラウザの起動が完了しました")
            except Exception as browser_start_error:
                add_job_log(job_id, f"❌ ブラウザの起動に失敗: {browser_start_error}")
                jobs[job_id]['status'] = 'error'
                return False
            
            # Jobcanにログイン
            add_job_log(job_id, "🔐 Jobcanにログイン中...")
            try:
                login_success = automation.login_to_jobcan(email, password)
                
                if not login_success:
                    add_job_log(job_id, "❌ ログインに失敗しました")
                    jobs[job_id]['status'] = 'error'
                    return False
                
                add_job_log(job_id, "✅ ログインに成功しました")
            except Exception as login_error:
                add_job_log(job_id, f"❌ ログイン処理でエラー: {login_error}")
                jobs[job_id]['status'] = 'error'
                return False
            
            # 勤怠ページに移動
            add_job_log(job_id, "📊 勤怠ページに移動中...")
            try:
                automation.navigate_to_attendance()
                add_job_log(job_id, "✅ 勤怠ページへの移動が完了しました")
            except Exception as navigation_error:
                add_job_log(job_id, f"❌ 勤怠ページへの移動に失敗: {navigation_error}")
                jobs[job_id]['status'] = 'error'
                return False
            
            # Excelファイルを読み込み
            add_job_log(job_id, "📁 Excelファイルを読み込み中...")
            try:
                data = load_excel_data(file_path)
                
                if not data:
                    add_job_log(job_id, "❌ Excelファイルの読み込みに失敗しました")
                    jobs[job_id]['status'] = 'error'
                    return False
                
                # 進捗情報を更新
                jobs[job_id]['progress']['total_data'] = len(data)
                add_job_log(job_id, f"📊 処理対象データ数: {len(data)}")
                
                # 勤怠データを処理
                add_job_log(job_id, "🔄 勤怠データを処理中...")
                processed_data = automation.process_attendance_data(data)
                
            except Exception as data_error:
                add_job_log(job_id, f"❌ データ処理でエラー: {data_error}")
                jobs[job_id]['status'] = 'error'
                return False
            
            # 結果を分析
            try:
                success_count = len([d for d in processed_data if d.get('status') == 'success'])
                error_count = len(processed_data) - success_count
                
                add_job_log(job_id, f"✅ 処理が完了しました")
                add_job_log(job_id, f"📊 成功: {success_count}件, 失敗: {error_count}件")
                jobs[job_id]['status'] = 'completed'
                return True
                
            except Exception as analysis_error:
                add_job_log(job_id, f"❌ 結果分析でエラー: {analysis_error}")
                jobs[job_id]['status'] = 'error'
                return False
            
        except Exception as process_error:
            add_job_log(job_id, f"❌ 処理中にエラーが発生: {process_error}")
            jobs[job_id]['status'] = 'error'
            return False
        finally:
            # ブラウザを閉じる
            try:
                add_job_log(job_id, "🔒 ブラウザを閉じています...")
                automation.close()
                add_job_log(job_id, "✅ ブラウザを正常に閉じました")
            except Exception as close_error:
                add_job_log(job_id, f"⚠️ ブラウザの終了でエラー: {close_error}")
            
    except Exception as e:
        error_msg = f"❌ 予期しないエラーが発生しました: {e}"
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
        try:
            thread = threading.Thread(
                target=run_automation,
                args=(job_id, email, password, file_path)
            )
            thread.daemon = True
            thread.start()
            
            add_job_log(job_id, "✅ バックグラウンド処理を開始しました")
            
        except Exception as e:
            error_msg = f"❌ バックグラウンド処理の開始に失敗: {e}"
            add_job_log(job_id, error_msg)
            return jsonify({
                'success': False,
                'error': error_msg
            })
        
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
            'diagnosis': job_data.get('diagnosis', {}),
            'progress': job_data.get('progress', {}),
            'start_time': job_data.get('start_time', ''),
            'current_time': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        })

@app.route('/health')
def health_check():
    """ヘルスチェックエンドポイント"""
    try:
        # 基本的なシステム情報を取得
        import psutil
        import os
        
        system_info = {
            'status': 'healthy',
            'python_version': os.sys.version,
            'memory_usage': psutil.virtual_memory().percent,
            'cpu_usage': psutil.cpu_percent(),
            'disk_usage': psutil.disk_usage('/').percent,
            'environment': os.environ.get('RAILWAY_ENVIRONMENT', 'local'),
            'port': os.environ.get('PORT', '5000')
        }
        
        return jsonify(system_info)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # 開発環境ではデバッグモードで実行
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=debug_mode) 
