"""
測試指令處理器基礎架構
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from linebot.v3.messaging import TextMessage

from src.domain.command_handler import (
    CommandHandler, 
    CommandContext, 
    CommandRegistry,
    get_command_registry
)


class MockCommandHandler(CommandHandler):
    """測試用的模擬指令處理器"""
    
    def __init__(self, name: str, description: str = "Mock handler", aliases: list = None):
        self._name = name
        self._description = description
        self._aliases = aliases or []
        
    @property
    def command_name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    @property
    def aliases(self) -> list[str]:
        return self._aliases
    
    async def handle(self, user_id: str, args: list[str]) -> TextMessage:
        return TextMessage(text=f"Handled {self._name}")
    
    def validate_args(self, args: list[str]) -> bool:
        return len(args) <= 2  # 最多允許2個參數
    
    def get_usage(self) -> str:
        return f"/{self._name} [arg1] [arg2]"


class TestCommandHandler:
    """測試指令處理器抽象基類"""
    
    def test_basic_properties(self):
        """測試基本屬性"""
        handler = MockCommandHandler("test", "Test command", ["t", "ts"])
        
        assert handler.command_name == "test"
        assert handler.description == "Test command"
        assert handler.aliases == ["t", "ts"]
    
    def test_default_aliases(self):
        """測試默認別名為空列表"""
        handler = MockCommandHandler("test")
        
        assert handler.aliases == []
    
    def test_default_validate_args(self):
        """測試默認參數驗證總是返回True"""
        # 創建一個不覆寫validate_args的處理器
        class SimpleHandler(CommandHandler):
            @property
            def command_name(self) -> str:
                return "simple"
            
            @property 
            def description(self) -> str:
                return "Simple handler"
            
            async def handle(self, user_id: str, args: list[str]) -> TextMessage:
                return TextMessage(text="Simple")
        
        handler = SimpleHandler()
        
        assert handler.validate_args([]) is True
        assert handler.validate_args(["arg1", "arg2", "arg3"]) is True
    
    def test_custom_validate_args(self):
        """測試自定義參數驗證"""
        handler = MockCommandHandler("test")
        
        assert handler.validate_args([]) is True
        assert handler.validate_args(["arg1"]) is True
        assert handler.validate_args(["arg1", "arg2"]) is True
        assert handler.validate_args(["arg1", "arg2", "arg3"]) is False
    
    def test_default_get_usage(self):
        """測試默認用法說明"""
        # 不覆寫get_usage的處理器
        class DefaultUsageHandler(CommandHandler):
            @property
            def command_name(self) -> str:
                return "default"
            
            @property
            def description(self) -> str:
                return "Default handler"
            
            async def handle(self, user_id: str, args: list[str]) -> TextMessage:
                return TextMessage(text="Default")
        
        handler = DefaultUsageHandler()
        
        assert handler.get_usage() == "/default"
    
    def test_custom_get_usage(self):
        """測試自定義用法說明"""
        handler = MockCommandHandler("test")
        
        assert handler.get_usage() == "/test [arg1] [arg2]"
    
    def test_get_help_text_no_aliases(self):
        """測試無別名的幫助文字"""
        handler = MockCommandHandler("test", "Test command")
        
        help_text = handler.get_help_text()
        
        assert "**" + handler.get_usage() + "**" in help_text
        assert handler.description in help_text
        assert "(別名:" not in help_text
    
    def test_get_help_text_with_aliases(self):
        """測試有別名的幫助文字"""
        handler = MockCommandHandler("test", "Test command", ["t", "ts"])
        
        help_text = handler.get_help_text()
        
        assert "**" + handler.get_usage() + "**" in help_text
        assert handler.description in help_text
        assert "(別名: t, ts)" in help_text

    @pytest.mark.asyncio
    async def test_handle_method(self):
        """測試handle方法"""
        handler = MockCommandHandler("test")
        
        result = await handler.handle("user123", ["arg1"])
        
        assert isinstance(result, TextMessage)
        assert "Handled test" in result.text


class TestCommandContext:
    """測試指令執行上下文"""
    
    def test_initialization(self):
        """測試初始化"""
        mock_mcp_factory = MagicMock()
        mock_ai_service = MagicMock()
        mock_nl_service = MagicMock()
        mock_db_service = MagicMock()
        mock_formatter = MagicMock()
        mock_openai = MagicMock()
        
        context = CommandContext(
            mcp_client_factory=mock_mcp_factory,
            ai_model_service=mock_ai_service,
            nl_service=mock_nl_service,
            db_service=mock_db_service,
            formatter=mock_formatter,
            openai_client=mock_openai
        )
        
        assert context.mcp_client_factory == mock_mcp_factory
        assert context.ai_model_service == mock_ai_service
        assert context.nl_service == mock_nl_service
        assert context.db_service == mock_db_service
        assert context.formatter == mock_formatter
        assert context.openai_client == mock_openai
    
    def test_initialization_without_openai(self):
        """測試不提供OpenAI客戶端的初始化"""
        mock_mcp_factory = MagicMock()
        mock_ai_service = MagicMock()
        mock_nl_service = MagicMock()
        mock_db_service = MagicMock()
        mock_formatter = MagicMock()
        
        context = CommandContext(
            mcp_client_factory=mock_mcp_factory,
            ai_model_service=mock_ai_service,
            nl_service=mock_nl_service,
            db_service=mock_db_service,
            formatter=mock_formatter
        )
        
        assert context.openai_client is None
    
    @pytest.mark.asyncio
    async def test_get_mcp_client(self):
        """測試獲取MCP客戶端"""
        mock_client = AsyncMock()
        mock_mcp_factory = AsyncMock(return_value=mock_client)
        
        context = CommandContext(
            mcp_client_factory=mock_mcp_factory,
            ai_model_service=MagicMock(),
            nl_service=MagicMock(),
            db_service=MagicMock(),
            formatter=MagicMock()
        )
        
        result = await context.get_mcp_client()
        
        assert result == mock_client
        mock_mcp_factory.assert_called_once()


class TestCommandRegistry:
    """測試指令註冊表"""
    
    def setup_method(self):
        """測試設置"""
        self.registry = CommandRegistry()
    
    def test_initialization(self):
        """測試初始化"""
        registry = CommandRegistry()
        
        assert len(registry._handlers) == 0
        assert len(registry._aliases) == 0
    
    def test_register_handler(self):
        """測試註冊處理器"""
        handler = MockCommandHandler("test", "Test command")
        
        self.registry.register(handler)
        
        assert "test" in self.registry._handlers
        assert self.registry._handlers["test"] == handler
    
    def test_register_handler_with_aliases(self):
        """測試註冊帶別名的處理器"""
        handler = MockCommandHandler("test", "Test command", ["t", "ts"])
        
        self.registry.register(handler)
        
        assert "test" in self.registry._handlers
        assert self.registry._aliases["t"] == "test"
        assert self.registry._aliases["ts"] == "test"
    
    def test_register_duplicate_command(self):
        """測試註冊重複指令"""
        handler1 = MockCommandHandler("test", "Test command 1")
        handler2 = MockCommandHandler("test", "Test command 2")
        
        self.registry.register(handler1)
        
        with pytest.raises(ValueError, match="指令 'test' 已經註冊"):
            self.registry.register(handler2)
    
    def test_register_duplicate_alias(self):
        """測試註冊重複別名"""
        handler1 = MockCommandHandler("test1", "Test command 1", ["t"])
        handler2 = MockCommandHandler("test2", "Test command 2", ["t"])
        
        self.registry.register(handler1)
        
        with pytest.raises(ValueError, match="別名 't' 已被指令 'test1' 使用"):
            self.registry.register(handler2)
    
    def test_get_handler_by_name(self):
        """測試通過名稱獲取處理器"""
        handler = MockCommandHandler("test", "Test command")
        self.registry.register(handler)
        
        result = self.registry.get_handler("test")
        
        assert result == handler
    
    def test_get_handler_by_alias(self):
        """測試通過別名獲取處理器"""
        handler = MockCommandHandler("test", "Test command", ["t"])
        self.registry.register(handler)
        
        result = self.registry.get_handler("t")
        
        assert result == handler
    
    def test_get_handler_not_found(self):
        """測試獲取不存在的處理器"""
        with pytest.raises(KeyError, match="未找到指令: unknown"):
            self.registry.get_handler("unknown")
    
    def test_list_commands(self):
        """測試列出所有指令"""
        handler1 = MockCommandHandler("test1", "Test command 1")
        handler2 = MockCommandHandler("test2", "Test command 2")
        
        self.registry.register(handler1)
        self.registry.register(handler2)
        
        commands = self.registry.list_commands()
        
        assert len(commands) == 2
        assert handler1 in commands
        assert handler2 in commands
    
    def test_has_command_by_name(self):
        """測試檢查指令是否存在（通過名稱）"""
        handler = MockCommandHandler("test", "Test command")
        self.registry.register(handler)
        
        assert self.registry.has_command("test") is True
        assert self.registry.has_command("unknown") is False
    
    def test_has_command_by_alias(self):
        """測試檢查指令是否存在（通過別名）"""
        handler = MockCommandHandler("test", "Test command", ["t"])
        self.registry.register(handler)
        
        assert self.registry.has_command("t") is True
        assert self.registry.has_command("unknown") is False
    
    def test_get_help_text(self):
        """測試獲取幫助文字"""
        handler1 = MockCommandHandler("aaa", "AAA command")
        handler2 = MockCommandHandler("bbb", "BBB command")
        
        self.registry.register(handler1)
        self.registry.register(handler2)
        
        help_text = self.registry.get_help_text()
        
        # 應該按字母順序排列
        assert help_text.find("aaa") < help_text.find("bbb")
        assert "AAA command" in help_text
        assert "BBB command" in help_text


class TestGlobalCommandRegistry:
    """測試全域指令註冊表"""
    
    def test_get_command_registry_singleton(self):
        """測試全域註冊表單例模式"""
        # 重置全域變數
        import src.domain.command_handler
        src.domain.command_handler._command_registry = None
        
        registry1 = get_command_registry()
        registry2 = get_command_registry()
        
        assert registry1 is registry2
        assert isinstance(registry1, CommandRegistry)
    
    def test_get_command_registry_reuse_existing(self):
        """測試重用現有的全域註冊表"""
        # 設置現有的註冊表
        existing_registry = CommandRegistry()
        handler = MockCommandHandler("existing", "Existing command")
        existing_registry.register(handler)
        
        import src.domain.command_handler
        src.domain.command_handler._command_registry = existing_registry
        
        registry = get_command_registry()
        
        assert registry is existing_registry
        assert registry.has_command("existing") is True