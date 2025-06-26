# 檔案分析報告：`apps/bot/src/domain/command_handler.py`

## 1. 檔案目的與角色

此檔案是應用程式中**命令模式 (Command Pattern) 的核心框架和基礎設施**。它不包含任何具體的業務指令，而是定義了建立、管理和執行這些指令所需的所有抽象類別和輔助工具。

它的核心角色是：
1.  **定義命令契約 (Defining the Command Contract)**: `CommandHandler` 抽象基底類別（ABC）定義了一個命令「應該是什麼樣子」。它規定了所有具體命令都必須提供一個名稱、一段描述和一個 `handle` 方法來執行邏輯。
2.  **提供執行上下文 (Providing Execution Context)**: `CommandContext` 類別解決了依賴注入的問題。它將所有指令執行時可能需要的共享服務（如資料庫、AI 服務）打包成一個物件，避免了向每個指令處理器單獨傳遞大量參數的混亂。
3.  **建立命令註冊表 (Creating a Command Registry)**: `CommandRegistry` 類別實現了註冊表模式，作為一個中央儲存庫，用於在執行時發現和管理所有可用的指令。它支援按名稱和別名查找指令。
4.  **確保全域唯一性 (Ensuring Global Uniqueness)**: `get_command_registry()` 工廠函數透過單例模式，確保整個應用程式中只有一個 `CommandRegistry` 實例，這對於命令的集中管理至關重要。

總之，這個檔案為整個專案的指令驅動架構奠定了堅實的、可擴展的基礎。

## 2. 主要類別/函數定義

### `class CommandHandler(ABC)`
一個抽象基底類別，作為所有具體指令處理器的**介面**。
*   **`@abstractmethod`**: `command_name`, `description`, `handle` 被定義為抽象的，強制子類別必須實現它們。
*   **`handle(...)`**: 這是命令模式的「execute」方法。它定義了一個清晰的簽名，接受 `user_id` 和 `args`。
*   **預設實現**: 提供了 `aliases`, `validate_args`, `get_usage` 等方法的預設實現，子類別可以按需覆寫。
*   **`get_help_text()`**: 一個非常實用的方法，可以根據指令的屬性自動生成格式化的幫助文字，確保了幫助文件的一致性。

### `class CommandContext`
一個**依賴容器**或**服務定位器**，專門為指令處理器服務。
*   **目的**: 它的存在是為了簡化依賴管理。它將所有高階的共享服務（如工廠、客戶端、服務物件）捆綁在一起。
*   **使用方式**: 在建立指令處理器時，會將這個 `CommandContext` 物件傳遞給它。然後在 `handle` 方法中，處理器可以透過 `context.db_service` 或 `context.ai_model_service` 來存取所需的服務。

### `class CommandRegistry`
一個典型的**註冊表模式**實現。
*   **`_handlers` 和 `_aliases`**: 使用字典來儲存對指令處理器的引用，提供了高效的查找能力。
*   **`register(self, handler)`**: 核心的註冊方法，它會檢查命令和別名的唯一性，防止衝突。
*   **`get_handler(self, command_name)`**: 核心的查找方法，支援透過別名找到原始命令。
*   **`get_help_text()`**: 一個高階功能，能夠遍歷所有已註冊的指令並生成一個完整的幫助手冊。

### `get_command_registry() -> CommandRegistry`
一個實現了**單例模式**的工廠函數。
*   **`global _command_registry`**: 透過一個全域變數來儲存唯一的 `CommandRegistry` 實例。
*   **懶漢式初始化 (Lazy Initialization)**: 只有在第一次被呼叫時，才會真正建立 `CommandRegistry` 的實例。

## 3. 功能實現的簡要描述

這個框架的預期工作流程如下：
1.  **啟動階段**: 在應用程式啟動時，系統會實例化所有具體的指令處理器類別（例如 `HelpCommand`, `StatusCommand` 等），並透過 `get_command_registry().register(...)` 將它們一一註冊到全域註冊表中。
2.  **執行階段**: 當 `MessageHandlerDI` 收到一個以 `/` 開頭的訊息時，它會將其解析為指令名稱和參數。
3.  **查找**: 它呼叫 `get_command_registry().get_handler(command_name)` 來從註冊表中獲取對應的處理器物件。
4.  **執行**: 它呼叫該處理器物件的 `handle(user_id, args)` 方法，並將結果（一個 `Message` 物件）回傳給使用者。

## 4. 依賴關係

*   **`abc`**: Python 標準函式庫，用於定義抽象基底類別。
*   **`linebot.v3.messaging.Message`**: 這是指令處理結果的返回類型，表明這個領域層的設計是為了最終服務於 LINE Bot 的。

此檔案的依賴非常少，符合其作為一個獨立領域框架的定位。

## 5. 設計模式與架構決策

*   **命令模式 (Command Pattern)**: 整個檔案的核心。將一個請求封裝成一個物件（`CommandHandler` 的子類別），從而讓你可以參數化客戶端、將請求排隊或記錄請求日誌，以及支援可撤銷的操作。
*   **註冊表模式 (Registry Pattern)**: `CommandRegistry` 是一個經典的註冊表，提供了一個在執行時查找物件的中心位置。
*   **單例模式 (Singleton Pattern)**: `get_command_registry` 確保了註冊表的唯一性。
*   **依賴注入 (Dependency Injection)**: `CommandContext` 是 DI 模式的一種體現，它將依賴項捆綁在一起，並在需要時注入到指令處理器中。
*   **模板方法模式 (Template Method Pattern)**: `CommandHandler` 中的 `get_help_text` 方法可以看作是一個模板方法，它定義了幫助文字的生成框架，而具體的內容（如 `command_name`, `description`）則由子類別提供。

## 6. 潛在的改進點

*   **非同步註冊**: 如果指令的初始化過程很複雜或需要 I/O 操作，可以考慮將 `register` 方法改為非同步。
*   **指令分組/分類**: 當指令數量非常多時，可以擴展 `CommandHandler` 和 `CommandRegistry`，增加一個 `category` 屬性，以便在生成幫助文字時可以按類別分組，提高可讀性。
*   **上下文的動態構建**: `CommandContext` 目前是靜態定義的。在更複雜的系統中，它本身可以由一個依賴注入容器（如 `punq`）動態構建，這樣 `CommandContext` 就不需要手動維護其所包含的服務列表。
*   **指令生命週期**: 可以為指令增加生命週期勾點（Hooks），如 `before_handle` 和 `after_handle`，允許在指令執行前後插入通用邏輯（如權限檢查、日誌記錄）。 