# 📄 `sql_query_builder.py` 檔案架構分析報告

本報告由 AI 架構師 Serena 根據 `LLM_文件問答樣板_架構師升級完整版.md` 模板，對 `apps/bot/src/services/nl_to_sql/builders/sql_query_builder.py` 進行分析。

**分析目標**: `apps/bot/src/services/nl_to_sql/builders/sql_query_builder.py`
**產出日期**: 2024-07-30
**撰寫角色**: AI 架構師 / 技術負責人

---

## 🧩 樣板 1：檔案在專案中扮演的角色

【文件角色摘要】
- 📌 **主要功能與責任**:
  - 此檔案定義了 `SQLQueryBuilder` 類別，它是 NL-to-SQL 子系統的**最終 SQL 生成器**。
  - **核心職責**：
    1.  **接收結構化輸入**: 接收從解析層傳來的、結構化的 `ParsedQuery` 物件（包含 `QueryType` 和 `parameters`）。
    2.  **模板驅動生成**: 根據 `QueryType`，從下游的 `ITemplateManager` 獲取對應的 SQL 模板。
    3.  **參數驗證與安全**: 在填充模板之前，對傳入的參數進行嚴格的驗證（`validate_parameters`）和安全轉義（`_escape_sql_parameter`），以防止 SQL 注入風險。
    4.  **SQL 建構**: 將安全的參數填入 SQL 模板，生成最終的可執行 SQL 語句。
    5.  **提供元數據**: 能夠提供關於不同查詢類型的元數據，如複雜度、效能提示等（`get_query_metadata`）。

- 🧠 **在系統架構中的定位**:
  - **定位**：在 NL-to-SQL 子系統中，它處於**建構層 (Building Layer)**。它位於解析層之後，資料庫執行層之前，是將「意圖」轉換為「行動」的關鍵環節。
  - **上層來源**：理論上由一個更高層的服務（如 `NaturalLanguageToSQLService` 適配器或未來的協調器）呼叫。
  - **下游依賴**：`ITemplateManager`。它依賴模板管理器來提供 SQL 模板，實現了邏輯與模板的分離。

- 🔐 **是否與授權、安全、敏感操作有關**:
  - **是，高度相關**。這是系統中抵禦 **SQL 注入**攻擊的**核心防線**。其 `_escape_sql_parameter` 和 `validate_parameters` 方法對於系統的安全性至關重要。

- 🎯 **實用比喻**:
  - `SQLQueryBuilder` 就像一位嚴謹的**法律文書撰寫人**。他會先從法務助理（解析器）那裡接收到一個案件的要點（`ParsedQuery`）。然後，他會根據案件類型（`QueryType`），從檔案櫃裡找出對應的法律文書模板（`ITemplateManager`）。在填寫具體資訊（`parameters`）之前，他會反覆核對資訊的準確性（參數驗證）和格式（安全轉義），確保最終產出的法律文書（SQL 語句）不僅內容正確，而且格式嚴謹、無懈可擊。

---

## 🧩 樣板 2：有哪些類別，以及創建目的與結構特性

【類別分析】
- 類別名稱：`SQLQueryBuilder`
- 📌 **創建目的**:
  - **核心目的**：將**查詢的意圖**（由解析層確定）與**查詢的具體實現**（SQL 語句）分離開來。
  - **具體目的**：
    1.  **集中管理 SQL 邏輯**: 將所有 SQL 語句集中在模板中管理，而不是散落在程式碼各處，極大提升了可維護性。
    2.  **確保安全**: 提供一個統一的地方來處理 SQL 參數的驗證和轉義，避免在多個地方重複實現安全邏輯，減少了出錯的可能。
- 🧭 **使用場景**:
  - 由 `EnhancedServiceFactory` 創建，並注入一個 `ITemplateManager` 實例。
  - 在 NL-to-SQL 流程的後期被呼叫，以生成最終的 SQL。
- 🧩 **內含哪些關鍵方法與邏輯功能**:
  - `__init__(...)`: 接收模板管理器，並初始化內部的參數驗證器。
  - `build_query()`: 核心的公開方法，實現了「驗證 -> 獲取模板 -> 填充參數 -> 生成 SQL」的完整流程。
  - `validate_parameters()`: 根據查詢類型，驗證傳入的參數是否合法、完整。
  - `_prepare_safe_parameters()`: 對所有參數進行安全處理。
  - `_escape_sql_parameter()`: 實現了具體的 SQL 轉義邏輯，是安全性的核心。
  - `get_supported_query_types()`: 聲明此建構器能夠處理哪些查詢類型。
- 🔄 **是否支援擴充或注入**:
  - **是**。它依賴注入了 `ITemplateManager`。更重要的是，它的擴展性體現在其**模板驅動**的設計上。要支援一種新的查詢，主要工作是：
    1.  在 `QueryType` 枚舉中增加一個新類型。
    2.  在模板管理器中增加一個對應的 SQL 模板。
    3.  在此類別的 `get_supported_query_types` 和參數驗證邏輯中增加對新類型的支持。
    整個過程無需對 `build_query` 的核心邏輯進行修改。
- 💡 **設計考量**:
  - **模板方法模式 (Template Method Pattern)**: `build_query` 方法定義了一個演算法的骨架，而具體的 SQL 內容則由模板決定。
  - **配置/資源分離**: 將 SQL 模板作為外部資源（由 `ITemplateManager` 管理），與建構邏輯本身分離。
  - **安全性第一**: 內建了多層次的驗證和防護機制，從參數驗證到最終生成的 SQL 驗證。

---

## 🧩 樣板 4：模組關係與相依

- **上游呼叫者**：一個更高層的協調服務（如 `NaturalLanguageToSQLService`）。
- **下游相依元件**：`ITemplateManager` (模板管理器介面)。
- **是否存在循環相依**：**否**。

---

## 🧱 額外架構師視角建議補充欄位

- 🗂️ **高耦合風險**：**低**。它只依賴於 `ITemplateManager` 這個抽象介面，並且與上層呼叫者之間也是透過 `IQueryBuilder` 介面進行互動，耦合度很低。
- 🧪 **可測試性**：**極高**。在測試中，可以輕易地 Mock `ITemplateManager`，讓它針對特定的 `QueryType` 回傳一個測試用的 SQL 模板。然後就可以驗證 `SQLQueryBuilder` 是否能正確地驗證參數、填充模板，並生成預期中的 SQL 語句。
- 🧠 **重構潛力**:
  - **參數化查詢**: 目前的 `_escape_sql_parameter` 是手動實現的字串替換和轉義，雖然有效，但業界的最佳實踐是使用資料庫驅動程式提供的**參數化查詢 (Parameterized Queries)** 功能（例如，使用 `?` 或 `%s` 作為佔位符）。這樣可以將 SQL 語句和參數分開傳輸給資料庫，由資料庫驅動底層來處理轉義，是抵禦 SQL 注入最根本、最安全的方法。建議將 `build_query` 重構為回傳一個包含 SQL 模板和參數列表的元組 `(sql_template, params)`，而不是一個已經格式化好的完整 SQL 字串。
  - **ORM/查詢建構庫**: 對於更複雜的動態查詢，可以考慮引入一個輕量級的查詢建構庫（如 `pypika`），而不是手動拼接字串。這可以使 SQL 的動態生成更加安全和易讀。但對於目前這種模板驅動的架構，直接使用模板可能更為直觀。 