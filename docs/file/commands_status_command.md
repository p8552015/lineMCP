# 檔案分析報告：`apps/bot/src/commands/status_command.py`

## 1. 檔案目的與角色

此檔案定義了 `StatusCommandHandler`，一個負責處理 `/status` 指令的具體指令處理器。它的核心角色是作為一個**即時健康檢查工具**，主動探測系統中所有關鍵服務和依賴項的當前狀態。

與 `info` 指令提供靜態配置快照不同，`status` 指令執行的是**動態的功能性測試**。它回答的問題不是「系統是如何配置的？」，而是「系統現在是否能正常工作？」。這對於快速診斷線上問題至關重要。

## 2. 主要類別/函數定義

### `class StatusCommandHandler(CommandHandler)`

這是檔案中唯一定義的類別，它實現了 `CommandHandler` 介面。

#### 核心方法

*   **`async handle(self, user_id: str, args: list[str]) -> Message`**:
    *   指令的進入點。它協調了狀態檢查的整個過程：呼叫 `_perform_status_checks` 來執行所有檢查，然後將結構化的結果傳遞給 `_format_status_report` 進行格式化。
    *   **`ErrorContext`**: 它使用了一個 `ErrorContext` 上下文管理器，這表明系統可能接入了一個集中的錯誤監控或日誌聚合服務，能夠在發生問題時捕獲更豐富的上下文資訊。

*   **`async _perform_status_checks(self) -> dict`**:
    *   這是**狀態檢查的協調器**。它呼叫一系列的私有 `_check_*` 方法，每個方法負責一個特定的服務，並將它們的結果（一個包含 `status` 和 `message` 的字典）聚合成一個大的狀態字典。

#### 狀態檢查方法 (`_check_*`)

*   **`async _check_mcp_connection(self) -> dict`**:
    *   **主動探測 (Active Probing)**: 這是最理想的健康檢查。它不僅檢查物件是否存在，而是實際 `await` `mcp_client.call_tool` 來執行一個無害的 `SELECT 1` 查詢。只有當查詢成功返回時，才認為連接是健康的。這提供了對網路、認證和遠端服務狀態的最高信心。

*   **`_check_ai_service(self) -> dict`**:
    *   **被動檢查 (Passive Check)**: 檢查 `ai_model_service` 是否存在，以及是否能讀取其 `available_models` 屬性。這能確認服務已成功初始化，但不能完全保證它能成功處理請求。

*   **`_check_database_service(self)` 和 `_check_internal_services(self)`**:
    *   **存在性檢查 (Existence Check)**: 這些方法檢查 `db_service`、`nl_service` 等服務是否已在 `CommandContext` 中被初始化（即不為 `None`）。這是最基礎的檢查級別。

*   **`_format_status_report(self, status_checks: dict) -> TextMessage`**:
    *   **表示層**: 負責將 `_perform_status_checks` 返回的結構化字典，轉換為人類可讀的報告。
    *   **智慧格式化**:
        1.  使用易於辨識的圖示（✅, ⚠️, ❌）來表示每個服務的狀態。
        2.  基於所有檢查的最壞結果，計算出一個**總體狀態**，並在報告末尾給出總結性建議。
        3.  能夠顯示如「內部服務」等檢查的詳細子項目。

## 3. 功能實現的簡要描述

`StatusCommandHandler` 的工作流程類似於一個**發射前的檢查清單**:
1.  **收到「檢查」指令**: 使用者輸入 `/status`。
2.  **開始檢查 (`_perform_status_checks`)**: 控制中心（`StatusCommandHandler`）開始逐項檢查：
    *   **檢查與任務控制中心的通訊 (`_check_mcp_connection`)**: 不只是看燈亮不亮，而是實際發送一個「聽到請回答」的信號並等待回覆。
    *   **檢查 AI 核心 (`_check_ai_service`)**: 確認 AI 核心已啟動並報告其模型數量。
    *   **檢查資料記錄儀 (`_check_database_service`)**: 確認資料記錄儀已開啟。
    *   **檢查其他維生系統 (`_check_internal_services`)**: 逐個點名，確認其他內部模組是否就位。
3.  **生成報告 (`_format_status_report`)**:
    *   匯總所有檢查結果。
    *   如果所有項目都是綠色（✅），則報告「系統狀態良好」。
    *   只要有一個項目是黃色（⚠️），總體狀態就變為警告。
    *   只要有一個項目是紅色（❌），總體狀態就變為錯誤，並拉響警報。
    *   將這份圖文並茂的報告發送給指揮官（使用者）。

## 4. 依賴關係

*   **`src.domain.command_handler.CommandContext`**: 這是此指令的命脈，它透過 DI 提供了所有需要檢查的服務 (`mcp_client`, `ai_model_service`, `db_service` 等)。
*   **`src.services.error_handlers.ErrorContext`**: 依賴於一個外部的錯誤處理上下文，表明系統具有良好的可觀察性。
*   `structlog`, `linebot.v3.messaging.TextMessage`, `datetime`。

## 5. 設計模式與架構決策

*   **依賴注入 (Dependency Injection)**: 這是該指令能夠存在的基石。它作為一個純粹的服務消費者，從 `CommandContext` 獲取一切所需，實現了高度解耦。
*   **健壯的錯誤處理**: 每個檢查都在自己的 `try...except` 沙箱中運行。這確保了**單點故障不會導致整個檢查流程中斷**，是構建可靠診斷工具的關鍵。
*   **關注點分離**: 資料的**獲取** (`_perform_status_checks`) 和**展示** (`_format_status_report`) 被清晰地分開，使得兩者都可以獨立演進。
*   **混合健康檢查策略**: 聰明地結合了高信心的**主動探測**和低成本的**被動/存在性檢查**，在效率和可靠性之間取得了良好的平衡。

## 6. 潛在的改進點

*   **深化健康檢查**: 對於被動檢查的服務（如資料庫），可以將其升級為主動探測，例如執行一個簡單的 `SELECT 1` 查詢來確認資料庫連接的活性。
*   **快取狀態**: 對於一些成本較高或不應過於頻繁的檢查（如外部 API 呼叫），可以考慮加入短時間的快取機制，避免使用者連續執行 `/status` 時對下游服務造成壓力。
*   **配置化檢查**: 可以將要檢查的服務列表配置化，而不是在 `_check_internal_services` 中寫死，這樣在新增服務時就無需修改指令碼碼。
*   **格式化錯誤**: `TextMessage` 的建立使用了 `\\n` 而非 `\n`，需要修正。 