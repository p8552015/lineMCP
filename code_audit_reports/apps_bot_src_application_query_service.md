### FILE REPORT: apps/bot/src/application/query_service.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：392
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | QueryApplicationService | 協調所有數據庫查詢流程，包括執行、驗證、快取、統計和歷史記錄。 | — | — | | 1 | `application/application_facade.py`
  | | | execute_sql_query | 安全地執行 SQL 查詢，是此服務的核心入口。 | | |
  | | | _validate_query | 執行多項安全檢查，確保查詢語句是安全的唯讀操作。 | | |
  | | | _generate_cache_key | 為查詢語句生成一個標準化的 MD5 快取鍵。 | | |
  | | | _is_cache_expired | 判斷一個快取項是否已超過其生存時間 (TTL)。 | | |
  | | | _should_cache_result | 根據查詢結果的特性（如執行時間、大小）決定是否應該快取。 | | |
  | | | _cache_result | 將查詢結果存入記憶體快取中，並管理快取大小。 | | |
  | | | _cleanup_expired_cache | 從快取中移除所有過期的項目。 | | |
  | | | _update_query_stats | 在每次查詢後更新性能統計數據（如總數、平均時間等）。 | | |
  | | | _add_to_history | 將每次查詢的元數據記錄到查詢歷史中。 | | |
  | | | get_table_info | 提供獲取所有資料表列表或特定資料表結構的功能。 | ❌ | 0 |
  | | | get_query_statistics | 獲取當前的查詢統計資訊。 | | |
  | | | get_recent_queries | 獲取最近的查詢歷史記錄。 | ❌ | 0 |
  | | | clear_cache | 清除所有記憶體中的查詢快取。 | | |
  | | | _perform_health_checks | 執行此服務內部的健康檢查，包括 MCP 連接和快取狀態。 | | |
  | | | _shutdown_service | 在服務關閉時清理所有資源，如快取、歷史和統計數據。 | | |
