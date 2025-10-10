#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import uuid
import threading
import tempfile
import shutil
import psutil
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_file, Response

from utils import allowed_file, create_template_excel, create_previous_month_template_excel
from automation import process_jobcan_automation

# メモリ制限設定（環境変数から取得、デフォルト値付き）
MEMORY_LIMIT_MB = int(os.getenv("MEMORY_LIMIT_MB", "450"))
MEMORY_WARNING_MB = int(os.getenv("MEMORY_WARNING_MB", "512"))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
MAX_ACTIVE_SESSIONS = int(os.getenv("MAX_ACTIVE_SESSIONS", "20"))

app = Flask(__name__)

# アップロードフォルダの設定
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 環境変数をテンプレートコンテキストに注入（AdSense設定用）
@app.context_processor
def inject_env_vars():
    """環境変数をテンプレートで使えるようにする"""
    return {
        'ADSENSE_ENABLED': os.getenv('ADSENSE_ENABLED', 'false').lower() == 'true'
    }

# ジョブの状態を管理（スレッドセーフな辞書）
jobs = {}
jobs_lock = threading.Lock()

# セッション管理とリソース監視
session_manager = {
    'active_sessions': {},
    'session_lock': threading.Lock(),
    'resource_monitor': {
        'last_check': time.time(),
        'memory_usage': 0,
        'cpu_usage': 0,
        'active_browsers': 0
    }
}

def get_system_resources():
    """システムリソースの使用状況を取得"""
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        cpu_percent = process.cpu_percent()
        
        return {
            'memory_mb': memory_info.rss / 1024 / 1024,
            'cpu_percent': cpu_percent,
            'active_sessions': len(session_manager['active_sessions'])
        }
    except ImportError:
        print("psutilが利用できません。リソース監視機能は無効化されます。")
        return {'memory_mb': 0, 'cpu_percent': 0, 'active_sessions': len(session_manager['active_sessions'])}
    except Exception as e:
        print(f"リソース監視エラー: {e}")
        return {'memory_mb': 0, 'cpu_percent': 0, 'active_sessions': len(session_manager['active_sessions'])}

def check_resource_limits():
    """リソース制限のチェック（メモリ制限チェック強化）"""
    resources = get_system_resources()
    
    warnings = []
    
    # メモリ使用量の警告（環境変数で設定可能）
    if resources['memory_mb'] > MEMORY_LIMIT_MB:
        raise RuntimeError(f"メモリ制限を超過しました: {resources['memory_mb']:.1f}MB > {MEMORY_LIMIT_MB}MB")
    elif resources['memory_mb'] > MEMORY_WARNING_MB:
        warnings.append(f"メモリ使用量が高いです: {resources['memory_mb']:.1f}MB")
    
    # アクティブセッション数の警告（環境変数で設定可能）
    if resources['active_sessions'] > MAX_ACTIVE_SESSIONS:
        warnings.append(f"アクティブセッション数が多いです: {resources['active_sessions']}個")
    
    return warnings

