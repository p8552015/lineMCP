"""
MessageHandler 單元測試
測試現有功能，確保重構過程中不破壞現有行為
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from linebot.v3.messaging import TextMessage

from src.services.message_handler import MessageHandler
from src.models.commands import Command


class TestMessageHandler:
    """MessageHandler 測試類別"""
    
    @pytest.fixture
    def message_handler(self, mock_mcp_client, mock_openai_client, 
                       mock_ai_model_service, mock_nl_service, 
                       mock_database_service, mock_formatter):
        """創建 MessageHandler 實例用於測試"""
        # 直接創建實例並替換屬性
        handler = MessageHandler()
        
        # 替換內部服務
        handler.openai_client = mock_openai_client
        handler._mcp_client = mock_mcp_client
        handler.ai_model_service = mock_ai_model_service
        handler.nl_service = mock_nl_service
        handler.db_service = mock_database_service
        handler.formatter = mock_formatter
        
        return handler
    
    @pytest.mark.asyncio
    async def test_process_message_sql_command(self, message_handler, mock_mcp_client):
        """測試 SQL 指令處理"""
        # 設置 MCP 客戶端回應
        mock_mcp_client.call_tool.return_value = {
            "success": True,
            "data": [{"id": 1, "machine": "M001"}]
        }
        
        result = await message_handler.process_message(
            "test_user", "/sql SELECT * FROM machines", "test_token"
        )
        
        assert isinstance(result, TextMessage)
        assert "SQL查詢結果" in result.text
        mock_mcp_client.call_tool.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_message_tables_command(self, message_handler):
        """測試表格列表指令處理"""
        result = await message_handler.process_message(
            "test_user", "/tables", "test_token"
        )
        
        assert isinstance(result, TextMessage)
        assert "資料庫表格列表" in result.text
    
    @pytest.mark.asyncio
    async def test_process_message_status_command(self, message_handler):
        """測試狀態查詢指令處理"""
        result = await message_handler.process_message(
            "test_user", "/status", "test_token"
        )
        
        assert isinstance(result, TextMessage)
        assert "系統狀態報告" in result.text
    
    @pytest.mark.asyncio
    async def test_process_message_help_command(self, message_handler):
        """測試幫助指令處理"""
        result = await message_handler.process_message(
            "test_user", "/help", "test_token"
        )
        
        assert isinstance(result, TextMessage)
        assert "LINE MCP Bot 使用說明" in result.text
    
    @pytest.mark.asyncio
    async def test_process_message_models_command(self, message_handler):
        """測試模型狀態指令處理"""
        result = await message_handler.process_message(
            "test_user", "/models", "test_token"
        )
        
        assert isinstance(result, TextMessage)
        assert "AI模型狀態報告" in result.text
    
    @pytest.mark.asyncio
    async def test_process_message_natural_language(self, message_handler):
        """測試自然語言處理"""
        result = await message_handler.process_message(
            "test_user", "M001機台狀況如何？", "test_token"
        )
        
        assert isinstance(result, TextMessage)
        # 結果應該來自格式化器的模擬回應
        assert result.text == "格式化的查詢結果"
    
    @pytest.mark.asyncio
    async def test_process_message_greeting(self, message_handler):
        """測試問候語處理"""
        result = await message_handler.process_message(
            "test_user", "你好", "test_token"
        )
        
        assert isinstance(result, TextMessage)
        assert "您好！我是產線管理助手" in result.text
    
    @pytest.mark.asyncio
    async def test_process_message_unknown_command(self, message_handler):
        """測試未知指令處理"""
        result = await message_handler.process_message(
            "test_user", "/unknown", "test_token"
        )
        
        assert isinstance(result, TextMessage)
        assert "未知的指令" in result.text
    
    @pytest.mark.asyncio
    async def test_process_message_error_handling(self, message_handler, mock_mcp_client):
        """測試錯誤處理"""
        # 模擬 MCP 客戶端拋出異常
        mock_mcp_client.call_tool.side_effect = Exception("Connection failed")
        
        result = await message_handler.process_message(
            "test_user", "/sql SELECT * FROM machines", "test_token"
        )
        
        assert isinstance(result, TextMessage)
        # 應該返回錯誤訊息而不是拋出異常
        assert "訊息處理時發生錯誤" in result.text or "查詢失敗" in result.text
    
    def test_is_greeting(self, message_handler):
        """測試問候語識別"""
        assert message_handler._is_greeting("你好")
        assert message_handler._is_greeting("hi")
        assert message_handler._is_greeting("Hello")
        assert not message_handler._is_greeting("查詢機台")
        assert not message_handler._is_greeting("/sql SELECT")
    
    def test_is_machine_query(self, message_handler):
        """測試機台查詢識別（向後相容性）"""
        # 目前所有查詢都進入自然語言處理流程
        assert message_handler._is_machine_query("M001機台狀況")
        assert message_handler._is_machine_query("任何文字")
    
    def test_message_handler_initialization(self, message_handler):
        """測試 MessageHandler 初始化"""
        assert message_handler.openai_client is not None
        assert message_handler.flex_builder is not None
        assert message_handler.ai_model_service is not None
        assert message_handler.nl_service is not None
        assert message_handler.db_service is not None
        assert message_handler.formatter is not None
    
    @pytest.mark.asyncio
    async def test_mcp_client_lazy_initialization(self, message_handler, mock_mcp_client):
        """測試 MCP 客戶端延遲初始化"""
        # 第一次調用應該初始化客戶端
        client = await message_handler._get_mcp_client()
        assert client is not None
        
        # 第二次調用應該返回同一個實例
        client2 = await message_handler._get_mcp_client()
        assert client is client2