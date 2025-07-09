### FILE REPORT: apps/bot/src/commands/help_command.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：153
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | HelpCommandHandler | 處理 `/help` 指令，為使用者提供所有可用指令的概覽或特定指令的詳細說明。 | — | — | | 1 | `domain/command_executor.py`
  | | | handle | 作為指令處理的入口點，根據參數決定是顯示全部幫助還是特定指令的幫助。 | | |
  | | | _get_specific_command_help | 從指令註冊表中查找特定指令的處理器，並格式化其詳細資訊（描述、用法、別名等）。 | | |
  | | | _get_all_commands_help | 從指令註冊表中獲取所有指令，並將它們格式化成一份完整的幫助手冊。 | | |
  | | | _get_extra_help | 提供一份預先定義好的、針對特定複雜指令（如 `sql`, `tables`）的額外詳細說明和範例。 | | |
