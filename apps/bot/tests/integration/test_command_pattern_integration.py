"""
Command Pattern 整合測試
驗證指令模式與 MessageHandlerDI 的整合
"""
import pytest
from unittest.mock import AsyncMock, Mock
from linebot.v3.messaging import TextMessage

from src.services.message_handler_command_pattern import MessageHandlerDI
from src.infrastructure.service_factory import ServiceFactory


class TestCommandPatternIntegration:
    """測試 Command Pattern 整合"""
    
    @pytest.mark.asyncio
    async def test_message_handler_with_command_pattern(self):
        """測試 MessageHandlerDI 使用 Command Pattern"""
        # 建立服務工廠
        factory = ServiceFactory()
        
        # 建立處理器
        handler = MessageHandlerDI(
            mcp_client_factory=lambda: AsyncMock(),
            ai_model_service=factory.get_ai_model_service(),
            nl_service=factory.get_nl_service(),
            db_service=factory.get_database_service(),
            formatter=factory.get_message_formatter(),
            flex_builder=factory.get_flex_builder()
        )
        
        # 測試幫助指令
        result = await handler.process_message("test_user", "/help", "test_token")
        
        assert isinstance(result, TextMessage)
        assert "幫助" in result.text or "help" in result.text.lower()
    
    @pytest.mark.asyncio
    async def test_status_command_execution(self):
        """測試狀態檢查指令執行"""
        factory = ServiceFactory()
        
        # 建立 mock MCP 客戶端
        mock_mcp_client = AsyncMock()
        mock_mcp_client.call_tool.return_value = {"test": "result"}
        
        handler = MessageHandlerDI(
            mcp_client_factory=lambda: mock_mcp_client,
            ai_model_service=factory.get_ai_model_service(),
            nl_service=factory.get_nl_service(),
            db_service=factory.get_database_service(),
            formatter=factory.get_message_formatter(),
            flex_builder=factory.get_flex_builder()
        )
        
        # 測試狀態指令
        result = await handler.process_message("test_user", "/status", "test_token")
        
        assert isinstance(result, TextMessage)
        assert "狀態" in result.text or "status" in result.text.lower()
    
    @pytest.mark.asyncio
    async def test_info_command_execution(self):
        """測試系統資訊指令執行"""
        factory = ServiceFactory()
        
        handler = MessageHandlerDI(
            mcp_client_factory=lambda: AsyncMock(),
            ai_model_service=factory.get_ai_model_service(),
            nl_service=factory.get_nl_service(),
            db_service=factory.get_database_service(),
            formatter=factory.get_message_formatter(),
            flex_builder=factory.get_flex_builder()
        )
        
        # 測試資訊指令
        result = await handler.process_message("test_user", "/info", "test_token")
        
        assert isinstance(result, TextMessage)
        assert ("資訊" in result.text or "info" in result.text.lower() or 
                "系統" in result.text or "version" in result.text.lower())
    
    @pytest.mark.asyncio
    async def test_models_command_execution(self):
        """測試 AI 模型指令執行"""
        factory = ServiceFactory()
        
        handler = MessageHandlerDI(
            mcp_client_factory=lambda: AsyncMock(),
            ai_model_service=factory.get_ai_model_service(),
            nl_service=factory.get_nl_service(),
            db_service=factory.get_database_service(),
            formatter=factory.get_message_formatter(),
            flex_builder=factory.get_flex_builder()
        )
        
        # 測試模型指令
        result = await handler.process_message("test_user", "/models", "test_token")
        
        assert isinstance(result, TextMessage)
        assert ("模型" in result.text or "model" in result.text.lower() or 
                "AI" in result.text)
    
    @pytest.mark.asyncio
    async def test_unknown_command_handling(self):
        """測試未知指令處理"""
        factory = ServiceFactory()
        
        handler = MessageHandlerDI(
            mcp_client_factory=lambda: AsyncMock(),
            ai_model_service=factory.get_ai_model_service(),
            nl_service=factory.get_nl_service(),
            db_service=factory.get_database_service(),
            formatter=factory.get_message_formatter(),
            flex_builder=factory.get_flex_builder()
        )
        
        # 測試未知指令
        result = await handler.process_message("test_user", "/unknown_command", "test_token")
        
        assert isinstance(result, TextMessage)
        # 應該返回錯誤處理結果或預設回應
        assert ("錯誤" in result.text or "失敗" in result.text or 
                "未知" in result.text or "助手" in result.text)
    
    @pytest.mark.asyncio
    async def test_natural_language_fallback(self):
        """測試自然語言回退處理"""
        factory = ServiceFactory()
        
        handler = MessageHandlerDI(
            mcp_client_factory=lambda: AsyncMock(),
            ai_model_service=factory.get_ai_model_service(),
            nl_service=factory.get_nl_service(),
            db_service=factory.get_database_service(),
            formatter=factory.get_message_formatter(),
            flex_builder=factory.get_flex_builder()
        )
        
        # 測試自然語言查詢
        result = await handler.process_message("test_user", "你好", "test_token")
        
        assert isinstance(result, TextMessage)
        # 應該返回預設回應或處理結果
        assert len(result.text) > 0
    
    @pytest.mark.asyncio
    async def test_command_executor_initialization(self):
        """測試指令執行器的初始化"""
        factory = ServiceFactory()
        
        handler = MessageHandlerDI(
            mcp_client_factory=lambda: AsyncMock(),
            ai_model_service=factory.get_ai_model_service(),
            nl_service=factory.get_nl_service(),
            db_service=factory.get_database_service(),
            formatter=factory.get_message_formatter(),
            flex_builder=factory.get_flex_builder()
        )
        
        # 第一次執行指令時會初始化指令執行器
        result1 = await handler.process_message("test_user", "/help", "test_token")
        
        # 檢查指令執行器是否已初始化
        assert hasattr(handler, '_command_executor')
        assert handler._command_executor is not None
        assert handler._command_executor._initialized == True
        
        # 第二次執行應該重用同一個執行器
        result2 = await handler.process_message("test_user", "/info", "test_token")
        
        assert isinstance(result1, TextMessage)
        assert isinstance(result2, TextMessage)
        
        # 檢查指令執行器的統計資訊
        command_info = handler._command_executor.get_command_info()
        assert command_info["total_commands"] >= 6  # 至少有6個基本指令
        assert command_info["total_aliases"] > 0  # 應該有一些別名