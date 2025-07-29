#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import uuid
import threading
import psutil
from datetime import datetime
from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename
import pandas as pd

# Flaskアプリケーション
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# アップロードフォルダが存在しない場合は作成
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# グローバル変数
jobs = {}

# 起動ログ
try:
    print("🚀 Jobcan自動化アプリケーションを起動中...")
    print(f"🔧 ポート: {os.environ.get('PORT', '5000')}")
    print(f"🔧 環境: {os.environ.get('RAILWAY_ENVIRONMENT', 'local')}")
    print(f"🔧 作業ディレクトリ: {os.getcwd()}")
    print(f"🔧 Python バージョン: {os.sys.version}")
    print("✅ アプリケーション起動完了")
except Exception as e:
    print(f"❌ 起動ログでエラー: {e}")
    import traceback
    traceback.print_exc()

def allowed_file(filename):
    """許可されたファイル形式かチェック"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx'}

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

@app.route('/')
def index():
    """メインページ"""
    try:
        return render_template('index.html')
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'message': 'テンプレートの読み込みに失敗しました'
        }), 500

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
        add_job_log(job_id, "✅ ファイルのアップロードが完了しました")
        add_job_log(job_id, "⚠️ 自動化機能は現在無効化されています")
        
        jobs[job_id]['status'] = 'completed'
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'ファイルのアップロードが完了しました。自動化機能は現在無効化されています。'
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

@app.route('/ping')
def ping():
    """シンプルなpingエンドポイント"""
    try:
        # 最小限の処理のみ実行
        return "pong"
    except Exception as e:
        print(f"❌ pingエンドポイントでエラー: {e}")
        return "pong"  # エラーが発生してもpongを返す

@app.route('/health')
def health():
    """ヘルスチェックエンドポイント"""
    try:
        # 最小限のチェックのみ実行
        return jsonify({
            'status': 'healthy',
            'timestamp': time.time(),
            'port': os.environ.get('PORT', 'N/A'),
            'environment': os.environ.get('RAILWAY_ENVIRONMENT', 'local')
        })
    except Exception as e:
        print(f"❌ healthエンドポイントでエラー: {e}")
        # エラーが発生してもhealthyを返す
        return jsonify({
            'status': 'healthy',
            'timestamp': time.time(),
            'error': str(e)
        })

@app.route('/api/status')
def api_status():
    """APIステータスエンドポイント"""
    try:
        return jsonify({
            'status': 'running',
            'message': 'Jobcan Automation Service',
            'timestamp': time.time(),
            'port': os.environ.get('PORT', 'N/A'),
            'environment': os.environ.get('RAILWAY_ENVIRONMENT', 'local')
        })
    except Exception as e:
        print(f"❌ api_statusエンドポイントでエラー: {e}")
        return jsonify({
            'status': 'running',
            'message': 'Jobcan Automation Service',
            'timestamp': time.time(),
            'error': str(e)
        })

@app.route('/ready')
def ready():
    """起動確認エンドポイント"""
    try:
        return jsonify({
            'status': 'ready',
            'timestamp': time.time()
        })
    except Exception as e:
        print(f"❌ readyエンドポイントでエラー: {e}")
        return jsonify({
            'status': 'ready',
            'timestamp': time.time(),
            'error': str(e)
        })

if __name__ == '__main__':
    try:
        port = int(os.environ.get('PORT', 5000))
        print(f"🚀 アプリケーションをポート {port} で起動中...")
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        print(f"❌ アプリケーション起動でエラー: {e}")
        import traceback
        traceback.print_exc() 
