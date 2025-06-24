"""
測試增強版服務工廠
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.infrastructure.enhanced_service_factory import (
    EnhancedServiceFactory,
    get_enhanced_service_factory
)
from src.infrastructure.service_registry import ServiceRegistry, ServiceScope
from src.services.ai_model_service import AIModelService
from src.services.message_formatter import MessageFormatter
from src.services.nl_to_sql_service import NaturalLanguageToSQLService
from src.application.messaging_service import MessagingApplicationService


class TestEnhancedServiceFactory:
    """增強版服務工廠測試"""
    
    @pytest.fixture
    def registry(self):
        """創建新的註冊表"""
        return ServiceRegistry()
    
    @pytest.fixture
    def factory(self, registry):
        """創建服務工廠"""
        return EnhancedServiceFactory(registry)
    
    def test_factory_initialization(self, factory):
        """測試工廠初始化"""
        assert not factory._initialized
        
        factory.initialize()
        
        assert factory._initialized
        assert factory._provider is not None
    
    def test_factory_double_initialization(self, factory):
        """測試重複初始化"""
        factory.initialize()
        provider1 = factory._provider
        
        # 第二次初始化應該被忽略
        factory.initialize()
        provider2 = factory._provider
        
        assert provider1 is provider2
    
    def test_register_core_services(self, factory, registry):
        """測試核心服務註冊"""
        factory._register_core_services()
        
        # 驗證核心服務已註冊
        assert registry.has_service(AIModelService)
        assert registry.has_service(MessageFormatter)
        
        # 驗證標籤
        ai_service_desc = registry.get_descriptor(AIModelService)
        assert "core" in ai_service_desc.tags
        assert "ai" in ai_service_desc.tags
    
    def test_get_service(self, factory):
        """測試獲取服務"""
        # 初始化工廠
        factory.initialize()
        
        # 獲取服務
        ai_service = factory.get_service(AIModelService)
        assert ai_service is not None
        assert isinstance(ai_service, AIModelService)
        
        # 獲取不存在的服務
        result = factory.get_service(str)  # 未註冊的服務
        assert result is None
    
    def test_get_required_service(self, factory):
        """測試獲取必需的服務"""
        factory.initialize()
        
        # 獲取存在的服務
        formatter = factory.get_required_service(MessageFormatter)
        assert isinstance(formatter, MessageFormatter)
        
        # 獲取不存在的服務應拋出異常
        with pytest.raises(ValueError, match="找不到必需的服務"):
            factory.get_required_service(str)
    
    @patch('src.infrastructure.enhanced_service_factory.get_unified_mcp_client')
    def test_create_message_handler(self, mock_mcp_client, factory):
        """測試創建訊息處理器"""
        # 設置模擬
        mock_mcp_client.return_value = AsyncMock()
        
        factory.initialize()
        
        # 創建訊息處理器
        handler = factory.create_message_handler()
        assert handler is not None
        
        # 驗證依賴注入
        assert hasattr(handler, 'ai_model_service')
        assert hasattr(handler, 'nl_service')
        assert hasattr(handler, 'formatter')
    
    
    def test_compatibility_methods(self, factory):
        """測試與原有 ServiceFactory 的兼容性方法"""
        factory.initialize()
        
        # 測試各個 get 方法
        assert factory.get_ai_model_service() is not None
        assert factory.get_message_formatter() is not None
        assert factory.get_nl_service() is not None
        assert factory.get_database_service() is not None
        
        # 測試異步方法
        import asyncio
        loop = asyncio.get_event_loop()
        mcp_factory = loop.run_until_complete(factory.get_mcp_client_factory())
        assert mcp_factory is not None
    
    def test_get_registry_info(self, factory):
        """測試獲取註冊表資訊"""
        factory.initialize()
        
        info = factory.get_registry_info()
        
        assert "total_services" in info
        assert info["total_services"] > 0
        
        assert "service_types" in info
        assert len(info["service_types"]) > 0
        
        assert "by_scope" in info
        assert info["by_scope"]["singleton"] > 0
        
        assert "by_tag" in info
        assert info["by_tag"]["core"] > 0
    
    def test_service_scopes(self, factory, registry):
        """測試不同作用域的服務"""
        factory.initialize()
        
        # 檢查單例服務
        ai_desc = registry.get_descriptor(AIModelService)
        assert ai_desc.scope == ServiceScope.SINGLETON
        
        # 獲取單例服務多次應返回同一實例
        ai1 = factory.get_service(AIModelService)
        ai2 = factory.get_service(AIModelService)
        assert ai1 is ai2
    
    def test_service_tags_and_metadata(self, factory, registry):
        """測試服務標籤和元數據"""
        factory.initialize()
        
        # 檢查服務標籤
        formatter_desc = registry.get_descriptor(MessageFormatter)
        assert "core" in formatter_desc.tags
        assert "formatting" in formatter_desc.tags
        
        # 檢查元數據
        assert "description" in formatter_desc.metadata
        assert formatter_desc.metadata["description"] == "訊息格式化器"
    
    def test_lazy_initialization(self, factory):
        """測試延遲初始化"""
        # 未初始化時調用 get_service 應自動初始化
        assert not factory._initialized
        
        service = factory.get_service(AIModelService)
        
        assert factory._initialized
        assert service is not None


class TestGlobalEnhancedFactory:
    """全域增強版工廠測試"""
    
    def test_get_enhanced_factory_singleton(self):
        """測試全域工廠單例"""
        factory1 = get_enhanced_service_factory()
        factory2 = get_enhanced_service_factory()
        
        assert factory1 is factory2
        assert isinstance(factory1, EnhancedServiceFactory)


class TestServiceCreation:
    """服務創建測試"""
    
    @pytest.fixture
    def factory(self):
        """創建已初始化的工廠"""
        factory = EnhancedServiceFactory()
        factory.initialize()
        return factory
    
    @patch('src.infrastructure.enhanced_service_factory.CommandExecutor')
    def test_create_command_executor(self, mock_executor_class, factory):
        """測試創建指令執行器"""
        # 設置模擬
        mock_executor = Mock()
        mock_executor.initialize = Mock()
        mock_executor_class.return_value = mock_executor
        
        # 創建執行器
        executor = factory._create_command_executor(factory._provider)
        
        # 驗證初始化被調用
        mock_executor.initialize.assert_called_once()
    
    @patch('src.infrastructure.enhanced_service_factory.get_unified_mcp_client')
    def test_create_messaging_service(self, mock_mcp_client, factory):
        """測試創建訊息處理應用服務"""
        # 設置模擬
        mock_mcp_client.return_value = AsyncMock()
        
        # 創建服務
        service = factory._create_messaging_service(factory._provider)
        
        assert service is not None
        assert hasattr(service, 'command_context')
        assert hasattr(service, 'nl_service')
        assert hasattr(service, 'message_formatter')
    
    def test_factory_methods_integration(self, factory):
        """測試工廠方法集成"""
        # 註冊的工廠方法應該能正確創建服務
        nl_service = factory.get_service(NaturalLanguageToSQLService)
        assert nl_service is not None
        
        # 依賴應該被正確注入
        assert hasattr(nl_service, 'ai_model_service')
        assert nl_service.ai_model_service is not None


class TestConfigurationIntegration:
    """配置集成測試"""
    
    def test_factory_with_custom_registry(self):
        """測試使用自定義註冊表"""
        # 創建自定義註冊表
        custom_registry = ServiceRegistry()
        
        # 創建工廠
        factory = EnhancedServiceFactory(custom_registry)
        
        # 初始化
        factory.initialize()
        
        # 驗證服務已註冊到自定義註冊表
        assert custom_registry.has_service(AIModelService)
        
        # 獲取服務
        service = factory.get_service(AIModelService)
        assert service is not None
    
    def test_service_resolution_chain(self):
        """測試服務解析鏈"""
        factory = EnhancedServiceFactory()
        factory.initialize()
        
        # 獲取有依賴的服務
        nl_service = factory.get_service(NaturalLanguageToSQLService)
        
        # 驗證依賴鏈
        assert nl_service is not None
        assert nl_service.ai_model_service is not None
        assert isinstance(nl_service.ai_model_service, AIModelService)