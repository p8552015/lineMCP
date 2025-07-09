### FILE REPORT: apps/bot/src/application/application_facade.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：323
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | ApplicationFacade | 作為應用層的統一入口 (Facade)，封裝和協調底層多個應用服務，為外部提供簡潔的高層次介面。 | — | — | | 1 | `routes/webhook.py`
  | | | initialize | 初始化門面，透過服務工廠創建、註冊並初始化所有依賴的應用服務。 | | |
  | | | process_message | 提供處理用戶訊息的高層次介面，內部委託給 `MessagingApplicationService`。 | | |
  | | | execute_sql_query | 提供執行 SQL 查詢的高層次介C介面，內部委託給 `QueryApplicationService`。 | ❌ | 0 |
  | | | get_system_health | 提供獲取系統健康狀況的高層次介面，內部委託給 `MonitoringApplicationService`。 | | |
  | | | get_dashboard_data | 從多個服務收集數據，組合儀表板所需的綜合資訊。 | | |
  | | | get_user_session | 提供獲取用戶會話資訊的介面。 | ❌ | 0 |
  | | | clear_user_session | 提供清除用戶會話的介面。 | ❌ | 0 |
  | | | get_query_statistics | 提供獲取查詢統計資訊的介面。 | ❌ | 0 |
  | | | clear_query_cache | 提供清除查詢快取的介面。 | ❌ | 0 |
  | | | get_performance_report | 提供獲取效能報告的介面。 | ❌ | 0 |
  | | | shutdown | 協調關閉所有已註冊的應用服務。 | | |
  | | | get_facade_info | 獲取關於門面自身及其管理的服務的綜合資訊。 | ❌ | 0 |
  | **Function** | **Purpose** | | | | |
  | get_application_facade | 以單例模式提供 `ApplicationFacade` 的全域實例。 | | | | 1 | `routes/webhook.py`

- **注意**: 此 Facade 提供了大量高層次的管理和查詢介面（如 `execute_sql_query`, `clear_query_cache` 等），這些介面目前未被 Webhook 直接使用，但它們為未來可能的管理 API 或內部調試工具提供了強大的支持。
