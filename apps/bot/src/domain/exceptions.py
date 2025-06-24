"""
自定義異常類型
提供清晰的錯誤語義和用戶友善的錯誤訊息
"""

from typing import Any


class BotError(Exception):
    """
    Bot 應用的基礎異常類型
    所有自定義異常都應該繼承自此類
    """

    def __init__(
        self,
        message: str,
        user_message: str | None = None,
        details: dict[str, Any] | None = None,
        error_code: str | None = None,
    ):
        """
        初始化 Bot 異常

        Args:
            message: 技術錯誤訊息（用於日誌）
            user_message: 用戶友善的錯誤訊息
            details: 錯誤的詳細資訊
            error_code: 錯誤代碼
        """
        super().__init__(message)
        self.user_message = user_message or "系統發生錯誤，請稍後再試"
        self.details = details or {}
        self.error_code = error_code

    def to_dict(self) -> dict[str, Any]:
        """轉換為字典格式（用於日誌或API回應）"""
        return {
            "error_type": self.__class__.__name__,
            "message": str(self),
            "user_message": self.user_message,
            "details": self.details,
            "error_code": self.error_code,
        }


class ValidationException(BotError):
    """輸入驗證異常"""

    def __init__(self, field: str, value: Any, reason: str):
        message = (
            f"Validation failed for field '{field}' with value '{value}': {reason}"
        )
        user_message = f"輸入的 {field} 格式不正確：{reason}"
        super().__init__(
            message=message,
            user_message=user_message,
            details={"field": field, "value": str(value), "reason": reason},
            error_code="VALIDATION_ERROR",
        )


class CommandParsingException(BotError):
    """指令解析異常"""

    def __init__(self, command: str, reason: str):
        message = f"Failed to parse command '{command}': {reason}"
        user_message = f"無法理解指令「{command}」：{reason}"
        super().__init__(
            message=message,
            user_message=user_message,
            details={"command": command, "reason": reason},
            error_code="COMMAND_PARSE_ERROR",
        )


class DatabaseQueryException(BotError):
    """資料庫查詢異常"""

    def __init__(self, query: str, reason: str, query_type: str | None = None):
        message = f"Database query failed: {reason}"
        user_message = "資料庫查詢失敗，請檢查查詢條件或稍後再試"
        super().__init__(
            message=message,
            user_message=user_message,
            details={
                "query": query[:100] + "..." if len(query) > 100 else query,
                "reason": reason,
                "query_type": query_type,
            },
            error_code="DB_QUERY_ERROR",
        )


class MCPConnectionException(BotError):
    """MCP 連接異常"""

    def __init__(self, server: str, operation: str, reason: str):
        message = f"MCP connection failed for {server}.{operation}: {reason}"
        user_message = "服務連接失敗，請稍後再試"
        super().__init__(
            message=message,
            user_message=user_message,
            details={"server": server, "operation": operation, "reason": reason},
            error_code="MCP_CONNECTION_ERROR",
        )


class AIServiceException(BotError):
    """AI 服務異常"""

    def __init__(self, service: str, operation: str, reason: str):
        message = f"AI service {service} failed during {operation}: {reason}"
        user_message = "AI 服務暫時不可用，請稍後再試"
        super().__init__(
            message=message,
            user_message=user_message,
            details={"service": service, "operation": operation, "reason": reason},
            error_code="AI_SERVICE_ERROR",
        )


class AuthenticationException(BotError):
    """認證異常"""

    def __init__(self, reason: str):
        message = f"Authentication failed: {reason}"
        user_message = "認證失敗，請確認您的權限"
        super().__init__(
            message=message,
            user_message=user_message,
            details={"reason": reason},
            error_code="AUTH_ERROR",
        )


class RateLimitException(BotError):
    """速率限制異常"""

    def __init__(self, limit: int, window: str, current_count: int):
        message = f"Rate limit exceeded: {current_count}/{limit} in {window}"
        user_message = "請求過於頻繁，請稍後再試"
        super().__init__(
            message=message,
            user_message=user_message,
            details={"limit": limit, "window": window, "current_count": current_count},
            error_code="RATE_LIMIT_ERROR",
        )


class ConfigurationException(BotError):
    """配置異常"""

    def __init__(self, config_name: str, reason: str):
        message = f"Configuration error for '{config_name}': {reason}"
        user_message = "系統配置錯誤，請聯絡管理員"
        super().__init__(
            message=message,
            user_message=user_message,
            details={"config_name": config_name, "reason": reason},
            error_code="CONFIG_ERROR",
        )


class BusinessLogicException(BotError):
    """業務邏輯異常"""

    def __init__(self, operation: str, reason: str, user_message: str | None = None):
        message = f"Business logic error in {operation}: {reason}"
        default_user_message = "操作失敗，請檢查輸入條件"
        super().__init__(
            message=message,
            user_message=user_message or default_user_message,
            details={"operation": operation, "reason": reason},
            error_code="BUSINESS_LOGIC_ERROR",
        )


class ExternalServiceException(BotError):
    """外部服務異常"""

    def __init__(
        self,
        service: str,
        operation: str,
        status_code: int | None = None,
        reason: str = "",
    ):
        message = f"External service {service} failed during {operation}"
        if status_code:
            message += f" (HTTP {status_code})"
        if reason:
            message += f": {reason}"

        user_message = f"{service} 服務暫時不可用，請稍後再試"
        super().__init__(
            message=message,
            user_message=user_message,
            details={
                "service": service,
                "operation": operation,
                "status_code": status_code,
                "reason": reason,
            },
            error_code="EXTERNAL_SERVICE_ERROR",
        )


# 便捷的異常工廠函數
def create_validation_error(field: str, value: Any, reason: str) -> ValidationException:
    """創建驗證錯誤"""
    return ValidationException(field, value, reason)


def create_command_error(command: str, reason: str) -> CommandParsingException:
    """創建指令解析錯誤"""
    return CommandParsingException(command, reason)


def create_db_error(
    query: str, reason: str, query_type: str | None = None
) -> DatabaseQueryException:
    """創建資料庫錯誤"""
    return DatabaseQueryException(query, reason, query_type)


def create_mcp_error(
    server: str, operation: str, reason: str
) -> MCPConnectionException:
    """創建 MCP 連接錯誤"""
    return MCPConnectionException(server, operation, reason)


def create_ai_error(service: str, operation: str, reason: str) -> AIServiceException:
    """創建 AI 服務錯誤"""
    return AIServiceException(service, operation, reason)
