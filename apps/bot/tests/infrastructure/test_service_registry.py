"""
測試服務註冊表
"""
import pytest
from typing import Protocol
from unittest.mock import Mock

from src.infrastructure.service_registry import (
    ServiceRegistry,
    ServiceProvider,
    ServiceScope,
    ServiceDescriptor,
    get_service_registry
)


# 測試用的介面和實現
class ITestService(Protocol):
    """測試服務介面"""
    def do_something(self) -> str:
        pass


class TestServiceImpl:
    """測試服務實現"""
    def do_something(self) -> str:
        return "test_result"


class DependentService:
    """有依賴的服務"""
    def __init__(self, test_service: ITestService):
        self.test_service = test_service
        
    def get_result(self) -> str:
        return f"dependent_{self.test_service.do_something()}"


class TestServiceRegistry:
    """服務註冊表測試"""
    
    @pytest.fixture
    def registry(self):
        """創建新的註冊表實例"""
        return ServiceRegistry()
    
    def test_register_service(self, registry):
        """測試服務註冊"""
        # 註冊服務
        registry.register(ITestService, TestServiceImpl)
        
        # 驗證註冊成功
        assert registry.has_service(ITestService)
        descriptor = registry.get_descriptor(ITestService)
        assert descriptor is not None
        assert descriptor.service_type == ITestService
        assert descriptor.implementation == TestServiceImpl
        assert descriptor.scope == ServiceScope.SINGLETON
    
    def test_register_with_scope(self, registry):
        """測試不同作用域的註冊"""
        # 註冊單例
        registry.register_singleton(ITestService, TestServiceImpl)
        descriptor = registry.get_descriptor(ITestService)
        assert descriptor.scope == ServiceScope.SINGLETON
        
        # 註冊瞬態
        registry.unregister(ITestService)
        registry.register_transient(ITestService, TestServiceImpl)
        descriptor = registry.get_descriptor(ITestService)
        assert descriptor.scope == ServiceScope.TRANSIENT
        
        # 註冊作用域
        registry.unregister(ITestService)
        registry.register_scoped(ITestService, TestServiceImpl)
        descriptor = registry.get_descriptor(ITestService)
        assert descriptor.scope == ServiceScope.SCOPED
    
    def test_register_with_tags_and_metadata(self, registry):
        """測試帶標籤和元數據的註冊"""
        tags = ["test", "example"]
        metadata = {"version": "1.0", "author": "test"}
        
        registry.register(
            ITestService,
            TestServiceImpl,
            tags=tags,
            metadata=metadata
        )
        
        descriptor = registry.get_descriptor(ITestService)
        assert descriptor.tags == tags
        assert descriptor.metadata == metadata
    
    def test_register_factory(self, registry):
        """測試工廠函數註冊"""
        def factory(provider: ServiceProvider) -> ITestService:
            return TestServiceImpl()
        
        registry.register_factory(ITestService, factory)
        
        descriptor = registry.get_descriptor(ITestService)
        assert callable(descriptor.implementation)
    
    def test_register_instance(self, registry):
        """測試實例註冊"""
        instance = TestServiceImpl()
        registry.register_instance(ITestService, instance)
        
        # 驗證實例被存儲為單例
        assert ITestService in registry._singletons
        assert registry._singletons[ITestService] is instance
    
    def test_unregister_service(self, registry):
        """測試取消註冊"""
        registry.register(ITestService, TestServiceImpl)
        assert registry.has_service(ITestService)
        
        # 取消註冊
        result = registry.unregister(ITestService)
        assert result is True
        assert not registry.has_service(ITestService)
        
        # 再次取消註冊應返回 False
        result = registry.unregister(ITestService)
        assert result is False
    
    def test_get_services_by_tag(self, registry):
        """測試根據標籤獲取服務"""
        # 註冊多個服務
        registry.register(ITestService, TestServiceImpl, tags=["api", "core"])
        registry.register(DependentService, tags=["api", "helper"])
        
        # 根據標籤查詢
        api_services = registry.get_services_by_tag("api")
        assert len(api_services) == 2
        
        core_services = registry.get_services_by_tag("core")
        assert len(core_services) == 1
        assert core_services[0].service_type == ITestService
    
    def test_clear_registry(self, registry):
        """測試清空註冊表"""
        # 註冊一些服務
        registry.register(ITestService, TestServiceImpl)
        registry.register(DependentService)
        
        # 清空
        registry.clear()
        
        # 驗證已清空
        assert not registry.has_service(ITestService)
        assert not registry.has_service(DependentService)
        assert len(registry._descriptors) == 0
        assert len(registry._singletons) == 0


