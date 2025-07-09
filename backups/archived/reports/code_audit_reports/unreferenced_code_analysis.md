# 未被引用程式碼審慎處置報告 (2025-06-23)

## A. 必須刪除（確定冗餘 / 重複）

| 檔案 | 類別 / 方法 | 建議 | 理由 |
| --- | --- | :---: | --- |
| `utils/observability.py` | `get_tracer`（第二次定義） | 刪除 | 同檔前方已有相同實作，重複定義將混淆維護者。 |
| `application/monitoring_service.py` | `_perform_health_checks`（第二次定義） | 刪除 | 內部重複，功能完全覆寫，保留一份即可。 |

---

## B. 建議保留（尚未使用但具設計意圖）

| 檔案 | 類別 / 方法 | 理由 |
| --- | --- | --- |
| `config/mcp_config.py` | `MCPConfigManager.add_server_config` / `list_servers` / `update_client_config` / `get_config_summary` | 預留 MCP 伺服器 CRUD 能力，未來管理後台或 CLI 會用到。 |
| `utils/observability.py` | `get_telemetry_health` | 高價值遙測診斷函式，可整合至 `/health`。 |
| `utils/redis_client.py` | `get_cached_value`, `set_cached_value` | 通用快取 API，日後可直接啟用 Response Cache。 |
| `application/messaging_service.py` | `get_user_session`, `clear_user_session` | 會話管理接口，方便客服 / 測試 / GDPR。 |
| `application/application_facade.py` | `execute_sql_query`, `clear_query_cache`, `get_performance_report`, `get_user_session`, `clear_user_session`, `get_query_statistics`, `get_facade_info` | Facade 高層管理 API，利於測試與運維。 |
| `application/query_service.py` | `get_table_info`, `get_recent_queries` | DB Explorer 與 APM 儀表板所需。 |
| `infrastructure/service_registry.py` | `unregister`, `has_service`, `get_service_provider` | 測試注入 mock 或熱插拔服務時必備。 |
| `domain/command_handler.py` | `CommandRegistry.has_command`, `CommandRegistry.get_help_text` | 外部工具可用來檢查指令衝突或產生文件。 |

---

## 結論

1. **立即清理**：刪除兩處重複定義 (`utils/observability.py`、`application/monitoring_service.py`)。
2. **全面保留**：其餘未被直接引用的程式碼均為擴展／診斷／管理用途，刪除將降低系統可維護性與可擴展性。

> 若需自動化移除 A 類重複程式碼，請指示，我可提交相應 patch。
