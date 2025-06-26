# 檔案分析報告：`apps/bot/src/services/nl_to_sql_service.py`

## 1. 檔案目的與角色

此檔案在專案中扮演著一個至關重要的 **向後兼容包裝器 (Backward-Compatible Wrapper)** 和 **適配器 (Adapter)** 的角色。它的主要目的不是實現自然語言轉 SQL (NL-to-SQL) 的核心邏輯，而是為了在不破壞現有系統功能的前提下，平穩地過渡到一個更先進、遵循 SOLID 設計原則的新架構。

它作為新舊世界之間的橋樑：
*   **對外 (對舊世界)**: 它維持了 `NaturalLanguageToSQLService` 這個類別和 `parse_natural_language` 等方法的既有 API 介面，使得依賴它的舊有程式碼（如 `MessageHandlerDI`）無需進行任何修改。
*   **對內 (對新世界)**: 它將所有實際工作委派給位於 `nl_to_sql/` 子目錄下的新一代 SOLID 元件。

因此，這個檔案是專案進行重大**架構重構**的一個明確證據，體現了在軟體演進過程中保持系統穩定運行的務實策略。

## 2. 主要類別/函數定義

### `class NaturalLanguageToSQLService`

這是此檔案中唯一定義的類別，它實現了適配器模式。

#### 主要方法

*   **`__init__(self, ai_model_service: AIModelService)`**:
    建構函數接收一個舊版的 `AIModelService` 依賴，但並未直接將其傳遞給新的 SOLID 元件。它初始化了四個指向新元件介面 (`IParser`, `IQueryBuilder`, 等) 的內部屬性為 `None`，為後續的延遲載入做準備。

*   **`async parse_natural_language(self, text: str, context: dict | None = None) -> ParsedQuery`**:
    這是對外的核心 API。它的執行流程清晰地展示了其包裝器職責：
    1.  **輸入驗證**: 首先調用 `_validate_input` 對輸入的自然語言進行嚴格的檢查。
    2.  **統計記錄**: 調用 `_get_statistics` 獲取統計服務，記錄驗證失敗或解析開始等事件。
    3.  **委派解析**: 調用 `_get_parser` 獲取新的解析器元件 (`IParser`)，並將實際的解析任務委派給它。
    4.  **空 SQL 防護**: 檢查解析結果，如果 AI 模型返回了意圖但沒有返回 SQL 字串，它會啟動修復機制，調用 `_get_query_builder` (`IQueryBuilder`) 來嘗試重建 SQL。
    5.  **返回結果**: 將最終的 `ParsedQuery` 物件返回給呼叫者。

#### 內部輔助方法

*   **`_get_parser()`, `_get_query_builder()`, `_get_statistics()`, `_get_configuration()`**:
    這一組方法實現了 **服務定位器 (Service Locator)** 模式。它們在首次被需要時，透過全域的 `get_enhanced_service_factory()` 來動態地、延遲地獲取新架構下的 SOLID 元件實例。這種方式解耦了 `NaturalLanguageToSQLService` 與新元件的直接創建過程。

*   **`_validate_input(self, text: str) -> dict`**:
    一個非常重要的 **防禦性** 方法。它在將任何使用者輸入傳遞給 AI 模型之前，實施了一系列清理和安全檢查，包括空值、長度、可疑 SQL 關鍵字（如 `drop table`）和特殊字元過濾。

## 3. 功能實現的簡要描述

這個類別不自己實現 NL-to-SQL 功能，而是精心編排了一系列新舊元件的協作：
1.  當外部（舊程式碼）呼叫 `parse_natural_language` 時，它首先像一個保安一樣，用 `_validate_input` 檢查來賓（輸入字串）的身份和意圖。
2.  驗證通過後，它透過服務工廠（服務定位器）找到並呼叫新聘請的專家——`IParser` 實例。
3.  拿到專家的初步分析報告 (`ParsedQuery`) 後，它會進行審核。如果發現報告的核心內容（SQL 查詢）缺失，它會要求另一位專家 `IQueryBuilder` 根據現有線索（參數）把核心內容補上。
4.  在整個過程中，它還會通知統計部門 (`IStatistics`) 記錄關鍵節點的活動，以便追蹤績效和問題。
5.  最終，它將一份完整、標準化的報告 (`ParsedQuery`) 提交給最初的呼叫者。

## 4. 依賴關係

*   **`structlog`**: 用於結構化日誌記錄。
*   **`..infrastructure.enhanced_service_factory`**: 這是此適配器模式的關鍵。它透過工廠（作為服務定位器）來獲取所有新架構的服務，從而實現了與新元件的解耦。
*   **`.nl_to_sql.interfaces.*`**: 依賴於新架構定義的一系列介面（`IParser`, `IQueryBuilder` 等）。這遵循了 **依賴反轉原則**——它不依賴於具體的實現，而是依賴於抽象。
*   **`.ai_model_service.AIModelService`**: 依賴於舊版的 AI 服務。這是一個有趣的點，顯示了過渡階段的特徵——它自身被舊架構的元件初始化，但內部又去呼叫新架構的元件。

## 5. 設計模式與架構決策

*   **適配器模式 (Adapter Pattern)**: 這是此檔案最核心的設計模式。它將 `nl_to_sql` 新元件的介面適配成舊版 `NaturalLanguageToSQLService` 的介面。
*   **服務定位器模式 (Service Locator Pattern)**: 透過 `_get_...` 系列方法和 `enhanced_service_factory` 來實現。這是一種實現依賴注入的替代方案，雖然有時被認為是反模式，但在這種需要與靜態或全域資源橋接的過渡性程式碼中，是一種務實的選擇。
*   **防禦性程式設計 (Defensive Programming)**: `_validate_input` 和空 SQL 防護機制是明確的架構決策，旨在增強系統面對不合法輸入和不穩定 AI 行為時的穩健性。
*   **漸進式重構 (Incremental Refactoring)**: 這個檔案本身就是這一重要軟體工程實踐的產物。它允許團隊在不停止服務或進行 "大爆炸式" 變更的情況下，安全地對系統核心部分進行現代化改造。

## 6. 潛在的改進點

*   **移除過渡性程式碼**: 此檔案的最終目標應該是被移除。一旦所有呼叫 `NaturalLanguageToSQLService` 的地方都被重構為直接使用新的 SOLID 元件（可能透過真正的依賴注入框架），這個適配器就完成了其歷史使命。檔案開頭的文檔也明確指出了這一點。
*   **服務定位器的依賴**: 對全域 `get_enhanced_service_factory()` 的依賴使得單元測試變得稍微困難，因為需要對這個全域工廠進行模擬 (Mocking)。如果未來全面轉向依賴注入，這個問題將自然解決。
*   **`AIModelService` 依賴**: 舊的 `ai_model_service` 依賴在 `__init__` 中被接收，但在後續方法中似乎並未被直接使用（新元件可能會從工廠內部接收更新的 AI 服務）。這可能是過渡階段遺留下來的一個可以清理的痕跡。 