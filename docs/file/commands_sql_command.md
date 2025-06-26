# 檔案分析報告：`apps/bot/src/commands/sql_command.py`

## 1. 檔案目的與角色

此檔案定義了 `SqlCommandHandler`，一個負責處理 `/sql` 指令的具體指令處理器。它的角色是為進階使用者或開發者提供一個**直接存取資料庫的後門**，允許他們執行原始的 SQL `SELECT` 查詢。

這是一個功能強大但有潛在風險的工具。因此，該指令的設計核心在於**風險控制**和**架構解耦**，確保在提供靈活性的同時，最大限度地降低安全風險並保持系統的模組化。

## 2. 主要類別/函數定義

### `class SqlCommandHandler(CommandHandler)`

這是檔案中唯一定義的類別，繼承自 `CommandHandler`。

#### 核心方法

*   **`validate_args(self, args: list[str]) -> bool`**:
    *   這是該指令的**第一道安全防線**。它覆寫了父類別的方法，以實現針對 SQL 的特定驗證。
    *   **實現方式**: 採用**關鍵字黑名單 (Denylist)** 的方式，檢查查詢中是否包含 `drop`, `delete`, `update` 等危險的、具有寫入性質的關鍵字。這是一個基礎但至關重要的安全措施。

*   **`async handle(self, user_id: str, args: list[str]) -> Message`**:
    *   指令的核心執行邏輯。
    *   **流程**:
        1.  **驗證**: 明確呼叫 `validate_args` 進行安全檢查。
        2.  **委派執行**: 它不直接與資料庫互動，而是將 SQL 查詢**委派給 MCP 層** (`mcp_client.call_tool("sqlite", "read_query", ...)`). 這是一個關鍵的架構決策。
        3.  **解析回應**: 它不信任來自 MCP 的原始回應，而是使用一個專門的 `MCPResponseParser` 來將其標準化為乾淨的資料結構。
        4.  **格式化輸出**: 呼叫 `_format_sql_result` 將查詢結果格式化為使用者友善的訊息。
    *   **錯誤處理**: 它的 `except` 區塊不是簡單地返回一個錯誤訊息，而是 `raise create_db_error(...)`。這會將錯誤**拋給上層的統一異常處理框架**，使得錯誤處理邏輯集中化，並能附帶豐富的上下文。

*   **`_format_sql_result(self, query: str, data: list[dict]) -> TextMessage`**:
    *   這是結果的**表示層**。
    *   它忠實地履行了 `help` 指令中的承諾：只顯示前 10 行結果，並告知使用者總共有多少行。
    *   為了防止訊息過長，它還聰明地截斷了單行內過長的內容。

## 3. 功能實現的簡要描述

`SqlCommandHandler` 的工作流程可以比喻為一個**高度管制的檔案室管理員**：
1.  **接收申請 (`handle`)**: 使用者提交一份 SQL 查詢申請。
2.  **審查申請 (`validate_args`)**: 管理員首先檢查申請表。如果上面寫著「銷毀」、「修改」或「刪除」等字眼，申請會被立即駁回，並告知使用者「只允許查閱」。
3.  **委託他人 (`mcp_client.call_tool`)**: 管理員自己不進入檔案庫。他將申請轉交給一個專門的內部工作人員（MCP 的 `sqlite` 工具），由該工作人員進入檔案庫執行查閱操作。這確保了管理員自己不會意外破壞任何東西。
4.  **整理報告 (`MCPResponseParser`)**: 內部工作人員拿回來的可能是一堆雜亂的原始資料。管理員會用一個標準範本（`MCPResponseParser`）將其整理成乾淨的表格。
5.  **提供結果 (`_format_sql_result`)**: 管理員將整理好的報告（最多前10條記錄）交給使用者，並告訴他總共找到了多少條記錄。
6.  **處理意外 (`except`)**: 如果在任何環節出錯（例如，內部工作人員找不到檔案），管理員不會自己編造一個理由，而是會填寫一份標準的「資料庫錯誤」報告（`create_db_error`），然後按響警鈴，交由總部（統一錯誤處理器）來決定如何向使用者解釋。

## 4. 依賴關係

*   **`src.domain.command_handler.CommandContext`**: 用於獲取 `mcp_client`。這是將指令與底層資料來源解耦的關鍵。
*   **`src.domain.exceptions.create_db_error`**: 用於與全域的異常處理框架整合。
*   **`src.services.mcp_response_parser.MCPResponseParser`**: 依賴一個專門的解析器來處理來自 MCP 的回應，增強了健壯性。
*   **`src.services.error_handlers.ErrorContext`**: 用於豐富錯誤日誌的上下文。

## 5. 設計模式與架構決策

*   **委派模式 (Delegation Pattern)**: `SqlCommandHandler` 的核心是委派。它將 SQL 的執行完全委派給了 MCP 層，這是一個非常漂亮的**解耦**決策。
*   **策略模式 (Strategy Pattern)** + **介面隔離原則 (Interface Segregation Principle)**: `validate_args` 的覆寫是策略模式的體現。每個指令可以定義自己的驗證策略。
*   **防禦性編程**:
    *   **安全**: 黑名單機制是第一層防禦。
    *   **健壯性**: 專門的回應解析器和統一的異常拋出機制，都顯著提高了指令的健壯性。

## 6. 潛在的改進點

*   **增強 SQL 安全性**: 基於關鍵字的黑名單可以被繞過。一個更安全的方法是使用一個 SQL 解析庫（如 `sqlparse`）來構建查詢的抽象語法樹 (AST)，並嚴格驗證其類型是否為 `SELECT`。
*   **移除多餘的驗證呼叫**: `CommandExecutor` 應已在呼叫 `handle` 前呼叫了 `validate_args`。可以移除 `handle` 方法中對 `validate_args` 的手動呼叫，以簡化程式碼並依賴框架的生命週期。
*   **修正換行符錯誤**: 在 `_format_sql_result` 和錯誤訊息中，存在 `\\n` 的排版錯誤，應修正為 `\n`。 