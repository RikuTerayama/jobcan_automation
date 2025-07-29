#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import uuid
import threading
import tempfile
import shutil
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_file

from utils import allowed_file, create_template_excel
from automation import process_jobcan_automation

app = Flask(__name__)

# アップロードフォルダの設定
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ジョブの状態を管理（スレッドセーフな辞書）
jobs = {}
jobs_lock = threading.Lock()

# アクティブなPlaywrightインスタンスを管理
active_browsers = {}
browser_lock = threading.Lock()

def get_user_session_dir(job_id):
    """ユーザーごとの一時ディレクトリを取得"""
    session_dir = os.path.join(tempfile.gettempdir(), f'jobcan_session_{job_id}')
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
    return session_dir

def cleanup_user_session(job_id):
    """ユーザーセッションのクリーンアップ"""
    try:
        session_dir = get_user_session_dir(job_id)
        if os.path.exists(session_dir):
            shutil.rmtree(session_dir)
    except Exception as e:
        print(f"セッションクリーンアップエラー: {e}")

def validate_input_data(email, password, file):
    """入力データの検証"""
    errors = []
    
    # メールアドレスの検証
    if not email or '@' not in email or '.' not in email:
        errors.append("有効なメールアドレスを入力してください")
    
    # パスワードの検証
    if not password or len(password) < 1:
        errors.append("パスワードを入力してください")
    
    # ファイルサイズの検証（10MB制限）
    if file and hasattr(file, 'content_length'):
        if file.content_length > 10 * 1024 * 1024:  # 10MB
            errors.append("ファイルサイズが大きすぎます（10MB以下にしてください）")
    
    return errors

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ping')
def ping():
    return jsonify({'status': 'ok', 'message': 'pong'})

@app.route('/health')
def health():
    from utils import pandas_available, openpyxl_available, playwright_available
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'pandas_available': pandas_available,
        'openpyxl_available': openpyxl_available,
        'playwright_available': playwright_available
    })

@app.route('/ready')
def ready():
    from utils import pandas_available, openpyxl_available, playwright_available
    return jsonify({
        'status': 'ready',
        'timestamp': datetime.now().isoformat(),
        'dependencies': {
            'pandas': pandas_available,
            'openpyxl': openpyxl_available,
            'playwright': playwright_available
        }
    })

