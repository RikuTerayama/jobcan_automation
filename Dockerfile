FROM python:3.11-slim

# システム依存関係のインストール
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    fonts-liberation \
    fonts-unifont \
    fonts-dejavu \
    fonts-noto \
    libasound2 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    libxss1 \
    libxtst6 \
    libx11-xcb1 \
    libxcb-dri3-0 \
    libxcursor1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrender1 \
    libcups2 \
    libdbus-1-3 \
    libatspi2.0-0 \
    libx11-6 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリの設定
WORKDIR /app

# Python依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwrightブラウザのインストール
RUN playwright install chromium

# アプリケーションファイルのコピー
COPY . .

# アップロードディレクトリの作成
RUN mkdir -p uploads

# ポートの公開
EXPOSE $PORT

# アプリケーションの起動（メモリ最適化版）
CMD gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 180 --max-requests 100 --max-requests-jitter 20 --preload app:app 
