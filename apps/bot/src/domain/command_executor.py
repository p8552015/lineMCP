"""
指令執行器
負責協調指令處理器的註冊和執行
"""

import structlog
from linebot.v3.messaging import Message

from src.domain.command_handler import (
    CommandContext,
    CommandHandler,
    get_command_registry,
)
from src.domain.exceptions import create_command_error, create_validation_error

# 移除對 models.commands 的依賴，改用內建解析邏輯

logger = structlog.get_logger()


class CommandExecutor:
    """
    指令執行器
    整合 Command Pattern 的核心協調器
    """

    def __init__(self, context: CommandContext):
        """
        初始化指令執行器

        Args:
            context: 指令執行上下文
        """
        self.context = context
        self.registry = get_command_registry()
        self._initialized = False

    def initialize(self):
        """初始化並註冊所有指令處理器"""
        if self._initialized:
            return

        logger.info("初始化指令執行器")

        # 註冊所有指令處理器
        self._register_all_commands()

        self._initialized = True
        logger.info(
            f"指令執行器初始化完成，註冊了 {len(self.registry.list_commands())} 個指令"
        )

    def parse_and_validate_command(
        self, message_text: str
    ) -> tuple[str, list[str]] | None:
        """
        解析並驗證指令，只依賴註冊表中的指令

        Args:
            message_text: 訊息文字

        Returns:
            tuple[str, list[str]] | None: (指令名稱, 參數列表) 或 None
                (如果不是有效指令)
        """
        message = message_text.strip()

        # 檢查是否為指令格式
        if not message.startswith("/"):
            return None

        # 解析指令和參數
        parts = message.split()
        command_name = parts[0][1:].lower()  # 移除 '/' 並轉為小寫
        args = parts[1:] if len(parts) > 1 else []

        # 確保已初始化
        if not self._initialized:
            self.initialize()

        # 驗證指令是否在註冊表中存在（包括別名）
        if not self.registry.has_command(command_name):
            return None

        return command_name, args

    def _register_all_commands(self):
        """註冊所有指令處理器"""
        from src.commands import (
            HelpCommandHandler,
            InfoCommandHandler,
            ModelsCommandHandler,
            PostgresCommandHandler,
            SqlCommandHandler,
            StatusCommandHandler,
            TablesCommandHandler,
        )

        # 創建並註冊所有指令處理器
        handlers = [
            SqlCommandHandler(self.context),
            TablesCommandHandler(self.context),
            StatusCommandHandler(self.context),
            HelpCommandHandler(self.context),
            InfoCommandHandler(self.context),
            ModelsCommandHandler(self.context),
            PostgresCommandHandler(self.context),
        ]

        for handler in handlers:
            try:
                self.registry.register(handler)
                logger.debug(f"註冊指令處理器: {handler.command_name}")
            except ValueError as e:
                logger.error(f"註冊指令處理器失敗: {e}")

    async def execute_command(self, user_id: str, message_text: str) -> Message:
        """
        執行指令

        Args:
            user_id: 用戶 ID
            message_text: 訊息文字

        Returns:
            處理結果訊息

        Raises:
            CommandParsingException: 指令解析失敗
            ValidationException: 參數驗證失敗
        """
        # 確保已初始化
        if not self._initialized:
            self.initialize()

        # 解析指令
        parsed_result = self.parse_and_validate_command(message_text)
        if not parsed_result:
            raise create_command_error(message_text, "無法解析為有效指令")

        command_name, args = parsed_result

        logger.info("執行指令", user_id=user_id, command=command_name, args=args)

        try:
            # 獲取指令處理器
            handler = self.registry.get_handler(command_name)

            # 驗證參數
            if not handler.validate_args(args):
                raise create_validation_error(
                    f"command_{command_name}_args",
                    args,
                    f"指令 /{command_name} 的參數無效",
                )

            # 執行指令
            result = await handler.handle(user_id, args)

            logger.info("指令執行成功", user_id=user_id, command=command_name)

            return result

        except KeyError as e:
            # 指令不存在
            available_commands = [h.command_name for h in self.registry.list_commands()]

            logger.warning(
                "未知指令", command=command_name, available_commands=available_commands
            )

            raise create_command_error(
                command_name,
                f"未知的指令，可用指令：{', '.join(available_commands[:5])}",
            ) from e

        except Exception as e:
            # 指令執行失敗
            logger.error(
                "指令執行失敗",
                user_id=user_id,
                command=command_name,
                error=str(e),
                exc_info=True,
            )
            raise

    def has_command(self, command_name: str) -> bool:
        """
        檢查是否存在指令

        Args:
            command_name: 指令名稱

        Returns:
            是否存在
        """
        if not self._initialized:
            self.initialize()

        return self.registry.has_command(command_name)

    def list_commands(self) -> list[CommandHandler]:
        """
        列出所有註冊的指令處理器

        Returns:
            指令處理器列表
        """
        if not self._initialized:
            self.initialize()

        return self.registry.list_commands()

    def get_help_text(self) -> str:
        """
        獲取所有指令的幫助文字

        Returns:
            幫助文字
        """
        if not self._initialized:
            self.initialize()

        return self.registry.get_help_text()

    def get_command_info(self) -> dict:
        """
        獲取指令統計資訊

        Returns:
            指令統計資訊
        """
        if not self._initialized:
            self.initialize()

        commands = self.list_commands()

        total_aliases = sum(len(cmd.aliases) for cmd in commands)

        return {
            "total_commands": len(commands),
            "total_aliases": total_aliases,
            "commands": [
                {
                    "name": cmd.command_name,
                    "description": cmd.description,
                    "aliases": cmd.aliases,
                }
                for cmd in commands
            ],
        }
