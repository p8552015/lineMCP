# 檔案分析報告：`apps/bot/src/services/nl_to_sql/builders/sql_query_builder.py`

## 1. 檔案目的與角色

此檔案定義了 `SQLQueryBuilder`，它是 NL-to-SQL 新架構中**建構階段的核心**。在自然語言被解析為結構化的 `ParsedQuery` 物件後，此建構器接手，將該結構化資訊轉換為一個**安全、有效且可執行的 SQL 查詢字串**。

它的核心角色是：
1.  **SQL 生成器 (SQL Generator)**: 根據輸入的查詢類型和參數，從模板中生成最終的 SQL。
2.  **安全閘門 (Security Gatekeeper)**: 嚴格檢查和清理所有傳入的參數，防止 SQL 注入等安全漏洞。
3.  **品質保證 (Quality Assurance)**: 在生成前後進行多重驗證，確保模板存在、參數齊全、輸出不為空，保證了查詢的健壯性。
4.  **效能分析師 (Performance Analyst)**: 具備估算查詢複雜度和成本的能力，甚至能提供優化建議，為系統監控和效能調優提供了基礎。

總之，它不只是一個簡單的「字串拼接器」，而是一個高度工程化的 SQL 查詢**工廠**。

## 2. 主要類別/函數定義

### `class SQLQueryBuilder(IQueryBuilder)`
這是檔案中唯一定義的類別，它嚴格實現了 `IQueryBuilder` 介面，確保了其在架構中的可替換性。

#### 核心方法

*   **`__init__(self, template_manager: ITemplateManager)`**:
    建構函數體現了**依賴倒置原則**，它不依賴具體的模板實現，而是依賴於 `ITemplateManager` 抽象介面。在初始化時，它會準備好內部使用的參數驗證器和複雜度估算規則。

*   **`build_query(self, query_type: QueryType, parameters: dict) -> str`**:
    這是建構器的主要入口點和核心工作流程：
    1.  **驗證**: 驗證查詢類型和參數的合法性。
    2.  **獲取模板**: 從 `_template_manager` 獲取對應的 SQL 模板。
    3.  **安全處理**: 呼叫 `_prepare_safe_parameters` 清理和轉義所有參數。
    4.  **建構**: 呼叫 `_build_query_from_template` 將安全參數填入模板。
    5.  **優化**: 呼叫 `_optimize_query` 進行後處理，如清理空白。
    6.  **回傳**: 回傳最終的 SQL 字串。
    整個過程被 `try...except` 區塊包裹，並帶有豐富的日誌記錄，非常健壯。

*   **`validate_parameters(self, ...)`**:
    根據預先定義在 `get_required_parameters` 和 `_build_parameter_validators` 中的規則，對傳入的參數進行全面檢查。

*   **`_prepare_safe_parameters(self, ...)` 和 `_escape_sql_parameter(self, ...)`**:
    這兩個方法構成了防止 SQL 注入的核心防線。它們協同工作，對參數值進行類型檢查、關鍵字過濾和特殊字元轉義，最大限度地確保了查詢的安全性。

*   **`estimate_query_cost(self, sql_query: str) -> dict`**:
    一個非常進階的功能。它使用正則表達式來分析 SQL 字串，識別出 `JOIN`, `GROUP BY`, `WHERE` 等高成本操作，從而對查詢的複雜度進行量化評分。

*   **`get_query_metadata(self, ...)`**:
    為每個支援的查詢類型提供豐富的元數據，包括人類可讀的描述、預估複雜度、效能提示等。這對於自動化、文件生成和除錯非常有價值。

## 3. 功能實現的簡要描述

`SQLQueryBuilder` 的工作流程可以比喻為一個嚴謹的德國汽車工廠：
1.  **接收訂單**: 接收到一個生產指令 (`query_type`) 和一批原料 (`parameters`)。
2.  **品質檢驗 (QC)**: 首先，它會嚴格檢驗這批原料是否符合規格（`validate_parameters`），不合格的直接退回。
3.  **調取藍圖**: 從藍圖庫（`ITemplateManager`）中調取對應的設計藍圖（SQL 模板）。
4.  **原料預處理**: 將所有原料進行清洗、消毒和標準化處理（`_prepare_safe_parameters`），確保它們不會損壞生產線。
5.  **裝配**: 按照藍圖，將處理好的原料精確地安裝到車體框架（模板）中（`_build_query_from_template`）。
6.  **最終調校與測試**: 對組裝好的汽車進行最後的調整（`_optimize_query`），並進行一次全面的壓力測試和安全評估（`estimate_query_cost`, `validate_query_security`）。
7.  **出廠**: 只有完全合格的產品（SQL 查詢）才能被交付出廠。

## 4. 依賴關係

*   **`structlog`**: 用於結構化日誌。
*   **`html`, `re`**: 標準函式庫，分別用於 HTML 字元轉義和正則表達式。
*   **`..interfaces.query_builder_interfaces.IQueryBuilder`**: **實現**此介面，遵循 LSP。
*   **`..interfaces.query_builder_interfaces.ITemplateManager`**: **依賴**此介面，遵循 DIP。
*   **`..models.query_models.QueryType`**: 使用查詢類型枚舉。

## 5. 設計模式與架構決策

*   **模板方法模式 (Template Method Pattern)**: `build_query` 方法定義了一個演算法的骨架，而將一些具體的步驟（如獲取模板、驗證參數）委託給子方法或依賴的物件去實現。
*   **策略模式 (Strategy Pattern)**: 參數驗證機制（`_parameter_validators`）就是一個小型的策略模式，它為不同的查詢類型定義了不同的驗證策略（函數）。
*   **單一職責原則 (SRP)**: 建構器專注於「建構 SQL」這一單一職責，將「儲存和管理模板」的職責分離給了 `ITemplateManager`。
*   **依賴倒置原則 (DIP)**: 這是最核心的設計決策之一。通過依賴抽象介面 `ITemplateManager`，使得 `SQLQueryBuilder` 可以與任何實現了該介面的模板來源（如檔案、資料庫、Redis）協同工作，極大地提高了靈活性和可測試性。
*   **防禦性程式設計 (Defensive Programming)**: 整個類別充滿了大量的檢查和驗證 (`if not ...`, `try...except`)，確保在任何異常情況下都能優雅地失敗並提供清晰的錯誤資訊。

## 6. 潛在的改進點

*   **參數化查詢**: 目前的參數轉義是手動實現的。一個更安全、更標準的做法是生成帶有預留位置（如 `?` 或 `%s`）的 SQL，並將參數值作為一個單獨的列表傳遞給資料庫驅動程式，由驅動程式來處理轉義。這能從根本上杜絕 SQL 注入的風險。
*   **模板引擎**: 目前的模板填充是簡單的 `str.format()`。對於更複雜的邏輯（例如，根據參數是否存在來動態添加 `WHERE` 子句），可以考慮引入一個輕量級的模板引擎，如 `Jinja2`，它可以提供更強大的條件和迴圈邏輯。
*   **非同步模板獲取**: 如果模板儲存在遠端（如資料庫或網路服務），`_template_manager.get_template` 方法應該是 `async` 的，`build_query` 也應該相應地使用 `await`。目前的實現是同步的。 