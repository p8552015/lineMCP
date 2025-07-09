### FILE REPORT: apps/bot/src/application/base_service.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：261
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | BaseApplicationService | 作為所有應用服務的抽象基底類，定義了統一的生命週期介面 (初始化、健康檢查、關閉) 和通用行為。 | — | — | | 2+ | `messaging_service.py`, `query_service.py`, etc.
  | | | initialize | 公開的初始化方法，確保初始化邏輯只執行一次。 | | |
  | | | get_service_info | 獲取服務的基本資訊，如名稱、類型和初始化狀態。 | ❌ | 0 |
  | | | health_check | 執行服務的健康檢查，並包含 OpenTelemetry 追蹤。 | | |
  | | | shutdown | 公開的關閉方法，確保服務資源被正確釋放。 | | |
  | ApplicationServiceContext | 作為一個服務容器，負責註冊、管理和協調所有應用服務的生命週期。 | — | — | | 1 | `application/application_facade.py`
  | | | register_service | 將一個應用服務實例註冊到上下文中。 | | |
  | | | get_service | 根據名稱從上下文中獲取一個已註冊的服務。 | ❌ | 0 |
  | | | initialize_all | 按照註冊順序初始化所有服務。 | | |
  | | | shutdown_all | 按照與註冊相反的順序關閉所有服務。 | | |
  | | | health_check_all | 對所有已註冊的服務執行健康檢查並提供一份總結報告。 | | |
  | | | get_context_info | 獲取關於服務容器本身的資訊。 | ❌ | 0 |
  | **Function** | **Purpose** | | | | |
  | get_application_context | 以單例模式提供 `ApplicationServiceContext` 的全域實例。 | | | | 1 | `application/application_facade.py`

- **注意**: `BaseApplicationService` 和 `ApplicationServiceContext` 中的幾個 `get_*_info` 方法目前未被使用，它們主要用於潛在的調試或監控場景。
