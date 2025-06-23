### FILE REPORT: apps/bot/src/infrastructure/error_handler.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：159
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | UnifiedErrorHandler | 作為一個統一的錯誤處理器，將各種系統和自定義異常轉換為對使用者友善的錯誤訊息。 | — | — | | 1+ | self-module
  | | | handle_error | 處理錯誤的核心入口，負責記錄日誌並根據異常類型分派處理。 | | |
  | | | _handle_bot_exception | 專門處理繼承自 `BotException` 的自定義業務異常。 | | |
  | | | _handle_system_exception | 處理未被捕獲的通用系統異常，並提供通用的錯誤回應。 | | |
  | | | _log_error | 根據異常的嚴重程度，以不同的日誌級別（`error` 或 `warning`）記錄詳細的錯誤資訊和上下文。 | | |
  | ErrorHandlerMiddleware | 提供一個裝飾器，可以方便地將 `UnifiedErrorHandler` 的處理邏輯應用到任何函數上。 | — | — | | 1 | self-module
  | **Function** | **Purpose** | | | | |
  | get_error_handler | 以單例模式提供 `UnifiedErrorHandler` 的全域實例。 | | | | 1 | self-module
  | handle_error_gracefully | 提供一個便利的函數，用於在程式碼的任何地方快速調用全域錯誤處理器。 | | | | 1 | `application/messaging_service.py`
  | create_error_middleware | 提供一個便利的函數，用於創建 `ErrorHandlerMiddleware` 的實例。 | ❌ | 0 |

- **注意**: `create_error_middleware` 函數提供了一種創建中介軟體的方式，但在目前版本中未被使用。
