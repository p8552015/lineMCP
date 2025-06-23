### FILE REPORT: apps/bot/src/domain/command_executor.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：165
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | CommandExecutor | 作為「指令模式」的總協調器，負責註冊所有指令處理器，並根據用戶輸入解析、分派和執行相應的指令。 | — | — | | 2 | `infrastructure/enhanced_service_factory.py`, `application/messaging_service.py`
  | | | initialize | 初始化執行器，動態地創建並向指令註冊表註冊所有具體的指令處理器。 | | |
  | | | _register_all_commands | 集中管理所有指令處理器的創建和註冊邏輯。 | | |
  | | | execute_command | 解析用戶訊息，從註冊表中查找對應的處理器，驗證參數，然後執行指令。 | | |
  | | | has_command | 檢查一個指令是否已被註冊。 | ❌ | 0 |
  | | | list_commands | 列出所有已註冊的指令。 | ❌ | 0 |
  | | | get_help_text | 獲取所有指令的幫助文本。 | ❌ | 0 |
  | | | get_command_info | 獲取關於已註冊指令的統計資訊。 | | |
