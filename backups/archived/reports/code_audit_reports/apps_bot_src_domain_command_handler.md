### FILE REPORT: apps/bot/src/domain/command_handler.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：196
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | CommandHandler | 作為「指令模式」的抽象基底類，定義了所有具體指令處理器必須遵循的契約 (interface)。 | — | — | | 4+ | 各 command 檔案
  | | | get_help_text | 提供一個格式化的、描述該指令用途的幫助文本。 | | |
  | CommandContext | 作為一個依賴容器，封裝並提供所有指令處理器在執行時所需的共享服務和資源。 | — | — | | 3+ | `command_executor.py`, etc.
  | | | get_mcp_client | 提供獲取 MCP 客戶端的異步方法。 | | |
  | CommandRegistry | 作為一個註冊表，管理所有指令處理器的註冊、查找和列表功能。 | — | — | | 1 | self-module
  | | | register | 將一個指令處理器實例註冊到表中。 | | |
  | | | get_handler | 根據指令名稱或別名查找並返回對應的處理器。 | | |
  | | | list_commands | 返回所有已註冊的指令處理器列表。 | | |
  | | | has_command | 檢查一個指令是否存在。 | ❌ | 0 |
  | | | get_help_text | 生成一份包含所有已註冊指令的完整幫助文檔。 | ❌ | 0 |
  | **Function** | **Purpose** | | | | |
  | get_command_registry | 以單例模式提供 `CommandRegistry` 的全域實例。 | | | | 2 | `command_executor.py`, `help_command.py`

- **注意**: `CommandRegistry` 中的 `has_command` 和 `get_help_text` 方法提供了方便的功能，但在目前版本中未被使用。
