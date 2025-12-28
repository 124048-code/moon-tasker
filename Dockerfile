FROM python:3.11-slim

WORKDIR /app

# 依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションをコピー
COPY . .

# ポート設定（Render.comは動的にポートを割り当て）
EXPOSE 8080

# 環境変数
ENV FLET_SERVER_PORT=8080
ENV FLET_WEB_RENDERER=canvaskit

# アプリケーション起動
CMD ["python", "-m", "moon_tasker.main"]
