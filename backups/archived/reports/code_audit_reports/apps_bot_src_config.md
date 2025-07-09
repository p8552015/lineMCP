### FILE REPORT: apps/bot/src/config.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：139
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | Settings | 透過 Pydantic 管理所有應用程式的環境變數和配置。 | — | — | | |
  | | | redis_url | 根據配置生成 Redis 連接 URL。 | | 1 | `utils/redis_client.py`
  | | | project_root | 自動推斷項目根目錄路徑。 | | 1 | `services/production_mcp_client.py`
  | | | mcp_sqlite_server_path | 組合出 MCP SQLite 服務器腳本的完整路徑。 | | 1 | `services/production_mcp_client.py`
  | | | mcp_sqlite_db_path | 組合出 MCP SQLite 資料庫的完整路徑。 | | 1 | `services/production_mcp_client.py`
  | **Function** | **Purpose** | | | | |
  | get_settings | 使用快取 (lru_cache) 提供全域的 Settings 實例。 | | | | 6 | `main.py`, `routes/webhook.py`, `services/cost_tracker.py`, `services/message_handler_di.py`, `services/openai_client.py`, `utils/observability.py`
