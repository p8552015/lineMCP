# 📄 `ai_enhanced_parser.py` 檔案架構分析報告

本報告由 AI 架構師 Serena 根據 `LLM_文件問答樣板_架構師升級完整版.md` 模板，對 `apps/bot/src/services/nl_to_sql/parsers/ai_enhanced_parser.py` 進行分析。

**分析目標**: `apps/bot/src/services/nl_to_sql/parsers/ai_enhanced_parser.py`
**產出日期**: 2024-07-30
**撰寫角色**: AI 架構師 / 技術負責人

---

## 🧩 樣板 1：檔案在專案中扮演的角色

【文件角色摘要】
- 📌 **主要功能與責任**:
  - 此檔案定義了 `AIEnhancedParser` 類別，是 `CompositeParser` 管理的**基於 AI 的核心解析策略**。
  - **核心職責**：
    1.  **處理複雜查詢**: 專門處理 `RuleBasedParser` 無法匹配的、語意複雜或模糊的自然語言查詢。
    2.  **建構 AI Prompt**: 根據使用者輸入和上下文（如資料庫結構），動態建構一個詳細的、結構化的 Prompt (`_build_system_prompt`, `_prepare_ai_context`)。
    3.  **與 AI 模型互動**: 呼叫下游的 `AIModelService`，將建構好的 Prompt 發送給大型語言模型（LLM）。
    4.  **解析 AI 回應**: 將 LLM 回傳的（通常是 JSON 格式的）字串結果解析成一個結構化的 `ParsedQuery` 物件。
    5.  **提供後備邏輯**: 如果 AI 回傳的結果不夠結構化或不完整，它還包含了多種後備的推斷邏輯（如 `_infer_query_type_from_content`）來嘗試補救。

- 🧠 **在系統架構中的定位**:
  - **定位**：在 NL-to-SQL 子系統中，它是一個**具體的、基於 AI 的解析引擎**。它代表了系統處理自然語言能力的**上限**和**最後一道防線**。
  - **上層來源**：由 `CompositeParser` 在 `RuleBasedParser` 無法高信心度處理請求時呼叫。
  - **下游依賴**：`AIModelService`。這是它唯一且最重要的依賴，負責與外部的 AI/LLM 服務進行實際的網路通訊。

- 🎯 **實用比喻**:
  - `AIEnhancedParser` 就是 `CompositeParser`（主治醫生）最終求助的**專家會診團隊**。當一個病例（自然語言文本）極其罕見和複雜時，主治醫生會召集這個由各科頂尖專家組成的團隊。團隊會仔細研究病歷（建構 Prompt），使用最先進的醫療設備（呼叫 LLM），然後給出一個詳細的診斷報告（`ParsedQuery`）。這個過程成本高、耗時長，但能解決最棘手的問題。

---

## 🧩 樣板 2：有哪些類別，以及創建目的與結構特性

【類別分析】
- 類別名稱：`AIEnhancedParser`
- 📌 **創建目的**:
  - **核心目的**：利用大型語言模型的強大語意理解能力，來彌補傳統基於規則的方法在處理查詢多樣性和模糊性上的不足。
  - **具體目的**：賦予系統處理未知、複雜、口語化查詢的能力，極大提升了使用者體驗和系統的適用範圍。
- 🧭 **使用場景**:
  - 由 `EnhancedServiceFactory` 創建，並注入一個 `AIModelService` 實例。
  - 被 `CompositeParser` 作為一個低優先級但能力全面的後備策略添加進去。
  - 當使用者輸入的文本無法被 `RuleBasedParser` 處理時，其 `parse` 方法被呼叫。
- 🧩 **內含哪些關鍵方法與邏輯功能**:
  - `__init__(...)`: 接收 `AIModelService` 的注入。
  - `parse()`: 核心邏輯，實現了「準備上下文 -> 呼叫 AI -> 解析結果」的完整流程。
  - `can_handle()`: 評估自身處理特定文本的能力。其邏輯是，越複雜的查詢，越適合由它來處理，因此它會給出一個與查詢複雜度相關的信心度分數。
  - `_build_system_prompt()`: 定義了給 AI 的核心指令，這是 Prompt Engineering 的關鍵部分，直接決定了 AI 回應的品質。
  - `_prepare_ai_context()`: 為每次查詢動態準備上下文資訊。
  - `_parse_ai_result()`: 核心的後處理邏輯，負責將 AI 的非結構化或半結構化輸出，轉換為系統內部可以使用的嚴格結構化資料。
- 💡 **設計考量**:
  - **Prompt Engineering**: 整個類別的設計圍繞著如何建構高品質的 Prompt。`_build_system_prompt` 和 `_prepare_ai_context` 體現了這一點。
  - **防禦性與容錯**: `_parse_ai_result` 中不僅有 `try...except` 處理 JSON 解析錯誤，還有對 AI 回傳結果不符合預期格式的各種後備處理邏輯，這對於與不確定性高的 LLM 互動至關重要。
  - **單一職責原則 (SRP)**: 同樣地，它只負責「解析」，將與 AI 模型的具體通訊邏輯完全委派給了 `AIModelService`。
  - **里氏替換原則 (LSP)**: 嚴格遵守 `IParser` 介面的約定。

---

## 🧩 樣板 4：模組關係與相依

- **上游呼叫者**：`CompositeParser` (透過 `IParser` 介面)
- **下游相依元件**：`AIModelService`
- **是否存在循環相依**：**否**。

---

## 🧱 額外架構師視角建議補充欄位

- 🗂️ **高耦合風險**：**低**。它只依賴於 `AIModelService`，這是一個清晰且單一的依賴。風險主要在於對 AI 模型回傳格式的隱性耦合，如果 AI 模型的輸出格式發生變化，`_parse_ai_result` 方法就需要同步修改。
- 🧪 **可測試性**：**高**。由於其對外的依賴只有 `AIModelService`，在測試中可以非常容易地 Mock 這個服務。可以模擬 `AIModelService` 回傳各種成功或失敗的結果，來全面測試 `AIEnhancedParser` 的解析和容錯邏輯，而無需真正地進行網路呼叫。
- 🧠 **重構潛力**:
  - **Prompt 管理**: `_build_system_prompt` 方法中的 Prompt 是硬編碼在程式碼中的。當 Prompt 變得越來越複雜時，可以考慮將其外部化，存放在專門的設定檔或模板檔案中（如 Jinja2 模板）。這將使得 Prompt 的迭代和管理更加方便。
  - **結果解析邏輯**: `_parse_ai_result` 方法非常複雜，包含了多種後備邏輯。可以考慮將不同的解析策略（如解析 JSON、從純文字中推斷等）進一步拆分成更小的輔助類別或函式，以提高可讀性和可維護性。
  - **AI 服務抽象**: 註解中提到 `ai_model_service` 參數暫時使用 `Any` 類型，並等待 ADR-005 的統一。這是一個非常好的技術債紀錄。一旦定義了統一的 `IAIModelService` 介面，應立刻回來更新此處的型別提示，以增強靜態檢查和程式碼清晰度。 