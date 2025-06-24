FROM python:3.11-slim-bookworm

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc=4:12.2.0-3 \
    g++=4:12.2.0-3 \
    git=1:2.39.2-1.1 \
    curl=7.88.1-10+deb12u8 \
    && rm -rf /var/lib/apt/lists/*

# 安裝 Poetry
RUN pip install --no-cache-dir poetry==1.8.3

# 複製 Poetry 配置檔案
COPY pyproject.toml poetry.lock ./

# 設定 Poetry 不創建虛擬環境
ENV POETRY_VIRTUALENVS_CREATE=false

# 安裝依賴
RUN poetry install --no-interaction --no-ansi --no-root

# 複製應用程式碼
COPY . .

# 安裝應用本身
RUN poetry install --no-interaction --no-ansi

# 設定環境變數
ENV PYTHONUNBUFFERED=1
ENV PYTHONUTF8=1
ENV PYTHONPATH=/app/src:$PYTHONPATH

# 暴露端口
EXPOSE 8000

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# 啟動命令
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]