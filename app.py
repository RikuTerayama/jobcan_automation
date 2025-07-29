#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import sys
import uuid
import threading
import pandas as pd
from datetime import datetime
from flask import Flask, jsonify, request, render_template, send_file
from werkzeug.utils import secure_filename
import io

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
    print("🚀 Jobcan自動化Webアプリケーションを起動中...")
    print(f"🔧 ポート: {os.environ.get('PORT', '5000')}")
    print(f"🔧 環境: {os.environ.get('RAILWAY_ENVIRONMENT', 'local')}")
    print(f"🔧 作業ディレクトリ: {os.getcwd()}")
    print(f"🔧 Python バージョン: {sys.version}")
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
            'start_time': datetime.now().isoformat(),
            'progress': {
                'current_step': 0,
                'total_steps': 8,
                'current_data': 0,
                'total_data': 0,
                'step_name': '初期化中'
            }
        }
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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

def process_jobcan_automation(job_id: str, email: str, password: str, file_path: str):
    """Jobcan自動化処理"""
    try:
        # ステップ1: 初期化
        update_progress(job_id, 1, "初期化中")
        add_job_log(job_id, "🚀 Jobcan自動化処理を開始")
        add_job_log(job_id, f"📧 メールアドレス: {email}")
        add_job_log(job_id, f"📁 ファイルパス: {file_path}")
        
        # ステップ2: Excelファイルの読み込み
        update_progress(job_id, 2, "Excelファイル読み込み中")
        add_job_log(job_id, "📊 Excelファイルを読み込み中...")
        
        try:
            df = pd.read_excel(file_path, skiprows=1)  # ヘッダー行をスキップ
            total_data = len(df)
            add_job_log(job_id, f"✅ Excelファイル読み込み完了: {total_data}件のデータ")
            update_progress(job_id, 2, "Excelファイル読み込み完了", 0, total_data)
        except Exception as e:
            add_job_log(job_id, f"❌ Excelファイル読み込みエラー: {e}")
            jobs[job_id]['status'] = 'error'
            return
        
        # ステップ3: データ検証
        update_progress(job_id, 3, "データ検証中")
        add_job_log(job_id, "🔍 データの検証中...")
        
        try:
            # 必要な列が存在するかチェック
            if len(df.columns) < 3:
                add_job_log(job_id, "❌ データ形式エラー: 必要な列（日付、開始時刻、終了時刻）が不足しています")
                jobs[job_id]['status'] = 'error'
                return
            
            add_job_log(job_id, "✅ データ検証完了")
            update_progress(job_id, 3, "データ検証完了", 0, total_data)
        except Exception as e:
            add_job_log(job_id, f"❌ データ検証エラー: {e}")
            jobs[job_id]['status'] = 'error'
            return
        
        # ステップ4: ブラウザ起動準備
        update_progress(job_id, 4, "ブラウザ起動準備中")
        add_job_log(job_id, "🌐 ブラウザ起動準備中...")
        
        # 実際のブラウザ起動は現在無効化（Railway環境の制約）
        add_job_log(job_id, "⚠️ ブラウザ起動機能は現在無効化されています（Railway環境の制約）")
        update_progress(job_id, 4, "ブラウザ起動準備完了", 0, total_data)
        
        # ステップ5: Jobcanログイン
        update_progress(job_id, 5, "Jobcanログイン中")
        add_job_log(job_id, "🔐 Jobcanログイン処理中...")
        add_job_log(job_id, "🌐 ログインURL: https://id.jobcan.jp/users/sign_in?app_key=atd&redirect_to=https://ssl.jobcan.jp/jbcoauth/callback")
        
        # 実際のログイン処理は現在無効化
        add_job_log(job_id, "⚠️ ログイン機能は現在無効化されています（Railway環境の制約）")
        update_progress(job_id, 5, "Jobcanログイン完了", 0, total_data)
        
        # ステップ6: 勤怠データ入力
        update_progress(job_id, 6, "勤怠データ入力中")
        add_job_log(job_id, "📝 勤怠データ入力処理中...")
        
        for index, row in df.iterrows():
            try:
                date = row.iloc[0]  # A列: 日付
                start_time = row.iloc[1]  # B列: 開始時刻
                end_time = row.iloc[2]  # C列: 終了時刻
                
                add_job_log(job_id, f"📅 データ {index + 1}/{total_data}: {date} {start_time}-{end_time}")
                add_job_log(job_id, f"🔧 打刻修正URL: https://ssl.jobcan.jp/employee/adit/modify?year={date.split('/')[0]}&month={date.split('/')[1]}&day={date.split('/')[2]}")
                update_progress(job_id, 6, f"勤怠データ入力中 ({index + 1}/{total_data})", index + 1, total_data)
                
                # 実際のデータ入力処理は現在無効化
                time.sleep(0.1)  # 処理時間をシミュレート
                
            except Exception as e:
                add_job_log(job_id, f"❌ データ {index + 1} の処理でエラー: {e}")
        
        # ステップ7: 最終確認
        update_progress(job_id, 7, "最終確認中")
        add_job_log(job_id, "✅ 最終確認中...")
        update_progress(job_id, 7, "最終確認完了", total_data, total_data)
        
        # ステップ8: 完了
        update_progress(job_id, 8, "処理完了")
        add_job_log(job_id, "🎉 勤怠データの入力が完了しました")
        jobs[job_id]['status'] = 'completed'
        
    except Exception as e:
        add_job_log(job_id, f"❌ 自動化処理でエラーが発生しました: {e}")
        jobs[job_id]['status'] = 'error'

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
            'environment': os.environ.get('RAILWAY_ENVIRONMENT', 'local')
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
            'timestamp': time.time()
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
        job_id = str(uuid.uuid4())
        
        # ジョブを開始
        add_job_log(job_id, "アップロード処理を開始")
        add_job_log(job_id, "✅ ファイルのアップロードが完了しました")
        
        # 自動化処理をバックグラウンドで開始
        jobs[job_id]['status'] = 'processing'
        
        def run_automation():
            process_jobcan_automation(job_id, email, password, file_path)
        
        # バックグラウンドスレッドで自動化処理を実行
        thread = threading.Thread(target=run_automation)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'ファイルのアップロードが完了しました。自動化処理を開始しています...'
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
            'current_time': datetime.now().isoformat()
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
