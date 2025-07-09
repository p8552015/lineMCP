### FILE REPORT: apps/bot/src/domain/exceptions.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：220 ❌ High LOC
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | BotException | 作為所有自定義業務異常的基底類，封裝了技術錯誤訊息和對使用者友善的訊息。 | — | — | | 10+ | self-module, `error_handler.py`
  | | | to_dict | 將異常的詳細資訊轉換為字典格式，方便日誌記錄。 | | |
  | ValidationException | 表示輸入驗證失敗的異常。 | — | — | | |
  | CommandParsingException | 表示指令解析失敗的異常。 | — | — | | |
  | DatabaseQueryException | 表示資料庫查詢執行失敗的異常。 | — | — | | |
  | MCPConnectionException | 表示與 MCP 服務連接失敗的異常。 | — | — | | |
  | AIServiceException | 表示與 AI 服務互動失敗的異常。 | — | — | | |
  | AuthenticationException | 表示認證或授權失敗的異常。 | — | — | | |
  | RateLimitException | 表示請求速率超過限制的異常。 | — | — | | |
  | ConfigurationException | 表示系統配置錯誤的異常。 | — | — | | |
  | BusinessLogicException | 表示通用業務邏輯錯誤的異常。 | — | — | | |
  | ExternalServiceException | 表示與外部第三方服務互動失敗的異常。 | — | — | | |
  | **Function** | **Purpose** | | | | |
  | create_*(multiple)* | 提供一組便利的工廠函數，用於快速創建並拋出特定類型的業務異常。 | | | | 5 | `command_executor.py`, `query_service.py`, etc.

- **注意**: 此檔案行數較多 (220 LOC)，但考慮到它定義了整個專案的異常體系，這種集中管理是合理的。