@app.route('/test')
def test():
    return jsonify({
        'status': 'ok',
        'message': 'Test endpoint working',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/download-template')
def download_template():
    try:
        template_file = create_template_excel()
        return send_file(
            template_file,
            as_attachment=True,
            download_name='jobcan_template.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        return jsonify({'error': f'テンプレートファイルの作成に失敗しました: {str(e)}'})

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        # 入力データの検証
        if 'file' not in request.files:
            return jsonify({'error': 'ファイルが選択されていません'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'ファイルが選択されていません'})
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Excelファイル（.xlsx, .xls）のみアップロード可能です'})
        
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        # 入力データの詳細検証
        validation_errors = validate_input_data(email, password, file)
        if validation_errors:
            return jsonify({'error': '入力エラー: ' + '; '.join(validation_errors)})
        
        # 同時実行数の制限チェック
        with jobs_lock:
            active_jobs = len([j for j in jobs.values() if j.get('status') == 'running'])
            if active_jobs >= 5:  # 最大5つの同時実行を制限
                return jsonify({'error': '現在処理中のジョブが多すぎます。しばらく待ってから再試行してください'})
        
        # ユーザーセッション用の一時ディレクトリを作成
        job_id = str(uuid.uuid4())
        session_dir = get_user_session_dir(job_id)
        
        # ファイルを保存（タイムスタンプ付きで一意性を確保）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = f"{job_id}_{timestamp}.xlsx"
        file_path = os.path.join(session_dir, filename)
        file.save(file_path)
        
        # ジョブ情報を初期化（スレッドセーフ）
        with jobs_lock:
            jobs[job_id] = {
                'status': 'running',
                'logs': [],
                'progress': 0,
                'start_time': datetime.now().timestamp(),
                'login_status': 'not_started',
                'login_message': 'ログイン処理が開始されていません',
                'session_dir': session_dir,
                'file_path': file_path,
                'email_hash': hash(email)  # 個人情報はハッシュ化
            }
        
        # バックグラウンドで処理を実行
        def run_automation():
            try:
                process_jobcan_automation(job_id, email, password, file_path, jobs, session_dir)
            except Exception as e:
                with jobs_lock:
                    if job_id in jobs:
                        jobs[job_id]['status'] = 'error'
                        jobs[job_id]['login_message'] = f'処理中にエラーが発生しました: {str(e)}'
            finally:
                # 処理完了後のクリーンアップ
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    cleanup_user_session(job_id)
                except Exception as cleanup_error:
                    print(f"クリーンアップエラー: {cleanup_error}")
        
        thread = threading.Thread(target=run_automation)
        thread.daemon = True  # メインプロセス終了時に自動終了
        thread.start()
        
        return jsonify({
            'job_id': job_id,
            'message': '処理を開始しました',
            'status_url': f'/status/{job_id}'
        })
        
    except Exception as e:
        return jsonify({'error': f'予期しないエラーが発生しました: {str(e)}'})

@app.route('/status/<job_id>')
def get_status(job_id):
    try:
        with jobs_lock:
            if job_id not in jobs:
                return jsonify({'error': 'ジョブが見つかりません'})
            
            job = jobs[job_id]
            
            # ログイン結果の詳細情報を取得
            login_status = job.get('login_status', 'unknown')
            login_message = job.get('login_message', 'ログイン状態が不明です')
            
            # ユーザー向けの詳細メッセージを生成
            user_message = generate_user_message(job['status'], login_status, login_message, job.get('progress', 0))
            
            return jsonify({
                'status': job['status'],
                'progress': job.get('progress', 0),
                'step_name': job.get('step_name', ''),
                'current_data': job.get('current_data', 0),
                'total_data': job.get('total_data', 0),
                'logs': job.get('logs', []),
                'start_time': job.get('start_time', 0),
                'login_status': login_status,
                'login_message': login_message,
                'user_message': user_message
            })
    except Exception as e:
        return jsonify({'error': f'ステータス取得エラー: {str(e)}'})

def generate_user_message(status, login_status, login_message, progress):
    """ユーザー向けの詳細メッセージを生成"""
    
    if status == 'error':
        return f"❌ エラーが発生しました: {login_message}"
    
    if status == 'completed':
        if login_status == 'success':
            return "✅ ログイン成功 → 打刻実行 → 各日付完了"
        elif login_status == 'captcha_detected':
            return "⚠️ CAPTCHA（画像認証）が表示されています。手動でのログインが必要です"
        elif login_status in ['login_error', 'login_failed']:
            return f"⚠️ ログインに失敗しました: {login_message}"
        elif login_status == 'account_restricted':
            return f"⚠️ アカウントに制限があります: {login_message}"
        elif login_status == 'timeout_error':
            return "⚠️ ページの読み込みがタイムアウトしました。ネットワーク接続を確認してください"
        elif login_status == 'browser_launch_error':
            return "⚠️ ブラウザの起動に失敗しました。システム環境を確認してください"
        elif login_status == 'playwright_unavailable':
            return "⚠️ ブラウザ自動化機能が利用できません。ローカル環境での実行を推奨します"
        else:
            return f"⚠️ 処理は完了しましたが、ログインに問題がありました: {login_message}"
    
    # 処理中のメッセージ（進捗に応じて詳細化）
    if progress == 1:
        return "🔄 初期化中..."
    elif progress == 2:
        return "🔄 Excelファイル読み込み中..."
    elif progress == 3:
        return "🔄 データ検証中..."
    elif progress == 4:
        return "🔄 ブラウザ起動中..."
    elif progress == 5:
        if login_status == 'success':
            return "🔄 ログイン成功 → データ入力処理中..."
        elif login_status in ['login_error', 'login_failed']:
            return f"🔄 ログインに失敗: {login_message}"
        else:
            return "🔄 Jobcanログイン中..."
    elif progress == 6:
        if login_status == 'success':
            return "🔄 ログイン成功 → 打刻データ入力中..."
        else:
            return "🔄 データ入力処理中（シミュレーションモード）..."
    elif progress == 7:
        return "🔄 最終確認中..."
    elif progress == 8:
        return "🔄 処理完了中..."
    else:
        if login_status == 'success':
            return "🔄 処理中... ログインに成功しました"
        elif login_status in ['login_error', 'login_failed']:
            return f"🔄 処理中... ログインに失敗: {login_message}"
        else:
            return "🔄 処理中..."

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000))) 
