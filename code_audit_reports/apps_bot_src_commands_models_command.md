### FILE REPORT: apps/bot/src/commands/models_command.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：246
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | ModelsCommandHandler | 處理 `/models` 指令，提供查詢可用 AI 模型列表及特定模型詳細資訊的功能。 | — | — | | 1 | `domain/command_executor.py`
  | | | handle | 作為指令處理的入口點，根據參數決定是列出所有模型還是顯示特定模型的詳情。 | | |
  | | | _list_all_models | 從 AI 服務獲取所有模型資訊，並將其格式化為一個列表。 | | |
  | | | _get_model_details | 從 AI 服務中查找並格式化特定模型的詳細資訊。 | | |
  | | | _get_models_from_service | 封裝從 AI 服務中獲取模型資訊的邏輯，以兼容不同版本的服務介面。 | | |
  | | | _format_models_list | 將模型資訊列表格式化成一份易於閱讀、按提供商分組的文字訊息。 | | |
  | | | _format_model_details | 將單個模型的詳細屬性（如ID、狀態、能力、成本等）格式化成一份詳細報告。 | | |
