"""
MessageHandler DI 版本測試
測試依賴注入實現是否正確工作
"""
import pytest
from unittest.mock import Mock, AsyncMock
from linebot.v3.messaging import TextMessage

from src.services.message_handler_di import MessageHandlerDI
from src.infrastructure.service_factory import ServiceFactory, create_message_handler


class TestMessageHandlerDI:
    """MessageHandler 依賴注入版本測試"""
    
    @pytest.fixture
    def mock_services(self):
        """創建所有模擬服務"""
        return {
            'mcp_client_factory': AsyncMock(),
            'ai_model_service': Mock(),
            'nl_service': AsyncMock(),
            'db_service': AsyncMock(),
            'formatter': Mock(),
            'flex_builder': Mock(),
            'openai_client': Mock()
        }
    
    @pytest.fixture
    def message_handler_di(self, mock_services):
        """創建依賴注入版本的 MessageHandler"""
        mock_mcp_client = AsyncMock()
        mock_services['mcp_client_factory'].return_value = mock_mcp_client
        
        handler = MessageHandlerDI(**mock_services)
        return handler
    
    def test_dependency_injection_initialization(self, message_handler_di, mock_services):
        """測試依賴注入初始化"""
        # 驗證所有依賴都已正確注入
        assert message_handler_di.mcp_client_factory is mock_services['mcp_client_factory']
        assert message_handler_di.ai_model_service is mock_services['ai_model_service']
        assert message_handler_di.nl_service is mock_services['nl_service']
        assert message_handler_di.db_service is mock_services['db_service']
        assert message_handler_di.formatter is mock_services['formatter']
        assert message_handler_di.flex_builder is mock_services['flex_builder']
        assert message_handler_di.openai_client is mock_services['openai_client']
    
    @pytest.mark.asyncio
    async def test_mcp_client_lazy_initialization(self, message_handler_di, mock_services):
        """測試 MCP 客戶端延遲初始化"""
        mock_client = AsyncMock()
        mock_services['mcp_client_factory'].return_value = mock_client
        
        # 第一次調用
        client1 = await message_handler_di._get_mcp_client()
        assert client1 is mock_client
        
        # 第二次調用應該返回緩存的實例
        client2 = await message_handler_di._get_mcp_client()
        assert client2 is mock_client
        
        # 工廠函數應該只被調用一次
        mock_services['mcp_client_factory'].assert_called_once()
    
    @pytest.mark.asyncio
    async def test_help_command_with_di(self, message_handler_di):
        """測試幫助指令處理（使用依賴注入）"""
        result = await message_handler_di._handle_help_command("user1", [])
        
        assert isinstance(result, TextMessage)
        assert "LINE MCP Bot 使用說明" in result.text
        assert "自然語言查詢" in result.text
    
    @pytest.mark.asyncio
    async def test_status_command_with_mocked_db(self, message_handler_di, mock_services):
        """測試狀態指令（使用模擬資料庫服務）"""
        # 設置模擬回應
        mock_services['db_service'].test_connection.return_value = True
        
        result = await message_handler_di._handle_status_command("user1", [])
        
        assert isinstance(result, TextMessage)
        assert "系統狀態報告" in result.text
        assert "資料庫連接：正常" in result.text
        
        # 驗證模擬服務被正確調用
        mock_services['db_service'].test_connection.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_models_command_with_mocked_ai_service(self, message_handler_di, mock_services):
        """測試模型狀態指令（使用模擬AI服務）"""
        # 設置模擬回應
        mock_services['ai_model_service'].get_available_models.return_value = [
            {
                "name": "gpt-4o-mini",
                "provider": "openai",
                "is_default": True,
                "cost_per_1k_input": 0.15,
                "cost_per_1k_output": 0.60,
                "context_window": 128000,
                "free_tier_limit": None
            }
        ]
        mock_services['nl_service'].enable_ai_enhancement = True
        mock_services['nl_service'].fallback_to_rules = True
        
        result = await message_handler_di._handle_models_command("user1", [])
        
        assert isinstance(result, TextMessage)
        assert "AI模型狀態報告" in result.text
        assert "gpt-4o-mini" in result.text
        
        # 驗證模擬服務被正確調用
        mock_services['ai_model_service'].get_available_models.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_natural_language_processing_with_mocks(self, message_handler_di, mock_services):
        """測試自然語言處理（完全模擬）"""
        from src.services.nl_to_sql_service import QueryType
        
        # 設置所有模擬回應
        mock_services['db_service'].get_table_info.return_value = {
            "machines": {"columns": ["id", "status"]}
        }
        
        mock_parsed_query = Mock()
        mock_parsed_query.query_type = QueryType.MACHINE_STATUS
        mock_parsed_query.confidence = 0.9
        mock_parsed_query.explanation = "查詢機台狀態"
        mock_services['nl_service'].parse_natural_language.return_value = mock_parsed_query
        
        mock_query_result = [{"id": "M001", "status": "running"}]
        mock_services['db_service'].execute_parsed_query.return_value = mock_query_result
        
        mock_formatted_result = TextMessage(text="機台M001運行正常")
        mock_services['formatter'].format_query_result.return_value = mock_formatted_result
        
        # 執行測試
        result = await message_handler_di._handle_natural_language("user1", "M001機台狀況如何？")
        
        assert isinstance(result, TextMessage)
        assert result.text == "機台M001運行正常"
        
        # 驗證調用順序
        mock_services['db_service'].get_table_info.assert_called_once()
        mock_services['nl_service'].parse_natural_language.assert_called_once()
        mock_services['db_service'].execute_parsed_query.assert_called_once()
        mock_services['formatter'].format_query_result.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_command_routing_with_di(self, message_handler_di, mock_services):
        """測試指令路由（依賴注入版本）"""
        from src.models.commands import Command
        
        # 模擬 tables 指令
        mock_services['db_service'].get_table_info.return_value = {
            "machines": {"row_count": 10, "columns": ["id", "name"]}
        }
        
        tables_cmd = Command(name="tables", args=[])
        result = await message_handler_di._handle_command("user1", tables_cmd)
        
        assert isinstance(result, TextMessage)
        assert "資料庫表格列表" in result.text
        
        # 驗證資料庫服務被調用
        mock_services['db_service'].get_table_info.assert_called_once()
    
    def test_greeting_detection_same_as_original(self, message_handler_di):
        """測試問候語檢測與原版本一致"""
        assert message_handler_di._is_greeting("你好")
        assert message_handler_di._is_greeting("hello")
        assert not message_handler_di._is_greeting("查詢機台狀態")
    
    def test_greeting_response(self, message_handler_di):
        """測試問候語回應"""
        result = message_handler_di._handle_greeting()
        
        assert isinstance(result, TextMessage)
        assert "您好！我是產線管理助手" in result.text


