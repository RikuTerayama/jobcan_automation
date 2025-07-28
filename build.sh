#!/bin/bash

# Playwrightブラウザのインストール
playwright install chromium

# 必要なディレクトリを作成
mkdir -p uploads

# 権限を設定
chmod +x build.sh

echo "Build completed successfully!" 
