# 檔案分析報告：`apps/bot/src/services/mcp_response_parser.py`

## 1. 檔案目的與角色

此檔案作為一個專門的 **MCP 回應解析器與標準化器**。其核心職責是接收來自各種 MCP (多進程通訊) 客戶端的原始、格式不一的回應，並將其轉換為應用程式內部可以穩定使用的、乾淨、標準化的 Python 資料結構（主要是 `list[dict]`）。

它在架構中扮演 **適配器 (Adapter)** 和 **防腐層 (Anti-Corruption Layer)** 的角色，將核心業務邏輯（如 `DatabaseService`）與外部 MCP 通訊協定的複雜性、不一致性和不可靠性隔離開來。透過將所有棘手的解析、錯誤處理和資料恢復邏輯集中在此處，它確保了應用程式的其他部分可以處理可預測的資料格式，從而顯著提高了程式碼的健壯性和可維護性。

## 2. 主要類別/函數定義

### `class MCPResponseParser`

這是一個不包含狀態的工具類別，其所有方法均為靜態方法 (`@staticmethod`)。

#### 主要方法

*   **`parse_query_result(result: dict | str) -> list[dict]`**:
    這是該類別最核心的公共方法。它接收一個原始 MCP 回應，並執行一系列複雜的解析與轉換步驟，以產出一個標準化的列表。其內部的邏輯極具彈性，能夠處理多種邊界情況。

*   **`parse_single_value(result: dict | str, field_name: str) -> Any`**:
    一個便利的包裝器，用於從查詢結果的第一行提取單一欄位的值。

*   **`parse_count_result(result: dict | str) -> int`**:
    專門用於解析計數查詢（例如 `SELECT COUNT(*)...`）的結果。它能智能地查找常見的計數欄位名稱（如 `count`, `total`）。

*   **`is_success(result: dict | str) -> bool`**:
    快速判斷 MCP 操作是否成功。

*   **`get_error_message(result: dict | str) -> str`**:
    從失敗的回應中提取錯誤訊息。

*   **`parse_response(content: str | dict) -> dict`**:
    一個核心的內部解析器，負責將字串格式的回應轉換為結構化的字典，並處理多種可能的格式（JSON、Python dict 字串等）。

#### 內部輔助方法

*   **`_attempt_recovery(content: str) -> list | dict | None`**:
    實現了複雜的錯誤恢復邏輯。當標準的 `json.loads` 失敗時，此方法會嘗試多種策略（例如，尋找並解析字串中嵌入的 JSON 片段、處理多個 JSON 物件等）來搶救資料。這是此解析器穩健性的關鍵。

*   **`_is_error_text(content: str) -> bool`**:
    使用正則表達式來判斷一個字串是否為純文字格式的錯誤訊息，而不是結構化的資料。

*   **`_parse_error_text(content: str) -> dict`**:
    當 `_is_error_text` 返回 `True` 時，此方法會從純文字中提取關鍵的錯誤資訊（如錯誤類型、訊息、來源），並將其格式化為標準的錯誤字典。

*   **`_detect_response_format(content: str) -> str`**:
    一個偵測器，用於識別輸入字串的格式（例如 'json_list', 'node_success', 'python_dict_string'），以指導後續的解析策略。

## 3. 功能實現的簡要描述

該解析器的工作流程可以概括如下：

1.  **輸入**: 接收一個可能是 `str` 或 `dict` 的 `result`。
2.  **預處理**: 如果輸入是字串，則調用 `parse_response` 將其轉換為 `dict`。`parse_response` 內部會使用 `_detect_response_format` 來決定如何解析。
3.  **成功檢查**: 檢查回應字典中 `success` 旗標。如果為 `False`，則立即提取錯誤資訊並引發 `MCPQueryError`。
4.  **資料提取**: 尋找 `data` 欄位。如果不存在，則返回空列表。
5.  **格式處理**: 根據 `data` 的類型（直接是 `list`，或是在 `dict` 中的 `content` 欄位，其 `text` 值又是一個 JSON 字串等）進行遞迴解析。
6.  **JSON 解析與恢復**:
    *   在解析 `text` 欄位中的 JSON 字串時，使用標準 `json.loads`。
    *   如果解析失敗，會先檢查它是否是一個純文字錯誤訊息 (`_is_error_text`)。如果是，則用 `_parse_error_text` 解析並引發 `MCPQueryError`。
    *   如果不是純文字錯誤，則啟動 `_attempt_recovery` 進行一系列的搶救嘗試。
    *   如果恢復失敗，則最終引發 `MCPParseError`。
7.  **標準化輸出**: 無論經過多麼複雜的路徑，最終的成功輸出總是一個 `list[dict]` 格式。

## 4. 依賴關係

*   **`json`**: 用於標準的 JSON 解析。
*   **`re`**: 用於複雜的模式匹配，主要在錯誤恢復和格式偵測中使用。
*   **`structlog`**: 用於結構化日誌記錄，提供了詳細的執行緒路徑和錯誤上下文，這對於除錯這種複雜的解析邏輯至關重要。
*   **自身定義的例外**: `MCPParseError` 和 `MCPQueryError`，用於清晰的錯誤傳播。

## 5. 設計模式與架構決策

*   **適配器模式 (Adapter Pattern)**: 完美地體現了此模式，將 MCP 客戶端多變的介面轉換為應用程式期望的穩定介面 (`list[dict]`)。
*   **防腐層 (Anti-Corruption Layer)**: 作為一個健壯的邊界，保護核心領域模型不受外部系統（MCP）的污染和影響。
*   **高度防禦性程式設計 (Defensive Programming)**: 程式碼中充滿了對各種可能失敗情況的預處理，從檢查 `None`、處理不同類型到複雜的錯誤恢復。這是一個明確的設計決策，旨在建立一個在面對不完美資料時不會輕易崩潰的系統。
*   **關注點分離 (Separation of Concerns)**: 將資料的 *解析* 與資料的 *獲取*（在 `DatabaseService` 或 MCP 客戶端中）完全分開。`DatabaseService` 不必關心它收到的 `result` 是如何被解析的，它只需要知道可以信任 `MCPResponseParser` 的輸出。
*   **靜態工具類別**: 將其設計為一個無狀態的工具類別是合適的，因為解析本身是一個純函數過程，不依賴於任何外部狀態。

## 6. 潛在的改進點

*   **恢復策略的可擴展性**: `_attempt_recovery` 方法中的恢復策略是硬編碼的。如果未來出現更多需要恢復的格式，該函數會變得更加複雜。可以考慮將每種恢復策略重構為單獨的、可註冊的策略類別，以提高可維護性。
*   **效能考量**: 對於極大的回應字串，多次的正則表達式匹配和字串操作可能會有效能開銷。但在當前的使用情境下（處理單次資料庫查詢的回應），這很可能不是問題。若未來用於解析巨型日誌檔案等場景，則可能需要進行效能分析。
*   **更詳細的錯誤分類**: `MCPParseError` 目前只是一個通用的解析錯誤。可以考慮引入更細粒度的子類別，例如 `JSONRecoveryError`、`UnsupportedFormatError` 等，以便上層呼叫者可以進行更精確的錯誤處理。 