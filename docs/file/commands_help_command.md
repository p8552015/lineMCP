# 檔案分析報告：`apps/bot/src/commands/help_command.py`

## 1. 檔案目的與角色

此檔案定義了 `HelpCommandHandler`，一個具體的指令處理器，專門負責處理 `/help` 指令。它的核心職責是為使用者提供關於如何使用此聊天機器人的清晰、準確且即時的說明。

與一個簡單地返回寫死文字的幫助指令不同，這個實作是**動態且智慧的**。它直接與指令註冊表 (`CommandRegistry`) 互動，以確保其提供的指令列表總是與系統當前可用的指令完全同步。這使得它不僅僅是一個功能，更是系統的一個**自我文檔化 (Self-documenting)** 元件。

## 2. 主要類別/函數定義

### `class HelpCommandHandler(CommandHandler)`

這是檔案中唯一的類別，它繼承了 `CommandHandler` 的契約。

#### 實現的介面屬性/方法

*   **`command_name`**: "help"
*   **`description`**: "顯示所有可用指令的幫助訊息"
*   **`aliases`**: `["?", "h"]`
*   **`get_usage()`**: "/help [指令名稱]"
*   **`async handle(self, user_id: str, args: list[str]) -> Message`**: 這是指令的核心邏輯。它會檢查 `args` 是否存在，並根據情況分派到兩個不同的私有方法中，實現了**兩級幫助**功能。

#### 核心私有方法

*   **`_get_all_commands_help(self) -> TextMessage`**:
    *   當使用者只輸入 `/help` 時被呼叫。
    *   它從 `CommandRegistry` 獲取所有已註冊的指令處理器。
    *   動態地為每個指令生成一行用法和描述。
    *   最終組合出一個美觀、易於閱讀的完整指令列表，以及關於如何使用自然語言查詢的提示。

*   **`_get_specific_command_help(self, command_name: str) -> TextMessage`**:
    *   當使用者輸入 `/help <指令名稱>` 時被呼叫。
    *   它嘗試從 `CommandRegistry` 獲取特定指令的處理器。
    *   如果找到，它會格式化該指令的詳細資訊，包括描述、用法、別名，並透過 `_get_extra_help` 附加上額外的詳細說明。
    *   如果找不到，它會返回一個清晰的錯誤訊息。

*   **`_get_extra_help(self, command_name: str) -> str`**:
    *   一個輔助方法，它包含了一個字典，為特定的、較複雜的指令（如 `sql`, `tables`）提供了額外的上下文和使用範例。這將靜態的說明文字與動態的生成邏輯分開，提高了可讀性和可維護性。

## 3. 功能實現的簡要描述

`HelpCommandHandler` 的運作流程如下：
1.  **接收請求**: `CommandExecutor` 解析出 `/help` 指令後，將控制權交給 `HelpCommandHandler.handle` 方法。
2.  **判斷意圖**: `handle` 方法檢查參數 (`args`)。
    *   **無參數**: 使用者想要一個完整的指令列表。`handle` 呼叫 `_get_all_commands_help`。
    *   **有參數**: 使用者想要特定指令的詳細資訊。`handle` 呼叫 `_get_specific_command_help`。
3.  **動態生成內容**:
    *   `_get_all_commands_help` 向 `CommandRegistry` "查詢"：「把所有你認識的指令都告訴我。」 然後將結果格式化成一個列表。
    *   `_get_specific_command_help` 向 `CommandRegistry` "查詢"：「你有沒有一個叫做 `sql` 的指令？把它的資料給我。」 然後將結果格式化成詳細的說明頁。
4.  **返回訊息**: 無論哪種情況，最終都會建立一個 `TextMessage` 物件，其中包含格式化好的幫助文字，並返回給 `CommandExecutor`，再由後者發送給使用者。

## 4. 依賴關係

*   **`structlog`**: 用於日誌記錄。
*   **`linebot.v3.messaging.TextMessage`**: 用於建立返回給 LINE 平台的文字訊息。
*   **`src.domain.command_handler`**: 這是它的核心依賴。它需要 `CommandHandler` 介面來繼承，需要 `CommandContext` 來滿足建構函數的契約，還需要 `get_command_registry` 函式來動態地獲取指令資訊。

## 5. 設計模式與架構決策

*   **策略模式 (Strategy Pattern)**: 每個指令處理器（包括 `HelpCommandHandler`）本身就是一個策略，定義了如何處理一個特定的指令。`CommandExecutor` 是上下文，它根據輸入選擇並執行相應的策略。
*   **註冊表模式 (Registry Pattern)**: 該指令是註冊表模式的一個**消費者**。它不向註冊表寫入任何東西，而是從中讀取資訊，以動態地構建其響應。這是該設計中最出色的一點，它確保了幫助訊息的**自動更新**和**高可維護性**。
*   **關注點分離 (Separation of Concerns)**:
    *   `handle` 方法只負責高層次的邏輯分派。
    *   `_get_..._help` 方法各自負責一種特定格式的幫助訊息的生成。
    *   `_get_extra_help` 方法將靜態的文字資料從生成邏輯中分離出來。
    這種分離使得每個部分都易於理解和修改。

## 6. 潛在的改進點

*   **幫助分頁**: 如果未來指令數量變得非常多，一次性在 `_get_all_commands_help` 中顯示所有指令可能會導致訊息過長。可以考慮實現分頁邏輯（例如，`/help 1`, `/help 2`）。
*   **權限感知幫助**: 如果系統引入了權限系統，幫助指令可以變得更智慧，只向特定使用者顯示他們有權限執行的指令。這可以透過在生成幫助前，檢查 `user_id` 的權限來實現。
*   **國際化 (i18n)**: 目前所有的幫助文字都是寫死的中文。如果需要支援多語言，可以將這些字串提取到資源檔中，並根據使用者的語言設定動態載入。 `_get_extra_help` 中的字典結構已經為這種轉換提供了一個良好的基礎。 