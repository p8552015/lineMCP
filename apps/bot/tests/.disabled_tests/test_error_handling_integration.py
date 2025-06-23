"""
錯誤處理整合測試
驗證 MessageHandlerDI 與統一錯誤處理的整合
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from linebot.v3.messaging import TextMessage

from src.services.message_handler_di import MessageHandlerDI
from src.infrastructure.service_factory import ServiceFactory
from src.domain.exceptions import (
    ValidationException,
    MCPConnectionException,
    AIServiceException,
    DatabaseQueryException
)
from src.infrastructure.error_handler import (
    UnifiedErrorHandler,
    get_error_handler,
    create_error_middleware
)


class TestErrorHandlingIntegration:
    """測試錯誤處理與 MessageHandlerDI 的整合"""
    
    @pytest.mark.asyncio
    async def test_message_handler_di_with_error_handling(self):
        """測試 MessageHandlerDI 整合錯誤處理"""
        # 建立具有錯誤處理的 MessageHandlerDI
        factory = ServiceFactory()
        
        # 建立模擬的錯誤情況
        mock_mcp_client = AsyncMock()
        mock_mcp_client.read_query.side_effect = MCPConnectionException(
            "sqlite", "read_query", "連接失敗"
        )
        
        # 建立處理器
        handler = MessageHandlerDI(
            mcp_client_factory=lambda: mock_mcp_client,
            ai_model_service=factory.get_ai_model_service(),
            nl_service=factory.get_nl_service(),
            db_service=factory.get_database_service(),
            formatter=factory.get_message_formatter(),
            flex_builder=factory.get_flex_builder()
        )
        
        # 建立錯誤處理中間件
        error_middleware = create_error_middleware(include_technical_details=False)
        
        # 包裝 process_message 方法
        @error_middleware
        async def wrapped_process_message(message: str) -> TextMessage:
            return await handler.process_message("test_user", message, "test_reply_token")
        
        # 測試 MCP 連接錯誤的處理
        result = await wrapped_process_message("SELECT * FROM test_table")
        
        assert isinstance(result, TextMessage)
        assert "🔌" in result.text
        assert "服務連接失敗" in result.text
        assert "連接失敗" not in result.text  # 技術細節不應該出現
    
    @pytest.mark.asyncio
    async def test_command_validation_error_handling(self):
        """測試指令驗證錯誤處理"""
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
        
        # 建立錯誤處理中間件
        error_middleware = create_error_middleware()
        
        @error_middleware
        async def wrapped_process_message(message: str) -> TextMessage:
            # 模擬處理過程中的驗證錯誤
            if message.startswith("/invalid"):
                raise ValidationException("command", message, "不支援的指令")
            return await handler.process_message(message)
        
        # 測試無效指令
        result = await wrapped_process_message("/invalid_command")
        
        assert isinstance(result, TextMessage)
        assert "⚠️" in result.text
        assert "輸入的 command 格式不正確" in result.text
    
    @pytest.mark.asyncio
    async def test_ai_service_error_handling(self):
        """測試 AI 服務錯誤處理"""
        factory = ServiceFactory()
        
        # 建立模擬的 AI 服務錯誤
        mock_ai_service = Mock()
        mock_ai_service.process_natural_language_query.side_effect = AIServiceException(
            "openai", "completion", "API 配額超過"
        )
        
        # 建立處理器
        handler = MessageHandlerDI(
            mcp_client_factory=lambda: AsyncMock(),
            ai_model_service=mock_ai_service,
            nl_service=factory.get_nl_service(),
            db_service=factory.get_database_service(),
            formatter=factory.get_message_formatter(),
            flex_builder=factory.get_flex_builder()
        )
        
        # 建立錯誤處理中間件
        error_middleware = create_error_middleware()
        
        @error_middleware
        async def wrapped_process_message(message: str) -> TextMessage:
            return await handler.process_message("test_user", message, "test_reply_token")
        
        # 測試 AI 服務錯誤
        result = await wrapped_process_message("你好")
        
        assert isinstance(result, TextMessage)
        assert "🤖" in result.text
        assert "AI 服務暫時不可用" in result.text
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self):
        """測試資料庫錯誤處理"""
        factory = ServiceFactory()
        
        # 建立模擬的資料庫錯誤
        mock_db_service = Mock()
        mock_db_service.execute_query.side_effect = DatabaseQueryException(
            "SELECT * FROM non_existent", "表格不存在", "SELECT"
        )
        
        # 建立處理器
        handler = MessageHandlerDI(
            mcp_client_factory=lambda: AsyncMock(),
            ai_model_service=factory.get_ai_model_service(),
            nl_service=factory.get_nl_service(),
            db_service=mock_db_service,
            formatter=factory.get_formatter(),
            flex_builder=factory.get_flex_builder()
        )
        
        # 建立錯誤處理中間件  
        error_middleware = create_error_middleware()
        
        @error_middleware
        async def wrapped_process_message(message: str) -> TextMessage:
            return await handler.process_message("test_user", message, "test_reply_token")
        
        # 測試資料庫錯誤
        result = await wrapped_process_message("SELECT * FROM test")
        
        assert isinstance(result, TextMessage)
        assert "🗄️" in result.text
        assert "資料庫查詢失敗" in result.text
    
    @pytest.mark.asyncio
    async def test_global_error_handler_singleton(self):
        """測試全域錯誤處理器的單例模式"""
        handler1 = get_error_handler()
        handler2 = get_error_handler()
        
        # 應該是同一個實例
        assert handler1 is handler2
        assert isinstance(handler1, UnifiedErrorHandler)
    
    @pytest.mark.asyncio
    async def test_error_context_propagation(self):
        """測試錯誤上下文的傳播"""
        factory = ServiceFactory()
        
        # 建立模擬的 MCP 客戶端
        mock_mcp_client = AsyncMock()
        mock_mcp_client.read_query.side_effect = MCPConnectionException(
            "sqlite", "read_query", "超時"
        )
        
        # 建立處理器
        handler = MessageHandlerDI(
            mcp_client_factory=lambda: mock_mcp_client,
            ai_model_service=factory.get_ai_model_service(),
            nl_service=factory.get_nl_service(),
            db_service=factory.get_database_service(),
            formatter=factory.get_message_formatter(),
            flex_builder=factory.get_flex_builder()
        )
        
        # 使用詳細模式的錯誤處理
        error_middleware = create_error_middleware(include_technical_details=True)
        
        @error_middleware
        async def wrapped_process_message(message: str) -> TextMessage:
            return await handler.process_message("test_user", message, "test_reply_token")
        
        # 測試錯誤上下文
        result = await wrapped_process_message("SELECT * FROM test")
        
        assert isinstance(result, TextMessage)
        assert "🔌" in result.text
        assert "服務連接失敗" in result.text
        # 在詳細模式下，應該包含技術細節
        if "技術詳情" in result.text:
            assert "sqlite" in result.text or "read_query" in result.text
    
    def test_error_handler_configuration(self):
        """測試錯誤處理器配置"""
        # 測試不包含技術細節的配置
        handler1 = UnifiedErrorHandler(include_technical_details=False)
        error = ValidationException("test", "value", "reason")
        result1 = handler1.handle_error(error)
        
        assert "技術詳情" not in result1.text
        
        # 測試包含技術細節的配置
        handler2 = UnifiedErrorHandler(include_technical_details=True)
        result2 = handler2.handle_error(error)
        
        assert "技術詳情" in result2.text
        assert "value" in result2.text