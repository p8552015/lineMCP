### FILE REPORT: apps/bot/src/commands/info_command.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：196
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | InfoCommandHandler | 處理 `/info` 指令，收集並展示全面的系統資訊。 | — | — | | 1 | `domain/command_executor.py`
  | | | handle | 作為指令處理的入口點，協調資訊收集和格式化回應。 | | |
  | | | _collect_system_info | 收集關於應用程式、系統環境、功能、AI模型和依賴的綜合資訊。 | | |
  | | | _is_production | 根據環境變數判斷當前是否為生產環境。 | | |
  | | | _get_available_features | 返回一個預先定義好的、描述系統主要功能的列表。 | | |
  | | | _get_ai_models_info | 從 AI 服務中獲取當前可用及正在使用的模型資訊。 | | |
  | | | _get_key_dependencies | 返回一個預先定義好的、描述系統核心技術依賴的列表。 | | |
  | | | _format_system_info | 將收集到的所有系統資訊格式化成一份結構清晰、易於閱讀的文字報告。 | | |
