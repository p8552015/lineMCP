# 📘 LLM 文件問答樣板（架構師升級版）- error_handler.py 分析報告

本報告由 AI 架構師助理生成，旨在對 `apps/bot/src/infrastructure/error_handler.py` 檔案進行深度分析。

---

## 🧩 樣板 1：檔案在專案中扮演的角色

【文件角色摘要】
- 📌 **主要功能與責任**：此檔案定義了一個**統一的錯誤處理框架**。其核心責任是捕獲系統中發生的各種預期和非預期的異常 (`Exception`)，並將它們轉換為對終端用戶友善、格式統一的 `TextMessage`。它同時負責根據錯誤的嚴重性記錄詳細的日誌，並提供了一個可以包裹業務邏輯的**錯誤處理中介軟體 (Middleware)**。
- 🧠 **在系統架構中的定位**：這是一個橫切關注點 (Cross-cutting Concern) 的實現，屬於**基礎設施層的核心**。它像一張安全網，覆蓋在所有可能拋出異常的業務邏輯之上。
    - **上層來源**：通常被應用程式的最高層（如 `MessageHandlerDI`、API 路由）或透過裝飾器應用於服務方法上。
    - **下游依賴**：它依賴於 `domain/exceptions.py` 中定義的自定義異常類型，以便提供更精確的錯誤訊息。它不直接被其他模組依賴，而是主動**包裹**其他模組。
- 🔁 **是否處理通訊 / 外部互動**：否。它的輸出 (`TextMessage`) 是為了外部通訊（回覆給 LINE 用戶），但它本身不執行通訊。
- ⚙️ **是否處理設定管理**：是，間接地。它有一個 `include_technical_details` 的設定選項，這通常會由全局設定檔或環境變數控制（例如，在開發環境中開啟，在生產環境中關閉）。
- 🧪 **是否負責資料驗證、格式轉換或協定解析**：它**響應**這些環節產生的錯誤（如 `ValidationException`），並將其轉換為用戶訊息。
- 💡 **是否涉及平台相依性、跨平台兼容性、錯誤恢復**：它本身是**錯誤恢復策略的一部分**。通過捕獲異常並返回友善訊息，它阻止了程式崩潰，實現了優雅降級 (Graceful Degradation)。
- 🔐 **是否與授權、安全、敏感操作有關**：是。它能明確處理 `AuthenticationException`，並能根據設定決定是否暴露敏感的技術細節。
- 🎯 **實用比喻**：這個模組就像是醫院的**「急診中心」**。
    - `UnifiedErrorHandler` 是經驗豐富的**主治醫生**。無論送來的是什麼病人（`Exception`），他都能快速診斷。
    - 自定義的 `BotError` 就像是病人自己說「我肚子疼」（已知、業務相關的錯誤），醫生可以根據這個主訴（`error.user_message`）快速給出安慰和處理意見。
    - 未知的 `Exception` 就像是昏迷的病人，醫生需要做全身檢查（`str(error)`、`traceback`），並根據一些典型症狀（如 `TimeoutError`, `ConnectionError`）給出初步判斷。
    - `_log_error` 是寫病歷，記錄詳細病情供後續分析。
    - `ErrorHandlerMiddleware` 就像是給每個出外勤的員工（業務邏輯函式）都配備了一個隨身急救包，確保他們一旦出事能被立刻處理。

---

## 🧩 樣板 2：有哪些類別，以及創建目的與結構特性

【類別分析】
- **類別名稱**：`UnifiedErrorHandler`
- 📌 **創建目的**：為了集中化處理所有類型的錯誤，將錯誤處理邏輯與業務邏輯分離，避免在業務程式碼中充斥大量的 `try...except` 區塊。
- 🧭 **使用場景**：在系統啟動時創建一個實例（通常是單例），然後在需要捕獲錯誤的地方（如最外層的請求處理器）使用它。
- 🧩 **內含哪些關鍵方法與邏輯功能**：
    - `handle_error()`: 處理錯誤的總入口，根據異常類型分發給不同的處理方法。
    - `_handle_bot_exception()`: 處理預期的、自定義的業務異常，通常能提供更精確的用戶訊息。
    - `_handle_system_exception()`: 處理非預期的系統異常或第三方庫異常，提供更通用的錯誤提示，並包含對 MCP、資料庫等常見錯誤的特殊判斷。
    - `_log_error()`: 根據錯誤的類型和嚴重性，使用 `structlog` 記錄結構化的日誌。對嚴重錯誤記錄完整的堆疊追蹤。
- 💡 **設計考量**：
    - **Strategy Pattern**: `handle_error` 內部根據 `isinstance(error, ...)` 的判斷，實際上是在動態選擇一個處理策略。
    - **SRP (單一職責原則)**：職責非常清晰，只做一件事：處理錯誤。
    - **Configurability**: 提供了 `include_technical_details` 選項，使其能適應不同環境的需求。

