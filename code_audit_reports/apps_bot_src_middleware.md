### FILE REPORT: apps/bot/src/middleware.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：107
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | **Function** | **Purpose** | | | | |
  | setup_middleware | 作為一個集中設定函數，將所有定義好的中介軟體應用到 FastAPI 的應用實例上。 | | | | 1 | `main.py`
  | add_trace_id | 為每個傳入的 HTTP 請求添加一個唯一的追蹤 ID (`X-Trace-Id`)，以便於在日誌和監控系統中追蹤請求。 | | | | |
  | prometheus_middleware | 在請求處理前後收集關鍵的效能指標 (請求總數、持續時間、活躍請求數)，並將它們暴露給 Prometheus 監控系統。 | | | | |
  | logging_middleware | 在請求處理前後使用結構化日誌 (structlog) 記錄詳細的請求資訊，如方法、路徑、狀態碼和處理時間。 | | | | |

- **全域設定**:
  - `CORSMiddleware`: 配置了跨來源資源共用策略，允許來自任何來源的請求。
  - `TrustedHostMiddleware`: 配置了信任主機策略，允許來自任何主機的請求。

- **Prometheus 指標**:
  - `http_requests_total`: 一個計數器，用於統計不同端點和狀態碼的請求總數。
  - `http_request_duration_seconds`:一個直方圖，用於記錄請求的響應時間分佈。
  - `active_requests`: 一個儀表，用於即時顯示當前正在處理的請求數量。
