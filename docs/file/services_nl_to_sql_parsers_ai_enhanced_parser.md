# 檔案分析報告：`apps/bot/src/services/nl_to_sql/parsers/ai_enhanced_parser.py`

## 1. 檔案目的與角色

此檔案是 NL-to-SQL 新架構中**解析層的「大腦」**，扮演著**智能解析核心**的角色。當簡單、快速的 `RuleBasedParser` 無法處理使用者輸入時，任務便會被傳遞到這裡。

它的核心職責是利用大型語言模型 (LLM) 的強大語意理解能力，處理那些**模糊、複雜或格式不固定**的自然語言查詢。它不僅僅是呼叫一個 AI API，而是包含了一整套與 LLM 高效、可靠互動的工程實踐。

在整個解析策略中，它作為系統能力的「天花板」，負責解決最困難的理解任務，是系統能夠被稱為「智能」的關鍵所在。

## 2. 主要類別/函數定義

### `class AIEnhancedParser(IParser)`
這是此檔案中唯一定義的類別，它完整地實現了 `IParser` 介面，使其能與其他解析器無縫協作。

#### 核心方法

*   **`__init__(self, ai_model_service)`**:
    建構函數接收一個 `ai_model_service` 的實例。這遵循了**依賴反轉原則**，使得 `AIEnhancedParser` 不與任何具體的 AI 模型（如 OpenAI, Anthropic）綁定，只依賴於一個抽象的 AI 服務介面。

*   **`async parse(self, text: str, context: dict | None = None)`**:
    這是 AI 解析的核心流程：
    1.  **準備上下文**: 呼叫 `_prepare_ai_context`，將使用者的問題、資料庫的結構描述 (`schema`) 和其他領域知識打包成一個豐富的上下文物件。
    2.  **呼叫 AI**: 將問題和上下文一同傳遞給 `_ai_service.enhance_natural_language_query` 方法，發起對 LLM 的呼叫。
    3.  **解析結果**: 接收 AI 返回的結果（預期為 JSON 字串）和信心度，然後呼叫 `_parse_ai_result` 對其進行解析。
    4.  **錯誤處理**: 整個過程被包裹在 `try...except` 中，以捕捉 AI 呼叫或結果解析中可能發生的任何異常。

*   **`can_handle(self, text: str) -> float`**:
    此方法透過一個內部的 `_assess_query_complexity` 函數來評估輸入文字的複雜度。它返回一個基礎信心度（例如 0.6），並根據複雜度給予少量加成。這為上層的組合解析器提供了一個信號：它總能「嘗試」處理，但信心度不如規則解析器那麼絕對。

#### 關鍵內部輔助方法

*   **`_build_system_prompt() -> str`**:
    **Prompt 工程**的核心。此方法定義了一個詳細的系統提示，它指導 LLM 扮演特定角色、理解任務、遵循輸出格式（**JSON**），這是確保 AI 可靠輸出的關鍵技術。

*   **`_prepare_ai_context(...) -> dict`**:
    另一個關鍵的 Prompt 工程部分。它負責收集和組織所有能幫助 LLM 理解問題的上下文資訊，其中最重要的就是**資料庫的 Schema**。

*   **`_parse_ai_result(...) -> ParsedQuery`**:
    一個**健壯的結果解析器**。它首先嘗試用 `json.loads` 解析 AI 的回應。如果失敗（LLM 的輸出有時不是完美的 JSON），它不會立即崩潰，而是會退回到一個備用的純文字解析方法 `_parse_text_ai_result`，嘗試從非結構化文字中「搶救」出有用的資訊。這是生產級 AI 應用的重要特徵。

## 3. 功能實現的簡要描述

`AIEnhancedParser` 的工作流程可以概括為一個與 AI 專家對話的過程：
1.  **整理材料**: 接收到使用者的問題後，它不會直接去問 AI。而是先扮演一個秘書的角色，將問題、公司內部資料（資料庫 Schema）、相關背景（領域知識）等所有材料整理成一份清晰的簡報（`ai_context`）。
2.  **進行諮詢**: 它拿著這份簡報和一個明確的指示清單（`_system_prompt`，告訴 AI 專家要以什麼格式回答），去向 AI 專家（`_ai_service`）提問。
3.  **解讀報告**: 拿到 AI 專家的回覆後，它首先嘗試按照預期的報告格式（JSON）進行解讀。
4.  **應對意外**: 如果專家喝多了，給了一份格式混亂的報告（無效 JSON），它不會放棄，而是會嘗試從報告的字裡行間（純文字）去理解核心意思。
5.  **形成決策**: 最後，它將解讀出的結果，打包成一份標準化的內部報告（`ParsedQuery` 物件），供後續部門使用。

## 4. 依賴關係

*   **`json`**: 用於解析 AI 返回的 JSON 字串。
*   **`structlog`**: 用於結構化日誌記錄。
*   **`..interfaces.parsing_interfaces.IParser`**: 實現此介面。
*   **`ai_model_service` (外部依賴)**: 依賴一個抽象的 AI 模型服務來執行推理。
*   **`..models.query_models.ParsedQuery`, `..models.query_models.QueryType`**: 使用這些核心資料模型來封裝其輸出。

## 5. 設計模式與架構決策

*   **Prompt 工程**: 這是此類 AI 驅動模組的核心「演算法」。將 Prompt 的構建 (`_build_system_prompt`, `_prepare_ai_context`) 抽象成獨立的方法，是一個清晰的設計決策。
*   **結構化輸出 (Structured Output)**: 要求並解析 JSON 格式的輸出，是當前與 LLM 進行可靠程式化互動的最佳實踐。
*   **防禦性程式設計與錯誤恢復**: 對 AI 輸出進行健壯的解析，並提供從格式錯誤中恢復的備用方案 (`fallback mechanism`)，是構建生產級 AI 應用的關鍵架構決策。
*   **依賴倒置**: 依賴抽象的 `ai_model_service` 而非具體實現，使得底層的 AI供應商可以被輕易替換。
*   **策略模式 (Strategy Pattern)**: 它自身是 `CompositeParser` 的一個具體策略，專門處理複雜查詢。

## 6. 潛在的改進點

*   **Prompt 模板化**: `_build_system_prompt` 中的提示是硬編碼的。可以考慮將其模板化，並從 `IConfiguration` 服務中載入，這樣就可以在不修改程式碼的情況下，對提示進行微調和 A/B 測試。
*   **幻覺 (Hallucination) 檢測**: 目前的解析邏輯主要關注格式。可以增加一層驗證，用於檢測 AI 回應內容中的「幻覺」。例如，如果 AI 返回的 `parameters` 包含了一個資料庫 Schema 中不存在的欄位，系統應該能夠識別出這是一個潛在的幻覺。
*   **成本與令牌計數**: 可以增加對 Prompt 和 Completion 令牌數量的追蹤，並將其記錄到 `IMetricsCollector`，以便進行成本分析和控制。
*   **上下文窗口管理**: 對於非常大的資料庫 Schema，需要有策略來管理傳遞給 AI 的上下文，確保其不超過模型的上下文視窗限制。 