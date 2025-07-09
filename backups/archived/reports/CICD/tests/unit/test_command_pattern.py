"""
Command Pattern 測試
驗證指令處理器和指令執行器的功能
"""

from unittest.mock import AsyncMock, Mock

import pytest
from linebot.v3.messaging import TextMessage

from src.domain.command_executor import CommandExecutor
from src.domain.command_handler import (
    CommandContext,
    CommandHandler,
    CommandRegistry,
    get_command_registry,
)
from src.domain.exceptions import CommandParsingError


class MockCommandHandler(CommandHandler):
    """測試用的模擬指令處理器"""

    def __init__(self, name: str, description: str, aliases: list[str] = None):
        self.name = name
        self.desc = description
        self._aliases = aliases or []
        self.handle_called = False

    @property
    def command_name(self) -> str:
        return self.name

    @property
    def description(self) -> str:
        return self.desc

    @property
    def aliases(self) -> list[str]:
        return self._aliases

    async def handle(self, user_id: str, args: list[str]) -> TextMessage:
        self.handle_called = True
        return TextMessage(text=f"Mock command {self.name} executed")


class TestCommandHandler:
    """測試指令處理器基礎功能"""

    def test_command_handler_properties(self):
        """測試指令處理器的基本屬性"""
        handler = MockCommandHandler("test", "Test command")

        assert handler.command_name == "test"
        assert handler.description == "Test command"
        assert handler.aliases == []
        assert handler.get_usage() == "/test"
        assert handler.validate_args([]) is True

    def test_command_handler_help_text(self):
        """測試幫助文字生成"""
        handler = MockCommandHandler("test", "Test command")
        help_text = handler.get_help_text()

        assert f"**/{handler.command_name}**" in help_text
        assert handler.description in help_text

    @pytest.mark.asyncio
    async def test_command_handler_execution(self):
        """測試指令處理器執行"""
        handler = MockCommandHandler("test", "Test command")

        result = await handler.handle("user_1", ["arg1", "arg2"])

        assert isinstance(result, TextMessage)
        assert handler.handle_called is True
        assert "Mock command test executed" in result.text


class TestCommandContext:
    """測試指令上下文"""

    def test_command_context_initialization(self):
        """測試指令上下文初始化"""
        mock_mcp_factory = AsyncMock()
        mock_ai_service = Mock()
        mock_nl_service = Mock()
        mock_db_service = Mock()
        mock_formatter = Mock()
        # mock_flex_builder 已移除

        context = CommandContext(
            mcp_client_factory=mock_mcp_factory,
            ai_model_service=mock_ai_service,
            nl_service=mock_nl_service,
            db_service=mock_db_service,
            formatter=mock_formatter,
            openai_client=Mock(),
        )

        assert context.mcp_client_factory == mock_mcp_factory
        assert context.ai_model_service == mock_ai_service
        assert context.nl_service == mock_nl_service
        assert context.db_service == mock_db_service
        assert context.formatter == mock_formatter

    @pytest.mark.asyncio
    async def test_command_context_get_mcp_client(self):
        """測試獲取 MCP 客戶端"""
        mock_client = AsyncMock()
        mock_factory = AsyncMock(return_value=mock_client)

        context = CommandContext(
            mcp_client_factory=mock_factory,
            ai_model_service=Mock(),
            nl_service=Mock(),
            db_service=Mock(),
            formatter=Mock(),
            openai_client=Mock(),
        )

        client = await context.get_mcp_client()

        assert client == mock_client
        mock_factory.assert_called_once()


