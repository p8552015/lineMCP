# 開發與運維命令指南

## 🚀 啟動命令

### 生產級啟動 (推薦)
```bash
# 完整啟動流程：依賴檢查 → 配置驗證 → MCP測試 → 服務啟動
./start-production.sh

# 查看所有選項
./start-production.sh help
```

### 快速開發啟動
```bash
# 快速開發模式
./quick-start.sh

# 手動啟動
cd apps/bot && poetry run uvicorn src.main:app --reload --port 8000
```

## 🧪 測試與驗證

### 系統測試
```bash
# 完整系統測試
./start-production.sh test

# 系統健康檢查
./status.sh

# 執行單元測試
cd apps/bot && poetry run pytest -v

# 零警告零錯誤驗證
./start-production.sh selftest
```

### 程式碼品質檢查
```bash
cd apps/bot

# 格式化檢查
poetry run black --check src/
poetry run ruff check src/
poetry run mypy src/
```

## 📦 依賴管理

### Poetry 環境管理
```bash
# 安裝生產依賴
poetry install --only=main --no-dev

# 安裝開發依賴
poetry install

# 更新依賴
poetry update
```

### 智能依賴安裝
```bash
# 智能安裝（跳過已安裝）
./start-production.sh install

# 強制重新安裝
./start-production.sh install-force

# 安裝開發環境
./start-production.sh install-dev
```

## 🐳 Docker 部署

### 完整系統啟動
```bash
# Docker Compose 啟動
docker-compose up -d

# 查看服務狀態
docker-compose ps

# 查看日誌
docker-compose logs -f line-bot
```

## 🔧 開發工具

### 日誌監控
```bash
# Webhook 處理日誌
tail -f apps/bot/logs/webhook.log

# MCP 服務日誌
tail -f apps/bot/logs/sqlite-mcp.log
```

### 交互式調試
```bash
cd apps/bot
poetry run python3 -i -c "from src.services import *"
```

## 🏭 macOS 開發環境

### 環境變數設置
```bash
# 修復 macOS KqueueSelector 掛起問題
export ASYNCIO_FORCE_SELECT_SELECTOR=1

# 設置 Python 路徑
export PYTHONPATH="$PWD/apps/bot/src:$PYTHONPATH"
```

### 系統工具
- **套件管理**: brew, pip3, poetry
- **容器**: docker, docker-compose
- **版本控制**: git
- **文本處理**: grep, find, sed, awk