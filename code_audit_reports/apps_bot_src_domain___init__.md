### FILE REPORT: apps/bot/src/domain/__init__.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：34
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | — | 此文件將 `domain` 目錄標記為一個包，並集中導出所有自定義的業務異常類和異常工廠函數，方便其他模組統一使用。 | — | — | | |

- **導出列表 (`__all__`)**:
  - **異常類**: `BotException`, `ValidationException`, `CommandParsingException`, `DatabaseQueryException`, `MCPConnectionException`, `AIServiceException`, `AuthenticationException`, `RateLimitException`, `ConfigurationException`, `BusinessLogicException`, `ExternalServiceException`
  - **異常工廠函數**: `create_validation_error`, `create_command_error`, `create_db_error`, `create_mcp_error`, `create_ai_error`
