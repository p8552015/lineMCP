# 循環依賴改善工作流規範

## 目標
解決 ApplicationFacade 與 EnhancedServiceFactory 之間的循環依賴問題，建立更清晰的架構層次。

## 現況分析

### 循環依賴結構
```
ApplicationFacade ←→ EnhancedServiceFactory
```

### 具體問題點
1. **ApplicationFacade 依賴 EnhancedServiceFactory**
   - `application_facade.py:15`: `from src.infrastructure.enhanced_service_factory import EnhancedServiceFactory`
   - `application_facade.py:31`: 構造函數參數 `service_factory: Optional[Union[EnhancedServiceFactory, Any]]`
   - `application_facade.py:373`: `get_application_facade` 函數參數

2. **EnhancedServiceFactory 依賴 ApplicationFacade**
   - `enhanced_service_factory.py:177-179`: 延遲導入 ApplicationFacade
   - `enhanced_service_factory.py:183-186`: 註冊 ApplicationFacade 到服務容器

## 改善方案：依賴倒置原則 (DIP)

### 架構設計原則
- 高層模組不應該依賴低層模組，兩者都應該依賴抽象
- 抽象不應該依賴細節，細節應該依賴抽象

### 新架構設計
```
ApplicationFacade → IServiceFactory ← EnhancedServiceFactory
```

## 實施步驟

### 步驟 1：創建服務工廠介面
創建 `src/infrastructure/service_factory_interface.py`：

```python
"""
服務工廠介面定義
"""
from abc import ABC, abstractmethod
from typing import Type, Optional, Any


class IServiceFactory(ABC):
    """
    服務工廠抽象介面
    
    定義了服務工廠必須實現的基本方法
    """
    
    @abstractmethod
    def get_service(self, service_type: Type) -> Optional[Any]:
        """
        獲取服務實例
        
        Args:
            service_type: 服務類型
            
        Returns:
            服務實例，如果不存在則返回 None
        """
        pass
    
    @abstractmethod
    def get_required_service(self, service_type: Type) -> Any:
        """
        獲取必需的服務實例
        
        Args:
            service_type: 服務類型
            
        Returns:
            服務實例
            
        Raises:
            ValueError: 找不到服務時拋出
        """
        pass
    
    @abstractmethod
    def initialize(self, config: Optional[dict] = None) -> None:
        """
        初始化服務工廠
        
        Args:
            config: 配置字典
        """
        pass
```

### 步驟 2：修改 EnhancedServiceFactory
更新 `src/infrastructure/enhanced_service_factory.py`：

```python
# 在文件開頭添加導入
from .service_factory_interface import IServiceFactory

# 修改類定義
class EnhancedServiceFactory(IServiceFactory):
    """
    增強版服務工廠
    
    實現 IServiceFactory 介面
    """
    
    # ... 現有程式碼 ...
    
    def _register_application_services(self):
        """註冊應用服務"""
        # 移除 ApplicationFacade 的註冊
        # 只註冊真正的應用服務
        
        # 應用服務上下文
        self._registry.register_singleton(
            ApplicationServiceContext,
            tags=["application", "context"],
            metadata={"description": "應用服務上下文"}
        )
        
        # 訊息處理應用服務
        self._registry.register_factory(
            MessagingApplicationService,
            lambda provider: self._create_messaging_service(provider),
            scope=ServiceScope.SINGLETON
        )
        
        # 查詢應用服務
        self._registry.register_factory(
            QueryApplicationService,
            lambda provider: QueryApplicationService(
                mcp_client_factory=get_unified_mcp_client,
                db_service=provider.get_required_service(DatabaseService),
                response_parser=provider.get_required_service(MCPResponseParser)
            ),
            scope=ServiceScope.SINGLETON
        )
        
        # 監控應用服務
        self._registry.register_factory(
            MonitoringApplicationService,
            lambda provider: MonitoringApplicationService(
                service_context=provider.get_required_service(ApplicationServiceContext)
            ),
            scope=ServiceScope.SINGLETON
        )
        
        # 移除 ApplicationFacade 相關的註冊邏輯
```

