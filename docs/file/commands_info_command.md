# 檔案分析報告：`apps/bot/src/commands/info_command.py`

## 1. 檔案目的與角色

此檔案定義了 `InfoCommandHandler`，一個具體的指令處理器，負責處理 `/info` 指令。它的主要角色是作為一個**系統儀表板**，向使用者（通常是開發者或管理員）提供關於應用程式當前狀態、配置和運行環境的快照。

與 `help` 指令專注於「能做什麼」不同，`info` 指令專注於「是什麼」。它從多個來源（靜態配置、作業系統環境、即時服務）聚合資訊，提供一個全面的系統概覽。

## 2. 主要類別/函數定義

### `class InfoCommandHandler(CommandHandler)`

這是檔案中唯一定義的類別，繼承自 `CommandHandler`。

#### 核心方法

*   **`async handle(self, user_id: str, args: list[str]) -> Message`**:
    *   這是指令的進入點。它的邏輯很直接：呼叫 `_collect_system_info` 來收集所有資料，然後將結果傳遞給 `_format_system_info` 來格式化輸出。
    *   它包含一個頂層的 `try...except` 區塊，以捕捉在資訊收集中可能發生的任何未知錯誤，確保指令的健壯性。

*   **`async _collect_system_info(self) -> dict`**:
    *   這是指令的**資料收集引擎**。它負責建構一個包含所有必要資訊的字典。
    *   **資訊來源**:
        1.  **作業系統**: 使用 `platform` 和 `sys` 模組獲取 Python 版本、OS 類型等。
        2.  **環境變數**: 透過 `os.getenv` 檢查 `ENVIRONMENT` 變數來判斷當前是生產還是開發環境。
        3.  **寫死配置**: 應用程式名稱、版本號、功能列表和依賴項列表是直接寫在程式碼中的。這適用於變更不頻繁的資訊。
        4.  **即時服務**: 呼叫 `_get_ai_models_info` 來動態獲取關於 AI 模型的即時資訊。

*   **`async _get_ai_models_info(self) -> dict`**:
    *   此方法展示了 `CommandContext` 的威力。它透過 `self.context.ai_model_service` 存取已注入的 AI 服務。
    *   **防禦性設計**: 它使用 `hasattr` 和 `getattr` 來安全地存取 `ai_service` 的屬性，並將整個邏輯包裹在 `try...except` 中。這確保了即使 AI 服務不可用或其介面發生變化，`/info` 指令也不會崩潰，而是會優雅地降級，顯示「未知」資訊。

*   **`_format_system_info(self, info: dict) -> TextMessage`**:
    *   這是**表示層**。它負責將 `_collect_system_info` 收集到的原始字典資料，轉換為一個對使用者友善、格式美觀的 `TextMessage`。
    *   它使用了表情符號、分隔線和適當的縮排來提高可讀性，並聰明地截斷了過長的列表，以避免訊息刷屏。

## 3. 功能實現的簡要描述

`InfoCommandHandler` 的工作流程可以被看作是一次**體檢**：
1.  **開始體檢**: 使用者輸入 `/info`。
2.  **各項檢查 (`_collect_system_info`)**:
    *   **基本資料**: 記錄姓名（應用程式名稱）、版本號。
    *   **環境測量**: 測量身高體重（OS、Python 版本）。
    *   **功能評估**: 列出掌握的技能（功能列表）。
    *   **呼叫專科醫生 (`_get_ai_models_info`)**: 連線到神經科（AI 服務），詢問大腦（AI 模型）的當前狀況。這位專科醫生非常謹慎，即使聯絡不上，也會在報告上寫「情況未知」，而不會讓整個體檢失敗。
3.  **生成報告 (`_format_system_info`)**: 將所有收集到的資訊整理成一份清晰、易讀的體檢報告，並交給使用者。

## 4. 依賴關係

*   **`structlog`**: 日誌記錄。
*   **`linebot.v3.messaging.TextMessage`**: 建立返回訊息。
*   **`src.domain.command_handler.CommandContext`**: 這是它的關鍵依賴，用於**獲取注入的服務**，例如 `ai_model_service`。
*   **標準庫**: `platform`, `sys`, `datetime`, `os` 用於收集環境資訊。

## 5. 設計模式與架構決策

*   **依賴注入 (Dependency Injection)**: `InfoCommandHandler` 是 DI 的一個典型消費者。它不建立或尋找依賴（如 `ai_model_service`），而是被動地從 `CommandContext` 接收它們。這使得該指令與具體的服務實現解耦，非常容易測試。
*   **關注點分離 (Separation of Concerns)**: 將**資料收集** (`_collect_system_info`) 和**資料表示** (`_format_system_info`) 分離在不同的方法中，是一個非常好的實踐。這使得兩部分的邏輯都可以獨立修改和維護。
*   **防禦性編程 (Defensive Programming)**: 在與外部服務（如 AI 服務）互動時，採用了 `try...except` 和 `hasattr` 等防禦性措施，大大提高了指令的**健壯性 (Robustness)** 和**可靠性 (Reliability)**。

## 6. 潛在的改進點

*   **版本號動態化**: 將應用程式版本號從寫死改為從某個檔案（如 `__version__.py`）或構建時的環境變數中讀取，這樣更容易與 CI/CD 流程整合。
*   **配置資訊來源**: 更多的配置資訊（如應用程式名稱）可以從我們之前分析過的 `Config` 物件中讀取，而不是寫死在指令中，以實現配置的集中化管理。
*   **格式化錯誤**: 在 `_format_system_info` 和 `handle` 的錯誤處理中，字串連接使用了 `\\n` 而不是 `\n`。這是一個需要修正的小錯誤，否則換行將無法正確顯示。
*   **擴展性**: 如果未來需要顯示更多服務的狀態（如資料庫連接池狀態），可以為 `_collect_system_info` 新增更多的私有方法（如 `_get_db_status`），每個方法負責一個服務，使得擴展更加清晰。 