### **分析報告: `test_query_service.py`**

**產出日期:** 2025-06-27
**撰寫角色:** 架構師 / 技術負責人
**版本:** v2 架構師增強版

---

### **【文件角色摘要】**

*   **📌 主要功能與責任：**
    此文件是 `QueryApplicationService` 的單元測試集。其核心職責是全面驗證查詢應用服務的所有功能，這是系統與資料庫（透過 MCP 抽象層）互動的核心。主要驗證點包括：
    1.  **查詢執行與委派**: 驗證 `execute_sql_query` 能否將 SQL 查詢正確地委派給 `MCP Client`。
    2.  **查詢驗證**: 測試 `_validate_query` 能否有效阻止潛在的惡意或破壞性查詢（如 `DROP`, `DELETE`）。
    3.  **快取機制**: 全面測試查詢結果的快取邏輯，包括快取命中、快取過期、快取清理、快取決策 (`_should_cache_result`) 以及快取大小限制。
    4.  **統計與歷史記錄**: 驗證服務是否能準確記錄查詢統計數據（總數、成功率、快取命中率）和查詢歷史。
    5.  **元數據查詢**: 測試 `get_table_info` 等獲取資料庫結構資訊的功能。
    6.  **錯誤處理**: 驗證在 MCP 客戶端或查詢本身出錯時，服務能否拋出定義好的業務異常 (`DatabaseQueryException`, `ValidationException`)。

*   **🧠 在系統架構中的定位（上層來源與下游依賴）：**
    *   **定位**: 位於測試層，專門驗證應用層的 `QueryApplicationService`。該服務封裝了所有與資料查詢相關的操作。
    *   **上層來源**: 由 `pytest` 測試框架驅動。
    *   **下游依賴**:
        *   `src.application.query_service.QueryApplicationService` (被測模組)
        *   `mcp_client_factory` (被模擬的 MCP 客戶端工廠)
        *   `db_service`, `response_parser` (被模擬的依賴)
        *   `pytest`, `unittest.mock`

*   **🔁 是否處理通訊 / 外部互動：**
    否。對 MCP Client 的呼叫被完全模擬，從而將測試與網絡和底層資料庫隔離開來。

*   **⚙️ 是否處理設定管理：**
    否。

*   **🧪 是否負責資料驗證、格式轉換或協定解析：**
    是。
    *   `_validate_query` 專門負責驗證 SQL 查詢的合法性。
    *   測試驗證了服務能處理來自 `MCP Client` 的原始回應，並透過（被模擬的）`response_parser` 進行解析。
    *   `_generate_cache_key` 負責將不同格式的等效 SQL 查詢標準化為統一的快取鍵。

*   **💡 是否涉及平台相依性、跨平台兼容性、錯誤恢復：**
    *   **平台相依性**: 無。
    *   **錯誤恢復**: 是。`test_execute_sql_query_error` 專門測試了當底層 MCP 呼叫失敗時，服務會向上拋出 `DatabaseQueryException`，這是一個比通用 `Exception` 更具體的、可控的異常。

*   **🔐 是否與授權、安全、敏感操作有關：**
    是。`_validate_query` 的存在是此服務的一個關鍵安全特性，它透過黑名單機制防止了 SQL 注入中最具破壞性的一類操作，是系統的第一道防線。

*   **🎯 實用比喻：**
    此測試文件就像一個圖書館管理員的崗位培訓考核。考核內容包括：
    1.  **查書流程**: 驗證管理員（`QueryApplicationService`）能否根據讀者需求單（SQL 查詢）到後端書庫（MCP Client）正確取書。
    2.  **禁書審查**: 驗證管理員能否識別出讀者試圖借閱禁書（`DROP TABLE` 等）的請求並立即拒絕（`_validate_query`）。
    3.  **常用書架**: 驗證管理員是否會將熱門書籍放在手邊的常用書架上（查詢快取），並在書籍太舊時（快取過期）重新去書庫取新版。
    4.  **工作日誌**: 驗證管理員是否準確記錄了每天的工作量和借閱成功率（查詢統計）。
    5.  **意外處理**: 在書庫回報找不到書時（MCP 錯誤），管理員是否能按規定流程處理，而不是驚慌失措（錯誤處理）。

