#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import uuid
import threading
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

# ジョブの状態を管理
jobs = {}

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
    if 'file' not in request.files:
        return jsonify({'error': 'ファイルが選択されていません'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'ファイルが選択されていません'})
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Excelファイル（.xlsx, .xls）のみアップロード可能です'})
    
    email = request.form.get('email', '')
    password = request.form.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'メールアドレスとパスワードを入力してください'})
    
    # ファイルを保存
    filename = f"{uuid.uuid4()}.xlsx"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    
    # ジョブIDを生成
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        'status': 'running',
        'logs': [],
        'progress': 0,
        'start_time': datetime.now().timestamp()
    }
    
    # バックグラウンドで処理を実行
    def run_automation():
        try:
            process_jobcan_automation(job_id, email, password, file_path, jobs)
        finally:
            # 処理完了後にファイルを削除
            try:
                os.remove(file_path)
            except:
                pass
    
    thread = threading.Thread(target=run_automation)
    thread.start()
    
    return jsonify({
        'job_id': job_id,
        'message': '処理を開始しました',
        'status_url': f'/status/{job_id}'
    })

@app.route('/status/<job_id>')
def get_status(job_id):
    if job_id not in jobs:
        return jsonify({'error': 'ジョブが見つかりません'})
    
    job = jobs[job_id]
    return jsonify({
        'status': job['status'],
        'progress': job.get('progress', 0),
        'step_name': job.get('step_name', ''),
        'current_data': job.get('current_data', 0),
        'total_data': job.get('total_data', 0),
        'logs': job.get('logs', []),
        'start_time': job.get('start_time', 0)
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000))) 