class TestServiceProvider:
    """服務提供者測試"""
    
    @pytest.fixture
    def registry(self):
        """創建並配置註冊表"""
        registry = ServiceRegistry()
        registry.register(ITestService, TestServiceImpl)
        registry.register(DependentService)
        return registry
    
    @pytest.fixture
    def provider(self, registry):
        """創建服務提供者"""
        return ServiceProvider(registry)
    
    def test_get_service(self, provider):
        """測試獲取服務"""
        service = provider.get_service(ITestService)
        assert service is not None
        assert isinstance(service, TestServiceImpl)
        assert service.do_something() == "test_result"
    
    def test_get_required_service(self, provider):
        """測試獲取必需的服務"""
        service = provider.get_required_service(ITestService)
        assert isinstance(service, TestServiceImpl)
        
        # 測試找不到服務時拋出異常
        with pytest.raises(ValueError, match="找不到必需的服務"):
            provider.get_required_service(str)  # 未註冊的類型
    
    def test_singleton_scope(self, registry):
        """測試單例作用域"""
        provider1 = ServiceProvider(registry)
        provider2 = ServiceProvider(registry)
        
        # 從不同提供者獲取服務
        service1 = provider1.get_service(ITestService)
        service2 = provider2.get_service(ITestService)
        
        # 應該是同一個實例
        assert service1 is service2
    
    def test_transient_scope(self, registry):
        """測試瞬態作用域"""
        # 重新註冊為瞬態
        registry.unregister(ITestService)
        registry.register_transient(ITestService, TestServiceImpl)
        
        provider = ServiceProvider(registry)
        
        # 每次獲取都應該是新實例
        service1 = provider.get_service(ITestService)
        service2 = provider.get_service(ITestService)
        
        assert service1 is not service2
        assert service1.do_something() == service2.do_something()
    
    def test_scoped_scope(self, registry):
        """測試作用域作用域"""
        # 重新註冊為作用域
        registry.unregister(ITestService)
        registry.register_scoped(ITestService, TestServiceImpl)
        
        # 同一個提供者內應該是同一實例
        provider1 = ServiceProvider(registry)
        service1 = provider1.get_service(ITestService)
        service2 = provider1.get_service(ITestService)
        assert service1 is service2
        
        # 不同提供者應該是不同實例
        provider2 = ServiceProvider(registry)
        service3 = provider2.get_service(ITestService)
        assert service1 is not service3
    
    def test_auto_wire_dependencies(self, provider):
        """測試自動注入依賴"""
        # DependentService 依賴 ITestService
        service = provider.get_service(DependentService)
        assert service is not None
        assert isinstance(service, DependentService)
        assert service.get_result() == "dependent_test_result"
    
    def test_factory_resolution(self, registry):
        """測試工廠函數解析"""
        # 使用工廠函數
        call_count = 0
        
        def factory(provider: ServiceProvider) -> ITestService:
            nonlocal call_count
            call_count += 1
            return TestServiceImpl()
        
        registry.unregister(ITestService)
        registry.register_factory(ITestService, factory, ServiceScope.TRANSIENT)
        
        provider = ServiceProvider(registry)
        
        # 每次調用工廠函數
        service1 = provider.get_service(ITestService)
        service2 = provider.get_service(ITestService)
        
        assert call_count == 2  # 工廠函數被調用兩次
        assert service1 is not service2  # 不同實例
    
    def test_get_services_multiple(self, registry):
        """測試獲取多個服務實例"""
        # 註冊多個實現
        class AnotherTestService:
            def do_something(self) -> str:
                return "another_result"
        
        # 清除現有註冊並重新註冊（使用瞬態作用域）
        registry.unregister(ITestService)
        registry.register_transient(ITestService, TestServiceImpl)
        registry.register_transient(ITestService, AnotherTestService)
        
        provider = ServiceProvider(registry)
        services = provider.get_services(ITestService)
        
        # 應該返回兩個服務
        assert len(services) == 2
        results = [s.do_something() for s in services]
        assert "test_result" in results
        assert "another_result" in results


class TestGlobalRegistry:
    """全域註冊表測試"""
    
    def test_get_service_registry_singleton(self):
        """測試全域註冊表單例"""
        registry1 = get_service_registry()
        registry2 = get_service_registry()
        
        assert registry1 is registry2
    
    def test_global_registry_isolation(self):
        """測試全域註冊表隔離性"""
        # 清理可能存在的註冊
        registry = get_service_registry()
        registry.clear()
        
        # 註冊服務
        registry.register(ITestService, TestServiceImpl)
        
        # 驗證註冊成功
        assert registry.has_service(ITestService)
        
        # 清理
        registry.clear()


class TestAutoWiring:
    """自動注入測試"""
    
    def test_auto_wire_with_default_values(self):
        """測試帶預設值的自動注入"""
        class ServiceWithDefaults:
            def __init__(self, 
                        test_service: ITestService,
                        name: str = "default"):
                self.test_service = test_service
                self.name = name
        
        registry = ServiceRegistry()
        registry.register(ITestService, TestServiceImpl)
        registry.register(ServiceWithDefaults)
        
        provider = ServiceProvider(registry)
        service = provider.get_service(ServiceWithDefaults)
        
        assert service is not None
        assert service.name == "default"
        assert isinstance(service.test_service, TestServiceImpl)
    
    def test_auto_wire_missing_required_dependency(self):
        """測試缺少必需依賴時的自動注入"""
        class ServiceWithRequiredDep:
            def __init__(self, missing_service: str):  # str 未註冊
                self.missing_service = missing_service
        
        registry = ServiceRegistry()
        registry.register(ServiceWithRequiredDep)
        
        provider = ServiceProvider(registry)
        
        with pytest.raises(ValueError, match="無法解析依賴"):
            provider.get_service(ServiceWithRequiredDep)