#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
from flask import Flask, jsonify

# Flaskアプリケーション
app = Flask(__name__)

# 起動ログ
print("🚀 最小限のJobcanアプリケーションを起動中...")
print(f"🔧 ポート: {os.environ.get('PORT', '5000')}")
print(f"🔧 環境: {os.environ.get('RAILWAY_ENVIRONMENT', 'local')}")
print(f"🔧 作業ディレクトリ: {os.getcwd()}")
print("✅ アプリケーション起動完了")

@app.route('/')
def index():
    """メインページ"""
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
    return "pong"

@app.route('/health')
def health():
    """ヘルスチェックエンドポイント"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'port': os.environ.get('PORT', 'N/A'),
        'environment': os.environ.get('RAILWAY_ENVIRONMENT', 'local')
    })

@app.route('/ready')
def ready():
    """起動確認エンドポイント"""
    return jsonify({
        'status': 'ready',
        'timestamp': time.time()
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
