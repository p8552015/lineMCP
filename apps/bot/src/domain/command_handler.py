"""
指令處理器抽象介面
定義 Command Pattern 的基礎架構
"""

from abc import ABC, abstractmethod
from typing import Any

from linebot.v3.messaging import Message


class CommandHandler(ABC):
    """
    指令處理器抽象基類
    實現 Command Pattern，每個具體指令有自己的處理器
    """

    @property
    @abstractmethod
    def command_name(self) -> str:
        """指令名稱"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """指令描述"""
        pass

    @property
    def aliases(self) -> list[str]:
        """指令別名（可選）"""
        return []

    @abstractmethod
    async def handle(self, user_id: str, args: list[str]) -> Message:
        """
        處理指令

        Args:
            user_id: 用戶 ID
            args: 指令參數

        Returns:
            處理結果訊息
        """
        pass

    def validate_args(self, args: list[str]) -> bool:
        """
        驗證參數（可覆寫）

        Args:
            args: 指令參數

        Returns:
            是否有效
        """
        return True

    def get_usage(self) -> str:
        """
        獲取使用說明（可覆寫）

        Returns:
            使用說明
        """
        return f"/{self.command_name}"

    def get_help_text(self) -> str:
        """
        獲取幫助文字

        Returns:
            幫助文字
        """
        usage = self.get_usage()
        description = self.description
        aliases = f" (別名: {', '.join(self.aliases)})" if self.aliases else ""

        return f"**{usage}**{aliases}\n{description}"


class CommandContext:
    """
    指令執行上下文
    提供指令處理器所需的服務和資源
    """

    def __init__(
        self,
        mcp_client_factory: Any,
        ai_model_service: Any,
        nl_service: Any,
        db_service: Any,
        formatter: Any,
        service_factory: Any = None,
        openai_client: Any = None,
    ) -> None:
        """
        初始化指令上下文

        Args:
            mcp_client_factory: MCP 客戶端工廠
            ai_model_service: AI 模型服務
            nl_service: 自然語言服務
            db_service: 資料庫服務
            formatter: 訊息格式化器
            service_factory: 服務工廠（用於依賴注入）
            openai_client: OpenAI 客戶端（可選）
        """
        self.mcp_client_factory = mcp_client_factory
        self.ai_model_service = ai_model_service
        self.nl_service = nl_service
        self.db_service = db_service
        self.formatter = formatter
        self.service_factory = service_factory
        self.openai_client = openai_client

    async def get_mcp_client(self) -> Any:
        """獲取 MCP 客戶端"""
        return await self.mcp_client_factory()


class CommandRegistry:
    """
    指令註冊表
    管理所有可用的指令處理器
    """

    def __init__(self) -> None:
        self._handlers: dict[str, CommandHandler] = {}
        self._aliases: dict[str, str] = {}

    def register(self, handler: CommandHandler) -> None:
        """
        註冊指令處理器

        Args:
            handler: 指令處理器
        """
        command_name = handler.command_name

        if command_name in self._handlers:
            raise ValueError(f"指令 '{command_name}' 已經註冊")

        self._handlers[command_name] = handler

        # 註冊別名
        for alias in handler.aliases:
            if alias in self._aliases:
                raise ValueError(
                    f"別名 '{alias}' 已被指令 '{self._aliases[alias]}' 使用"
                )
            self._aliases[alias] = command_name

    def get_handler(self, command_name: str) -> CommandHandler:
        """
        獲取指令處理器

        Args:
            command_name: 指令名稱或別名

        Returns:
            指令處理器

        Raises:
            KeyError: 找不到指令
        """
        # 首先檢查是否為別名
        actual_command = self._aliases.get(command_name, command_name)

        if actual_command not in self._handlers:
            raise KeyError(f"未找到指令: {command_name}")

        return self._handlers[actual_command]

    def list_commands(self) -> list[CommandHandler]:
        """
        列出所有指令處理器

        Returns:
            指令處理器列表
        """
        return list(self._handlers.values())

    def has_command(self, command_name: str) -> bool:
        """
        檢查是否存在指令

        Args:
            command_name: 指令名稱或別名

        Returns:
            是否存在
        """
        actual_command = self._aliases.get(command_name, command_name)
        return actual_command in self._handlers

    def get_help_text(self) -> str:
        """
        獲取所有指令的幫助文字

        Returns:
            幫助文字
        """
        help_sections : list[Any] = []

        for handler in sorted(self._handlers.values(), key=lambda h: h.command_name):
            help_sections.append(handler.get_help_text())

        return "\n\n".join(help_sections)


# 全域指令註冊表實例
_command_registry: CommandRegistry | None = None


def get_command_registry() -> CommandRegistry:
    """獲取全域指令註冊表"""
    global _command_registry
    if _command_registry is None:
        _command_registry = CommandRegistry()
    return _command_registry
