FROM python:3.11-slim-bookworm

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 安裝 Python 依賴
RUN pip install --no-cache-dir \
    mcp \
    aiosqlite \
    pydantic \
    aiohttp

# 複製 MCP SQLite 服務器代碼
COPY . /app/

# 創建資料庫目錄
RUN mkdir -p /data

# 設定環境變數
ENV PYTHONUNBUFFERED=1
ENV PYTHONUTF8=1
ENV PORT=3003

# 暴露端口
EXPOSE 3003

# 使用簡化的 HTTP 橋接器
ENTRYPOINT ["python", "/app/http_bridge_simple.py", "/data/test.db"]