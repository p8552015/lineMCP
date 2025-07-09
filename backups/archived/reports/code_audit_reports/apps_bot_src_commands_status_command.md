### FILE REPORT: apps/bot/src/commands/status_command.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：189
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | StatusCommandHandler | 處理 `/status` 指令，執行一系列系統健康檢查並回報結果。 | — | — | | 1 | `domain/command_executor.py`
  | | | handle | 作為指令處理的入口點，協調狀態檢查並格式化回應。 | | |
  | | | _perform_status_checks | 協調執行所有定義的健康檢查任務。 | | |
  | | | _get_current_time | 獲取當前時間以標記報告時間。 | | |
  | | | _check_mcp_connection | 透過發送一個簡單的 `SELECT 1` 查詢來測試與 MCP 服務的連通性。 | | |
  | | | _check_ai_service | 檢查 AI 模型服務是否已載入且可用。 | | |
  | | | _check_database_service | 檢查資料庫服務是否已成功初始化。 | | |
  | | | _check_internal_services | 檢查其他核心內部服務 (如自然語言服務、格式化器) 的狀態。 | | |
  | | | _format_status_report | 將所有健康檢查的結果格式化成一份易於閱讀的文字訊息報告。 | | |
