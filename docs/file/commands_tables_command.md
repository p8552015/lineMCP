# 檔案分析報告：`apps/bot/src/commands/tables_command.py`

## 1. 檔案目的與角色

此檔案定義了 `TablesCommandHandler`，一個專門處理 `/tables` 指令的具體指令處理器。它的核心角色是作為一個**資料庫結構瀏覽器**，為使用者提供探索資料庫中有哪些資料表以及每個資料表結構的能力。

與 `/sql` 指令專注於「資料 (data)」不同，`/tables` 指令專注於「元資料 (metadata)」。它提供了兩個層級的功能：**發現**（列出所有資料表）和**檢查**（顯示特定資料表的結構）。

## 2. 主要類別/函數定義

### `class TablesCommandHandler(CommandHandler)`

這是檔案中唯一定義的類別，繼承自 `CommandHandler`。

#### 核心方法

*   **`async handle(self, user_id: str, args: list[str]) -> Message`**:
    *   指令的進入點和邏輯分派器。它檢查 `args` 是否存在，如果不存在，則呼叫 `_list_all_tables`；如果存在，則呼叫 `_get_table_schema`。這種模式提供了一個清晰、直觀的使用者介面。

*   **`async _list_all_tables(self) -> TextMessage`**:
    *   **功能**: 查詢並列出資料庫中的所有資料表。
    *   **實現**: 它不直接連線資料庫，而是透過 `mcp_client` 執行一個 SQLite 特定的查詢 (`SELECT name FROM sqlite_master WHERE type='table'`) 來獲取資料表列表。

*   **`async _get_table_schema(self, table_name: str) -> TextMessage`**:
    *   **功能**: 獲取並顯示單一資料表的詳細結構。
    *   **實現**:
        1.  它執行一個 SQLite 特定的 `PRAGMA table_info(...)` 查詢來獲取欄位定義。
        2.  為了提供更豐富的上下文，它**額外**執行了一個 `SELECT COUNT(*)` 查詢來獲取該資料表的總行數。這個額外的查詢被包裹在一個獨立的 `try...except` 區塊中，使其成為一個**可選的增強功能**，即使失敗也不會影響核心的結構顯示，非常健壯。
        3.  將結果格式化為一個清晰、易讀的欄位列表。

## 3. 功能實現的簡要描述

`TablesCommandHandler` 的工作流程可以比喻為一個**圖書館的圖書管理員**：
1.  **接待讀者 (`handle`)**: 一位讀者前來諮詢。
2.  **判斷需求**:
    *   **讀者問「你們這有哪些書架？」**: 管理員 (`_list_all_tables`) 會拿出圖書館的樓層圖，上面列出了所有書架的名稱和編號。
    *   **讀者問「『科幻』這個書架上有什麼書？」**: 管理員 (`_get_table_schema`) 會走到那個書架前。
3.  **詳細介紹 (`_get_table_schema`)**:
    *   管理員不僅會告訴讀者這個書架上有哪些書（欄位），還會介紹每本書的類型、是否為孤本等詳細資訊（欄位類型、是否為空、主鍵等）。
    *   他還會順便看一眼書架上的書的總數（`SELECT COUNT(*)`），並告訴讀者「這個書架上大概有 100 本書」。
4.  **提供指引**: 在完成介紹後，管理員會友好地提示下一步可以做什麼，例如「你可以用 `/tables <書架名>` 查看其他書架」，或者「你可以用 `/sql SELECT * FROM ...` 來看看某本書的前幾頁」。

## 4. 依賴關係

*   **`src.domain.command_handler.CommandContext`**: 用於獲取 `mcp_client`，這是與底層資料庫互動的唯一途徑。
*   **`src.domain.exceptions.create_db_error`**: 用於與集中的異常處理框架整合。
*   **`src.services.mcp_response_parser.MCPResponseParser`**: 依賴於一個標準的解析器來處理來自 MCP 的資料。
*   `structlog`, `linebot.v3.messaging.TextMessage`, `ErrorContext`。

## 5. 設計模式與架構決策

*   **委派模式 (Delegation Pattern)**: 再次地，指令將所有的資料庫操作都委派給了 MCP 層。這保持了指令處理器與資料庫實現的高度解耦。
*   **與實現耦合，而非與介面耦合 (Coupling to Implementation, not Interface)**: 該指令的 SQL 查詢 (`sqlite_master`, `PRAGMA`) 是 SQLite 特定的。這是一個有意識的權衡。它沒有試圖編寫一個通用的、適用於所有資料庫的元資料查詢，而是**選擇與其直接依賴的 `sqlite` MCP 工具的具體實現保持一致**。這使得程式碼更簡單、直接，只要 `mcp_client` 的 `sqlite` 工具不換核心，這段程式碼就無需更改。
*   **漸進增強 (Progressive Enhancement)**: 在 `_get_table_schema` 中，獲取行數的操作是一個很好的漸進增強的例子。核心功能是顯示結構，獲取行數是附加的、有用的資訊。透過將其放在一個 `try...except` 塊中，確保了即使這個增強功能失敗，核心功能仍然可用。

## 6. 潛在的改進點

*   **抽象化資料庫方言**: 如果未來需要支援多種資料庫後端（例如，MCP 層新增了一個 `postgres` 工具），可以考慮在 `DatabaseService` 或一個新的 `SchemaService` 中抽象化這些元資料查詢，指令本身只呼叫如 `schema_service.list_tables()` 的通用方法。但對於目前只支援 SQLite 的情況，當前的實現是恰當的。
*   **安全性**: 雖然元資料查詢通常被認為是安全的，但在 `_get_table_schema` 中，`table_name` 被直接拼接到查詢字串中。這可能會帶來 SQL 注入的風險（儘管在 `PRAGMA` 中利用可能很困難）。一個更安全的方法是先列出所有合法的資料表名稱，然後驗證使用者輸入的 `table_name` 是否在該列表中。
*   **修正換行符錯誤**: `TextMessage` 的建立中存在 `\\n` 的排版錯誤。 