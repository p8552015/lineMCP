# 檔案分析報告：`apps/bot/src/commands/models_command.py`

## 1. 檔案目的與角色

此檔案定義了 `ModelsCommandHandler`，一個專門處理 `/models` 指令的具體指令處理器。它的角色是為使用者提供一個**深入、透明的視窗**，來查看系統集成的 AI 模型的能力、狀態和配置。

這個指令不僅僅是 `info` 或 `status` 指令中 AI 部分的簡單擴展，而是一個功能完備的**模型瀏覽器**。它允許使用者從一個高層次的列表視圖，下鑽到單一模型的詳細規格表，提供了豐富的互動性。

## 2. 主要類別/函數定義

### `class ModelsCommandHandler(CommandHandler)`

這是檔案中唯一定義的類別，繼承自 `CommandHandler`。

#### 核心方法

*   **`async handle(self, user_id: str, args: list[str]) -> Message`**:
    *   指令的入口和分派器。它根據 `args` 的有無，將請求路由到 `_list_all_models`（列表視圖）或 `_get_model_details`（詳細視圖）。

*   **`async _list_all_models(self)`**:
    *   獲取並展示所有可用模型的列表。它的輸出不是一個單純的列表，而是經過精心設計的。

*   **`async _get_model_details(self, model_name: str)`**:
    *   根據使用者提供的名稱或 ID，查找並顯示單一模型的詳細資訊。它的搜尋邏輯是使用者友善的（不區分大小寫，同時匹配名稱和 ID），並且在找不到時會給出有用的提示。

#### 最具代表性的方法

*   **`async _get_models_from_service(self, ai_service) -> dict`**:
    *   這是該指令**最具彈性和防禦性**的部分。它展現了作者對真實世界軟體演進的深刻理解：API 是會變的。
    *   **多重備援策略**: 它不假設 `ai_service` 只有一種固定的介面，而是按順序嘗試多種方式來獲取模型列表和當前模型：
        1.  嘗試讀取 `available_models` **屬性**。
        2.  如果失敗，則嘗試 `await` 一個 `list_models()` **方法**。
        3.  同樣地，它會嘗試 `current_model` 屬性和 `get_current_model()` 方法。
    *   這個設計使得 `ModelsCommandHandler` 能夠與不同版本、不同實現的 `ai_model_service` 無縫協作，而無需修改自身程式碼。

#### 格式化方法

*   **`_format_models_list(self, models_info: dict)`**:
    *   **智慧分組**: 將模型按其 `provider` 進行分組，極大地增強了長列表的可讀性。
    *   **資訊密度**: 在有限的空間內，透過圖示（🟢/🔴/⭐）和簡潔的文字，有效地傳達了每個模型的狀態、名稱和是否為當前模型。

*   **`_format_model_details(self, model: dict, ...)`**:
    *   **條件式渲染**: 動態地檢查 `model` 字典中是否存在 `description`, `capabilities`, `cost` 等可選鍵。只在資料存在時才顯示對應的區塊。這使得報告既能展示豐富資訊，又能優雅地處理資訊不完整的模型。

## 3. 功能實現的簡要描述

`ModelsCommandHandler` 的工作流程就像一個**汽車展廳的導覽員**：
1.  **迎接訪客**: 使用者輸入 `/models`。
2.  **判斷需求**:
    *   **只說 `/models`**: 訪客想先快速瀏覽一下。導覽員 (`_list_all_models`) 拿出展廳地圖，按品牌（`provider`）分區，指出每個品牌下有哪些車型（模型），哪些是可用的（🟢），以及哪輛是當前的試駕車（⭐）。
    *   **說 `/models gpt-4`**: 訪客指名要看某款車。導覽員 (`_get_model_details`) 帶他到那輛車前。
3.  **詳細介紹 (`_format_model_details`)**:
    *   導覽員開始介紹這款車的詳細規格：廠商、型號、性能指標（上下文窗口、最大輸出）、選配功能（`capabilities`）以及價格（`cost`）。
    *   他只介紹這輛車有的配置，不會提及不存在的功能，讓介紹單清晰明瞭。
4.  **完成導覽**: 將整理好的資訊（列表或詳細規格）以文字訊息的形式呈現給訪客。

## 4. 依賴關係

*   **`src.domain.command_handler.CommandContext`**: 這是獲取 `ai_model_service` 的唯一來源，是 DI 模式的完美應用。
*   `structlog`, `linebot.v3.messaging.TextMessage`。

## 5. 設計模式與架構決策

*   **彈性適配器 (Resilient Adapter)**: `_get_models_from_service` 的設計思想類似於適配器模式，但它更進一步，成為一個能夠適應多種不同介面（`Adaptee`）的**彈性適配器**。這是構建健壯、低維護成本軟體的典範。
*   **關注點分離**: 資料的**獲取** (`_get_models_from_service`)、**業務邏輯** (`handle`, `_list_all_models`, `_get_model_details`) 和 **表示** (`_format_*`) 被清晰地劃分在不同的方法中。
*   **防禦性編程**: 整個檔案處處體現著防禦性編程思想。從 `try...except` 的廣泛使用，到 `getattr` 和 `dict.get` 的安全存取，都確保了指令在面對非預期資料或服務故障時的穩定性。

## 6. 潛在的改進點

*   **模型比較功能**: 可以新增一個功能，如 `/models compare gpt-4 gpt-3.5`，來並排顯示兩個或多個模型的關鍵規格，方便使用者比較。
*   **與 `Config` 服務整合**: 如果模型的某些元資料（如 `description` 或 `capabilities`）可以從中央配置服務中讀取並與即時狀態合併，可以使配置更加集中化。
*   **格式化錯誤修正**: 所有 `TextMessage` 的建立都使用了 `\\n` 而非 `\n`，需要修正這個換行符的錯誤。 