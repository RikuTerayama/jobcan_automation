#!/bin/bash

# 依存関係をインストール
pip install -r requirements.txt

# Playwrightブラウザをインストール（強制的に再インストール）
playwright install --force chromium

# 必要なディレクトリを作成
mkdir -p uploads

# 権限を設定
chmod +x build.sh

echo "Build completed successfully!" 
