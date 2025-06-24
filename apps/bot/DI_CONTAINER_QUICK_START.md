# Enhanced Service Factory 快速上手指南

## 🚀 5 分鐘快速入門

### 什麼是 Enhanced Service Factory？

Enhanced Service Factory 是我們的依賴注入 (DI) 容器，用於管理系統中所有服務的創建和生命週期。

```python
# 簡單來說：不要這樣寫
ai_service = AIModelService()
db_service = DatabaseService()
handler = MessageHandler(ai_service, db_service)  # 手動管理依賴

# 而是這樣寫
service_factory = get_enhanced_service_factory()
handler = service_factory.get_required_service(MessageHandlerDI)  # 自動注入
```

### 核心概念

1. **服務工廠** - 創建和管理服務實例
2. **依賴注入** - 自動提供服務所需的依賴
3. **生命週期** - 控制服務是單例還是每次新建
4. **服務註冊** - 告訴工廠如何創建服務

## 📖 基礎使用

### 1. 獲取服務工廠

```python
from src.infrastructure.enhanced_service_factory import get_enhanced_service_factory

# 獲取全域服務工廠實例
service_factory = get_enhanced_service_factory()
service_factory.initialize()  # 初始化所有服務
```

### 2. 獲取服務實例

```python
# 獲取必需的服務（如果不存在會拋出異常）
ai_service = service_factory.get_required_service(AIModelService)

# 獲取可選的服務（如果不存在返回 None）
optional_service = service_factory.get_service(SomeOptionalService)

# 使用便利方法
nl_service = service_factory.get_nl_service()
db_service = service_factory.get_database_service()
```

### 3. 在類中使用依賴注入

```python
class MyApplicationService:
    def __init__(self, service_factory: IServiceFactory):
        self._service_factory = service_factory
        # 延遲初始化依賴
        self._ai_service = None
        self._db_service = None
    
    def initialize(self):
        # 在需要時初始化依賴
        self._ai_service = self._service_factory.get_required_service(AIModelService)
        self._db_service = self._service_factory.get_required_service(DatabaseService)
    
    async def process_query(self, query: str):
        # 使用注入的服務
        result = await self._ai_service.generate_response(query)
        await self._db_service.save_result(result)
        return result
```

## 🏗️ 進階使用

### 1. 添加新服務

當你需要添加新服務時，選擇適當的註冊器：

#### Core Services (核心服務)
```python
# 在 src/infrastructure/core_services_registry.py
def register_core_services(registry: ServiceRegistry):
    # AI、消息處理等核心服務
    registry.register_singleton(MyNewCoreService, MyNewCoreService)
```

#### Application Services (應用服務)
```python
# 在 src/infrastructure/application_services_registry.py
def register_application_services(registry: ServiceRegistry):
    # 業務邏輯相關的應用服務
    registry.register_singleton(MyBusinessService, MyBusinessService)
```

#### Infrastructure Services (基礎設施服務)
```python
# 在 src/infrastructure/infrastructure_services_registry.py
def register_infrastructure_services(registry: ServiceRegistry):
    # 資料庫、檔案系統等基礎設施服務
    registry.register_transient(MyInfraService, MyInfraService)
```

### 2. 服務生命週期

```python
# Singleton - 全域共享一個實例
registry.register_singleton(DatabaseService, DatabaseService)

# Transient - 每次獲取都創建新實例
registry.register_transient(MessageHandlerDI, MessageHandlerDI)

# 帶工廠函數的註冊
registry.register_singleton(
    ComplexService,
    lambda provider: ComplexService(
        config=provider.get_service(ConfigService),
        logger=get_logger("complex")
    )
)
```

### 3. 服務標籤

```python
# 註冊時添加標籤
registry.register_singleton(
    QueryStatisticsService,
    QueryStatisticsService,
    tags=["statistics", "monitoring", "nl-to-sql"]
)

# 根據標籤查詢服務
monitoring_services = registry.get_services_by_tag("monitoring")
```

## 🧪 測試指南

### 1. 單元測試中的 Mock

```python
import pytest
from unittest.mock import Mock
from src.infrastructure.service_factory_interface import IServiceFactory

class MockServiceFactory(IServiceFactory):
    def __init__(self):
        self._services = {}
    
    def register_mock(self, service_type, mock_instance):
        self._services[service_type] = mock_instance
    
    def get_service(self, service_type):
        return self._services.get(service_type)
    
    def get_required_service(self, service_type):
        service = self.get_service(service_type)
        if service is None:
            raise ValueError(f"Service {service_type} not found")
        return service

@pytest.fixture
def mock_service_factory():
    factory = MockServiceFactory()
    
    # 註冊常用的 Mock 服務
    factory.register_mock(AIModelService, Mock())
    factory.register_mock(DatabaseService, Mock())
    
    return factory

def test_my_service(mock_service_factory):
    # 使用 Mock 服務工廠進行測試
    service = MyService(mock_service_factory)
    service.initialize()
    
    # 測試邏輯
    result = service.do_something()
    assert result is not None
```

### 2. 整合測試

```python
def test_real_services():
    # 使用真實的服務工廠進行整合測試
    service_factory = get_enhanced_service_factory()
    service_factory.initialize()
    
    # 測試服務間的真實交互
    facade = ApplicationFacade(service_factory)
    await facade.initialize()
    
    result = await facade.process_message("test", "測試查詢", "token")
    assert result is not None
```