class TestCommandRegistry:
    """測試指令註冊表"""

    def test_command_registry_initialization(self):
        """測試指令註冊表初始化"""
        registry = CommandRegistry()

        assert len(registry.list_commands()) == 0
        assert registry.has_command("nonexistent") is False

    def test_command_registry_register_handler(self):
        """測試註冊指令處理器"""
        registry = CommandRegistry()
        handler = MockCommandHandler("test", "Test command")

        registry.register(handler)

        assert registry.has_command("test") is True
        assert len(registry.list_commands()) == 1
        assert registry.get_handler("test") == handler

    def test_command_registry_register_with_aliases(self):
        """測試註冊帶別名的指令處理器"""
        registry = CommandRegistry()

        # 創建帶別名的處理器
        handler = MockCommandHandler("test", "Test command", ["t", "testing"])

        registry.register(handler)

        # 測試主名稱和別名都能找到
        assert registry.has_command("test") is True
        assert registry.has_command("t") is True
        assert registry.has_command("testing") is True
        assert registry.get_handler("t") == handler
        assert registry.get_handler("testing") == handler

    def test_command_registry_duplicate_command(self):
        """測試重複註冊指令"""
        registry = CommandRegistry()
        handler1 = MockCommandHandler("test", "Test command 1")
        handler2 = MockCommandHandler("test", "Test command 2")

        registry.register(handler1)

        with pytest.raises(ValueError, match="指令 'test' 已經註冊"):
            registry.register(handler2)

    def test_command_registry_duplicate_alias(self):
        """測試重複的別名"""
        registry = CommandRegistry()

        handler1 = MockCommandHandler("test1", "Test command 1", ["t"])
        handler2 = MockCommandHandler("test2", "Test command 2", ["t"])

        registry.register(handler1)

        with pytest.raises(ValueError, match="別名 't' 已被指令 'test1' 使用"):
            registry.register(handler2)

    def test_command_registry_get_nonexistent_handler(self):
        """測試獲取不存在的指令處理器"""
        registry = CommandRegistry()

        with pytest.raises(KeyError, match="未找到指令: nonexistent"):
            registry.get_handler("nonexistent")

    def test_command_registry_help_text(self):
        """測試獲取幫助文字"""
        registry = CommandRegistry()

        handler1 = MockCommandHandler("test1", "Test command 1")
        handler2 = MockCommandHandler("test2", "Test command 2")

        registry.register(handler1)
        registry.register(handler2)

        help_text = registry.get_help_text()

        assert "test1" in help_text
        assert "test2" in help_text
        assert "Test command 1" in help_text
        assert "Test command 2" in help_text


class TestCommandExecutor:
    """測試指令執行器"""

    @pytest.fixture
    def mock_context(self):
        """創建模擬的指令上下文"""
        return CommandContext(
            mcp_client_factory=AsyncMock(),
            ai_model_service=Mock(),
            nl_service=Mock(),
            db_service=Mock(),
            formatter=Mock(),
            openai_client=Mock(),
        )

    def test_command_executor_initialization(self, mock_context):
        """測試指令執行器初始化"""
        executor = CommandExecutor(mock_context)

        assert executor.context == mock_context
        assert executor._initialized is False

    def test_command_executor_initialize(self, mock_context):
        """測試指令執行器初始化過程"""
        executor = CommandExecutor(mock_context)

        # 初始化指令執行器
        executor.initialize()

        assert executor._initialized is True
        assert len(executor.list_commands()) > 0

    @pytest.mark.asyncio
    async def test_command_executor_execute_valid_command(self, mock_context):
        """測試執行有效指令"""
        executor = CommandExecutor(mock_context)

        # 使用新的註冊表避免衝突
        executor.registry = CommandRegistry()

        # 手動註冊一個支援的指令
        test_handler = MockCommandHandler("help", "Help command")
        executor.registry.register(test_handler)
        executor._initialized = True

        result = await executor.execute_command("user_1", "/help")

        assert isinstance(result, TextMessage)
        assert test_handler.handle_called is True

    @pytest.mark.asyncio
    async def test_command_executor_execute_invalid_command(self, mock_context):
        """測試執行無效指令"""
        executor = CommandExecutor(mock_context)
        executor._initialized = True

        with pytest.raises(CommandParsingError):
            await executor.execute_command("user_1", "not a command")

    @pytest.mark.asyncio
    async def test_command_executor_execute_unknown_command(self, mock_context):
        """測試執行未知指令"""
        executor = CommandExecutor(mock_context)
        executor._initialized = True

        with pytest.raises(CommandParsingError):
            await executor.execute_command("user_1", "/unknown")

    def test_command_executor_has_command(self, mock_context):
        """測試檢查指令是否存在"""
        executor = CommandExecutor(mock_context)

        # 使用新的註冊表避免衝突
        executor.registry = CommandRegistry()

        # 手動註冊一個測試指令
        test_handler = MockCommandHandler("help", "Help command")
        executor.registry.register(test_handler)
        executor._initialized = True

        assert executor.has_command("help") is True
        assert executor.has_command("nonexistent") is False

    def test_command_executor_get_command_info(self, mock_context):
        """測試獲取指令統計資訊"""
        executor = CommandExecutor(mock_context)

        # 使用新的註冊表避免衝突
        executor.registry = CommandRegistry()

        # 手動註冊測試指令
        handler1 = MockCommandHandler("test1", "Test command 1", ["t1"])
        handler2 = MockCommandHandler("test2", "Test command 2", ["t2", "test"])

        executor.registry.register(handler1)
        executor.registry.register(handler2)
        executor._initialized = True

        info = executor.get_command_info()

        assert info["total_commands"] == 2
        assert info["total_aliases"] == 3
        assert len(info["commands"]) == 2


class TestGlobalCommandRegistry:
    """測試全域指令註冊表"""

    def test_get_global_command_registry_singleton(self):
        """測試全域指令註冊表的單例模式"""
        registry1 = get_command_registry()
        registry2 = get_command_registry()

        assert registry1 is registry2
        assert isinstance(registry1, CommandRegistry)
