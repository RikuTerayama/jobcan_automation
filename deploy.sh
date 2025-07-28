#!/bin/bash

echo "🚀 Jobcan Web App デプロイ開始..."

# 依存関係をインストール
echo "📦 依存関係をインストール中..."
pip install -r requirements.txt

# Playwrightブラウザを強制インストール
echo "🌐 Playwrightブラウザをインストール中..."
playwright install --force chromium

# 必要なディレクトリを作成
echo "📁 ディレクトリを作成中..."
mkdir -p uploads

# 権限を設定
chmod +x build.sh
chmod +x deploy.sh

echo "✅ デプロイ準備完了！" 
