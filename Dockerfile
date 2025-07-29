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
    && rm -rf /var/lib/apt/lists/*

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

# ポートを公開
EXPOSE 8000

# 環境変数を設定
ENV PORT=8000
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# アプリケーションを起動（Railway環境最適化）
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8000", "--timeout", "300", "--workers", "1", "--preload", "--max-requests", "1000", "--keep-alive", "2", "--log-level", "info", "--access-logfile", "-", "--error-logfile", "-"] 
