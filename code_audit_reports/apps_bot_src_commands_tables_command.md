### FILE REPORT: apps/bot/src/commands/tables_command.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：141
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | TablesCommandHandler | 處理 `/tables` 指令，提供查詢資料庫中所有資料表列表或特定資料表結構的功能。 | — | — | | 1 | `domain/command_executor.py`
  | | | handle | 作為指令處理的入口點，根據參數決定是列出所有資料表還是顯示特定資料表的結構。 | | |
  | | | _list_all_tables | 透過 MCP 呼叫執行 SQL 查詢 (`SELECT name FROM sqlite_master`) 來獲取所有資料表並格式化成列表。 | | |
  | | | _get_table_schema | 透過 MCP 呼叫執行 `PRAGMA table_info` 和 `SELECT COUNT(*)` 來獲取特定資料表的結構和行數，並格式化成詳細報告。 | | |
