#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
from flask import Flask, jsonify, render_template

# Flaskアプリケーション
app = Flask(__name__)

# 起動ログ
try:
    print("🚀 Jobcan自動化アプリケーションを起動中...")
    print(f"🔧 ポート: {os.environ.get('PORT', '5000')}")
    print(f"🔧 環境: {os.environ.get('RAILWAY_ENVIRONMENT', 'local')}")
    print(f"🔧 作業ディレクトリ: {os.getcwd()}")
    print("✅ アプリケーション起動完了")
except Exception as e:
    print(f"❌ 起動ログでエラー: {e}")

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

@app.route('/ping')
def ping():
    """シンプルなpingエンドポイント"""
    try:
        return "pong"
    except Exception as e:
        return f"error: {str(e)}", 500

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
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': time.time()
        }), 500

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
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': time.time()
        }), 500

if __name__ == '__main__':
    try:
        port = int(os.environ.get('PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        print(f"❌ アプリケーション起動でエラー: {e}")
        import traceback
        traceback.print_exc() 
