# SQLite 到 PostgreSQL 移轉分析

## 🔍 發現的 SQLite 引用分類

### 1. 業務邏輯代碼 (需要修改)
- `apps/bot/src/commands/info_command.py:138` - 系統依賴說明文字
- `apps/bot/src/services/nl_to_sql/builders/query_template_manager.py:257` - PRAGMA 語法檢查註釋

### 2. 配置和架構文件 (保留，作為選項)
- `apps/bot/src/nodecomman/implementations/universal_mcp_factory.py` - SQLite MCP 服務器配置
- `apps/bot/src/nodecomman/interfaces/server_interfaces.py` - SQLite 服務器類型定義
- `apps/bot/src/nodecomman/implementations/python_runtime_manager.py` - SQLite 服務器支援
- `apps/bot/src/nodecomman/implementations/nodejs_runtime_manager.py` - SQLite 服務器支援

### 3. 測試文件 (需要更新測試邏輯)
- `apps/bot/tests/services/test_unified_mcp_client.py` - 使用 sqlite 作為測試服務器
- `apps/bot/tests/integration/test_mcp_connection.py` - SQLite 服務器連接測試
- `apps/bot/tests/integration/test_mcp_queries.py` - SQLite 查詢測試
- `apps/bot/tests/unit/test_error_handling.py` - SQLite 錯誤處理測試

### 4. 外部文件 (非核心)
- `test_connection_pool_integration.py` - 獨立測試腳本
- `mcp_file_searcher.py` - 獨立工具腳本

## 🎯 修改策略
1. **業務邏輯**: 更新說明文字，反映當前使用 PostgreSQL
2. **架構配置**: 保留 SQLite 作為可選 MCP 服務器，但主要使用 PostgreSQL
3. **測試代碼**: 更新測試使用 postgres 而非 sqlite
4. **外部工具**: 暫時保留，因為不影響核心業務