#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
from flask import Flask, jsonify

# 最小限のFlaskアプリケーション
app = Flask(__name__)

# 起動ログ
print("🚀 シンプルアプリケーションを起動中...")
print(f"🔧 ポート: {os.environ.get('PORT', '5000')}")
print(f"🔧 環境: {os.environ.get('RAILWAY_ENVIRONMENT', 'local')}")
print("✅ アプリケーション起動完了")

@app.route('/')
def root():
    """ルートエンドポイント"""
    return jsonify({
        'status': 'running',
        'message': 'Simple Jobcan Service',
        'timestamp': time.time()
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
        'timestamp': time.time()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 
