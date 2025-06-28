#!/usr/bin/env python3
"""
PostgreSQL 查詢命令處理器
整合到 LINE Bot 指令系統中
包含增強的延遲初始化錯誤處理
"""

import structlog
from linebot.v3.messaging import Message, TextMessage

from src.commands.postgres_command import PostgreSQLCommand
from src.domain.command_handler import CommandContext, CommandHandler
from src.infrastructure.lazy_initialization_error_handler import (
    LazyServiceConfig,
    get_lazy_service_registry,
)

logger = structlog.get_logger()


class PostgresCommandHandler(CommandHandler):
    """PostgreSQL 查詢命令處理器"""

    def __init__(self, context: CommandContext):
        """初始化 PostgreSQL 命令處理器（增強錯誤處理）"""
        self.context = context
        self.postgres_command = None

        # 創建延遲初始化錯誤處理器
        config = LazyServiceConfig(
            service_name="PostgreSQLCommand",
            max_retry_attempts=3,
            retry_delay_base=1.0,
            timeout_seconds=10.0,
            auto_recovery=True,
            user_notifications=True,
        )

        # 註冊到全局註冊表
        registry = get_lazy_service_registry()
        self.error_handler = registry.register_service("PostgreSQLCommand", config)

        # 如果 service_factory 可用，嘗試立即初始化
        if context.service_factory is not None:
            self._try_immediate_initialization()
        else:
            logger.info("🐘 PostgreSQL 命令處理器已初始化（延遲創建，含錯誤處理）")

    def _try_immediate_initialization(self):
        """嘗試立即初始化"""
        try:
            self.postgres_command = PostgreSQLCommand(self.context.service_factory)
            logger.info("🐘 PostgreSQL 命令處理器已初始化")
        except Exception as e:
            logger.warning(f"立即初始化失敗，將使用延遲初始化: {e}")
            self.postgres_command = None

    async def _safe_lazy_initialization(self) -> tuple[bool, any, str]:
        """安全的延遲初始化"""

        def create_postgres_command():
            if self.context.service_factory is None:
                raise RuntimeError("service_factory 不可用")
            return PostgreSQLCommand(self.context.service_factory)

        success, result, user_message = await self.error_handler.safe_initialize(
            create_postgres_command
        )

        if success:
            self.postgres_command = result

        return success, result, user_message

    def get_initialization_status(self) -> dict:
        """獲取初始化狀態"""
        return {
            "postgres_command_ready": self.postgres_command is not None,
            "service_factory_available": self.context.service_factory is not None,
            "error_handler_status": self.error_handler.get_health_status(),
        }

    @property
    def command_name(self) -> str:
        """命令名稱"""
        return "pg"

    @property
    def description(self) -> str:
        """命令描述"""
        return "PostgreSQL 數據庫查詢"

    @property
    def command_description(self) -> str:
        """命令描述（向下兼容）"""
        return self.description

    @property
    def command_usage(self) -> str:
        """命令使用方法"""
        return """
🐘 PostgreSQL 查詢命令

使用方法:
• /pg <查詢內容>
• /pg help - 顯示詳細幫助
• /pg 員工數 - 執行預定義查詢
• /pg 有多少員工在工程部 - 自然語言查詢

預定義查詢關鍵字:
• 員工數、部門統計、機台狀態、產品庫存
• 高薪員工、缺貨產品、運行機台、待處理訂單
"""

    async def handle(self, user_id: str, args: list[str]) -> Message:
        """
        處理 PostgreSQL 查詢命令（增強錯誤處理）

        Args:
            args: 命令參數
            user_id: 用戶 ID

        Returns:
            處理結果訊息
        """
        try:
            # 使用增強的延遲初始化
            if self.postgres_command is None:
                success, result, user_message = await self._safe_lazy_initialization()

                if not success:
                    # 初始化失敗，返回用戶友好的錯誤消息
                    error_text = user_message or "❌ PostgreSQL 服務暫時不可用，請稍後再試"
                    return TextMessage(text=error_text)

                logger.info("🐘 PostgreSQL 命令延遲初始化完成")
            if not args:
                return TextMessage(text=self.command_usage)

            # 處理幫助命令
            if args[0].lower() in ["help", "幫助", "?", "？"]:
                # 對於幫助命令，如果 postgres_command 不可用，返回基本使用說明
                if self.postgres_command is None:
                    return TextMessage(text=self.command_usage)

                help_text = self.postgres_command.get_help_text()
                return TextMessage(text=help_text)

            # 合併所有參數為查詢字符串
            query = " ".join(args)

            logger.info("🔍 處理 PostgreSQL 查詢命令", query=query, user_id=user_id)

            # 執行 PostgreSQL 查詢
            result = await self.postgres_command.execute(query, user_id)

            if result.get("success"):
                response_text = result.get("display_text", "查詢執行成功")

                # 添加查詢信息
                if result.get("sql_query"):
                    response_text += f"\n\n🔍 執行的 SQL:\n{result['sql_query']}"

                return TextMessage(text=response_text)
            else:
                error_text = f"❌ 查詢失敗: {result.get('error', '未知錯誤')}"

                # 添加建議
                suggestions = result.get("suggestions", [])
                if suggestions:
                    error_text += "\n\n💡 建議:\n" + "\n".join(suggestions)

                return TextMessage(text=error_text)

        except Exception as e:
            logger.error("❌ PostgreSQL 命令處理失敗", error=str(e), exc_info=True)
            error_text = f"❌ 命令處理失敗: {str(e)}\n\n使用 '/pg help' 查看使用說明"
            return TextMessage(text=error_text)

    def get_supported_commands(self) -> list[str]:
        """獲取支援的命令列表"""
        return ["pg", "postgres", "postgresql", "數據庫", "查詢"]
