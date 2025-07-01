"""
幫助指令處理器
處理 /help 指令的幫助訊息顯示
"""

import structlog
from linebot.v3.messaging import Message, TextMessage

from src.domain.command_handler import (
    CommandContext,
    CommandHandler,
    get_command_registry,
)

logger = structlog.get_logger()


class HelpCommandHandler(CommandHandler):
    """幫助指令處理器"""

    def __init__(self, context: CommandContext):
        self.context = context

    @property
    def command_name(self) -> str:
        return "help"

    @property
    def description(self) -> str:
        return "顯示所有可用指令的幫助訊息"

    @property
    def aliases(self) -> list[str]:
        return ["?", "h"]

    def get_usage(self) -> str:
        return "/help [指令名稱]"

    async def handle(self, user_id: str, args: list[str]) -> Message:
        """處理幫助指令"""
        logger.info("顯示幫助訊息", user_id=user_id, args=args)

        if args:
            # 顯示特定指令的幫助
            command_name = args[0]
            return self._get_specific_command_help(command_name)
        else:
            # 顯示所有指令的幫助
            return self._get_all_commands_help()

    def _get_specific_command_help(self, command_name: str) -> TextMessage:
        """獲取特定指令的詳細幫助"""
        registry = get_command_registry()

        try:
            handler = registry.get_handler(command_name)

            response_lines = [
                f"📖 指令幫助：/{handler.command_name}",
                "━━━━━━━━━━━━━━━━━━━━",
                "",
                f"📝 描述：{handler.description}",
                f"💡 用法：{handler.get_usage()}",
            ]

            if handler.aliases:
                response_lines.append(f"🔗 別名：{', '.join(handler.aliases)}")

            # 添加特定指令的額外說明
            extra_help = self._get_extra_help(handler.command_name)
            if extra_help:
                response_lines.extend(["", "📋 詳細說明：", extra_help])

            return TextMessage(text="\n".join(response_lines))

        except KeyError:
            return TextMessage(
                text=(
                    f"❌ 找不到指令：{command_name}\n\n"
                    "💡 使用 /help 查看所有可用指令"
                )
            )

    def _get_all_commands_help(self) -> TextMessage:
        """獲取所有指令的幫助概覽"""
        response_lines = [
            "👋 您好！我是產線管理助手",
            "━━━━━━━━━━━━━━━━━━━━",
            "",
            "🔍 我可以幫您查詢：",
            "   • 機台狀態和效能",
            "   • 故障記錄和分析",
            "   • 生產統計報告",
            "   • 部門運行狀況",
            "",
            "💡 可用指令：",
            "",
        ]

        # 獲取指令註冊表
        registry = get_command_registry()
        commands = registry.list_commands()

        # 按指令名稱排序
        sorted_commands = sorted(commands, key=lambda cmd: cmd.command_name)

        for handler in sorted_commands:
            usage = handler.get_usage()
            desc = handler.description
            aliases = f" ({', '.join(handler.aliases)})" if handler.aliases else ""

            response_lines.append(f"   • {usage}{aliases}")
            response_lines.append(f"     {desc}")
            response_lines.append("")

        response_lines.extend(
            [
                "🌟 自然語言查詢：",
                "   直接描述您想查詢的內容，例如：",
                "   「M001機台狀況如何？」",
                "   「今天的生產統計」",
                "",
                "📞 需要幫助？使用 /help <指令名稱> 查看詳細說明",
            ]
        )

        return TextMessage(text="\n".join(response_lines))

    def _get_extra_help(self, command_name: str) -> str:
        """獲取指令的額外說明"""
        extra_help_map = {
            "sql": (
                "• 只支援 SELECT 查詢以確保資料安全\n"
                "• 查詢結果最多顯示前10行\n"
                "• 示例：/sql SELECT * FROM machines WHERE status='running'"
            ),
            "tables": (
                "• 不帶參數：列出所有資料表\n"
                "• 帶資料表名稱：顯示資料表結構\n"
                "• 示例：/tables machines"
            ),
            "status": (
                "• 顯示系統運行狀態\n"
                "• 包含資料庫連接、服務狀態等資訊\n"
                "• 可用於系統健康檢查"
            ),
            "info": (
                "• 顯示系統配置和版本資訊\n" "• 包含支援的功能列表\n" "• 用於系統診斷"
            ),
            "models": (
                "• 列出所有可用的 AI 模型\n"
                "• 顯示模型狀態和配置\n"
                "• 用於檢查 AI 服務可用性"
            ),
        }

        return extra_help_map.get(command_name, "")