---

### **【類別分析】**

*   **類別名稱：** `TestQueryApplicationService`
    *   **📌 創建目的：** 提供一個全面的單元測試套件，以確保 `QueryApplicationService` 的數據查詢、快取、安全和統計功能都按設計工作。
    *   **🧭 使用場景：** 在 CI/CD 流程中，作為驗證核心數據鏈路功能的關鍵一環。
    *   **📂 管理資源：** 主要管理 `pytest` fixtures，為每個測試提供模擬的 `mcp_client` 和其他依賴。同時，它也間接管理著被測對象內部狀態的資源，如 `_query_cache` 和 `_query_history`。
    *   **🧩 內含哪些關鍵方法與邏輯功能：**
        *   `test_execute_sql_query_*`: 測試核心查詢路徑，包括成功、快取命中、快取過期和錯誤場景。
        *   `test_validate_query_*`: 專門測試 SQL 安全驗證邏輯。
        *   `test_cache_*`, `test_is_cache_expired`, `test_should_cache_result`: 深入測試快取機制的各個方面，邏輯覆蓋非常完整。
        *   `test_stats_*`, `test_history_*`: 測試可觀測性相關的功能。
        *   `test_get_table_info_*`: 測試元數據查詢功能。
    *   **🔄 是否支援擴充或注入：** 是。所有外部依賴都通過建構子注入，易於模擬。
    *   **💡 設計考量：**
        *   **SRP**: 服務本身職責清晰，專注於「查詢」。測試類別也遵循此原則，每個方法只測一個點。
        *   **安全**: `test_validate_query_invalid` 體現了對安全性的高度重視。
        *   **效能**: 快取相關的測試 (`test_execute_sql_query_with_cache`, `test_should_cache_result` 等) 顯示了該服務在設計時對效能的考量。
    *   **✅ 是否容易測試 / 是否有測試機制設計：** 是。該測試文件展示瞭如何對一個包含複雜內部狀態（快取、歷史記錄）和業務規則（驗證、快取決策）的服務進行有效測試。

---

### **【方法總覽】**

| 方法名稱 | 功能簡述 | 是否為關鍵邏輯 | 內部使用次數 | 外部被呼叫 | 錯誤處理 | 資源釋放 | 存在價值 |
|---|---|---|---|---|---|---|---|
| `test_execute_sql_query_*`| 驗證核心查詢流程 | 是 | 0 | pytest | 是 | 無 | 極高 (核心業務) |
| `test_validate_query_*`| 驗證SQL安全防護 | 是 | 0 | pytest | 是 | 無 | 極高 (安全保障) |
| `test_cache_*` | 驗證快取機制 | 是 | 0 | pytest | 是 | 是(清理)| 極高 (效能保障) |
| `test_get_table_info_*`| 驗證元數據查詢 | 是 | 0 | pytest | 是 | 無 | 高 (輔助功能) |
| `test_get_query_statistics`| 驗證統計數據聚合 | 是 | 0 | pytest | 無 | 無 | 高 (可觀測性) |

---

### **【模組關係與相依】**

*   **上游呼叫者（誰依賴此模組？）：** `pytest`
*   **下游相依元件（此模組依賴哪些外部資源/API？）：**
    *   `QueryApplicationService` (被測對象)
    *   `DatabaseQueryException`, `ValidationException` (自定義異常)
    *   `unittest.mock`, `pytest`, `datetime`
*   **是否存在循環相依（circular dependency）：** 否。

---

### **【架構師補充面向】**

*   **🗂️ 是否有循環相依 / 高耦合風險：** 無。
*   **🧪 可測試性：** 非常高。該文件是一個優秀的測試範例，它不僅測試了服務的公開 API，還透過對內部方法 (protected method) 的測試（如 `_validate_query`, `_generate_cache_key`），確保了核心演算法和業務規則的正確性。這在單元測試中是合理且推薦的做法。
*   **🧠 能否重構為 microservice 或 reusable package：** `QueryApplicationService` 的設計已經非常獨立，如果未來有多個服務需要統一的、帶有快取和安全校驗的查詢能力，它有潛力被重構成一個可重用的共享庫。 