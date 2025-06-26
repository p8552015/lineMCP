# 檔案分析報告：`apps/bot/src/services/nl_to_sql/interfaces/statistics_interfaces.py`

## 1. 檔案目的與角色

此檔案是 NL-to-SQL 新 SOLID 架構中，負責定義所有**橫切關注點 (Cross-Cutting Concerns)** 的**契約定義中心**。它的核心職責是將系統的**可觀測性 (Observability)** 和 **可配置性 (Configurability)** 相關的功能，透過一系列抽象介面，從核心的業務邏輯中完全分離出來。

它在架構中的核心角色是：
1.  **定義契約**: 為統計、指標、設定和日誌這四個關鍵的橫切功能提供了清晰、獨立的抽象介面。
2.  **實現關注點分離**: 確保業務邏輯的開發者可以專注於實現功能，而無需關心這些功能是如何被監控、測量或設定的。
3.  **提供可插拔性**: 允許底層的實現可以被輕易替換。例如，指標收集的實現可以從簡單的日誌輸出切換到專業的監控系統（如 Prometheus），而無需修改任何業務程式碼。

這個檔案為建立一個健壯、可維護、易於在生產環境中管理的系統奠定了基礎。

## 2. 主要類別/函數定義

此檔案定義了四個精細劃分的抽象基底類別 (Interface)。

### `class IStatistics(ABC)`
*   **職責**: 一個**高層級、面向業務**的統計介面。它用於記錄具有業務意義的事件，如「解析成功」或「快取命中」。
*   **核心方法**:
    *   `record_event(event_type: StatisticsEventType, ...)`: 記錄一個預定義的業務事件。
    *   `record_success(...)` 和 `record_failure(...)`: 專門用於記錄一次操作的成功或失敗及其上下文。
    *   `get_summary_stats()`: 提供業務層面的統計摘要，如成功率。

### `class IConfiguration(ABC)`
*   **職責**: **集中式的配置管理**介面。它負責提供系統運行所需的所有配置項，並將配置的來源（檔案、環境變數等）與使用者解耦。
*   **核心方法**:
    *   `get_config_value(key: str, ...)`: 獲取單個配置項。
    *   `get_sql_templates()` 和 `get_parser_settings()`: 提供了獲取特定領域配置的便利方法。
    *   `reload_config()`: 支援**配置熱重載**，這是一個非常強大的特性，允許在不重啟服務的情況下改變系統行為。

### `class IMetricsCollector(ABC)`
*   **職責**: 一個**低層級、通用**的指標收集介面，與具體的業務無關。它對應於業界標準的監控原語。
*   **核心方法**:
    *   `increment_counter(...)`: 增加一個計數器，用於記錄發生次數。
    *   `record_gauge(...)`: 記錄一個瞬時值（如佇列長度）。
    *   `record_histogram(...)`: 記錄一個值的分布情況（如請求延遲）。
    *   `start_timer()` / `stop_timer()`: 提供了方便的程式碼段計時功能。

### `class ILogger(ABC)`
*   **職責**: 一個標準的**日誌記錄器**介面，旨在將應用程式與任何特定的日誌庫實現解耦。
*   **核心方法**: `debug`, `info`, `warning`, `error`, `critical`，提供了不同嚴重性級別的日誌記錄方法。

## 3. 功能實現的簡要描述

這個檔案描繪了一個分層、解耦的可觀測性架構：

1.  **分層的度量**: `IMetricsCollector` 作為底層基礎設施，負責收集原始的度量數據。而 `IStatistics` 作為上層建築，可能會在內部使用 `IMetricsCollector` 來實現其業務統計功能。例如，一次 `IStatistics.record_success` 的呼叫，可能會觸發 `IMetricsCollector.increment_counter` (成功次數+1) 和 `IMetricsCollector.record_histogram` (記錄本次耗時)。
2.  **配置即服務**: 任何需要配置的元件（如 `IParser` 或 `IQueryBuilder` 的實作）都將從 `IConfiguration` 的實作中獲取配置，而不是自行讀取檔案。
3.  **統一的日誌介面**: 所有元件都透過 `ILogger` 介面來寫日誌，使得整個系統的日誌風格和格式可以被統一控制。

## 4. 依賴關係

*   **`abc.ABC`, `abc.abstractmethod`**: 依賴 Python 的標準抽象基底類別工具。
*   **`enum.Enum`**: 用於定義 `StatisticsEventType` 枚舉，增加了程式碼的可讀性和類型安全性。

## 5. 設計模式與架構決策

*   **介面隔離原則 (ISP)**: 這是此檔案設計的核心。四個介面職責清晰，互不干擾。
*   **策略模式 (Strategy Pattern)**: 每個介面都允許多種實現策略。例如，`IMetricsCollector` 可以有 `PrometheusMetricsCollector` 或 `LoggingMetricsCollector` 等不同實現。`IConfiguration` 可以有 `FileConfiguration` 或 `EnvironmentConfiguration` 等實現。
*   **外觀模式 (Facade Pattern)** 的應用: `IStatistics` 可以看作是 `IMetricsCollector` 的一個簡化外觀，為使用者提供了更簡單、更貼近業務的介面。
*   **可觀測性設計 (Design for Observability)**: 將指標、日誌、統計作為一等公民，並為其設計專門的、解耦的介面，是構建可在生產環境中可靠運行的系統的關鍵架構決策。
*   **可配置性與熱重載**: 支援配置熱重載的決定，極大提升了系統的靈活性和可維護性。

## 6. 潛在的改進點

*   **介面的複雜度**: 對於一個小型專案，這四個介面可能顯得過於繁重。但對於目標系統來說，這種精細的劃分是其健壯性和可維護性的保證。
*   **上下文傳遞**: 在 `ILogger` 和 `IMetricsCollector` 中，可以考慮增加一個統一的 `context` 參數，用於傳遞請求 ID、使用者 ID 等上下文資訊，以便在日誌和指標中進行關聯分析。不過，目前的 `extra` 和 `tags` 參數已經提供了類似的功能。 