### FILE REPORT: apps/bot/src/commands/sql_command.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：124
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | SqlCommandHandler | 處理 `/sql` 指令，允許用戶安全地執行唯讀的 SQL 查詢。 | — | — | | 1 | `domain/command_executor.py`
  | | | validate_args | 驗證輸入的 SQL 查詢，確保它不為空且不包含任何不安全的寫入操作關鍵字。 | | |
  | | | handle | 作為指令處理的入口點，驗證參數後，透過 MCP 呼叫執行 SQL 查詢並格式化結果。 | | |
  | | | _format_sql_result | 將從資料庫返回的資料列表格式化為一份易於閱讀的文字訊息報告。 | | |
