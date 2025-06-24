### FILE REPORT: apps/bot/src/application/monitoring_service.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：439 ❌ High LOC
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | PerformanceMetric | 以資料類別 (dataclass) 形式標準化地表示一條效能指標數據。 | — | — | | |
  | HealthStatus | 以資料類別 (dataclass) 形式標準化地表示一個組件的健康狀態。 | — | — | | |
  | MonitoringApplicationService | 作為一個小型的應用性能監控(APM)系統，負責收集指標、執行健康檢查、提供儀表板數據和效能報告。 | — | — | | 1 | `application/application_facade.py`
  | | | record_metric | 記錄一條詳細的效能指標，並管理指標數據的保留策略。 | | |
  | | | record_request_metrics | 專門用於記錄與單次請求相關的關鍵指標（如持續時間、狀態）。 | | |
  | | | perform_comprehensive_health_check | 執行一個涵蓋所有應用服務、系統資源和效能指標的全面健康檢查。 | | |
  | | | _check_system_resources | 檢查主機的系統資源使用情況（CPU、記憶體、磁碟），需要 `psutil` 庫。 | | |
  | | | _check_performance_metrics | 根據預設的效能基線，檢查當前的效能指標是否達標。 | | |
  | | | _generate_health_summary | 根據各組件的健康狀況生成一份總結報告。 | | |
  | | | _update_health_status | 更新內部記錄的組件健康狀態。 | | |
  | | | get_dashboard_data | 聚合各種指標和統計數據，為監控儀表板提供所需的綜合資訊。 | | |
  | | | get_performance_report | 根據指定時間範圍內的指標數據，生成一份包含摘要和建議的效能報告。 | | |
  | | | _generate_performance_recommendations | 根據指標數據和效能基線，自動生成可行的效能優化建議。 | | |
  | | | _perform_health_checks | (重複定義) 執行此服務自身的健康檢查。 | | |
  | | | _shutdown_service | 在服務關閉時記錄關閉指標並清理所有監控數據。 | | |

- **注意**: `_perform_health_checks` 方法在此類別中被定義了兩次，這是冗餘的。此檔案行數較多 (439 LOC)，可以考慮將 `PerformanceMetric` 和 `HealthStatus` 等資料類別移至獨立的 `models` 文件中以提高可讀性。
