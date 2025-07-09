### FILE REPORT: apps/bot/src/infrastructure/service_factory_interface.py
- 檔案狀態：<REFERENCED>
- 檔案 LOC：39
- 類別╱方法一覽
  | 類別 | Purpose | 方法 | Usage | 未使用 |引用次數| 引用文件
  |------|---------|------|-------|--------|---|---
  | IServiceFactory | 作為一個抽象基底類 (ABC)，定義了所有服務工廠必須遵循的契約 (interface)，是實現依賴倒置原則的關鍵。 | — | — | | 2 | `application/application_facade.py`, `infrastructure/enhanced_service_factory.py`
  | | | get_service | 抽象方法，定義了獲取可選服務的簽名。 | | |
  | | | get_required_service | 抽象方法，定義了獲取必要服務的簽名。 | | |
  | | | initialize | 抽象方法，定義了服務工廠初始化流程的簽名。 | | |