class TestServiceFactory:
    """ServiceFactory 測試"""
    
    @pytest.fixture
    def service_factory(self):
        """創建服務工廠實例"""
        factory = ServiceFactory()
        yield factory
        # 清理實例
        factory.clear_instances()
    
    def test_service_factory_singleton_behavior(self, service_factory):
        """測試服務工廠的單例行為"""
        # 多次獲取同一服務應該返回同一實例
        ai_service1 = service_factory.get_ai_model_service()
        ai_service2 = service_factory.get_ai_model_service()
        
        assert ai_service1 is ai_service2
    
    def test_service_factory_creates_all_services(self, service_factory):
        """測試服務工廠能創建所有必需的服務"""
        # 測試所有服務都能正確創建
        services = {
            'ai_model_service': service_factory.get_ai_model_service(),
            'openai_client': service_factory.get_openai_client(),
            'flex_builder': service_factory.get_flex_builder(),
            'message_formatter': service_factory.get_message_formatter(),
            'nl_service': service_factory.get_nl_service(),
            'database_service': service_factory.get_database_service()
        }
        
        # 驗證所有服務都已創建且不為 None
        for service_name, service_instance in services.items():
            assert service_instance is not None, f"{service_name} should not be None"
    
    def test_service_factory_dependency_injection(self, service_factory):
        """測試服務工廠的依賴注入"""
        nl_service = service_factory.get_nl_service()
        ai_service = service_factory.get_ai_model_service()
        
        # 驗證 NL 服務使用了正確的 AI 服務實例
        assert nl_service.ai_model_service is ai_service
    
    def test_create_message_handler_with_factory(self, service_factory):
        """測試使用工廠創建消息處理器"""
        handler = service_factory.create_message_handler()
        
        assert isinstance(handler, MessageHandlerDI)
        assert handler.ai_model_service is not None
        assert handler.nl_service is not None
        assert handler.db_service is not None
        assert handler.formatter is not None
        assert handler.flex_builder is not None
    
    def test_service_info(self, service_factory):
        """測試服務資訊功能"""
        # 創建一些服務
        service_factory.get_ai_model_service()
        service_factory.get_flex_builder()
        
        info = service_factory.get_service_info()
        
        assert "created_instances" in info
        assert "singleton_services" in info
        assert "total_instances" in info
        assert len(info["created_instances"]) == 2
    
    def test_global_service_factory(self):
        """測試全域服務工廠"""
        from src.infrastructure.service_factory import get_service_factory
        
        factory1 = get_service_factory()
        factory2 = get_service_factory()
        
        # 應該返回同一個實例
        assert factory1 is factory2
    
    def test_convenience_function(self):
        """測試便捷函數"""
        handler = create_message_handler()
        
        assert isinstance(handler, MessageHandlerDI)
        assert handler.ai_model_service is not None