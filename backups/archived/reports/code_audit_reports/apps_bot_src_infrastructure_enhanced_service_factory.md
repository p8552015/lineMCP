### FILE REPORT: apps/bot/src/infrastructure/enhanced_service_factory.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：512 ❌ High LOC
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | EnhancedServiceFactory | 作為依賴注入(DI)容器的核心，負責註冊、管理和提供系統中所有服務的實例。 | — | — | | 1 | `routes/webhook.py`
  | | | initialize | 初始化工廠，註冊所有服務並創建服務提供者。 | | |
  | | | _register_core_services | 註冊核心服務，如 AI、訊息格式化、MCP客戶端等。 | | |
  | | | _register_domain_services | 註冊領域服務，如自然語言處理、資料庫、指令執行器等。 | | |
  | | | _register_application_services | 註冊應用層服務，如訊息、查詢、監控服務等。 | | |
  | | | _register_infrastructure_services | 註冊基礎設施服務，如 `MessageHandlerDI`。 | | |
  | | | _register_nl_to_sql_services | 註冊所有與 NL-to-SQL 相關的、遵循 SOLID 原則的微服務。 | | |
  | | | _create_composite_parser | 創建並配置組合解析器，設定其包含的解析策略。 | | |
  | | | _create_command_executor | 創建指令執行器，並為其注入所有必要的依賴。 | | |
  | | | _create_messaging_service | 創建訊息處理應用服務，並為其注入所有必要的依賴。 | | |
  | | | _create_message_handler | 創建 `MessageHandlerDI`，並為其注入所有必要的依賴。 | | |
  | | | get_service | 從服務提供者獲取一個服務實例。 | | |
  | | | get_required_service | 獲取一個必需的服務實例，如果找不到則會引發錯誤。 | | |
  | | | create_message_handler | 創建一個 `MessageHandlerDI` 的便利方法。 | | |
  | | | get_registry_info | 獲取關於服務註冊表的詳細統計資訊。 | ❌ | 0 |
  | | | get_*(multiple)* | 提供多個 `get_<service_name>` 方法以保持向後兼容性或提供便利訪問。 | | |
  | **Function** | **Purpose** | | | | |
  | get_enhanced_service_factory | 以單例模式提供 `EnhancedServiceFactory` 的全域實例。 | | | | 1 | `routes/webhook.py`

- **注意**: 此檔案行數極多 (512 LOC)，是整個系統複雜度的核心。它明確地展示了系統中所有服務的依賴關係。可以考慮將不同層級的服務註冊邏輯 (`_register_*_services`) 拆分到不同的輔助函數或類中，以提高可讀性和可維護性。
