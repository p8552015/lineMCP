### FILE REPORT: apps/bot/src/infrastructure/service_registry.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：378 ❌ High LOC
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | ServiceScope | 以列舉 (Enum) 形式定義服務的三種生命週期：單例、瞬態和作用域。 | — | — | | |
  | ServiceDescriptor | 以資料類別 (dataclass) 形式標準化地表示一條服務註冊資訊，包含其類型、實現和元數據。 | — | — | | |
  | IServiceProvider | 作為一個抽象基底類 (ABC)，定義了服務提供者必須遵循的契約 (interface)。 | — | — | | |
  | ServiceRegistry | 作為一個依賴注入(DI)容器，負責管理所有服務的註冊資訊和生命週期。 | — | — | | 2+ | `enhanced_service_factory.py`, self-module
  | | | register | 核心的註冊方法，允許註冊服務的類型、實現和生命週期。 | | |
  | | | unregister | 從註冊表中移除一個服務。 | ❌ | 0 |
  | | | has_service | 檢查一個服務是否已被註冊。 | ❌ | 0 |
  | | | get_services_by_tag | 根據標籤查找所有匹配的服務。 | | |
  | | | create_provider | 根據當前的註冊資訊創建一個服務提供者實例。 | | |
  | ServiceProvider | 負責根據註冊表解析和創建服務實例，並自動注入依賴。 | — | — | | 2+ | `enhanced_service_factory.py`, self-module
  | | | get_service | 獲取一個服務實例，是 DI 運作的核心。 | | |
  | | | _resolve_service | 根據服務的生命週期（單例、作用域、瞬態）解析服務實例。 | | |
  | | | _create_instance | 實際創建服務實例，並觸發自動依賴注入。 | | |
  | | | _auto_wire | 透過反射 (inspect) 機制分析服務的構造函數，並遞迴地解析和注入其所需的依賴項。 | | |
  | **Function** | **Purpose** | | | | |
  | get_service_registry | 以單例模式提供 `ServiceRegistry` 的全域實例。 | | | | 1+ | `enhanced_service_factory.py`
  | get_service_provider | 提供一個便利的函數來從全域註冊表創建一個服務提供者。 | ❌ | 0 |

- **注意**: 此檔案行數較多 (378 LOC)。`unregister` 和 `has_service` 等方法提供了完整的註冊表管理能力，但目前未被使用。
