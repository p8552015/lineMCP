### FILE REPORT: apps/bot/src/config/mcp_config.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：257
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | MCPServerConfig | 以資料類別 (dataclass) 形式定義 MCP 伺服器的所有配置參數。 | — | — | | |
  | MCPClientConfig | 以資料類別 (dataclass) 形式定義 MCP 客戶端的所有配置參數。 | — | — | | |
  | MCPConfigManager | 統一管理、初始化和驗證所有 MCP 相關的伺服器與客戶端配置。 | — | — | | |
  | | | _init_default_servers | 根據主設定檔初始化預設的 MCP 伺服器 (如 SQLite, PostgreSQL)。 | | |
  | | | get_server_config | 根據名稱獲取指定的伺服器配置。 | | |
  | | | add_server_config | 動態新增一個伺服器配置。 | ❌ | 0 |
  | | | list_servers | 列出所有已配置的伺服器名稱。 | ❌ | 0 |
  | | | get_client_config | 獲取 MCP 客戶端的配置。 | | |
  | | | update_client_config | 更新客戶端的特定配置項。 | ❌ | 0 |
  | | | validate_server_config | 驗證指定伺服器的配置是否完整且有效。 | | |
  | | | get_config_summary | 提供一份包含所有伺服器和客戶端配置的摘要。 | ❌ | 0 |
  | **Function** | **Purpose** | | | | |
  | get_mcp_config | 以單例模式提供 `MCPConfigManager` 的全域實例。 | | | | |
  | get_server_config | 作為便利函數，快速獲取指定伺服器的配置。 | | | | |
  | validate_server_config | 作為便利函數，快速驗證指定伺服器的配置。 | | | | |
