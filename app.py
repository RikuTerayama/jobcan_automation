#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import sys
from flask import Flask, jsonify, request

# Flaskアプリケーション
app = Flask(__name__)

# 起動ログ
print("🚀 最小限のJobcanアプリケーションを起動中...")
print(f"🔧 ポート: {os.environ.get('PORT', '5000')}")
print(f"🔧 環境: {os.environ.get('RAILWAY_ENVIRONMENT', 'local')}")
print(f"🔧 作業ディレクトリ: {os.getcwd()}")
print(f"🔧 Python バージョン: {sys.version}")
print("✅ アプリケーション起動完了")

# 起動確認
@app.before_request
def before_request():
    print(f"🌐 リクエスト受信: {request.method} {request.path}")

@app.route('/')
def index():
    """メインページ"""
    try:
        return jsonify({
            'status': 'running',
            'message': 'Jobcan Automation Service',
            'timestamp': time.time(),
            'port': os.environ.get('PORT', 'N/A'),
            'environment': os.environ.get('RAILWAY_ENVIRONMENT', 'local')
        })
    except Exception as e:
        print(f"❌ indexエンドポイントでエラー: {e}")
        return "Jobcan Automation Service is running"

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

@app.route('/status')
def status():
    """ステータスエンドポイント"""
    try:
        return jsonify({
            'status': 'running',
            'timestamp': time.time()
        })
    except Exception as e:
        print(f"❌ statusエンドポイントでエラー: {e}")
        return jsonify({
            'status': 'running',
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
