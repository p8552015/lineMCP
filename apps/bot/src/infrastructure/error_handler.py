"""
統一錯誤處理器
提供一致的錯誤處理策略和用戶友善的錯誤回應
"""

import traceback
from typing import Any

import structlog
from linebot.v3.messaging import TextMessage

from src.domain.exceptions import (
    AIServiceException,
    AuthenticationException,
    BotException,
    BusinessLogicException,
    CommandParsingException,
    ConfigurationException,
    DatabaseQueryException,
    ExternalServiceException,
    MCPConnectionException,
    RateLimitException,
    ValidationException,
)

logger = structlog.get_logger()


class UnifiedErrorHandler:
    """
    統一錯誤處理器
    負責將各種異常轉換為用戶友善的回應
    """

    def __init__(self, include_technical_details: bool = False):
        """
        初始化錯誤處理器

        Args:
            include_technical_details: 是否在回應中包含技術細節
        """
        self.include_technical_details = include_technical_details
        self._error_icons = {
            ValidationException: "⚠️",
            CommandParsingException: "❓",
            DatabaseQueryException: "🗄️",
            MCPConnectionException: "🔌",
            AIServiceException: "🤖",
            AuthenticationException: "🔒",
            RateLimitException: "⏰",
            ConfigurationException: "⚙️",
            BusinessLogicException: "💼",
            ExternalServiceException: "🌐",
        }

    def handle_error(
        self, error: Exception, context: dict[str, Any] | None = None
    ) -> TextMessage:
        """
        處理錯誤並返回用戶友善的訊息

        Args:
            error: 異常對象
            context: 錯誤上下文資訊

        Returns:
            用戶友善的錯誤訊息
        """
        context = context or {}

        # 記錄錯誤
        self._log_error(error, context)

        # 生成用戶回應
        if isinstance(error, BotException):
            return self._handle_bot_exception(error)
        else:
            return self._handle_system_exception(error)

    def _handle_bot_exception(self, error: BotException) -> TextMessage:
        """處理自定義 Bot 異常"""
        icon = self._error_icons.get(type(error), "❌")
        message = f"{icon} {error.user_message}"

        if self.include_technical_details and error.details:
            message += f"\n\n🔧 技術詳情：{error.details}"

        return TextMessage(text=message)

    def _handle_system_exception(self, error: Exception) -> TextMessage:
        """處理系統異常 - 增強 MCP 錯誤處理"""
        error_str = str(error).lower()

        # MCP 相關錯誤的特殊處理
        if "mcp" in error_str or "connection broken" in error_str:
            if "connection broken" in error_str:
                return TextMessage(text="🔌 資料庫連接中斷，系統正在重新連接...")
            elif "no response" in error_str or "timeout" in error_str:
                return TextMessage(text="⏰ 資料庫回應逾時，請稍後再試")
            elif "invalid response format" in error_str:
                return TextMessage(text="📡 資料傳輸格式錯誤，請重新嘗試")
            else:
                return TextMessage(text="🗄️ 資料庫服務暫時不可用，請稍後再試")

        # 針對常見的系統異常提供特定處理
        elif isinstance(error, TimeoutError):
            return TextMessage(text="⏰ 操作逾時，請稍後再試")
        elif isinstance(error, ConnectionError):
            return TextMessage(text="🔌 網路連接失敗，請檢查網路狀態")
        elif isinstance(error, PermissionError):
            return TextMessage(text="🔒 權限不足，請聯絡管理員")
        elif isinstance(error, ValueError):
            return TextMessage(text="⚠️ 輸入值錯誤，請檢查輸入格式")
        elif isinstance(error, KeyError):
            return TextMessage(text="🔍 找不到指定的資源")
        elif "json" in error_str and ("decode" in error_str or "parse" in error_str):
            return TextMessage(text="📄 資料格式錯誤，請重新嘗試")
        elif "sql" in error_str or "database" in error_str:
            return TextMessage(text="🗄️ 資料庫查詢錯誤，請檢查查詢條件")
        else:
            # 未知異常
            message = "💥 系統發生未知錯誤"
            if self.include_technical_details:
                message += f"：{str(error)}"
            else:
                message += "，請聯絡系統管理員"
            return TextMessage(text=message)

    def _log_error(self, error: Exception, context: dict[str, Any]):
        """記錄錯誤詳情"""
        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
        }

        # 如果是自定義異常，記錄額外資訊
        if isinstance(error, BotException):
            error_data.update(error.to_dict())

        # 對於嚴重錯誤，記錄完整的堆疊追蹤
        if not isinstance(error, ValidationException | CommandParsingException):
            error_data["traceback"] = traceback.format_exc()
            logger.error("Error occurred", **error_data)
        else:
            logger.warning("Validation/Command error", **error_data)


class ErrorHandlerMiddleware:
    """
    錯誤處理中間件
    可以作為裝飾器使用
    """

    def __init__(self, error_handler: UnifiedErrorHandler):
        self.error_handler = error_handler

    def __call__(self, func):
        """裝飾器實現"""
        import functools

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # 提取上下文資訊
                context = {
                    "function": func.__name__,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys()),
                }

                # 處理錯誤並返回訊息
                return self.error_handler.handle_error(e, context)

        return wrapper


# 全域錯誤處理器實例
_global_error_handler: UnifiedErrorHandler | None = None


def get_error_handler(include_technical_details: bool = False) -> UnifiedErrorHandler:
    """獲取全域錯誤處理器實例"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = UnifiedErrorHandler(include_technical_details)
    return _global_error_handler


def handle_error_gracefully(
    error: Exception, context: dict[str, Any] | None = None
) -> TextMessage:
    """便捷函數：優雅地處理錯誤"""
    handler = get_error_handler()
    return handler.handle_error(error, context)


def create_error_middleware(include_technical_details: bool = False):
    """創建錯誤處理中間件"""
    handler = UnifiedErrorHandler(include_technical_details)
    return ErrorHandlerMiddleware(handler)
