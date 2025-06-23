### FILE REPORT: apps/bot/src/application/messaging_service.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：280
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | MessagingApplicationService | 作為訊息處理的總協調器，負責分類訊息（指令或自然語言）並分派給相應的服務處理。 | — | — | | 1 | `application/application_facade.py`
  | | | _initialize_service | 初始化內部的指令執行器 `CommandExecutor`。 | | |
  | | | process_message | 處理傳入訊息的主要入口點，協調整個處理流程。 | | |
  | | | _classify_message | 根據訊息內容（是否以 `/` 開頭）將其分類為指令或自然語言。 | | |
  | | | _process_command_message | 將指令訊息轉發給 `CommandExecutor` 進行處理。 | | |
  | | | _process_natural_language_message | 將自然語言訊息轉發給自然語言服務（`nl_service`）進行處理。 | | |
  | | | _get_default_response | 當自然語言處理失敗或無結果時，提供一個預設的幫助訊息。 | | |
  | | | _update_user_session | 更新或創建用戶的會話資訊，記錄互動歷史。 | | |
  | | | _update_session_result | 在會話中記錄每次處理的成功或失敗狀態。 | | |
  | | | get_user_session | 獲取特定用戶的會話資訊。 | ❌ | 0 |
  | | | clear_user_session | 清除特定用戶的會話資訊。 | ❌ | 0 |
  | | | get_processing_stats | 獲取關於訊息處理的統計數據，如總數、錯誤率等。 | | |
  | | | _perform_health_checks | 執行此服務內部的健康檢查，包括指令執行器和自然語言服務的狀態。 | | |
  | | | _shutdown_service | 在服務關閉時執行清理工作，如清除會話和重置統計。 | | |

- **注意**: `get_user_session` 和 `clear_user_session` 提供了會話管理的能力，但在目前版本中未被外部呼叫，可能為未來的功能（如管理後台）預留。
