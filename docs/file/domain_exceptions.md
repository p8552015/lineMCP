# 檔案分析報告：`apps/bot/src/domain/exceptions.py`

## 1. 檔案目的與角色

此檔案是整個應用程式的**統一錯誤處理契約 (Unified Error Handling Contract)**。它定義了一套自定義的、具有豐富語義的異常類別，用於在應用程式的不同層級中表示各種已知的錯誤情境。

它的核心角色是：
1.  **建立錯誤詞彙表 (Creating an Error Vocabulary)**: 它為專案建立了一套通用的「錯誤語言」。開發者可以透過 `raise ValidationException(...)` 而不是 `raise ValueError("...")` 來拋出錯誤，使得錯誤的意圖更加清晰、明確。
2.  **區分已知與未知錯誤**: 透過提供一個共同的基底類別 `BotError`，它允許應用程式的高層（如中介軟體或 API 路由）能夠輕易地區分「業務邏輯內的預期錯誤」（所有繼承自 `BotError` 的錯誤）和「真正的意外系統錯誤」（如 `MemoryError` 或第三方函式庫的 `Exception`）。
3.  **豐富錯誤上下文**: 它將錯誤從一個簡單的字串，升級為一個包含多種資訊的結構化物件，包括給開發者看的技術訊息、給使用者看的友善訊息、用於機器解析的錯誤碼以及用於詳細除錯的附帶資料。
4.  **促進關注點分離**: 它將「向使用者顯示什麼」(`user_message`) 與「在日誌中記錄什麼」(`message`, `details`) 分離，讓業務邏輯的開發者在拋出異常時就能決定這兩者，而無需讓上層的 UI 或 API 層來做這個決定。

## 2. 主要類別/函數定義

### `class BotError(Exception)`
這是所有自定義業務異常的**基底類別**。
*   **建構函數**: 接受 `message` (技術細節), `user_message` (給使用者), `details` (結構化數據), `error_code` (機器可讀代碼)。這種設計非常全面。
*   **`to_dict(self)`**: 一個序列化方法，可以輕易地將異常物件轉換為字典，非常適合用於生成 JSON API 回應或寫入結構化日誌。

### 繼承自 `BotError` 的具體異常類別
檔案中定義了多個具體的異常類別，每個都代表一種特定的錯誤領域。這種做法極大地提高了程式碼的可讀性和可維護性。
*   **`ValidationException`**: 用於輸入資料驗證失敗。
*   **`CommandParsingException`**: 用於解析使用者輸入的指令失敗，與我們猜測的命令模式緊密相關。
*   **`DatabaseQueryException`**: 用於資料庫操作失敗。
*   **`MCPConnectionException`**: 用於與 MCP 服務（一個核心依賴）連接失敗。
*   **`AIServiceException`**: 用於與外部 AI 服務（如 OpenAI, Google AI）互動失敗。
*   **`AuthenticationException`**: 用於權限驗證失敗。
*   **`RateLimitException`**: 用於請求頻率超過限制。
*   **`ConfigurationException`**: 用於系統設定不正確或缺失。
*   **`BusinessLogicException`**: 一個更通用的業務邏輯錯誤。
*   **`ExternalServiceException`**: 用於其他所有外部服務的通用錯誤。

### 便捷工廠函數
檔案末尾提供了一系列的 `create_*_error` 函數。
*   **目的**: 這些函數是語法糖，它們封裝了對應異常類別的實例化過程，使得建立異常物件的程式碼更簡潔。例如，`create_db_error(...)` 比 `DatabaseQueryException(...)` 更具可讀性。

## 3. 功能實現的簡要描述

當系統的某個部分（例如，一個服務或一個資料庫存取物件）遇到一個已知的錯誤時，它不會引發一個通用的 `Exception` 或 `ValueError`，而是會實例化並引發一個對應的、語義化的異常。

例如，如果資料庫查詢超時，資料存取層會 `raise DatabaseQueryException(query="...", reason="timeout")`。

在應用程式的更高層級，例如一個 FastAPI 的中介軟體中，可以這樣處理：
```python
try:
    # ... 執行業務邏輯 ...
except BotError as e:
    # 這是我們已知的、可控的業務錯誤
    log.error(e.to_dict())  # 記錄詳細的結構化日誌
    return JSONResponse(
        status_code=400,  # 或者根據 e.error_code 決定更精確的狀態碼
        content={"error": e.user_message} # 只向使用者顯示安全、友善的訊息
    )
except Exception as e:
    # 這是未知的、意外的系統錯誤
    log.critical("An unexpected system error occurred!", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "系統發生未預期的嚴重錯誤，請聯絡管理員。"}
    )
```

## 4. 依賴關係

*   **`typing.Any`**: 來自 Python 的標準型別提示函式庫。除此之外，此檔案**沒有任何外部依賴**，這對於一個基礎的領域模組來說是完美的，保證了其高度的可移植性。

## 5. 設計模式與架構決策

*   **自定義異常層次結構 (Custom Exception Hierarchy)**: 這是此檔案最核心的設計模式。建立一個繼承自 `Exception` 的基底類別，然後從該基底類別派生出所有具體的業務異常。
*   **關注點分離 (Separation of Concerns)**: 在異常物件本身中分離了內部錯誤細節和外部使用者訊息，是一個非常成熟的設計決策。
*   **工廠函數 (Factory Functions)**: 雖然是一個小型的模式應用，但使用 `create_*` 函數來簡化物件的建立過程，提高了程式碼的可讀性和一致性。
*   **面向失敗的設計 (Design for Failure)**: 整個檔案的存在都體現了「面向失敗設計」的理念。它承認錯誤是系統運作的正常部分，並為之提供了健壯、可預測的處理框架。

## 6. 潛在的改進點

*   **HTTP 狀態碼映射**: 可以在 `BotError` 基底類別中增加一個 `status_code` 屬性，並為每個子類別設定一個預設的 HTTP 狀態碼（如 `ValidationException` -> 400, `AuthenticationException` -> 401/403）。這樣，上層的錯誤處理中介軟體就可以直接使用這個屬性，而無需自己去判斷。
*   **國際化 (i18n)**: `user_message` 目前是硬編碼的。在需要支援多語言的應用中，可以將其改為一個錯誤碼或鍵，然後由一個專門的國際化服務根據這個鍵和使用者的語言環境來產生最終的錯誤訊息。
*   **自動日誌記錄**: 可以在 `BotError` 的 `__init__` 方法中直接加入日誌記錄邏輯，這樣一旦異常被建立，就會被自動記錄下來，即使它後來被捕獲且沒有被再次記錄。但這也可能導致重複日誌，需要謹慎設計。 