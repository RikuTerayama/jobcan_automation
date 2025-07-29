#!/bin/bash

echo "🚀 Jobcanアプリケーションを起動中..."

# 環境変数の確認
echo "🔧 PORT: $PORT"
echo "🔧 RAILWAY_ENVIRONMENT: $RAILWAY_ENVIRONMENT"

# Pythonの確認
python --version

# 依存関係の確認
pip list

# アプリケーションの起動
echo "🚀 Gunicornでアプリケーションを起動中..."
gunicorn app:app --bind 0.0.0.0:$PORT --timeout 60 --workers 1 --log-level info 
