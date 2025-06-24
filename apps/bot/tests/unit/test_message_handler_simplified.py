"""
MessageHandler 簡化測試
專注於測試核心功能而不被複雜的依賴阻礙
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from linebot.v3.messaging import TextMessage

# 確保可以導入 MessageHandler
try:
    from src.services.message_handler import MessageHandler
    from src.models.commands import Command, parse_command
except ImportError as e:
    pytest.skip(f"Cannot import required modules: {e}", allow_module_level=True)


class TestMessageHandlerCore:
    """測試 MessageHandler 的核心功能"""
    
    def test_parse_command_functionality(self):
        """測試指令解析功能"""
        # 測試 SQL 指令
        sql_command = parse_command("/sql SELECT * FROM machines")
        assert sql_command is not None
        assert sql_command.name == "sql"
        assert sql_command.args == ["SELECT", "*", "FROM", "machines"]
        
        # 測試 help 指令
        help_command = parse_command("/help")
        assert help_command is not None
        assert help_command.name == "help"
        assert help_command.args == []
        
        # 測試非指令文字
        no_command = parse_command("這是一般對話")
        assert no_command is None
    
    def test_greeting_detection(self):
        """測試問候語檢測"""
        handler = MessageHandler()
        
        # 測試中文問候語
        assert handler._is_greeting("你好")
        assert handler._is_greeting("哈囉")
        assert handler._is_greeting("早安")
        
        # 測試英文問候語
        assert handler._is_greeting("hello")
        assert handler._is_greeting("Hi there")
        
        # 測試非問候語（注意：現有實現使用 'greeting in text' 所以需要更精確的測試）
        assert not handler._is_greeting("查詢機台狀態")
        # 注意：由於現有實現的問題，包含問候語片段的文字會被誤判
        # 這是需要重構修正的問題之一
    
    def test_machine_query_detection(self):
        """測試機台查詢檢測（向後相容性）"""
        handler = MessageHandler()
        
        # 根據程式碼，所有查詢都返回 True（進入自然語言處理）
        assert handler._is_machine_query("M001機台狀況")
        assert handler._is_machine_query("任何文字")
        assert handler._is_machine_query("/sql SELECT")
    
    @pytest.mark.asyncio
    async def test_mcp_client_initialization(self):
        """測試 MCP 客戶端初始化邏輯"""
        handler = MessageHandler()
        
        # 初始狀態
        assert handler._mcp_client is None
        
        # 模擬獲取客戶端（這會觸發真實初始化，但我們只測試邏輯）
        with patch('src.services.message_handler.get_unified_mcp_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            # 第一次調用
            client1 = await handler._get_mcp_client()
            assert client1 is mock_client
            assert handler._mcp_client is mock_client
            
            # 第二次調用應該返回緩存的實例
            client2 = await handler._get_mcp_client()
            assert client2 is mock_client
            assert mock_get_client.call_count == 1  # 只調用一次
    
    @pytest.mark.asyncio
    async def test_process_message_command_routing(self):
        """測試訊息處理的指令路由邏輯"""
        handler = MessageHandler()
        
        # 模擬所有依賴
        with patch.object(handler, '_handle_command') as mock_handle_command, \
             patch.object(handler, '_handle_natural_language') as mock_handle_nl:
            
            mock_handle_command.return_value = TextMessage(text="指令回應")
            mock_handle_nl.return_value = TextMessage(text="自然語言回應")
            
            # 測試指令路由
            result = await handler.process_message("user1", "/help", "token1")
            mock_handle_command.assert_called_once()
            mock_handle_nl.assert_not_called()
            assert result.text == "指令回應"
            
            # 重置 mock
            mock_handle_command.reset_mock()
            mock_handle_nl.reset_mock()
            
            # 測試自然語言路由
            result = await handler.process_message("user1", "機台狀況如何", "token1")
            mock_handle_command.assert_not_called()
            mock_handle_nl.assert_called_once()
            assert result.text == "自然語言回應"
    
    @pytest.mark.asyncio
    async def test_command_handler_routing(self):
        """測試指令處理器的路由邏輯"""
        handler = MessageHandler()
        
        # 模擬各種指令處理方法
        with patch.object(handler, '_handle_sql_command') as mock_sql, \
             patch.object(handler, '_handle_help_command') as mock_help, \
             patch.object(handler, '_handle_status_command') as mock_status:
            
            mock_sql.return_value = TextMessage(text="SQL回應")
            mock_help.return_value = TextMessage(text="幫助回應")
            mock_status.return_value = TextMessage(text="狀態回應")
            
            # 測試 SQL 指令
            sql_cmd = Command(name="sql", args=["SELECT * FROM machines"])
            result = await handler._handle_command("user1", sql_cmd)
            mock_sql.assert_called_once_with("user1", ["SELECT * FROM machines"])
            assert result.text == "SQL回應"
            
            # 測試 help 指令
            help_cmd = Command(name="help", args=[])
            result = await handler._handle_command("user1", help_cmd)
            mock_help.assert_called_once_with("user1", [])
            assert result.text == "幫助回應"
            
            # 測試未知指令
            unknown_cmd = Command(name="unknown", args=[])
            result = await handler._handle_command("user1", unknown_cmd)
            assert "未知的指令" in result.text
    
    @pytest.mark.asyncio
    async def test_help_command_response(self):
        """測試幫助指令的回應內容"""
        handler = MessageHandler()
        
        # 直接調用真實的 _handle_help_command 方法
        result = await handler._handle_help_command("user1", [])
        assert isinstance(result, TextMessage)
        assert "LINE MCP Bot 使用說明" in result.text
    
    def test_greeting_response(self):
        """測試問候語回應"""
        handler = MessageHandler()
        
        result = handler._handle_greeting()
        assert isinstance(result, TextMessage)
        assert "您好！我是產線管理助手" in result.text
        assert "機台狀態和效能" in result.text
    
    @pytest.mark.asyncio
    async def test_error_handling_in_process_message(self):
        """測試 process_message 中的錯誤處理"""
        handler = MessageHandler()
        
        # 模擬 _handle_command 拋出異常
        with patch.object(handler, '_handle_command') as mock_handle:
            mock_handle.side_effect = Exception("測試異常")
            
            # 應該捕獲異常並返回錯誤訊息
            result = await handler.process_message("user1", "/help", "token1")
            assert isinstance(result, TextMessage)
            assert "訊息處理時發生錯誤" in result.text
    
    def test_service_initialization(self):
        """測試服務初始化"""
        handler = MessageHandler()
        
        # 檢查所有服務都已初始化
        assert handler.openai_client is not None
        assert handler.flex_builder is not None
        assert handler.ai_model_service is not None
        assert handler.nl_service is not None
        assert handler.db_service is not None
        assert handler.formatter is not None
        
        # 檢查服務類型
        from src.services.openai_client import OpenAIClient
        from src.services.ai_model_service_enhanced import EnhancedAIModelService
        from apps.bot.backup.nl_to_sql_service import NaturalLanguageToSQLService
        from src.services.database_service import DatabaseService
        from src.services.message_formatter import MessageFormatter
        from src.services.flex_builder import FlexBuilder
        
        assert isinstance(handler.openai_client, OpenAIClient)
        assert isinstance(handler.ai_model_service, EnhancedAIModelService)
        assert isinstance(handler.nl_service, NaturalLanguageToSQLService)
        assert isinstance(handler.db_service, DatabaseService)
        assert isinstance(handler.formatter, MessageFormatter)
        assert isinstance(handler.flex_builder, FlexBuilder)