# 檔案分析報告：`apps/bot/src/services/nl_to_sql/interfaces/query_builder_interfaces.py`

## 1. 檔案目的與角色

此檔案是 NL-to-SQL 新 SOLID 架構中，負責**查詢建構**環節的**契約定義中心**。它遵循單一職責和介面隔離原則，將「根據結構化輸入生成 SQL 查詢」這一複雜任務，精細地拆分為多個獨立的職責，並為每個職責定義了清晰的抽象介面。

它在架構中的核心角色是：
1.  **定義契約**: 為查詢建構器、模板管理器、查詢優化器和快取機制提供了一致的、穩定的抽象介面。
2.  **實現解耦**: 將 SQL 的**模板管理**、**參數填充**、**效能優化**和**結果快取**這四個高度相關但又截然不同的關注點完全分離。
3.  **奠定可配置性和可擴展性**: 透過模板化和策略化的介面設計，使得 SQL 邏輯、優化規則和快取策略都可以在不修改核心建構邏輯的情況下進行替換和擴展。

這個檔案是查詢生成引擎的 "憲法"，確保所有元件各司其職，協同工作。

## 2. 主要類別/函數定義

此檔案定義了四個高度專注的抽象基底類別 (Interface)。

### `class IQueryBuilder(ABC)`
*   **職責**: 這是查詢建構流程的**總指揮**。它負責接收結構化的查詢意圖 (`QueryType`, `parameters`)，並協調其他元件，最終產出一個可執行的 SQL 字串。
*   **核心方法**:
    *   `build_query(...) -> str`: 核心的建構方法。
    *   `validate_parameters(...) -> bool`: 在建構前驗證輸入的參數是否滿足要求。
    *   `get_required_parameters(...)` 和 `get_supported_query_types()`: 提供了自我描述的能力，讓外界了解它的需求和能力範圍。

### `class ITemplateManager(ABC)`
*   **職責**: 專門負責 **SQL 模板的管理**。這是一個關鍵的架構決策，它將 SQL 的邏輯從程式碼中剝離，使其成為可配置的資源。
*   **核心方法**:
    *   `get_template(...) -> str`: 根據查詢類型獲取對應的 SQL 模板。
    *   `load_templates_from_file(...)` 和 `reload_templates()`: 提供了從外部檔案載入和**熱重載**模板的能力，這對於實現動態更新查詢邏輯至關重要，無需重啟服務。

### `class IQueryOptimizer(ABC)`
*   **職責**: 專門負責 **SQL 的優化與安全**。它代表了一個可選的、可插入的處理階段，用於提升查詢品質。
*   **核心方法**:
    *   `optimize_query(...) -> str`: 接收一個 SQL，返回一個更優化的版本。
    *   `analyze_query(...) -> dict`: 分析查詢的潛在效能問題。
    *   `validate_query_security(...) -> dict`: 進行 SQL 安全性掃描。

### `class IQueryCache(ABC)`
*   **職責**: 專門負責 **查詢結果的快取**。它將快取策略和實現細節從主業務邏輯中分離出來。
*   **核心方法**:
    *   `get_cached_result(...)` 和 `set_cached_result(...)`: 提供了標準的 Key-Value 快取讀寫操作。
    *   `invalidate_cache(...)`: 提供了快取失效機制。

## 3. 功能實現的簡要描述

這個檔案本身不實現功能，但它精確地描繪了一個功能強大、高度解耦的查詢建構流程：

1.  **請求發起**: 外部客戶端（如 `NaturalLanguageToSQLService`）向 `IQueryBuilder` 的實例發起一個 `build_query` 請求。
2.  **模板獲取**: `IQueryBuilder` 實例轉向 `ITemplateManager` 實例，根據 `query_type` 獲取對應的 SQL 模板字串。
3.  **參數驗證與填充**: `IQueryBuilder` 使用 `validate_parameters` 檢查客戶端提供的參數，然後安全地將這些參數填充到模板的佔位符中，生成一個 "草稿" SQL。
4.  **優化 (可選)**: `IQueryBuilder` 可以將這個 "草稿" SQL 交給 `IQueryOptimizer` 實例，後者對其進行分析、重寫和安全加固，返回一個 "優化後" 的 SQL。
5.  **快取檢查 (可選)**: 在最終執行 SQL 之前，系統可以先用一個由 SQL 和參數構成的唯一鍵，去 `IQueryCache` 實例中查找是否已有快取結果。如果有，則直接返回結果，跳過資料庫查詢。
6.  **返回 SQL**: `IQueryBuilder` 將最終成型的 SQL 字串返回給客戶端。
7.  **結果快取 (可選)**: 客戶端在從資料庫拿到結果後，可以將結果存入 `IQueryCache` 中，以備後用。

## 4. 依賴關係

*   **`abc.ABC`, `abc.abstractmethod`**: 依賴 Python 的標準抽象基底類別工具。
*   **`..models.query_models.QueryType`**: 依賴於模型層定義的 `QueryType` 枚舉。再次強調，介面依賴於穩定的資料模型，這是一個優秀的架構實踐。

## 5. 設計模式與架構決策

*   **單一職責原則 (SRP)**: 體現得淋漓盡致。建構、模板管理、優化、快取，四個職責被完美地分離到四個不同的介面中。
*   **介面隔離原則 (ISP)**: 客戶端可以只依賴 `IQueryBuilder`，而 `IQueryBuilder` 的實作則可以根據需要依賴其他三個介面。沒有任何一個介面包含了它不應該有的方法。
*   **策略模式 (Strategy Pattern)**: `IQueryOptimizer` 本質上就是一個策略介面，允許插入不同的優化策略。`IQueryCache` 也是如此，可以插入不同的快取策略（内存、Redis、檔案等）。
*   **模板方法模式 (Template Method Pattern)** 的思想: `IQueryBuilder` 的 `build_query` 方法可以看作是一個模板方法，它定義了查詢建構的骨架流程，而具體的步驟（如從哪裡獲取模板、如何優化）則委託給其他策略元件。
*   **可配置性與熱重載**: `ITemplateManager` 中對熱重載的支援是一個關鍵的架構決策，旨在提高系統的動態性和可維護性。

## 6. 潛在的改進點

*   **介面的粒度**: 對於某些非常簡單的應用，同時實現四個介面可能會顯得有些過度設計。但對於一個追求長期可維護性和擴展性的複雜系統來說，這種粒度是恰到好處的。
*   **錯誤處理**: 介面的 `docstring` 中提到了各種自訂錯誤類型（如 `InvalidQueryTypeError`, `TemplateNotFoundError`），這些需要在一個統一的地方被定義，以便客戶端可以捕獲和處理它們。 