# 檔案分析報告：`apps/bot/src/domain/command_executor.py`

## 1. 檔案目的與角色

此檔案定義了 `CommandExecutor` 類別，它是整個指令處理子系統的**總指揮和協調器**。它扮演著一個**外觀 (Facade)** 的角色，將指令的註冊、解析和執行等複雜的內部流程，封裝在一個簡潔、統一的介面背後。

它的核心角色是：
1.  **指令系統的初始化器 (Initializer)**: 負責在首次需要時，載入並註冊所有具體的指令處理器。這是應用程式中唯一一個知道所有可用指令具體實現的地方。
2.  **指令執行的生命週期管理者 (Lifecycle Manager)**: `execute_command` 方法完整地管理了一次指令執行的所有階段：解析使用者輸入、查找對應的處理器、驗證參數、執行處理邏輯以及捕獲和轉換錯誤。
3.  **複雜性的封裝者 (Complexity Encapsulator)**: 對於系統的其他部分（例如 `MessageHandlerDI`），它們只需要與 `CommandExecutor` 互動，而無需關心 `CommandRegistry` 的存在、指令的實例化過程或延遲初始化的細節。`CommandExecutor` 為它們提供了一個簡單的、高層次的 API。
4.  **錯誤處理的統一出口 (Unified Error Handling Exit-Point)**: 在 `execute_command` 方法中，它將底層的技術性錯誤（如 `KeyError`）捕獲，並轉換為我們之前分析過的、具有豐富語義的領域異常（`CommandParsingException`），為上層提供了穩定且可預測的錯誤契約。

## 2. 主要類別/函數定義

### `class CommandExecutor`
這是檔案中唯一定義的類別，也是整個指令處理框架的引擎。

#### 核心方法

*   **`__init__(self, context: CommandContext)`**:
    建構函數接收 `CommandContext`。這至關重要，因為 `CommandExecutor` 在內部實例化所有具體的指令處理器時，需要將這個包含了所有共享服務的上下文物件傳遞給它們。

*   **`initialize(self)` 和 `_register_all_commands(self)`**:
    *   這兩個方法協同工作，實現了**延遲初始化 (Lazy Initialization)**。只有在第一次嘗試執行指令時，指令系統才會被真正地初始化。
    *   `_register_all_commands` 是整個系統的**服務註冊中心**。它集中地 `import` 所有定義在 `src/commands/` 目錄下的具體 `CommandHandler` 類別，實例化它們，並將它們註冊到全域的 `CommandRegistry` 中。這種集中式註冊使得新增或移除指令變得非常簡單，只需修改這個地方即可。

*   **`async execute_command(self, user_id: str, message_text: str) -> Message`**:
    *   這是 `CommandExecutor` 最核心的公開方法。
    *   **流程**:
        1.  **解析**: 呼叫 `parse_command` 將原始文字轉換為結構化的 `Command` 物件（包含名稱和參數）。
        2.  **查找**: 透過 `self.registry.get_handler` 找到對應的處理器。
        3.  **驗證**: 呼叫處理器的 `validate_args` 進行參數驗證。
        4.  **執行**: `await handler.handle(...)` 來執行真正的業務邏輯。
    *   **健壯性**: 整個流程被包裹在健壯的 `try...except` 區塊中，能夠優雅地處理指令不存在或執行失敗的情況。

*   **Facade 方法**:
    *   `has_command`, `list_commands`, `get_help_text` 等方法都只是簡單地將呼叫轉發給內部的 `CommandRegistry`。它們的存在是為了讓 `CommandExecutor` 成為與外界互動的唯一介面，符合**最少知識原則 (Principle of Least Knowledge)**。

## 3. 功能實現的簡要描述

`CommandExecutor` 的工作模式可以比喻為一個劇院的**舞台監督**：
1.  **開場準備 (Initialization)**: 在大幕拉開前（第一次執行指令），舞台監督（`CommandExecutor`）會拿出劇本，把所有需要上場的演員（具體的 `CommandHandler`）都叫到後台，並讓他們在一個名冊（`CommandRegistry`）上登記（`_register_all_commands`）。
2.  **接收指令 (Receiving a Cue)**: 主持人（`MessageHandlerDI`）說：「下一幕，『幫助』！」（使用者輸入 `/help`）。
3.  **執行場景 (Executing the Scene)**:
    *   舞台監督聽到指令，查閱名冊，找到名叫「幫助」的演員。
    *   他對演員說：「你的台詞（參數）沒有問題」（`validate_args`）。
    *   然後一揮手，說：「上場！」（`await handler.handle`）。
    *   演員上場表演，完成他的戲份。
4.  **處理意外 (Handling Mishaps)**: 如果主持人喊了一個名冊上沒有的名字，舞台監督會攔住他，告訴他「沒有這個演員」（`KeyError` -> `CommandParsingException`）。如果演員在台上出了意外，舞台監督也會記錄下來並處理（`Exception` -> `raise`）。

## 4. 依賴關係

*   **`structlog`**: 用於結構化日誌。
*   **`linebot.v3.messaging.Message`**: 指令執行的返回類型。
*   **`src.domain.command_handler`**: 依賴於命令模式的基礎框架（`CommandHandler`, `CommandContext`, `CommandRegistry`）。
*   **`src.domain.exceptions`**: 依賴於自定義的領域異常。
*   **`src.models.commands.parse_command`**: 依賴一個外部的解析函數來處理原始文字。
*   **`src.commands.*`**: 在 `_register_all_commands` 方法中，它**直接依賴**於所有具體的指令處理器實現。這是合理的，因為它的職責就是作為這些具體實現的聚合根 (Aggregation Root)。

## 5. 設計模式與架構決策

*   **外觀模式 (Facade Pattern)**: `CommandExecutor` 是命令子系統的一個標準外觀，它為外部提供了一個簡化的、高層次的介面。
*   **單例模式 (Singleton Pattern)**: 雖然 `CommandExecutor` 本身不是單例，但它依賴於單例的 `CommandRegistry` 來確保狀態的唯一性。
*   **延遲初始化 (Lazy Initialization)**: 使用 `_initialized` 旗標來推遲昂貴的指令註冊過程，直到它第一次被需要時才執行。
*   **集中式服務註冊 (Centralized Service Registration)**: `_register_all_commands` 方法是服務定位模式的一種手動實現，它集中管理了所有指令處理器的生命週期。
*   **職責分離 (Separation of Responsibilities)**:
    *   `command_handler.py` 負責**定義框架**。
    *   `commands/*.py` 負責**實現具體邏輯**。
    *   `command_executor.py` 負責**協調和執行**。
    這種清晰的職責分離是該架構成功的關鍵。

## 6. 潛在的改進點

*   **自動發現指令**: 目前 `_register_all_commands` 需要手動 `import` 和實例化每一個指令。一個更進階的實現可以透過動態掃描 `src/commands` 目錄下的所有檔案，自動發現所有繼承自 `CommandHandler` 的類別並實例化它們。這將使得新增指令完全無需修改 `CommandExecutor` 的程式碼。
*   **執行中介軟體 (Execution Middleware)**: 可以在指令執行前後加入一個中介軟體或裝飾器鏈。例如，可以在所有指令執行前自動執行權限檢查、日誌記錄或效能計時。這可以透過在 `execute_command` 中包裝 `handler.handle` 的呼叫來實現。
*   **非同步初始化**: `initialize` 方法是同步的。如果指令的註冊過程涉及到 I/O（例如，從遠端配置中心讀取指令列表），那麼 `initialize` 應該是一個 `async` 方法。 