## 🔧 故障排除

### 常見錯誤與解決方案

#### 1. `ValueError: Service XXX not found`

**原因**: 服務未註冊或註冊器未載入

**解決方案**:
```python
# 檢查服務是否已註冊
factory = get_enhanced_service_factory()
registry_info = factory.get_registry_info()
print("已註冊的服務:", registry_info["service_types"])

# 確保初始化已完成
factory.initialize()
```

#### 2. 循環依賴錯誤

**原因**: 服務 A 依賴服務 B，服務 B 又依賴服務 A

**解決方案**:
```python
# 使用延遲初始化
class ServiceA:
    def __init__(self, service_factory: IServiceFactory):
        self._service_factory = service_factory
        self._service_b = None  # 延遲初始化
    
    def get_service_b(self):
        if self._service_b is None:
            self._service_b = self._service_factory.get_required_service(ServiceB)
        return self._service_b
```

#### 3. 服務初始化失敗

**原因**: 服務依賴的資源不可用

**解決方案**:
```python
# 檢查服務健康狀況
health_status = factory.get_health_status()
print("服務工廠健康狀況:", health_status)

# 檢查個別服務
try:
    service = factory.get_required_service(ProblematicService)
except Exception as e:
    print(f"服務初始化失敗: {e}")
```

### 調試技巧

```python
# 1. 啟用詳細日誌
import logging
logging.getLogger().setLevel(logging.DEBUG)

# 2. 檢查服務註冊情況
factory = get_enhanced_service_factory()
summary = factory.get_registry_info()
print(f"總共註冊了 {summary['total_services']} 個服務")

# 3. 按作用域查看服務
for scope, count in summary["by_scope"].items():
    print(f"{scope}: {count} 個服務")

# 4. 按標籤查看服務
for tag, count in summary["by_tag"].items():
    print(f"標籤 '{tag}': {count} 個服務")
```

## 📚 常用服務參考

### AI 和 NL-to-SQL 相關

```python
# AI 模型服務
ai_service = factory.get_ai_model_service()

# 自然語言轉 SQL
nl_service = factory.get_nl_service()

# 解析器
rule_parser = factory.get_rule_parser()
ai_parser = factory.get_ai_parser()
composite_parser = factory.get_composite_parser()

# 查詢建構器
query_builder = factory.get_query_builder()

# 統計服務
stats_service = factory.get_statistics_service()
```

### 資料庫和消息相關

```python
# 資料庫服務
db_service = factory.get_database_service()

# 消息處理器
message_handler = factory.create_message_handler()

# 消息格式化器
formatter = factory.get_message_formatter()
```

### 配置和監控相關

```python
# 配置服務
config_service = factory.get_configuration_service()

# 模板管理器
template_manager = factory.get_template_manager()
```

## 🎯 最佳實踐

### 1. 服務設計原則

```python
# ✅ 好的做法：依賴介面而非具體實現
class MyService:
    def __init__(self, service_factory: IServiceFactory):
        self._factory = service_factory

# ❌ 避免：直接依賴具體類
class BadService:
    def __init__(self, concrete_service: ConcreteService):
        self._service = concrete_service
```

### 2. 資源管理

```python
# ✅ 好的做法：適當的資源清理
class ResourceService:
    def __init__(self):
        self._connection = None
    
    async def __aenter__(self):
        self._connection = await create_connection()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._connection:
            await self._connection.close()
```

### 3. 錯誤處理

```python
# ✅ 好的做法：優雅的錯誤處理
class RobustService:
    def __init__(self, service_factory: IServiceFactory):
        self._factory = service_factory
        self._ai_service = None
    
    async def process(self, data):
        try:
            if not self._ai_service:
                self._ai_service = self._factory.get_service(AIModelService)
            
            if not self._ai_service:
                return await self._fallback_process(data)
            
            return await self._ai_service.process(data)
        except Exception as e:
            logger.error("處理失敗，使用備用方案", error=str(e))
            return await self._fallback_process(data)
```

## 🔄 遷移指南

### 從舊服務工廠遷移

```python
# 舊方式
from src.infrastructure.service_factory import ServiceFactory
old_factory = ServiceFactory()
service = old_factory.get_ai_model_service()

# 新方式
from src.infrastructure.enhanced_service_factory import get_enhanced_service_factory
new_factory = get_enhanced_service_factory()
new_factory.initialize()
service = new_factory.get_ai_model_service()
```

### 逐步遷移策略

1. **第一步**: 更新導入和初始化
2. **第二步**: 使用新的服務獲取方法
3. **第三步**: 更新測試以使用 Mock 服務工廠
4. **第四步**: 移除對舊服務工廠的依賴

## 🆘 需要幫助？

### 文檔資源

- [ADR: Enhanced Service Factory](./ADR_ENHANCED_SERVICE_FACTORY.md) - 詳細的架構決策
- [統一配置管理指南](./UNIFIED_CONFIG_GUIDE.md) - 配置管理最佳實踐
- [CLAUDE.md](./CLAUDE.md) - 專案整體開發指南

### 常見場景範例

查看 `tests/infrastructure/test_enhanced_service_factory.py` 中的完整測試範例。

---

**快速上手指南版本**: 1.0  
**最後更新**: 2025-06-23  
**適用版本**: Enhanced Service Factory v2.0+