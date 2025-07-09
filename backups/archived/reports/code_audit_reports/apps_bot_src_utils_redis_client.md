### FILE REPORT: apps/bot/src/utils/redis_client.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：34
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | **Function** | **Purpose** | | | | |
  | get_redis_client | 使用快取 (lru_cache) 提供一個單例的異步 Redis 客戶端實例。 | | | | 6+ | `main.py`, `services/cost_tracker.py`, `services/message_handler_di.py`, and self-module calls
  | get_cached_value | 從 Redis 中獲取指定鍵的緩存值。 | | | ❌ | 0 |
  | set_cached_value | 將一個值設置到 Redis 緩存中，並可選擇設定過期時間。 | | | ❌ | 0 |
  | increment_counter | 將 Redis 中指定鍵的計數器增加特定數值。 | | | | 1 | `services/cost_tracker.py`
  | get_counter | 從 Redis 中獲取指定計數器的當前值。 | | | | 1 | `services/cost_tracker.py`

- **注意**: 此模組提供了通用的快取功能 (`get_cached_value`, `set_cached_value`)，但在目前的專案中並未被使用。只有計數器相關的功能被 `cost_tracker` 服務所利用。這可能表示快取功能是為未來擴展所預留的。
