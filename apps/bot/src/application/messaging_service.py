"""
訊息處理應用服務
負責協調 LINE 訊息的處理流程
"""

from typing import Any

import structlog
from linebot.v3.messaging import Message, TextMessage

from src.domain.command_executor import CommandExecutor
from src.domain.command_handler import CommandContext
from src.models.commands import parse_command

from .base_service import BaseApplicationService

logger = structlog.get_logger()


class MessagingApplicationService(BaseApplicationService):
    """
    訊息處理應用服務

    職責：
    - 協調指令處理和自然語言處理
    - 管理訊息處理工作流
    - 提供統一的訊息處理介面
    - 處理用戶會話狀態
    """

    def __init__(self, command_context: CommandContext, nl_service, message_formatter):
        """
        初始化訊息處理服務

        Args:
            command_context: 指令處理上下文
            nl_service: 自然語言處理服務
            message_formatter: 訊息格式化器
        """
        super().__init__("messaging")
        self.command_context = command_context
        self.nl_service = nl_service
        self.message_formatter = message_formatter

        # 指令執行器（延遲初始化）
        self._command_executor: CommandExecutor | None = None

        # 用戶會話管理
        self._user_sessions: dict[str, dict[str, Any]] = {}

        # 處理統計
        self._stats = {
            "total_messages": 0,
            "command_messages": 0,
            "natural_language_messages": 0,
            "error_messages": 0,
        }

    async def _initialize_service(self) -> None:
        """初始化訊息處理服務"""
        # 初始化指令執行器
        self._command_executor = CommandExecutor(self.command_context)
        
        # 同步初始化方法
        if hasattr(self._command_executor, 'initialize'):
            self._command_executor.initialize()

        self.logger.info("指令執行器已初始化")

    async def process_message(
        self,
        user_id: str,
        message_text: str,
        reply_token: str,
        additional_context: dict[str, Any] | None = None,
    ) -> Message:
        """
        處理訊息的主要入口點

        Args:
            user_id: 用戶 ID
            message_text: 訊息內容
            reply_token: 回覆 token
            additional_context: 額外的上下文資訊

        Returns:
            處理結果訊息
        """
        if not self._initialized:
            await self.initialize()

        self._stats["total_messages"] += 1

        try:
            # 更新用戶會話
            self._update_user_session(user_id, message_text, additional_context)

            # 創建帶上下文的 logger
            context_logger = self.logger.bind(
                user_id=user_id, message_length=len(message_text)
            )
            context_logger.info("開始處理訊息")

            # 解析訊息類型
            message_type = self._classify_message(message_text)

            if message_type == "command":
                self._stats["command_messages"] += 1
                result = await self._process_command_message(user_id, message_text)
            else:
                self._stats["natural_language_messages"] += 1
                result = await self._process_natural_language_message(
                    user_id, message_text
                )

            # 更新會話結果
            self._update_session_result(user_id, result, success=True)

            self.logger.info("訊息處理完成")
            return result

        except Exception as e:
            self._stats["error_messages"] += 1
            self.logger.error("訊息處理失敗", error=str(e), exc_info=True)

            # 更新會話錯誤
            self._update_session_result(user_id, None, success=False, error=str(e))

            # 使用統一錯誤處理
            from src.infrastructure.error_handler import handle_error_gracefully

            return handle_error_gracefully(
                e,
                {
                    "user_id": user_id,
                    "message_text": message_text,
                    "service": "messaging",
                },
            )

    def _classify_message(self, message_text: str) -> str:
        """
        分類訊息類型

        Args:
            message_text: 訊息內容

        Returns:
            訊息類型: "command" 或 "natural_language"
        """
        command = parse_command(message_text)
        return "command" if command else "natural_language"

    async def _process_command_message(
        self, user_id: str, message_text: str
    ) -> Message:
        """
        處理指令訊息

        Args:
            user_id: 用戶 ID
            message_text: 指令訊息

        Returns:
            處理結果
        """
        self.logger.info("處理指令訊息", message_text=message_text[:50])

        if not self._command_executor:
            raise RuntimeError("指令執行器未初始化")

        return await self._command_executor.execute_command(user_id, message_text)

    async def _process_natural_language_message(
        self, user_id: str, message_text: str
    ) -> Message:
        """
        處理自然語言訊息

        Args:
            user_id: 用戶 ID
            message_text: 自然語言訊息

        Returns:
            處理結果
        """
        self.logger.info("處理自然語言訊息", message_text=message_text[:50])

        try:
            # 使用自然語言服務處理
            parsed_query = await self.nl_service.parse_natural_language(message_text)

            # 檢查解析是否成功（ParsedQuery物件）
            if parsed_query.is_successful() and parsed_query.has_sql_query():
                # 通過服務工廠獲取資料庫服務
                from src.infrastructure.enhanced_service_factory import get_enhanced_service_factory
                from src.services.database_service import DatabaseService
                
                factory = get_enhanced_service_factory()
                db_service = factory.get_service(DatabaseService)
                query_result = await db_service.execute_parsed_query(parsed_query)
                
                # 格式化結果
                return self.message_formatter.format_query_result(query_result)
            else:
                # 解析失敗或信心度不足，返回預設友善回應
                self.logger.warning("自然語言解析失敗或信心度不足", 
                                  confidence=parsed_query.confidence,
                                  query_type=parsed_query.query_type.value)
                return self._get_default_response()

        except Exception as e:
            self.logger.error("自然語言處理失敗", error=str(e))
            return self._get_default_response()

    def _get_default_response(self) -> TextMessage:
        """獲取預設回應"""
        return TextMessage(
            text="👋 您好！我是產線管理助手\\n"
            "━━━━━━━━━━━━━━━━━━━━\\n"
            "🔍 我可以幫您查詢：\\n"
            "   • 機台狀態和效能\\n"
            "   • 故障記錄和分析\\n"
            "   • 生產統計報告\\n"
            "   • 部門運行狀況\\n\\n"
            "💡 試試問我：「M001機台狀況如何？」\\n"
            "或使用 /help 查看可用指令"
        )

    def _update_user_session(
        self,
        user_id: str,
        message_text: str,
        additional_context: dict[str, Any] | None,
    ) -> None:
        """更新用戶會話資訊"""
        import time

        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = {
                "first_interaction": time.time(),
                "message_count": 0,
                "last_command": None,
                "context": {},
            }

        session = self._user_sessions[user_id]
        session["last_interaction"] = time.time()
        session["last_message"] = message_text[:100]  # 保留前100字符
        session["message_count"] += 1

        # 更新指令歷史
        command = parse_command(message_text)
        if command:
            session["last_command"] = command.name

        # 合併額外上下文
        if additional_context:
            session["context"].update(additional_context)

    def _update_session_result(
        self,
        user_id: str,
        result: Message | None,
        success: bool,
        error: str | None = None,
    ) -> None:
        """更新會話處理結果"""
        if user_id in self._user_sessions:
            session = self._user_sessions[user_id]
            session["last_success"] = success

            if error:
                session["last_error"] = error
            elif "last_error" in session:
                del session["last_error"]

    def get_user_session(self, user_id: str) -> dict[str, Any] | None:
        """獲取用戶會話資訊"""
        return self._user_sessions.get(user_id)

    def clear_user_session(self, user_id: str) -> bool:
        """清除用戶會話"""
        if user_id in self._user_sessions:
            del self._user_sessions[user_id]
            return True
        return False

    def get_processing_stats(self) -> dict[str, Any]:
        """獲取處理統計資訊"""
        return {
            **self._stats,
            "active_sessions": len(self._user_sessions),
            "command_success_rate": (
                (self._stats["total_messages"] - self._stats["error_messages"])
                / max(self._stats["total_messages"], 1)
            )
            * 100,
        }

    async def _perform_health_checks(self) -> dict[str, dict[str, Any]]:
        """執行健康檢查"""
        checks = {}

        # 檢查指令執行器
        if self._command_executor:
            try:
                command_info = self._command_executor.get_command_info()
                checks["command_executor"] = {
                    "status": "healthy",
                    "total_commands": command_info["total_commands"],
                    "total_aliases": command_info["total_aliases"],
                }
            except Exception as e:
                checks["command_executor"] = {"status": "unhealthy", "error": str(e)}
        else:
            checks["command_executor"] = {"status": "not_initialized"}

        # 檢查自然語言服務
        try:
            if hasattr(self.nl_service, "health_check"):
                nl_health = await self.nl_service.health_check()
                checks["natural_language_service"] = nl_health
            else:
                checks["natural_language_service"] = {
                    "status": "healthy" if self.nl_service else "missing"
                }
        except Exception as e:
            checks["natural_language_service"] = {
                "status": "unhealthy",
                "error": str(e),
            }

        # 檢查處理統計
        stats = self.get_processing_stats()
        checks["processing_stats"] = {"status": "healthy", **stats}

        return checks

    async def _shutdown_service(self) -> None:
        """關閉服務"""
        # 清理用戶會話
        self._user_sessions.clear()

        # 重置統計
        self._stats = {
            "total_messages": 0,
            "command_messages": 0,
            "natural_language_messages": 0,
            "error_messages": 0,
        }

        self.logger.info("訊息處理服務已清理")