def create_unique_session_id():
    """ユニークなセッションIDを生成"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    session_id = f"session_{uuid.uuid4().hex}_{timestamp}"
    return session_id

def get_user_session_dir(session_id):
    """ユーザーごとの一時ディレクトリを取得（完全分離）"""
    session_dir = os.path.join(tempfile.gettempdir(), f'jobcan_session_{session_id}')
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
    return session_dir

def cleanup_user_session(session_id):
    """ユーザーセッションのクリーンアップ（完全削除）"""
    try:
        session_dir = get_user_session_dir(session_id)
        if os.path.exists(session_dir):
            shutil.rmtree(session_dir)
            print(f"セッションクリーンアップ完了: {session_id}")
    except Exception as e:
        print(f"セッションクリーンアップエラー {session_id}: {e}")

def register_session(session_id, job_id):
    """セッションを登録"""
    with session_manager['session_lock']:
        session_manager['active_sessions'][session_id] = {
            'job_id': job_id,
            'start_time': time.time(),
            'status': 'active'
        }
        print(f"セッション登録: {session_id} (ジョブ: {job_id})")

def unregister_session(session_id):
    """セッションを登録解除"""
    with session_manager['session_lock']:
        if session_id in session_manager['active_sessions']:
            del session_manager['active_sessions'][session_id]
            print(f"セッション解除: {session_id}")

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

@app.route('/privacy')
def privacy():
    """プライバシーポリシーページ"""
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    """利用規約ページ"""
    return render_template('terms.html')

@app.route('/contact')
def contact():
    """お問い合わせページ"""
    return render_template('contact.html')

@app.route('/ping')
def ping():
    return jsonify({'status': 'ok', 'message': 'pong'})

@app.route('/health')
def health():
    from utils import pandas_available, openpyxl_available, playwright_available
    
    # リソース監視情報を追加
    resources = get_system_resources()
    warnings = check_resource_limits()
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'pandas_available': pandas_available,
        'openpyxl_available': openpyxl_available,
        'playwright_available': playwright_available,
        'resources': resources,
        'warnings': warnings
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
        print("テンプレートダウンロード開始")
        template_file, error_message = create_template_excel()
        
        if error_message:
            print(f"テンプレート作成エラー: {error_message}")
            return jsonify({'error': f'テンプレートファイルの作成に失敗しました: {error_message}'}), 500
        
        if not template_file or not os.path.exists(template_file):
            print(f"テンプレートファイルが存在しません: {template_file}")
            return jsonify({'error': 'テンプレートファイルの生成に失敗しました'}), 500
        
        print(f"テンプレートファイル作成成功: {template_file}")
        return send_file(
            template_file,
            as_attachment=True,
            download_name='jobcan_template.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        print(f"テンプレートダウンロード例外: {str(e)}")
        return jsonify({'error': f'テンプレートファイルの作成に失敗しました: {str(e)}'}), 500

@app.route('/download-previous-template')
def download_previous_template():
    try:
        print("先月テンプレートダウンロード開始")
        template_file, error_message = create_previous_month_template_excel()
        
        if error_message:
            print(f"先月テンプレート作成エラー: {error_message}")
            return jsonify({'error': f'先月テンプレートファイルの作成に失敗しました: {error_message}'}), 500
        
        if not template_file or not os.path.exists(template_file):
            print(f"先月テンプレートファイルが存在しません: {template_file}")
            return jsonify({'error': '先月テンプレートファイルの生成に失敗しました'}), 500
        
        print(f"先月テンプレートファイル作成成功: {template_file}")
        return send_file(
            template_file,
            as_attachment=True,
            download_name='jobcan_previous_month_template.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        print(f"先月テンプレートダウンロード例外: {str(e)}")
        return jsonify({'error': f'先月テンプレートファイルの作成に失敗しました: {str(e)}'}), 500

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
        
        # ファイルサイズ制限（環境変数で設定可能）
        file.seek(0, 2)  # ファイルの末尾に移動
        file_size = file.tell()  # ファイルサイズを取得
        file.seek(0)  # ファイルの先頭に戻す
        
        if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
            return jsonify({'error': f'ファイルサイズが{MAX_FILE_SIZE_MB}MBを超えています。より小さいファイルを使用してください。'})
        
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        company_id = request.form.get('company_id', '').strip()
        
        # 入力データの詳細検証
        validation_errors = validate_input_data(email, password, file)
        if validation_errors:
            return jsonify({'error': '入力エラー: ' + '; '.join(validation_errors)})
        
        # リソース監視と警告（処理は継続）
        resource_warnings = check_resource_limits()
        if resource_warnings:
            print(f"リソース警告: {', '.join(resource_warnings)}")
        
        # ユニークなセッションIDを生成
        session_id = create_unique_session_id()
        job_id = str(uuid.uuid4())
        
        # 完全分離されたセッションディレクトリを作成
        session_dir = get_user_session_dir(session_id)
        
        # ファイルを保存（セッションID付きで一意性を確保）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = f"{session_id}_{timestamp}.xlsx"
        file_path = os.path.join(session_dir, filename)
        file.save(file_path)
        
        # セッションを登録
        register_session(session_id, job_id)
        
        # ジョブ情報を初期化（スレッドセーフ）
        with jobs_lock:
            jobs[job_id] = {
                'status': 'running',
                'logs': [],
                'progress': 0,
                'step_name': 'initializing',
                'current_data': 0,
                'total_data': 0,
                'start_time': datetime.now().timestamp(),
                'login_status': 'initializing',
                'login_message': '🔄 処理を初期化中...',
                'session_id': session_id,
                'session_dir': session_dir,
                'file_path': file_path,
                'email_hash': hash(email),  # 個人情報はハッシュ化
                'company_id': company_id,  # 会社IDを保存
                'resource_warnings': resource_warnings,
                'last_updated': time.time()
            }
        
        # バックグラウンドで処理を実行（エラーハンドリング強化）
        def run_automation():
            try:
                # セッション固有のブラウザ環境で処理を実行
                process_jobcan_automation(job_id, email, password, file_path, jobs, session_dir, session_id, company_id)
            except Exception as e:
                error_message = f'処理中にエラーが発生しました: {str(e)}'
                print(f"自動化処理エラー {job_id}: {error_message}")
                
                with jobs_lock:
                    if job_id in jobs:
                        jobs[job_id]['status'] = 'error'
                        jobs[job_id]['login_status'] = 'error'
                        jobs[job_id]['login_message'] = error_message
                        jobs[job_id]['logs'].append(f"❌ {error_message}")
                        jobs[job_id]['last_updated'] = time.time()
            finally:
                # 処理完了後の完全クリーンアップ（エラーが発生しても必ず実行）
                try:
                    cleanup_start_time = time.time()
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"ファイル削除完了: {file_path}")
                    
                    cleanup_user_session(session_id)
                    unregister_session(session_id)
                    
                    cleanup_time = time.time() - cleanup_start_time
                    print(f"セッションクリーンアップ完了 {session_id}: {cleanup_time:.2f}秒")
                    
                except Exception as cleanup_error:
                    print(f"クリーンアップエラー {session_id}: {cleanup_error}")
                    # クリーンアップエラーでも処理は継続
        
        thread = threading.Thread(target=run_automation)
        thread.daemon = True  # メインプロセス終了時に自動終了
        thread.start()
        
        return jsonify({
            'job_id': job_id,
            'session_id': session_id,
            'message': '処理を開始しました',
            'status_url': f'/status/{job_id}',
            'resource_warnings': resource_warnings
        })
        
    except Exception as e:
        return jsonify({'error': f'予期しないエラーが発生しました: {str(e)}'})

@app.route('/status/<job_id>')
def get_status(job_id):
    try:
        with jobs_lock:
            if job_id not in jobs:
                print(f"ジョブが見つかりません: {job_id}")
                print(f"現在のジョブ一覧: {list(jobs.keys())}")
                return jsonify({
                    'error': 'ジョブが見つかりません',
                    'job_id': job_id,
                    'available_jobs': list(jobs.keys())
                }), 404
            
            job = jobs[job_id]
            
            # ログイン結果の詳細情報を取得
            login_status = job.get('login_status', 'unknown')
            login_message = job.get('login_message', 'ログイン状態が不明です')
            
            # ユーザー向けの詳細メッセージを生成
            user_message = generate_user_message(job['status'], login_status, login_message, job.get('progress', 0))
            
            # リソース情報を追加（エラーが発生しても処理を続行）
            try:
                resources = get_system_resources()
            except Exception as resource_error:
                print(f"リソース情報取得エラー: {resource_error}")
                resources = {'memory_mb': 0, 'cpu_percent': 0, 'active_sessions': 0}
            
            # レスポンスデータを構築
            response_data = {
                'status': job['status'],
                'progress': job.get('progress', 0),
                'step_name': job.get('step_name', ''),
                'current_data': job.get('current_data', 0),
                'total_data': job.get('total_data', 0),
                'logs': job.get('logs', []),
                'start_time': job.get('start_time', 0),
                'login_status': login_status,
                'login_message': login_message,
                'user_message': user_message,
                'session_id': job.get('session_id', ''),
                'resources': resources,
                'resource_warnings': job.get('resource_warnings', [])
            }
            
            # ステータスに応じたHTTPステータスコードを設定
            if job['status'] == 'error':
                return jsonify(response_data), 500
            elif job['status'] == 'completed':
                return jsonify(response_data), 200
            else:
                return jsonify(response_data), 200
                
    except Exception as e:
        print(f"ステータス取得で予期しないエラー: {e}")
        return jsonify({
            'error': 'ステータス取得エラー',
            'status': 'error',
            'progress': 0,
            'login_status': 'error',
            'login_message': 'システムエラーが発生しました'
        }), 500

@app.route('/sessions')
def get_active_sessions():
    """アクティブセッション情報を取得"""
    try:
        with session_manager['session_lock']:
            active_sessions = session_manager['active_sessions'].copy()
        
        resources = get_system_resources()
        warnings = check_resource_limits()
        
        return jsonify({
            'active_sessions': len(active_sessions),
            'sessions': [
                {
                    'session_id': session_id,
                    'job_id': session_info['job_id'],
                    'start_time': session_info['start_time'],
                    'duration': time.time() - session_info['start_time']
                }
                for session_id, session_info in active_sessions.items()
            ],
            'resources': resources,
            'warnings': warnings
        })
    except Exception as e:
        return jsonify({'error': f'セッション情報取得エラー: {str(e)}'})

@app.route('/cleanup-sessions')
def cleanup_expired_sessions():
    """期限切れセッションのクリーンアップ"""
    try:
        current_time = time.time()
        expired_sessions = []
        
        with session_manager['session_lock']:
            for session_id, session_info in list(session_manager['active_sessions'].items()):
                # 30分以上経過したセッションを期限切れとする
                if current_time - session_info['start_time'] > 1800:
                    expired_sessions.append(session_id)
                    del session_manager['active_sessions'][session_id]
        
        # 期限切れセッションのクリーンアップ
        for session_id in expired_sessions:
            cleanup_user_session(session_id)
        
        return jsonify({
            'cleaned_sessions': len(expired_sessions),
            'remaining_sessions': len(session_manager['active_sessions']),
            'message': f'{len(expired_sessions)}個のセッションをクリーンアップしました'
        })
    except Exception as e:
        return jsonify({'error': f'セッションクリーンアップエラー: {str(e)}'})

def generate_user_message(status, login_status, login_message, progress):
    """ユーザー向けメッセージを生成"""
    if status == 'running':
        if login_status == 'success':
            return f"✅ ログイン成功 - {login_message}"
        elif login_status == 'failed':
            return f"❌ ログイン失敗 - {login_message}"
        elif login_status == 'captcha':
            return f"🔄 画像認証が必要です - {login_message}"
        elif login_status == 'processing':
            return f"🔄 ログイン処理中... - {login_message}"
        else:
            return f"🔄 処理中... - {login_message}"
    elif status == 'completed':
        return "✅ 処理完了 勤怠データの入力が完了しました。"
    elif status == 'error':
        return f"❌ エラーが発生しました: {login_message}"
    else:
        return "🔄 処理中..."

@app.route('/ads.txt')
def ads_txt():
    """ads.txt を配信（Google AdSense用）"""
    content = "google.com, pub-4232725615106709, DIRECT, f08c47fec0942fa0"
    return Response(content, mimetype='text/plain')

@app.route('/robots.txt')
def robots_txt():
    """robots.txt を配信"""
    try:
        return send_file('static/robots.txt', mimetype='text/plain')
    except Exception as e:
        # ファイルがない場合のフォールバック
        content = """User-agent: *
Allow: /

User-agent: Googlebot
Allow: /

User-agent: AdsBot-Google
Allow: /
"""
        return Response(content, mimetype='text/plain')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000))) 
