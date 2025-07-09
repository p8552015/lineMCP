### FILE REPORT: apps/bot/src/config/__init__.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：40
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | **Function** | **Purpose** | | | | |
  | get_settings | 為保持向後兼容，動態導入並返回主 `config.py` 的設定。 | | | ❌ | 0 |
- **導出說明**: 此文件將 `mcp_config.py` 中的多個類和函數 (`MCPServerConfig`, `MCPClientConfig`, `MCPConfigManager`, `get_mcp_config`, `get_server_config`, `validate_server_config`) 重新導出，使其可直接從 `config` 包中導入。
