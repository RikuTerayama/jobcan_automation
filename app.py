#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import sys
from flask import Flask, jsonify, request, render_template, send_file
from werkzeug.utils import secure_filename
import io

# pandasは必要時にインポート
pandas_available = False
try:
    import pandas as pd
    pandas_available = True
except ImportError:
    print("⚠️ pandasが利用できません。Excel処理機能は無効化されます。")

# Flaskアプリケーション
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# アップロードフォルダが存在しない場合は作成
try:
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
except Exception as e:
    print(f"⚠️ アップロードフォルダ作成エラー: {e}")

# グローバル変数
jobs = {}

# 起動ログ
try:
    print("🚀 Jobcan自動化Webアプリケーションを起動中...")
    print(f"🔧 ポート: {os.environ.get('PORT', '5000')}")
    print(f"🔧 環境: {os.environ.get('RAILWAY_ENVIRONMENT', 'local')}")
    print(f"🔧 作業ディレクトリ: {os.getcwd()}")
    print(f"🔧 Python バージョン: {sys.version}")
    print(f"🔧 pandas利用可能: {pandas_available}")
    print("✅ アプリケーション起動完了")
except Exception as e:
    print(f"❌ 起動ログでエラー: {e}")

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
            'start_time': time.time(),
            'progress': {
                'current_step': 0,
                'total_steps': 8,
                'current_data': 0,
                'total_data': 0,
                'step_name': '初期化中'
            }
        }
    
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    jobs[job_id]['logs'].append(f"[{timestamp}] {message}")
    print(f"[{job_id}] {message}")

def update_progress(job_id: str, step: int, step_name: str, current_data: int = 0, total_data: int = 0):
    """進捗状況を更新"""
    if job_id in jobs:
        jobs[job_id]['progress']['current_step'] = step
        jobs[job_id]['progress']['step_name'] = step_name
        jobs[job_id]['progress']['current_data'] = current_data
        jobs[job_id]['progress']['total_data'] = total_data

def create_template_excel():
    """テンプレートExcelファイルを作成"""
    try:
        if not pandas_available:
            return None
        
        # サンプルデータでDataFrameを作成
        data = {
            'A': ['日付', '2025/01/01', '2025/01/02', '2025/01/03'],
            'B': ['始業時刻', '09:00', '09:00', '09:00'],
            'C': ['終業時刻', '18:00', '18:00', '18:00']
        }
        df = pd.DataFrame(data)
        
        # Excelファイルをメモリに作成
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, header=False)
        
        output.seek(0)
        return output
    except Exception as e:
        print(f"❌ テンプレートExcel作成エラー: {e}")
        return None

@app.route('/')
def index():
    """メインページ"""
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"❌ indexエンドポイントでエラー: {e}")
        return jsonify({
            'status': 'running',
            'message': 'Jobcan Automation Service',
            'timestamp': time.time(),
            'port': os.environ.get('PORT', 'N/A'),
            'environment': os.environ.get('RAILWAY_ENVIRONMENT', 'local')
        })

@app.route('/ping')
def ping():
    """シンプルなpingエンドポイント"""
    try:
        return "pong"
    except Exception as e:
        print(f"❌ pingエンドポイントでエラー: {e}")
        return "pong"

@app.route('/health')
def health():
    """ヘルスチェックエンドポイント"""
    try:
        return jsonify({
            'status': 'healthy',
            'timestamp': time.time(),
            'port': os.environ.get('PORT', 'N/A'),
            'environment': os.environ.get('RAILWAY_ENVIRONMENT', 'local'),
            'pandas_available': pandas_available
        })
    except Exception as e:
        print(f"❌ healthエンドポイントでエラー: {e}")
        return jsonify({
            'status': 'healthy',
            'timestamp': time.time(),
            'error': str(e)
        })

@app.route('/ready')
def ready():
    """起動確認エンドポイント"""
    try:
        return jsonify({
            'status': 'ready',
            'timestamp': time.time(),
            'pandas_available': pandas_available
        })
    except Exception as e:
        print(f"❌ readyエンドポイントでエラー: {e}")
        return jsonify({
            'status': 'ready',
            'timestamp': time.time(),
            'error': str(e)
        })

@app.route('/test')
def test():
    """テストエンドポイント"""
    try:
        return "OK"
    except Exception as e:
        print(f"❌ testエンドポイントでエラー: {e}")
        return "OK"

@app.route('/download-template')
def download_template():
    """テンプレートExcelファイルをダウンロード"""
    try:
        if not pandas_available:
            return jsonify({'error': 'pandasが利用できません。テンプレート機能は無効化されています。'}), 500
        
        output = create_template_excel()
        if output:
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name='jobcan_template.xlsx'
            )
        else:
            return jsonify({'error': 'テンプレートファイルの作成に失敗しました'}), 500
    except Exception as e:
        print(f"❌ テンプレートダウンロードエラー: {e}")
        return jsonify({'error': str(e)}), 500

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
        import uuid
        job_id = str(uuid.uuid4())
        
        # ジョブを開始
        add_job_log(job_id, "アップロード処理を開始")
        add_job_log(job_id, "✅ ファイルのアップロードが完了しました")
        add_job_log(job_id, "⚠️ 自動化機能は現在無効化されています（Railway環境の制約）")
        
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
        progress = job_data.get('progress', {})
        
        # 進捗メッセージを生成
        if progress.get('current_step', 0) > 0:
            step_name = progress.get('step_name', '処理中')
            current_step = progress.get('current_step', 0)
            total_steps = progress.get('total_steps', 8)
            current_data = progress.get('current_data', 0)
            total_data = progress.get('total_data', 0)
            
            if total_data > 0:
                progress_message = f"ステップ {current_step}/{total_steps}: {step_name} ({current_data}/{total_data}件)"
            else:
                progress_message = f"ステップ {current_step}/{total_steps}: {step_name}"
        else:
            progress_message = "初期化中..."
        
        return jsonify({
            'status': job_data.get('status', 'not_found'),
            'logs': job_data.get('logs', []),
            'diagnosis': job_data.get('diagnosis', {}),
            'progress': progress,
            'progress_message': progress_message,
            'start_time': job_data.get('start_time', ''),
            'current_time': time.time()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
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