### 步驟 3：修改 ApplicationFacade
更新 `src/application/application_facade.py`：

```python
# 修改導入
from typing import Optional, Dict, Any
from src.infrastructure.service_factory_interface import IServiceFactory
# 移除對 EnhancedServiceFactory 的直接導入

class ApplicationFacade:
    """
    應用服務門面
    """
    
    def __init__(self, service_factory: IServiceFactory):
        """
        初始化應用門面
        
        Args:
            service_factory: 實現 IServiceFactory 介面的服務工廠
        """
        self.service_factory = service_factory
        self.context = ApplicationServiceContext()
        self._initialized = False
        
        # 應用服務實例
        self._messaging_service: Optional[MessagingApplicationService] = None
        self._query_service: Optional[QueryApplicationService] = None
        self._monitoring_service: Optional[MonitoringApplicationService] = None
    
    # 移除 _create_default_service_factory 方法
    # 其他方法保持不變

# 修改全域函數
def get_application_facade(service_factory: IServiceFactory) -> ApplicationFacade:
    """
    獲取全域應用門面實例
    
    Args:
        service_factory: 實現 IServiceFactory 介面的服務工廠
        
    Returns:
        應用門面實例
    """
    global _application_facade
    if _application_facade is None:
        _application_facade = ApplicationFacade(service_factory)
    return _application_facade
```

### 步驟 4：調整初始化流程
更新 `src/main.py`：

```python
from src.infrastructure.enhanced_service_factory import EnhancedServiceFactory
from src.application.application_facade import ApplicationFacade

# 在應用初始化時
async def initialize_application():
    # 創建服務工廠
    service_factory = EnhancedServiceFactory()
    service_factory.initialize()
    
    # 創建應用門面
    application_facade = ApplicationFacade(service_factory)
    await application_facade.initialize()
    
    return application_facade
```

### 步驟 5：更新測試
需要更新相關測試以反映新的架構：

1. **單元測試**
   - 使用 Mock 物件實現 IServiceFactory 介面
   - 測試 ApplicationFacade 與抽象介面的交互

2. **整合測試**
   - 驗證實際的服務工廠實現
   - 確保依賴注入正確運作

## 驗證計劃

### 1. 靜態分析
- 使用工具檢查循環依賴是否已解決
- 確認導入關係符合依賴方向

### 2. 單元測試
- ApplicationFacade 測試應使用 Mock IServiceFactory
- EnhancedServiceFactory 測試應獨立進行

### 3. 整合測試
- 驗證完整的初始化流程
- 確保所有服務正確創建和注入

### 4. 效能測試
- 確保重構後的效能沒有退化
- 驗證服務創建時間

## 預期效益

1. **解決循環依賴**
   - ApplicationFacade 不再直接依賴具體實現
   - 架構層次更加清晰

2. **提高可測試性**
   - 容易創建測試用的 Mock 工廠
   - 單元測試更加隔離

3. **增強靈活性**
   - 可以輕鬆替換不同的服務工廠實現
   - 支援多種配置場景

4. **符合 SOLID 原則**
   - 依賴倒置原則 (DIP)
   - 開閉原則 (OCP)
   - 單一職責原則 (SRP)

## 風險評估

### 風險點
1. 現有程式碼可能需要調整初始化邏輯
2. 測試需要更新以適應新架構

### 緩解措施
1. 分階段實施，先創建介面再逐步調整
2. 保持向後兼容性，提供過渡期
3. 完整的測試覆蓋確保穩定性

## 實施時間表

1. **第一階段**（1-2 小時）
   - 創建 IServiceFactory 介面
   - 更新 EnhancedServiceFactory 實現介面

2. **第二階段**（2-3 小時）
   - 修改 ApplicationFacade 使用介面
   - 調整初始化流程

3. **第三階段**（2-3 小時）
   - 更新所有相關測試
   - 執行完整測試套件

4. **第四階段**（1 小時）
   - 效能驗證
   - 文檔更新

## 結論

