# LINE MCP Bot

LINE Bot 整合 Model Context Protocol (MCP) 的智慧製造監控系統。

## 特色功能

- 🤖 LINE Bot 整合
- 🔗 MCP 協議支援
- 🏭 製造業資料查詢
- 🧠 AI 增強的自然語言處理
- 📊 即時監控與分析

## 快速開始

```bash
# 安裝依賴
poetry install

# 設置環境變數
cp .env.example .env

# 啟動服務
poetry run uvicorn src.main:app --reload
```

## 環境變數

參考專案根目錄的 CLAUDE.md 文件了解完整的環境變數配置。

## 開發

參考專案根目錄的開發指南和 CI/CD 文檔。