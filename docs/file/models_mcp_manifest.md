# 檔案分析報告：`apps/bot/src/models/mcp_manifest.py`

## 1. 檔案目的與角色

此檔案的目的不是像傳統的 Model 檔案那樣定義應用程式的內部資料結構。相反，它的角色是作為一個**AI 工具清單 (AI Tool Manifest)**。它定義了一個供大型語言模型 (LLM) 使用的「API 契約」，其格式完全遵循 OpenAI 的**函式/工具呼叫 (Function/Tool Calling)** 規範。

這個檔案是連接**人類自然語言**和**程式碼確定性執行**的橋樑。它將應用程式的能力（如查詢資料庫、搜尋文件）以 LLM 能夠理解的方式進行描述，使得 LLM 可以充當一個智慧型的路由器，將使用者的模糊意圖轉換為對這些具體工具的結構化呼叫。

## 2. 主要類別/函數定義

### `get_mcp_manifest() -> dict[str, Any]`

這是檔案中唯一定義的函式。它不接收任何參數，直接返回一個巨大的字典。

#### 字典結構

返回的字典結構如下：
*   **鍵 (Key)**: 字串，是工具的名稱（例如 `execute_query`, `search_docs`）。這是 LLM 在決定呼叫哪個工具時返回的識別碼。
*   **值 (Value)**: 一個描述工具的物件，包含：
    *   `description: str`: 對工具功能的高層次、人類可讀的描述。這是 LLM 決定**何時**使用此工具的主要依據。
    *   `parameters: dict`: 一個遵循 **JSON Schema** 規範的字典，定義了呼叫此工具所需的參數。
        *   `type`: 總是 "object"。
        *   `properties`: 一個字典，其中每個鍵是參數名，值是描述該參數的物件（包含 `type`, `description`, `default` 等）。
        *   `required`: 一個字串列表，聲明哪些參數是必需的。

#### 定義的工具

此清單定義了兩大類工具：
1.  **文件與知識查詢工具**: `search_docs`, `get_code_examples`, `get_api_reference`, `get_best_practices`。這些工具顯然是為了讓機器人具備程式設計助理的能力，可以查詢外部知識庫（如 Context7）來回答技術問題。
2.  **PostgreSQL 資料庫操作工具**: `execute_query`, `describe_table`, `list_tables`, `get_table_sample`。這些是我們在 `sql_command`, `tables_command` 等指令中看到的資料庫操作的底層抽象。

## 3. 功能實現的簡要描述

這個檔案本身不「執行」任何功能，但它是功能得以實現的**藍圖**。其工作流程在整個系統中的位置如下：
1.  一個服務（例如 `nl_to_sql_service`）接收到一個自然語言查詢，如「員工人數最多的部門是哪個？」。
2.  該服務將此查詢，連同 `get_mcp_manifest()` 返回的這份**工具清單**，一起發送給一個支援工具呼叫的 LLM。
3.  LLM 閱讀使用者的查詢和所有工具的 `description`。它發現 `execute_query` 工具的描述（「執行一個唯讀的 SQL 查詢」）最符合使用者的意圖。
4.  LLM 接著自己生成一個 SQL 查詢：`SELECT department, COUNT(*) FROM employees GROUP BY department ORDER BY COUNT(*) DESC LIMIT 1`。
5.  然後，LLM 根據 `execute_query` 工具的 `parameters` 定義，構建一個 JSON 物件：`{"name": "execute_query", "arguments": {"query": "SELECT department, ... LIMIT 1"}}`。
6.  LLM 將這個 JSON 作為其回應返回給應用程式。
7.  應用程式中的 `UnifiedMCPClient` 接收到這個回應，解析出工具名稱和參數，然後去執行對應的內部函式。

## 4. 依賴關係

*   **`typing.Any`**: 這是唯一的依賴。該檔案完全自給自足。

## 5. 設計模式與架構決策

*   **API 契約 (API Contract)**: 這個清單本質上是應用程式為 AI 定義的一個內部 API。它明確了 AI 可以使用的「函式」及其簽名，是人類開發者與 AI 模型之間的一個重要契約。
*   **配置即程式碼 (Configuration as Code)**: 與將此清單儲存在外部 JSON 或 YAML 檔案中不同，將其直接定義在 Python 程式碼中，使其成為「配置即程式碼」。這簡化了部署，並允許在未來動態地建構或修改這個清單。
*   **關注點分離**: `mcp_manifest.py` 只關心**定義工具有哪些以及它們的參數是什麼**。它不關心這些工具**如何實現**。實現的邏輯被完全分離在其他地方（可能是在 `UnifiedMCPClient` 或其呼叫的具體服務中）。

## 6. 潛在的改進點

*   **與 Pydantic 模型結合**: 雖然目前的字典是有效的，但如果使用 Pydantic 模型來定義 `Tool`, `Parameters`, `Property` 等結構，然後在程式啟動時將這些模型序列化為符合 OpenAI 規範的字典，可以帶來強型別檢查的好處，減少手動編寫字典時出錯的可能性。
*   **動態生成清單**: 目前清單是完全靜態的。在一個更複雜的系統中，可以根據目前載入的外掛程式或使用者權限，動態地從不同的模組中收集工具定義，並在執行時建構這份清單。
*   **版本控制**: 當工具的參數發生變化時，可能需要一種方式來對這個清單進行版本控制，以確保與可能使用舊版清單的快取提示或 LLM 互動時的相容性。 