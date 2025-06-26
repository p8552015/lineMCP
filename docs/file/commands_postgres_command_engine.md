# 檔案分析報告：`apps/bot/src/commands/postgres_command.py`

## 1. 檔案目的與角色

此檔案定義了 `PostgreSQLCommand` 類別，它是 `/pg` 指令背後的**核心業務邏輯引擎**。與我們分析過的其他所有指令處理器都不同，這個類別本身並不與指令框架直接掛鉤。相反，它是一個自成一體、可重用的元件，封裝了與 PostgreSQL 互動的所有複雜性。

它的核心角色是作為一個**智慧型查詢路由器和執行器**，能夠理解多種類型的使用者輸入（預定義關鍵字、自然語言、甚至可能是原始 SQL），將它們轉換為可執行的 SQL 查詢，然後透過 MCP 服務執行它們，並以結構化的方式返回結果。

這個檔案與 `postgres_command_handler.py` 一起，完美地詮釋了**適配器模式 (Adapter Pattern)**。`PostgreSQLCommand` 是被適配的、功能強大的服務，而 `PostgresCommandHandler` 則是使其能夠插入現有指令框架的適配器。

## 2. 主要類別/函數定義

### `class PostgreSQLCommand`

這是檔案中唯一定義的類別，是 `/pg` 功能的核心。

#### 核心方法

*   **`__init__(self, service_factory: IServiceFactory)`**:
    *   建構函數接收一個 `service_factory`。它立即使用工廠來獲取它所依賴的關鍵服務，特別是 `nl_to_sql_service`。
    *   它還定義了一個 `postgres_queries` 字典，這是一個**預定義查詢的註冊表**，將簡單的使用者友好關鍵字（如「員工數」）對應到安全、固定的 SQL 查詢。

*   **`async execute(self, user_input: str, ...)`**:
    *   這是該類別的主要入口點，一個**智慧型分派器**。
    *   **執行流程**:
        1.  **檢查預定義查詢**: 首先檢查輸入是否為 `postgres_queries` 中的一個關鍵字。如果是，直接使用預設的 SQL。這是最優先、最快的路徑。
        2.  **自然語言轉 SQL**: 如果不是預定義查詢，則將輸入傳遞給 `_convert_natural_language_to_sql` 方法。
        3.  **執行查詢**: 無論 SQL 來自哪個步驟，最終都會被傳遞給 `_execute_postgres_query` 進行執行。
    *   **結構化回傳**: 此方法不返回格式化的字串，而是返回一個包含 `success`, `error`, `data`, `sql_query` 等鍵的**結構化字典**，將資料與表示分離。

*   **`async _convert_natural_language_to_sql(self, user_input: str)`**:
    *   這是**自然語言處理的核心**。它呼叫 `nl_to_sql_service` 來執行轉換。
    *   **提供上下文**: 在呼叫服務之前，它會建構一個 `postgres_context` 字典，其中包含資料庫的結構資訊（表名、列名等）。這極大地提高了 AI 模型生成準確 SQL 的能力，是實現高品質 NL-to-SQL 的關鍵步驟。

*   **`async _execute_postgres_query(self, sql_query: str, ...)`**:
    *   這是**與資料庫的介面**。它透過 `get_unified_mcp_client()` 獲取客戶端，並呼叫其 `postgres` 工具來執行查詢。這保持了與其他資料存取指令的架構一致性。

*   **`async _format_postgres_result(self, result: Dict, ...)`**:
    *   **複雜回應解析**: 此方法負責解析來自 MCP 的、可能是複雜的 JSON 回應。它展示了處理真實世界 API 回應所需的防禦性程式碼（例如，處理 JSON 解碼錯誤）。
    *   它將解析後的資料、摘要和格式化的顯示文字捆綁成一個豐富的結果字典。

*   **`_format_display_text(...)`, `_detect_query_type(...)`, `get_help_text(...)`, `_get_..._suggestions(...)`**:
    *   這些都是輔助方法，共同構建了一個**極其使用者友善**的體驗。它們負責生成美觀的輸出、提供有用的元資料（查詢類型）、詳細的幫助文件以及在出錯時的智慧建議。

## 3. 功能實現的簡要描述

`PostgreSQLCommand` 的工作流程可以比喻為一個**配備了 AI 助理的資深資料分析師**：
1.  **接收任務 (`execute`)**: 老闆（`PostgresCommandHandler`）丟過來一個需求（`user_input`）。
2.  **快速響應**:
    *   **分析師心想：「這個問題我每天都做，有現成的報表。」**: 如果需求是「員工數」這種關鍵字，他直接從 `postgres_queries` 抽屜裡拿出寫好的 SQL 腳本。
    *   **分析師心想：「這個問題有點模糊，讓我的 AI 助理先理解一下。」**: 如果需求是「工程部高薪的員工有哪些？」，他會把這句話和相關的資料庫結構圖（`postgres_context`）一起交給他的 AI 助理（`nl_to_sql_service`）。
3.  **AI 助理工作 (`_convert_natural_language_to_sql`)**: AI 助理將自然語言轉寫成一份精確的 SQL 查詢腳本，然後交還給分析師。
4.  **執行與彙報**:
    *   分析師拿著 SQL 腳本，交給後端的資料中心（MCP `postgres` tool）去執行。
    *   資料中心返回原始資料後，分析師 (`_format_postgres_result`) 會將其整理成清晰的表格 (`display_text`) 和摘要 (`summary`)。
    *   最後，他將這份包含所有細節（原始需求、執行的SQL、結果、摘要）的完整分析報告（結構化字典）交還給老闆。

## 4. 依賴關係

*   **`IServiceFactory`**: 這是其**命脈**，用於獲取所有必要的服務，如 `nl_to_sql_service`。
*   **`nl_to_sql_service`**: 實現自然語言查詢的核心依賴。
*   **`unified_mcp_client`**: 執行最終資料庫查詢的依賴。

## 5. 設計模式與架構決策

*   **引擎與適配器分離 (Engine/Adapter Separation)**: 這是該設計中最核心、最成功的決策。將複雜的、可重用的業務邏輯（引擎）與框架整合的膠水程式碼（適配器）分開，使得兩者都可以獨立開發、測試和演進。
*   **策略模式 (Strategy Pattern)**: `execute` 方法本身就是一個策略模式的應用。它根據輸入的類型（預定義、自然語言）選擇不同的處理策略。
*   **上下文感知 (Context-Awareness)**: 在呼叫 NL-to-SQL 服務時提供詳細的資料庫上下文，是實現高準確率 AI 功能的關鍵，這是一個非常成熟的設計。
*   **豐富的錯誤處理**: 不僅僅是捕獲錯誤，還提供了**上下文相關的建議**，極大地提升了使用者體驗。

## 6. 潛在的改進點

*   **安全性**: 雖然 NL-to-SQL 服務可能會進行一些安全檢查，但在執行由 AI 生成的 SQL 之前，增加一道額外的安全校驗（例如，確保它仍然是一個 `SELECT` 語句）可以增加系統的縱深防禦。
*   **可配置性**: `postgres_queries` 中的預定義查詢是寫死的。可以考慮將它們移到一個 YAML 或 JSON 設定檔中，使其更易於管理和擴展，而無需修改程式碼。
*   **查詢快取**: 對於常見的自然語言查詢或預定義查詢，可以引入一個快取層來儲存結果，減少資料庫負載並加快回應速度。 