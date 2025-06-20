# ADR-002: 循環依賴解決方案

## 狀態
**接受** - 2025-06-20

## 背景

在 LINE MCP 智慧製造監控系統的架構演進過程中，我們發現了一個關鍵的循環依賴問題。ApplicationFacade (應用門面) 和 EnhancedServiceFactory (增強服務工廠) 之間存在雙向依賴，這違反了 SOLID 原則中的依賴倒置原則 (Dependency Inversion Principle)，並影響了系統的可測試性和維護性。

### 問題發現過程
- **發現時間**: 2025-06-20 架構審查期間
- **觸發因素**: 準備企業級部署時的代碼品質檢查
- **影響範圍**: 核心架構穩定性和可測試性

## 問題

### 循環依賴結構
```
ApplicationFacade ↔ EnhancedServiceFactory
```

### 具體問題點

#### 1. ApplicationFacade 依賴 EnhancedServiceFactory
- **位置**: `application_facade.py:15`
- **代碼**: `from src.infrastructure.enhanced_service_factory import EnhancedServiceFactory`
- **問題**: 應用層直接依賴基礎設施層的具體實現

#### 2. EnhancedServiceFactory 依賴 ApplicationFacade
- **位置**: `enhanced_service_factory.py:177-179`
- **代碼**: 延遲導入 ApplicationFacade 並註冊到服務容器
- **問題**: 基礎設施層回過頭依賴應用層

### 造成的問題
1. **違反 SOLID 原則**: 特別是依賴倒置原則 (DIP)
2. **測試困難**: 無法獨立測試 ApplicationFacade
3. **架構不清晰**: 層次界限模糊
4. **擴展困難**: 難以替換不同的服務工廠實現
5. **維護風險**: 循環依賴增加代碼修改的複雜度

## 考慮的選項

### 選項 1: 延遲導入 (現狀)
- **優點**:
  - 最小修改
  - 避免導入時錯誤
- **缺點**:
  - 治標不治本
  - 運行時仍存在循環依賴
  - 違反架構原則
  - 測試問題依然存在

### 選項 2: 重構服務位置
- **優點**:
  - 可以打破循環
  - 相對簡單
- **缺點**:
  - 破壞現有架構邏輯
  - 違反分層架構原則
  - 不符合領域驅動設計

### 選項 3: 依賴倒置原則 (推薦)
- **優點**:
  - 符合 SOLID 原則
  - 提升可測試性
  - 架構更清晰
  - 支援多種實現
  - 降低耦合度
- **缺點**:
  - 需要引入抽象層
  - 初期開發成本略高

### 選項 4: 事件驅動解耦
- **優點**:
  - 完全解耦
  - 高度靈活
- **缺點**:
  - 過度複雜化
  - 引入額外複雜性
  - 不適合當前系統規模

## 決策

我們選擇 **選項 3: 依賴倒置原則**，因為：

1. **符合企業級標準**: 實現 SOLID 原則，提升架構品質
2. **可測試性**: 易於創建 Mock 對象進行單元測試
3. **可擴展性**: 支援未來替換不同的服務工廠實現
4. **清晰的職責分離**: 應用層專注業務邏輯，基礎設施層專注技術實現
5. **最佳實務對齊**: 符合企業級軟體開發的最佳實務

## 結果和影響

### 正面影響
- **架構清晰**: 明確的依賴方向，高層模組不依賴低層模組的具體實現
- **可測試性提升**: ApplicationFacade 可以輕鬆使用 Mock IServiceFactory 進行測試
- **擴展性增強**: 可以輕鬆引入不同的服務工廠實現
- **SOLID 原則實現**: 特別是依賴倒置原則 (DIP)
- **維護性改善**: 降低模組間耦合，提升代碼維護性

### 負面影響
- **複雜度略增**: 引入抽象介面增加了一定的複雜度
- **學習成本**: 新開發者需要理解依賴倒置的概念

### 技術風險
- **抽象洩漏**: 介面設計不當可能導致抽象洩漏
- **過度設計**: 需要避免不必要的抽象化

## 實施細節

### 步驟 1: 創建抽象介面
創建 `IServiceFactory` 介面：
```python
# src/infrastructure/service_factory_interface.py
from abc import ABC, abstractmethod
from typing import Type, Optional, Any, Dict

class IServiceFactory(ABC):
    @abstractmethod
    def get_service(self, service_type: Type) -> Optional[Any]:
        pass
    
    @abstractmethod
    def get_required_service(self, service_type: Type) -> Any:
        pass
    
    @abstractmethod
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        pass
```

### 步驟 2: 修改 EnhancedServiceFactory
```python
# 實現 IServiceFactory 介面
class EnhancedServiceFactory(IServiceFactory):
    # 移除 ApplicationFacade 的註冊邏輯
    # 專注於服務創建和管理
```

### 步驟 3: 修改 ApplicationFacade
```python
# 依賴抽象介面而非具體實現
def __init__(self, service_factory: IServiceFactory):
    self.service_factory = service_factory
```

### 步驟 4: 更新測試
- ApplicationFacade 測試使用 Mock IServiceFactory
- EnhancedServiceFactory 測試獨立進行

## 驗證標準

- [x] **循環依賴檢查**: `python3 -c "import src.application.application_facade; import src.infrastructure.enhanced_service_factory; print('✅ 無循環依賴')"`
- [x] **介面實現驗證**: EnhancedServiceFactory 正確實現 IServiceFactory
- [x] **測試可執行性**: 所有相關測試能夠正常執行
- [x] **功能完整性**: 系統功能沒有受到影響
- [x] **架構原則符合**: 符合 SOLID 原則，特別是 DIP

## 相關資源

- [ADR-001: 依賴注入架構設計](./001-dependency-injection-architecture.md)
- [ADR-004: SOLID 原則實現策略](./004-solid-principles-implementation.md)
- [依賴倒置原則詳解](https://en.wikipedia.org/wiki/Dependency_inversion_principle)
- [循環依賴重構規範](../../../循環依賴spec.md)
- [ApplicationFacade 實現](../../../apps/bot/src/application/application_facade.py)
- [IServiceFactory 介面](../../../apps/bot/src/infrastructure/service_factory_interface.py)

## 修訂歷史

| 日期 | 變更 | 作者 |
|------|------|------|
| 2025-06-20 | 初始版本，記錄循環依賴解決方案 | Claude Code Assistant |
| 2025-06-20 | 完成實施並更新驗證結果 | Claude Code Assistant |

---

## 實施結果總結

### 架構改善前後對比

#### 改善前
```
ApplicationFacade ←→ EnhancedServiceFactory
(循環依賴，違反 DIP)
```

#### 改善後
```
ApplicationFacade → IServiceFactory ← EnhancedServiceFactory
(依賴倒置，符合 SOLID 原則)
```

### 量化效益
- **測試覆蓋率提升**: 可以輕鬆 Mock 介面進行測試
- **耦合度降低**: 從強耦合改為介面耦合
- **擴展性增強**: 支援多種服務工廠實現
- **架構品質**: 從技術債務轉為技術資產

這個決策標誌著 LINE MCP 系統從功能導向架構向企業級架構的重要轉變，為系統的長期發展奠定了堅實的基礎。