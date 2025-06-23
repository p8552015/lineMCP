### FILE REPORT: apps/bot/src/main.py
- 檔案狀態：<REFERENCED> (應用程式入口)
- 檔案 LOC：92
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | **Function** | **Purpose** | | | | |
  | lifespan | 作為 FastAPI 的生命週期管理器，在應用啟動時設置可觀測性並檢查 Redis 連接，在關閉時優雅地清理資源。 | | | | |
  | health_check | 提供一個 `/health` 端點，用於檢查應用程式及其核心依賴（如 Redis）的健康狀況。 | | | | |
  | global_exception_handler | 作為一個全域的例外處理器，捕獲所有未被處理的異常，記錄詳細日誌並返回一個標準的 500 錯誤回應。 | | | | |

- **應用程式 (`app`) 說明**:
  - **核心功能**: 這是整個 Web 服務的 FastAPI 實例。
  - **中介軟體**: 透過 `setup_middleware` 設置了必要的請求處理中介軟體。
  - **路由**: 包含了 `webhook.router` 來處理來自 LINE 的請求。
  - **監控**:
    - 透過 `FastAPIInstrumentor` 自動整合 OpenTelemetry 追蹤。
    - 掛載了 `/metrics` 端點，用於暴露 Prometheus 格式的監控指標。
