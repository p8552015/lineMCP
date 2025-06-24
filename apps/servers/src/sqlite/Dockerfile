FROM python:3.11-slim-bookworm

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc=4:12.2.0-3 \
    && rm -rf /var/lib/apt/lists/*

# 安裝 Python 依賴
RUN pip install --no-cache-dir \
    mcp==1.9.4 \
    aiosqlite==0.20.0 \
    pydantic==2.10.3 \
    aiohttp==3.11.10

# 複製 MCP SQLite 服務器代碼
COPY . /app/
# 設定 Python 路徑以找到模組
ENV PYTHONPATH=/app/src

# 創建資料庫目錄
RUN mkdir -p /data

# 設定環境變數
ENV PYTHONUNBUFFERED=1
ENV PYTHONUTF8=1

# MCP STDIO 服務器不需要暴露 HTTP 端口
# 通過 STDIO 進行通信

# 使用標準 MCP STDIO 服務器（Docker Linux 環境無 macOS 問題）
ENTRYPOINT ["python", "-m", "mcp_server_sqlite", "--db-path", "/data/test.db"]