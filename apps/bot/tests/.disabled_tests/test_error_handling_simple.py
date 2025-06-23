"""
簡化的錯誤處理整合測試
"""
import pytest
from unittest.mock import AsyncMock, Mock
from linebot.v3.messaging import TextMessage

from src.services.message_handler_di import MessageHandlerDI
from src.infrastructure.service_factory import ServiceFactory
from src.domain.exceptions import MCPConnectionException
from src.infrastructure.error_handler import create_error_middleware


class TestSimplifiedErrorHandling:
    """簡化的錯誤處理測試"""
    
    @pytest.mark.asyncio
    async def test_mcp_connection_error_integration(self):
        """測試 MCP 連接錯誤的整合處理"""
        # 建立 mock 的 MCP 客戶端，會拋出 MCP 連接錯誤
        mock_mcp_client = AsyncMock()
        mock_mcp_client.call_tool.side_effect = MCPConnectionException(
            "sqlite", "read_query", "連接超時"
        )
        
        # 建立服務工廠
        factory = ServiceFactory()
        
        # 建立處理器，注入 mock 客戶端
        handler = MessageHandlerDI(
            mcp_client_factory=lambda: mock_mcp_client,
            ai_model_service=factory.get_ai_model_service(),
            nl_service=factory.get_nl_service(),
            db_service=factory.get_database_service(),
            formatter=factory.get_message_formatter(),
            flex_builder=factory.get_flex_builder()
        )
        
        # 直接測試處理器（不使用中間件，因為處理器內部已經整合錯誤處理）
        result = await handler.process_message("test_user", "SELECT * FROM machines", "test_token")
        
        # 驗證結果
        assert isinstance(result, TextMessage)
        # 由於 MessageHandlerDI 內部使用 handle_error_gracefully，應該得到統一的錯誤處理
        assert ("🔌" in result.text or "💥" in result.text)
        assert "失敗" in result.text or "錯誤" in result.text
    
    @pytest.mark.asyncio 
    async def test_general_error_handling(self):
        """測試一般錯誤的處理"""
        # 建立會拋出一般錯誤的 mock 服務
        mock_ai_service = Mock()
        mock_ai_service.process_natural_language_query.side_effect = ValueError("無效的查詢格式")
        
        factory = ServiceFactory()
        
        handler = MessageHandlerDI(
            mcp_client_factory=lambda: AsyncMock(),
            ai_model_service=mock_ai_service,
            nl_service=factory.get_nl_service(),
            db_service=factory.get_database_service(),
            formatter=factory.get_message_formatter(),
            flex_builder=factory.get_flex_builder()
        )
        
        # 測試自然語言查詢
        result = await handler.process_message("test_user", "查詢機台狀態", "test_token")
        
        assert isinstance(result, TextMessage)
        # 應該得到用戶友善的錯誤訊息
        assert ("⚠️" in result.text or "💥" in result.text)
        assert ("錯誤" in result.text or "失敗" in result.text)