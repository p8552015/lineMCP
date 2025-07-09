### FILE REPORT: apps/bot/src/models/commands.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：43
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | Command | 以資料類別 (dataclass) 形式標準化地表示一個從用戶訊息中解析出的指令，包含指令名稱和參數。 | — | — | | |
  | **Function** | **Purpose** | | | | |
  | parse_command | 將以 `/` 開頭的用戶訊息解析成一個 `Command` 物件，如果訊息不是有效的指令則返回 `None`。 | | | | 1 | `domain/command_handler.py`
