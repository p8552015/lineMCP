# 📄 `query_template_manager.py` 檔案架構分析報告

本報告由 AI 架構師 Serena 根據 `LLM_文件問答樣板_架構師升級完整版.md` 模板，對 `apps/bot/src/services/nl_to_sql/builders/query_template_manager.py` 進行分析。

**分析目標**: `apps/bot/src/services/nl_to_sql/builders/query_template_manager.py`
**產出日期**: 2024-07-30
**撰寫角色**: AI 架構師 / 技術負責人

---

## 🧩 樣板 1：檔案在專案中扮演的角色

【文件角色摘要】
- 📌 **主要功能與責任**:
  - 此檔案定義了 `QueryTemplateManager` 類別，它是 NL-to-SQL 子系統的 **SQL 模板註冊與管理中心**。
  - **核心職責**：
    1.  **模板載入**: 從外部來源（主要是 YAML 設定檔）載入所有預先定義好的 SQL 查詢模板。
    2.  **模板提供**: 根據上游 `SQLQueryBuilder` 傳入的 `QueryType`，提供對應的 SQL 模板字串。
    3.  **模板驗證**: 在載入和提供模板時，對其進行有效性（如是否為合法的 SELECT 語句）和安全性（如是否包含 DROP、DELETE 等危險關鍵字）的驗證。
    4.  **元數據管理**: 不僅管理模板本身，還管理與模板相關的元數據，如模板需要的參數、效能評估等。
    5.  **熱更新支持**: 提供了 `reload_templates` 方法，允許在應用程式不重啟的情況下重新載入模板，極大提升了維運效率。

- 🧠 **在系統架構中的定位**:
  - **定位**：在 NL-to-SQL 子系統中，它處於**資源層 (Resource Layer)** 或**配置層 (Configuration Layer)**。它本身不包含業務邏輯，而是為建構層 (`SQLQueryBuilder`) 提供所需的「原料」。
  - **上層來源**：由 `SQLQueryBuilder` 依賴並呼叫。
  - **下游依賴**：`IConfiguration`。它依賴配置服務來獲取 SQL 模板的內容以及安全驗證的規則。

- 🔐 **是否與授權、安全、敏感操作有關**:
  - **是，高度相關**。雖然它不直接執行 SQL，但它負責**審核和守衛**所有將被執行的 SQL 模板。其 `validate_template` 和 `_validate_sql_security` 方法是防止惡意或危險的 SQL 模板被載入系統的**第一道防線**。

- 🎯 **實用比喻**:
  - `QueryTemplateManager` 就像一家大型律師事務所的**檔案管理員**。他負責保管所有標準化的法律文書模板（SQL 模板）。當律師（`SQLQueryBuilder`）需要撰寫一份特定類型的文件時，會向他索取對應的模板。檔案管理員不僅要提供正確的模板，還要確保模板本身是最新、最合規的版本（模板驗證），絕不會給出一份包含過時或危險條款的草稿。

---

## 🧩 樣板 2：有哪些類別，以及創建目的與結構特性

【類別分析】
- 類別名稱：`QueryTemplateManager`
- 📌 **創建目的**:
  - **核心目的**：實現**邏輯與數據（或稱配置）的分離**。將易變的 SQL 查詢語句從相對穩定的 Python 程式碼 (`SQLQueryBuilder`) 中剝離出來，存放在外部的設定檔中。
  - **具體目的**：
    1.  **可維護性**: DBA 或資料分析師可以在不接觸 Python 程式碼的情況下，直接修改 YAML 檔案來優化或修改 SQL 查詢。
    2.  **可讀性**: 將複雜的 SQL 語句存放在專門的檔案中，使得 `SQLQueryBuilder` 的程式碼更簡潔，專注於建構邏輯。
    3.  **靈活性**: 提供了熱更新等機制，使得 SQL 的調整可以快速上線。
- 🧭 **使用場景**:
  - 由 `EnhancedServiceFactory` 創建，並注入一個 `IConfiguration` 實例。
  - 被注入到 `SQLQueryBuilder` 中，為其提供 SQL 模板。
- 🧩 **內含哪些關鍵方法與邏輯功能**:
  - `__init__(...)`: 接收配置服務，並在初始化時自動呼叫 `_load_templates`。
  - `get_template()`: 獲取模板的核心方法，包含了模板不存在時的容錯和重試邏輯。
  - `validate_template()`: 驗證單個模板的格式和安全性。
  - `_load_templates()`: 核心的載入邏輯，從配置服務中讀取模板資料並存入記憶體。
  - `reload_templates()`: 允許外部觸發模板的重新載入。
  - `validate_all_templates()`: 提供一個可以一次性驗證所有已載入模板健康狀況的工具方法。
- 🔄 **是否支援擴充或注入**:
  - **是**。它依賴注入了 `IConfiguration`。其擴展性與 `RuleBasedParser` 類似，是**配置驅動**的。要新增一種查詢，無需修改此檔案的程式碼，只需在 YAML 設定檔中新增一個模板即可。
- 💡 **設計考量**:
  - **配置驅動 (Configuration-Driven)**: 核心設計思想。
  - **容錯與健壯性**: `get_template` 中對模板不存在或為空的處理，體現了強烈的防禦性編程思想。
  - **安全性**: `validate_template` 和 `_validate_sql_security` 強調了對模板內容的安全審查。

---

## 🧩 樣板 4：模組關係與相依

- **上游呼叫者**：`SQLQueryBuilder` (透過 `ITemplateManager` 介面)
- **下游相依元件**：`IConfiguration` (用於獲取模板內容和安全規則)
- **是否存在循環相依**：**否**。

---

## 🧱 額外架構師視角建議補充欄位

- 🗂️ **高耦合風險**：**低**。它只依賴於 `IConfiguration` 抽象介面，職責單一。
- 🧪 **可測試性**：**極高**。在測試中，可以 Mock `IConfiguration`，讓它回傳各種正常或異常的模板設定，來全面測試 `QueryTemplateManager` 的載入、驗證、提供和容錯邏輯。
- 🧠 **重構潛力**:
  - **模板來源擴展**: 目前的設計主要從配置服務載入。架構上可以輕易地擴展，使其能從更多來源載入模板，例如直接從資料庫、遠端的 Git 倉庫，甚至是一個專門的模板管理微服務。
  - **模板語言**: 目前使用的是簡單的 f-string 格式化。對於更複雜的動態 SQL，可以考慮引入一個更強大的模板引擎，如 **Jinja2**。Jinja2 提供了更豐富的語法（如迴圈、條件判斷），可以在模板層面實現更複雜的動態 SQL 生成，進一步減少 `SQLQueryBuilder` 中的 Python 邏輯。例如，可以根據參數是否存在來動態地添加 `WHERE` 條件。 