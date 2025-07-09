### FILE REPORT: apps/bot/src/models/mcp_manifest.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：152
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | **Function** | **Purpose** | | | | |
  | get_mcp_manifest | 定義並返回一個包含所有可透過 MCP (Model Context Protocol) 呼叫的工具清單，用於文件查詢和資料庫操作。 | | | | 1 | `services/openai_client.py`

- **工具清單 (Manifest) 摘要**:
  - **文件查詢工具 (Context7)**:
    - `search_docs`: 搜尋文件和程式碼範例。
    - `get_code_examples`: 獲取特定技術的程式碼範例。
    - `get_api_reference`: 獲取 API 參考文件。
    - `get_best_practices`: 獲取技術的最佳實踐。
  - **資料庫操作工具 (PostgreSQL)**:
    - `execute_query`: 執行唯讀的 SQL 查詢。
    - `describe_table`: 獲取資料表的結構 (schema)。
    - `list_tables`: 列出資料庫中所有的資料表。
    - `get_table_sample`: 獲取資料表的範例數據。