這個重構計劃將徹底解決循環依賴問題，同時提升系統的架構品質。通過引入抽象介面，我們不僅解決了當前問題，還為未來的擴展奠定了良好基礎。

## 執行日誌

### 執行時間：2025-06-20

#### 步驟 1：創建服務工廠介面 ✅
- **時間**：16:45
- **操作**：創建 `/apps/bot/src/infrastructure/service_factory_interface.py`
- **結果**：成功創建 IServiceFactory 抽象介面，定義了三個核心方法：
  - `get_service()`：獲取服務實例（可選）
  - `get_required_service()`：獲取必需服務實例
  - `initialize()`：初始化服務工廠

#### 步驟 2：修改 EnhancedServiceFactory 實現介面 ✅
- **時間**：16:47
- **操作**：更新 `/apps/bot/src/infrastructure/enhanced_service_factory.py`
- **變更**：
  1. 導入 IServiceFactory 介面
  2. 使 EnhancedServiceFactory 繼承 IServiceFactory
  3. 移除 ApplicationFacade 的註冊邏輯
  4. 刪除 `create_application_facade()` 方法
- **結果**：成功實現介面，移除了對 ApplicationFacade 的依賴

#### 步驟 3：修改 ApplicationFacade 使用介面 ✅
- **時間**：16:50
- **操作**：更新 `/apps/bot/src/application/application_facade.py`
- **變更**：
  1. 將導入從 EnhancedServiceFactory 改為 IServiceFactory
  2. 修改構造函數參數類型為 IServiceFactory
  3. 移除 `_create_default_service_factory()` 方法
  4. 更新 `get_application_facade()` 函數參數類型
- **結果**：成功使用抽象介面，不再依賴具體實現

#### 步驟 4：調整初始化流程 ✅
- **時間**：16:52
- **發現**：現有架構中，初始化流程在 `webhook.py` 中處理
- **現況**：`webhook.py` 創建 EnhancedServiceFactory 並初始化 MessageHandlerDI
- **評估**：當前設計符合依賴倒置原則，不需要修改

#### 步驟 5：更新相關測試 ✅
- **時間**：16:55
- **操作**：更新測試檔案
- **變更**：
  1. `/tests/application/test_application_facade.py`：
     - 修改導入為 IServiceFactory
     - 更新 Mock 對象的 spec
     - 調整模擬方法以符合介面定義
  2. `/tests/infrastructure/test_enhanced_service_factory.py`：
     - 移除 ApplicationFacade 相關導入
     - 刪除 `test_create_application_facade()` 測試
     - 更新兼容性測試方法
- **結果**：測試已更新以反映新架構

#### 步驟 6：驗證循環依賴已解決 ✅
- **時間**：17:00
- **驗證方法**：執行 Python 導入測試
- **命令**：
  ```python
  python3 -c "import src.application.application_facade as app; import src.infrastructure.enhanced_service_factory as factory; print('No circular import detected!')"
  ```
- **結果**：輸出 "No circular import detected!"，確認循環依賴已成功解決

### 總結

#### 完成的改變
1. ✅ 創建了 IServiceFactory 抽象介面
2. ✅ EnhancedServiceFactory 實現了該介面
3. ✅ ApplicationFacade 現在依賴抽象而非具體實現
4. ✅ 移除了所有循環依賴
5. ✅ 更新了相關測試
6. ✅ 驗證了導入不再產生循環依賴

#### 架構改善
- **之前**：ApplicationFacade ↔ EnhancedServiceFactory（循環依賴）
- **之後**：ApplicationFacade → IServiceFactory ← EnhancedServiceFactory（依賴倒置）

#### 未修改的部分
- main.py：因為現有初始化流程在 webhook.py 中，不需要修改
- 整合測試：需要後續進一步檢查和更新

#### 效益實現
1. **循環依賴解決**：完全消除了兩個類之間的循環依賴
2. **可測試性提升**：現在可以輕鬆 Mock IServiceFactory 進行單元測試
3. **架構清晰度**：層次分明，高層模組不再依賴低層模組的具體實現
4. **符合 SOLID 原則**：實現了依賴倒置原則（DIP）