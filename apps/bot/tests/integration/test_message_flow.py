"""
整合測試：測試完整的訊息處理流程
驗證所有組件協同工作的能力
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from linebot.v3.messaging import TextMessage

from src.services.message_handler import MessageHandler


class TestMessageFlow:
    """測試完整的訊息處理流程"""
    
    @pytest.fixture
    def message_handler(self):
        """創建真實的 MessageHandler 實例"""
        return MessageHandler()
    
    @pytest.mark.asyncio
    async def test_help_command_flow(self, message_handler):
        """測試幫助指令的完整流程"""
        result = await message_handler.process_message(
            "test_user", "/help", "test_token"
        )
        
        assert isinstance(result, TextMessage)
        assert "LINE MCP Bot 使用說明" in result.text
        assert "自然語言查詢" in result.text
        assert "指令查詢" in result.text
    
    @pytest.mark.asyncio
    async def test_greeting_flow(self, message_handler):
        """測試問候語的完整流程"""
        result = await message_handler.process_message(
            "test_user", "你好", "test_token"
        )
        
        assert isinstance(result, TextMessage)
        assert "您好！我是產線管理助手" in result.text
        assert "機台狀態和效能" in result.text
    
    @pytest.mark.asyncio
    async def test_models_command_flow(self, message_handler):
        """測試AI模型狀態指令的完整流程"""
        result = await message_handler.process_message(
            "test_user", "/models", "test_token"
        )
        
        assert isinstance(result, TextMessage)
        assert "AI模型狀態報告" in result.text
        assert "Gemini" in result.text or "GPT" in result.text
    
    @pytest.mark.asyncio
    async def test_info_command_flow(self, message_handler):
        """測試資訊查詢指令的完整流程"""
        result = await message_handler.process_message(
            "test_user", "/info", "test_token"
        )
        
        assert isinstance(result, TextMessage)
        assert "建議查詢範例" in result.text
    
    @pytest.mark.asyncio
    async def test_natural_language_flow_with_mock(self, message_handler):
        """測試自然語言處理流程（使用模擬避免實際MCP調用）"""
        # 模擬資料庫服務和自然語言服務
        with patch.object(message_handler.db_service, 'get_table_info') as mock_table_info, \
             patch.object(message_handler.nl_service, 'parse_natural_language') as mock_parse, \
             patch.object(message_handler.db_service, 'execute_parsed_query') as mock_execute, \
             patch.object(message_handler.formatter, 'format_query_result') as mock_format:
            
            # 設置模擬回應
            mock_table_info.return_value = {"machines": {"columns": ["id", "status"]}}
            
            from src.services.nl_to_sql_service import QueryType
            mock_parse.return_value = Mock(
                query_type=QueryType.MACHINE_STATUS,
                confidence=0.9,
                explanation="查詢機台狀態"
            )
            
            mock_execute.return_value = [{"id": "M001", "status": "running"}]
            mock_format.return_value = TextMessage(text="機台M001運行正常")
            
            # 執行測試
            result = await message_handler.process_message(
                "test_user", "M001機台狀況如何？", "test_token"
            )
            
            assert isinstance(result, TextMessage)
            assert result.text == "機台M001運行正常"
            
            # 驗證調用順序
            mock_table_info.assert_called_once()
            mock_parse.assert_called_once()
            mock_execute.assert_called_once()
            mock_format.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_unknown_query_flow(self, message_handler):
        """測試未知查詢的處理流程"""
        # 模擬自然語言服務返回低信心度結果
        with patch.object(message_handler.nl_service, 'parse_natural_language') as mock_parse:
            from src.services.nl_to_sql_service import QueryType
            mock_parse.return_value = Mock(
                query_type=QueryType.UNKNOWN,
                confidence=0.1,
                explanation="無法理解查詢意圖"
            )
            
            result = await message_handler.process_message(
                "test_user", "這是一個無法理解的查詢", "test_token"
            )
            
            assert isinstance(result, TextMessage)
            # 應該返回建議訊息
            assert "建議" in result.text or "幫助" in result.text
    
    @pytest.mark.asyncio
    async def test_status_command_flow(self, message_handler):
        """測試狀態指令的完整流程"""
        # 模擬資料庫連接測試
        with patch.object(message_handler.db_service, 'test_connection') as mock_test:
            mock_test.return_value = True
            
            result = await message_handler.process_message(
                "test_user", "/status", "test_token"
            )
            
            assert isinstance(result, TextMessage)
            assert "系統狀態報告" in result.text
            assert "資料庫連接：正常" in result.text
    
    @pytest.mark.asyncio
    async def test_error_recovery_flow(self, message_handler):
        """測試錯誤恢復流程"""
        # 模擬服務拋出異常
        with patch.object(message_handler, '_handle_command') as mock_handle:
            mock_handle.side_effect = Exception("模擬的系統錯誤")
            
            result = await message_handler.process_message(
                "test_user", "/help", "test_token"
            )
            
            assert isinstance(result, TextMessage)
            assert "訊息處理時發生錯誤" in result.text
    
    def test_service_dependencies(self, message_handler):
        """測試服務依賴關係是否正確建立"""
        # 驗證所有服務都已正確初始化
        assert message_handler.ai_model_service is not None
        assert message_handler.nl_service is not None
        assert message_handler.db_service is not None
        assert message_handler.formatter is not None
        
        # 驗證服務間的依賴關係
        assert message_handler.nl_service.ai_service is message_handler.ai_model_service
        
        # 驗證 DatabaseService 具有正確的 MCP 客戶端工廠
        assert callable(message_handler.db_service.mcp_client_factory)
    
    @pytest.mark.asyncio
    async def test_command_routing_comprehensive(self, message_handler):
        """綜合測試所有指令的路由"""
        commands_to_test = [
            ("/help", "使用說明"),
            ("/models", "AI模型狀態"),
            ("/info", "建議查詢"),
        ]
        
        for command, expected_keyword in commands_to_test:
            result = await message_handler.process_message(
                "test_user", command, "test_token"
            )
            
            assert isinstance(result, TextMessage)
            assert expected_keyword in result.text, f"Command {command} failed"