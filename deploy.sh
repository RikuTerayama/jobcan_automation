#!/bin/bash

echo "🚀 Jobcan Web App デプロイ開始..."

# システム依存関係をインストール
echo "📦 システム依存関係をインストール中..."
apt-get update
apt-get install -y \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxcb1 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    fonts-liberation \
    xvfb

# 依存関係をインストール
echo "📦 Python依存関係をインストール中..."
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
