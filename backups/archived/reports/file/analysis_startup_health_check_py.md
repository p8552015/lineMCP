# 📄 `startup_health_check.py` 檔案架構分析報告

本報告由 AI 架構師 Serena 根據 `LLM_文件問答樣板_架構師升級完整版.md` 模板，對 `apps/bot/src/utils/startup_health_check.py` 進行分析。

**分析目標**: `apps/bot/src/utils/startup_health_check.py`
**產出日期**: 2024-07-30
**撰寫角色**: AI 架構師 / 技術負責人

---

## 🧩 樣板 1：檔案在專案中扮演的角色

【文件角色摘要】
- 📌 **主要功能與責任**:
  - 此檔案定義了 `StartupHealthChecker` 類別，其核心職責是在應用程式啟動的生命週期事件中，作為一個**啟動守衛 (Startup Guard)**。
  - **核心職責**：
    1.  **協調檢查 (Coordinate Checks)**: 它的主要工作是**呼叫**其他更專業的檢查器（目前是 `DatabaseHealthChecker`），來獲取關於外部依賴的健康狀況報告。
    2.  **解釋報告 (Interpret Reports)**: 它**消費並解釋**來自 `DatabaseHealthChecker` 的詳細 JSON 報告。`_log_health_report` 方法將複雜的 JSON 轉化為對人類友善的、帶有清晰等級（INFO, WARNING, ERROR）的日誌輸出。
    3.  **執行策略 (Enforce Policy)**: `_evaluate_startup_safety` 方法是該類別最關鍵的部分。它包含了一系列**硬編碼的啟動規則和策略**。它不僅僅是看總體狀態是否為 `healthy`，而是會進行更細粒度的判斷，例如：
        -   「連接失敗絕對不能啟動」。
        -   「缺少 `machines` 這個**關鍵**資料表，絕對不能啟動」。
        -   「在**嚴格模式**下，任何功能驗證失敗都不能啟動」。
    4.  **決定生死 (Decide Fate)**: 最終，它會根據策略評估的結果，返回一個布林值，告訴上層呼叫者（如 FastAPI 的啟動事件）應用程式是否可以安全啟動。

- 🧠 **在系統架構中的定位**:
  - **定位**：這是一個**應用程式生命週期管理**元件。它被設計為在應用程式的 `startup` 事件中被非同步呼叫。它的存在是為了實現**快速失敗 (Fail-fast)** 和**啟動時自檢 (Startup Self-test)**，這對於構建高可靠性的服務至關重要。
  - **上層來源**：`main.py` 中的 FastAPI `startup` 事件處理器。
  - **下游依賴**：`DatabaseHealthChecker`。

- 🎯 **實用比喻**:
  - `StartupHealthChecker` 就像是火箭發射前的**發射控制中心主管**。
    -   `DatabaseHealthChecker` 是負責檢查引擎的工程師。他向主管提交了一份詳細的引擎參數報告（`health_report`）。
    -   主管 (`StartupHealthChecker`) 不會只看報告的總結頁，他會仔細閱讀 (`_log_health_report`)。
    -   然後，他會對照著一本**發射手冊**（`_evaluate_startup_safety`）來做最終決定。手冊上寫著：
        -   「規則 1：燃料壓力不足（連接失敗），禁止發射」。
        -   「規則 2：主引擎噴嘴脫落（關鍵表缺失），禁止發射」。
        -   「規則 3：如果是載人任務（嚴格模式），任何一個儀表讀數不在綠色區域內，都禁止發射」。
    -   只有當所有關鍵規則都滿足時，主管才會按下那個允許發射的按鈕（返回 `True`）。

---

## 🧩 樣板 2：有哪些類別，以及創建目的與結構特性

【類別分析】
- 類別名稱：`StartupHealthChecker`
  - 📌 **創建目的**: **將「獲取健康資訊」的職責與「根據資訊做出決策」的職責分離開來**。`DatabaseHealthChecker` 只負責客觀地提供報告，而 `StartupHealthChecker` 則負責主觀地、帶有策略性地去解讀這份報告。這種分離使得兩者的職責都非常單一。
  - 🧩 **內含哪些關鍵方法與邏輯功能**:
    - `__init__()`: 接收 `database_url` 和一個 `strict_mode` 旗標。`strict_mode` 的設計非常實用，它允許在開發環境中容忍一些非關鍵的警告，但在生產環境中採取最嚴格的標準。
    - `verify_startup_requirements()`: **公開的入口點**，協調整個檢查、記錄和評估的流程。
    - `_log_health_report()` & `_log_verification_report()`: 將結構化的報告資料轉化為人類可讀的日誌。
    - `_evaluate_startup_safety()`: **決策邏輯的核心**。包含了關於哪些問題是「致命的」的業務規則。
  - 💡 **設計考量**:
    - **策略與機制分離**: `DatabaseHealthChecker` 是「機制」（提供資訊），`StartupHealthChecker` 是「策略」（做出決策）。這是非常健康的軟體設計模式。
    - **可配置的嚴格性**: `strict_mode` 參數使得該檢查器可以靈活地適應不同的部署環境。
    - **清晰的日誌**: 即使檢查失敗，它也會產生非常清晰的日誌，準確地告訴開發者是哪個環節的哪個規則導致了啟動失敗，極大地簡化了問題排查。

---

## 🧱 額外架構師視角建議補充欄位

- 🗂️ **高耦合風險**：**低**。它只依賴於 `DatabaseHealthChecker` 的公開介面（`comprehensive_health_check`），與其內部實現解耦。
- 🧪 **可測試性**：**極高**。
    -   可以輕易地 Mock `DatabaseHealthChecker`。
    -   在測試中，可以精心構造各種不同的 `health_report` 字典（例如，一個模擬連接失敗的報告，一個模擬缺少關鍵表的報告等）。
    -   將這些 Mock 報告餵給 `_evaluate_startup_safety` 方法，然後斷言其返回值是否符合預期。這使得對所有複雜的決策分支進行測試變得非常簡單。
- 🧠 **設計優點**:
  - **職責分離**：策略與機制分離的設計是其最大的優點。
  - **快速失敗**：在應用程式啟動早期就發現並報告問題，避免了將問題延遲到運行時才被使用者發現。
  - **可操作的日誌**: 產生的日誌不僅僅是告知「失敗了」，而是告知「為什麼失敗」以及「哪個規則被觸發了」。
- 🧠 **重構潛力**:
  - **策略物件化**: 目前的啟動規則是硬編碼在 `_evaluate_startup_safety` 方法的一系列 `if` 語句中的。對於更複雜的系統，可以將這些規則提取出來，變成一個個的「策略物件」（例如，`ConnectionRequiredPolicy`, `CriticalTablesRequiredPolicy`）。這樣，`StartupHealthChecker` 就可以在初始化時接收一個策略物件列表，並依次執行它們。這將使得新增或修改啟動規則變得更加靈活，而無需修改 `StartupHealthChecker` 本身，更好地遵循了**開放/封閉原則**。 