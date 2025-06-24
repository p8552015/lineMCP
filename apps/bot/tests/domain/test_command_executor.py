"""
測試指令執行器
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from linebot.v3.messaging import TextMessage

from src.domain.command_executor import CommandExecutor
from src.domain.command_handler import CommandContext, CommandHandler
from src.domain.exceptions import CommandParsingException, ValidationException
from src.models.commands import Command


class MockCommandHandler(CommandHandler):
    """測試用的模擬指令處理器"""

    def __init__(self, name: str, aliases: list = None):
        self._name = name
        self._aliases = aliases or []

    @property
    def command_name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"Mock handler for {self._name}"

    @property
    def aliases(self) -> list[str]:
        return self._aliases

    async def handle(self, user_id: str, args: list[str]) -> TextMessage:
        return TextMessage(text=f"Handled {self._name} with args: {args}")

    def validate_args(self, args: list[str]) -> bool:
        return True


class TestCommandExecutor:
    """指令執行器測試"""

    def setup_method(self):
        """測試設置"""
        self.mock_context = MagicMock(spec=CommandContext)

    def test_initialization(self):
        """測試初始化"""
        executor = CommandExecutor(self.mock_context)

        assert executor.context == self.mock_context
        assert executor._initialized is False
        assert executor.registry is not None

    @patch("src.domain.command_executor.get_command_registry")
    def test_initialization_with_registry(self, mock_get_registry):
        """測試使用註冊表初始化"""
        mock_registry = MagicMock()
        mock_get_registry.return_value = mock_registry

        executor = CommandExecutor(self.mock_context)

        assert executor.registry == mock_registry
        mock_get_registry.assert_called_once()

    @patch("src.domain.command_executor.get_command_registry")
    def test_initialize_once(self, mock_get_registry):
        """測試只初始化一次"""
        mock_registry = MagicMock()
        mock_registry.list_commands.return_value = []
        mock_get_registry.return_value = mock_registry

        executor = CommandExecutor(self.mock_context)

        # 第一次初始化
        executor.initialize()
        assert executor._initialized is True

        # 第二次初始化應該不做任何事
        executor.initialize()

        # 確保_register_all_commands只被調用一次
        assert executor._initialized is True

    @patch("src.domain.command_executor.get_command_registry")
    @patch("src.commands.SqlCommandHandler")
    @patch("src.commands.HelpCommandHandler")
    def test_register_all_commands(
        self, mock_help_handler, mock_sql_handler, mock_get_registry
    ):
        """測試註冊所有指令處理器"""
        mock_registry = MagicMock()
        mock_registry.list_commands.return_value = []
        mock_get_registry.return_value = mock_registry

        # 創建模擬處理器實例
        mock_sql_instance = MagicMock()
        mock_help_instance = MagicMock()
        mock_sql_handler.return_value = mock_sql_instance
        mock_help_handler.return_value = mock_help_instance

        executor = CommandExecutor(self.mock_context)
        executor.initialize()

        # 確保註冊方法被調用
        assert mock_registry.register.call_count >= 2

    @pytest.mark.asyncio
    @patch("src.domain.command_executor.parse_command")
    async def test_execute_command_success(self, mock_parse_command):
        """測試成功執行指令"""
        # 設置模擬 - 使用支持的指令名稱
        mock_command = Command(name="help", args=["arg1"])
        mock_parse_command.return_value = mock_command

        mock_handler = AsyncMock(spec=CommandHandler)
        mock_handler.validate_args.return_value = True
        mock_handler.handle.return_value = TextMessage(text="Success")

        mock_registry = MagicMock()
        mock_registry.get_handler.return_value = mock_handler

        executor = CommandExecutor(self.mock_context)
        executor.registry = mock_registry
        executor._initialized = True

        result = await executor.execute_command("user123", "/help arg1")

        assert isinstance(result, TextMessage)
        assert result.text == "Success"
        mock_parse_command.assert_called_once_with("/help arg1")
        mock_registry.get_handler.assert_called_once_with("help")
        mock_handler.validate_args.assert_called_once_with(["arg1"])
        mock_handler.handle.assert_called_once_with("user123", ["arg1"])

    @pytest.mark.asyncio
    @patch("src.domain.command_executor.parse_command")
    async def test_execute_command_parsing_failure(self, mock_parse_command):
        """測試指令解析失敗"""
        mock_parse_command.return_value = None

        executor = CommandExecutor(self.mock_context)
        executor._initialized = True

        with pytest.raises(CommandParsingException):
            await executor.execute_command("user123", "invalid command")

    @pytest.mark.asyncio
    @patch("src.models.commands.parse_command")
    async def test_execute_command_validation_failure(self, mock_parse_command):
        """測試參數驗證失敗"""
        mock_command = Command(name="sql", args=["invalid"])
        mock_parse_command.return_value = mock_command

        mock_handler = MagicMock(spec=CommandHandler)
        mock_handler.validate_args.return_value = False

        mock_registry = MagicMock()
        mock_registry.get_handler.return_value = mock_handler

        executor = CommandExecutor(self.mock_context)
        executor.registry = mock_registry
        executor._initialized = True

        with pytest.raises(ValidationException):
            await executor.execute_command("user123", "/sql invalid")

    @pytest.mark.asyncio
    @patch("src.models.commands.parse_command")
    async def test_execute_command_handler_not_found(self, mock_parse_command):
        """測試找不到指令處理器"""
        mock_command = Command(name="help", args=[])
        mock_parse_command.return_value = mock_command

        mock_registry = MagicMock()
        mock_registry.get_handler.side_effect = KeyError("Command not found")
        mock_registry.list_commands.return_value = [
            MagicMock(command_name="sql"),
            MagicMock(command_name="status"),
        ]

        executor = CommandExecutor(self.mock_context)
        executor.registry = mock_registry
        executor._initialized = True

        with pytest.raises(CommandParsingException) as exc_info:
            await executor.execute_command("user123", "/help")

        assert "未知的指令" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("src.models.commands.parse_command")
    async def test_execute_command_handler_exception(self, mock_parse_command):
        """測試指令處理器拋出異常"""
        mock_command = Command(name="status", args=[])
        mock_parse_command.return_value = mock_command

        mock_handler = AsyncMock(spec=CommandHandler)
        mock_handler.validate_args.return_value = True
        mock_handler.handle.side_effect = Exception("Handler error")

        mock_registry = MagicMock()
        mock_registry.get_handler.return_value = mock_handler

        executor = CommandExecutor(self.mock_context)
        executor.registry = mock_registry
        executor._initialized = True

        with pytest.raises(Exception) as exc_info:
            await executor.execute_command("user123", "/status")

        assert "Handler error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_command_auto_initialize(self):
        """測試自動初始化"""
        mock_registry = MagicMock()
        mock_registry.list_commands.return_value = []

        executor = CommandExecutor(self.mock_context)
        executor.registry = mock_registry

        # 模擬parse_command返回None以觸發初始化但不執行指令
        with patch("src.models.commands.parse_command", return_value=None):
            with pytest.raises(CommandParsingException):
                await executor.execute_command("user123", "invalid")

        assert executor._initialized is True

    def test_has_command_auto_initialize(self):
        """測試has_command會自動初始化"""
        mock_registry = MagicMock()
        mock_registry.list_commands.return_value = []
        mock_registry.has_command.return_value = True

        executor = CommandExecutor(self.mock_context)
        executor.registry = mock_registry

        result = executor.has_command("test")

        assert result is True
        assert executor._initialized is True
        mock_registry.has_command.assert_called_once_with("test")

    def test_list_commands_auto_initialize(self):
        """測試list_commands會自動初始化"""
        mock_handlers = [MagicMock(), MagicMock()]
        mock_registry = MagicMock()
        mock_registry.list_commands.return_value = mock_handlers

        executor = CommandExecutor(self.mock_context)
        executor.registry = mock_registry

        result = executor.list_commands()

        assert result == mock_handlers
        assert executor._initialized is True

    def test_get_help_text_auto_initialize(self):
        """測試get_help_text會自動初始化"""
        mock_registry = MagicMock()
        mock_registry.list_commands.return_value = []
        mock_registry.get_help_text.return_value = "Help text"

        executor = CommandExecutor(self.mock_context)
        executor.registry = mock_registry

        result = executor.get_help_text()

        assert result == "Help text"
        assert executor._initialized is True

    def test_get_command_info_auto_initialize(self):
        """測試get_command_info會自動初始化"""
        mock_cmd1 = MagicMock()
        mock_cmd1.command_name = "test1"
        mock_cmd1.description = "Test 1"
        mock_cmd1.aliases = ["t1"]

        mock_cmd2 = MagicMock()
        mock_cmd2.command_name = "test2"
        mock_cmd2.description = "Test 2"
        mock_cmd2.aliases = []

        mock_registry = MagicMock()
        mock_registry.list_commands.return_value = [mock_cmd1, mock_cmd2]

        executor = CommandExecutor(self.mock_context)
        executor.registry = mock_registry

        result = executor.get_command_info()

        assert executor._initialized is True
        assert result["total_commands"] == 2
        assert result["total_aliases"] == 1
        assert len(result["commands"]) == 2
        assert result["commands"][0]["name"] == "test1"
        assert result["commands"][1]["aliases"] == []
