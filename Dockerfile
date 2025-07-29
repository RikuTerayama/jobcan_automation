# Python 3.11を使用
FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムの依存関係をインストール（最適化版）
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    ca-certificates \
    procps \
    libxss1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    fonts-liberation \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/*

# Google Chromeをインストール（最適化版）
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/*

# Pythonの依存関係をコピーしてインストール
COPY requirements.txt .
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

# Playwrightのブラウザをインストール（最適化版）
RUN playwright install chromium --with-deps --force

# アプリケーションのコードをコピー
COPY . .

# 環境変数を設定
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 起動スクリプトを作成
RUN echo '#!/bin/bash\n\
echo "🚀 アプリケーションを起動中..."\n\
echo "🔧 ポート: $PORT"\n\
echo "🔧 環境: $RAILWAY_ENVIRONMENT"\n\
\n\
# ポートが設定されていない場合は8000を使用\n\
if [ -z "$PORT" ]; then\n\
    export PORT=8000\n\
fi\n\
\n\
echo "✅ Gunicornを起動中: 0.0.0.0:$PORT"\n\
exec gunicorn app:app \\\n\
    --bind 0.0.0.0:$PORT \\\n\
    --timeout 300 \\\n\
    --workers 1 \\\n\
    --preload \\\n\
    --max-requests 1000 \\\n\
    --keep-alive 2 \\\n\
    --log-level info \\\n\
    --access-logfile - \\\n\
    --error-logfile - \\\n\
    --capture-output\n\
' > /app/start.sh && chmod +x /app/start.sh

# アプリケーションを起動
CMD ["/app/start.sh"] 