---

- **類別名稱**：`ErrorHandlerMiddleware`
- 📌 **創建目的**：將 `UnifiedErrorHandler` 的功能以 Python 裝飾器 (Decorator) 的形式提供，使其能以一種聲明式、非侵入性的方式應用於任何異步函式。
- 🧭 **使用場景**：作為裝飾器用在 FastAPI 的路由函式上，或任何需要進行錯誤捕獲的服務層方法上。
- 🧩 **內含哪些關鍵方法與邏輯功能**：
    - `__init__()`: 接收一個 `UnifiedErrorHandler` 的實例，實現了**依賴注入**。
    - `__call__()`: 實現了裝飾器協議。它返回一個 `wrapper` 函式，該函式用 `try...except` 包裹了原始函式的呼叫。
- 💡 **設計考量**：
    - **Decorator Pattern**: 這是裝飾器模式的經典應用。
    - **Dependency Injection**: 它不自己創建 `UnifiedErrorHandler`，而是依賴外部傳入，這使得它非常靈活且易於測試。

---

## 🧩 樣板 3：所有方法分析、使用情況與價值評估

【模組層級函式】

| 函式名稱 | 功能用途 | 使用情境 | 是否必要 | 替代方式 | 存在價值 |
|---|---|---|---|---|---|
| `get_error_handler` | 獲取一個全域共享的 `UnifiedErrorHandler` 單例。 | 在程式碼中任何地方需要手動處理錯誤時。 | ✅ 是 | 每次都手動創建 `UnifiedErrorHandler`。 | **高**。提供了一個方便的全域訪問點，簡化了使用。 |
| `handle_error_gracefully` | `get_error_handler().handle_error()` 的便捷包裝。 | 當需要用一行程式碼處理錯誤並獲取 `TextMessage` 時。 | 否 | 直接呼叫 `get_error_handler()...`。 | **中**。是一個語法糖，讓呼叫更簡潔。 |
| `create_error_middleware` | 創建 `ErrorHandlerMiddleware` 的工廠函式。 | 當需要創建一個帶特定設定的中介軟體實例時。 | ✅ 是 | 手動創建 `UnifiedErrorHandler` 再創建 `ErrorHandlerMiddleware`。 | **高**。封裝了創建過程，簡化了使用。 |

---

## 🧩 樣板 4：模組關係與相依

- **上游呼叫者（誰依賴此模組？）**
  - 任何需要捕獲和處理異常的模組。最常見的是頂層請求處理器，如 `MessageHandlerDI` 或 FastAPI 路由。
  - 任何使用了 `create_error_middleware` 作為裝飾器的方法。

- **下游相依元件（此模組依賴哪些外部資源/API？）**
  - `structlog`: 用於日誌記錄。
  - `linebot.v3.messaging.TextMessage`: 它的最終輸出產物。
  - `src.domain.exceptions`: 強烈依賴自定義的異常體系，這是其能提供精確錯誤訊息的基礎。
  - `traceback`: Python 標準庫，用於獲取堆疊追蹤。

- **是否存在循環相依（circular dependency）？**
  - 否。它位於依賴鏈的頂端，包裹其他服務，但很少被其他服務直接依賴。

---

## 🧱 額外架構師視角建議補充欄位

【架構師補充面向】
- 🧩 **模組相依關係圖**：這是一個典型的**橫切關注點**模組，它不位於主業務流程的依賴鏈上，而是像一個切面 (Aspect) 一樣，從側面切入到業務流程中。
- 🗂️ **是否有循環相依 / 高耦合風險**：無。設計上是低耦合的。
- ☁️ **是否容器化部署友善**：是。可以通過環境變數輕鬆控制 `include_technical_details` 的行為，非常適合容器化部署。
- 🧪 **可測試性**：**高**。
    - `UnifiedErrorHandler` 可以被獨立測試，只需傳入各種 `Exception` 實例，然後斷言返回的 `TextMessage` 內容是否符合預期。
    - `ErrorHandlerMiddleware` 也可以輕鬆測試，只需裝飾一個會拋出異常的假函式，然後驗證其返回值。
- ♻️ **是否為共享模組（utility）或純服務模組（service）**：這是一個**共享的基礎設施工具 (Shared Infrastructure Utility)**。
- 🧠 **能否重構為 microservice 或 reusable package**：**非常適合**。幾乎任何基於 `linebot` 的專案都可以重用這個錯誤處理框架，只需稍作修改（例如替換掉自定義的 `BotError` 或使其更通用）。

---

產出日期：由 LLM 生成
撰寫角色：架構師 / 技術負責人
版本：v2 架構師增強版 