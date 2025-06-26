# 檔案分析報告：`apps/bot/src/services/nl_to_sql/parsers/rule_based_parser.py`

## 1. 檔案目的與角色

此檔案是 NL-to-SQL 新架構中**解析層的具體實作之一**。它扮演著**高效、低成本的第一道防線**的角色，專門負責處理那些結構清晰、意圖明確的自然語言查詢。

它的核心職責是使用**預定義的規則（主要是正則表達式）**，快速地將使用者輸入匹配到一個已知的查詢意圖 (`QueryType`)，並提取出關鍵參數。它並不處理模糊或複雜的語義理解，而是專注於模式匹配。

在整個解析策略中，它作為 AI 解析器的補充，旨在用最低的延遲和計算成本，篩選和處理掉大量的簡單請求，從而為昂貴的 AI 模型減負。

## 2. 主要類別/函數定義

### `class RuleBasedParser(IParser)`
這是此檔案中唯一定義的類別，它完整地實現了 `IParser` 介面。

#### 核心方法

*   **`__init__(self, configuration: IConfiguration)`**:
    建構函數接收一個 `IConfiguration` 的實例。這是一個關鍵的設計：它不將規則硬編碼在程式碼中，而是從配置服務中動態載入 `_query_patterns`。這使得規則庫可以熱更新和擴展，而無需修改程式碼。

*   **`async parse(self, text: str, ...)`**:
    這是解析器的核心執行邏輯。其內部實現了一個清晰的**優先級匹配策略**：
    1.  **最高優先級 - 機台 ID 匹配**: 首先，它使用一個預編譯的正則表達式 `_machine_id_pattern` 來尋找明確的機台 ID（如 'M01', 'm345'）。如果找到，它會立即返回一個高信心度的 `SPECIFIC_MACHINE` 類型的 `ParsedQuery` 物件。
    2.  **次高優先級 - 通用模式匹配**: 如果未找到機台 ID，它會遍歷所有從配置中載入的查詢模式。這些模式按照其配置的 `confidence` 值降序排列，確保高信心度的規則被優先嘗試。
    3.  **最低優先級 - 未知查詢**: 如果所有規則都匹配失敗，它將返回一個 `UNKNOWN` 類型的 `ParsedQuery`。

*   **`can_handle(self, text: str) -> float`**:
    這個方法快速地對輸入文字執行與 `parse` 方法類似的匹配邏輯，但不進行完整的參數提取。它返回其能夠匹配到的規則中最高的信心度分數。這個分數對於上層的組合解析器（`CompositeParser`）來說，是決定是否委派任務給此解析器的重要依據。

*   **`get_parser_info() -> dict`**:
    返回關於此解析器的元資料，如名稱、版本和能力，使其對系統是「自我描述」的。

#### 內部輔助方法

*   `_create_machine_query`, `_create_typed_query`, `_create_unknown_query`: 這些是工廠方法，用於創建不同類型的 `ParsedQuery` 物件，使主邏輯更清晰。
*   `_extract_type_specific_parameters`: 負責在一個模式匹配成功後，根據具體的 `QueryType` 進一步提取詳細參數（例如，從 "最近 7 天的故障" 中提取出 `days=7`）。

## 3. 功能實現的簡要描述

`RuleBasedParser` 的工作流程如下：
1.  **初始化**: 從配置中載入所有規則。
2.  **接收請求**: 接收到一個自然語言字串。
3.  **機台 ID 優先**: 檢查字串中是否有 "Mxxx" 格式的機台 ID。有則立即判斷為查詢特定機台，打包參數後返回。
4.  **遍歷規則**: 若無機台 ID，則逐一用設定好的正則表達式去匹配輸入。
5.  **匹配成功**: 一旦有規則匹配成功，立即停止後續匹配，並根據該規則的定義（查詢類型、信心度）和從文字中提取的參數，打包成一個 `ParsedQuery` 物件返回。
6.  **全部失敗**: 若所有規則都試過仍未成功，則返回一個表示「無法理解」的 `ParsedQuery` 物件。

一個關鍵點是，它返回的 `ParsedQuery` 物件中，`sql_query` 欄位永遠是空的。它嚴格遵守職責分離，將 SQL 生成的任務完全交給下游的 `IQueryBuilder`。

## 4. 依賴關係

*   **`re`**: 依賴 Python 的正則表達式模組，這是其功能的核心。
*   **`structlog`**: 用於結構化日誌記錄。
*   **`..interfaces.parsing_interfaces.IParser`**: 實現此介面。
*   **`..interfaces.statistics_interfaces.IConfiguration`**: 依賴此介面來獲取規則配置，這是一個關鍵的解耦設計。
*   **`..models.query_models.ParsedQuery`, `..models.query_models.QueryType`**: 使用這些核心資料模型來封裝其輸出。

## 5. 設計模式與架構決策

*   **配置驅動開發 (Configuration-Driven Development)**: 將規則從程式碼中分離到設定檔中，是此解析器最核心的設計決策。這遵循了**開放/封閉原則 (OCP)**，使得系統在不修改程式碼的情況下具備了良好的擴展性。
*   **策略模式 (Strategy Pattern)**: `RuleBasedParser` 本身可以被看作是 `CompositeParser` 的一個具體策略。
*   **職責鏈模式 (Chain of Responsibility) 的一環**: 在與 `AIEnhancedParser` 和 `CompositeParser` 結合使用時，它構成了職責鏈的第一環——先用最簡單的方式處理，處理不了再傳遞給下一個更複雜的處理者。
*   **職責分離 (Separation of Concerns)**: 嚴格地將「意圖解析」與「SQL 生成」的職責分開，是其遵循 SOLID 原則的明確體現。

## 6. 潛在的改進點

*   **規則衝突**: 如果配置中的正則表達式寫得不好，可能會發生衝突（一個輸入可能被多個模式匹配）。目前的實現是「先到先得」（基於信心度排序），這在大多數情況下是有效的。但在更複雜的系統中，可能需要引入更明確的衝突解決機制或在載入時進行驗證。
*   **性能**: 對於極其龐大的規則集，遍歷所有規則可能會有效能影響。目前的實現中，規則數量是可控的，這不是問題。若規則集規模巨大，可以考慮使用更高效的匹配演算法（如 Aho-Corasick 演算法）來代替逐一的正則表達式搜索。
*   **參數提取的複雜性**: `_extract_type_specific_parameters` 方法如果需要處理非常複雜的參數提取邏輯，可能會變得臃腫。可以考慮將參數提取邏輯也進行策略化或配置化。 