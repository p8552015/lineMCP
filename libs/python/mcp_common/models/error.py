"""
MCP 錯誤定義

定義 MCP 系統中的所有錯誤類型。
"""

from typing import Any, Optional


class MCPError(Exception):
    """MCP 基礎錯誤類別"""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        server: Optional[str] = None,
        tool: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.server = server
        self.tool = tool
        self.details = details or {}
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.server:
            parts.append(f"server={self.server}")
        if self.tool:
            parts.append(f"tool={self.tool}")
        if self.error_code:
            parts.append(f"code={self.error_code}")
        return f"MCPError: {', '.join(parts)}"


class ConnectionError(MCPError):
    """連線錯誤"""
    
    def __init__(
        self,
        message: str = "連線失敗",
        server: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="CONNECTION_ERROR",
            server=server,
            details=details,
        )


class TimeoutError(MCPError):
    """超時錯誤"""
    
    def __init__(
        self,
        message: str = "請求超時",
        timeout: Optional[float] = None,
        server: Optional[str] = None,
        tool: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        details = details or {}
        if timeout is not None:
            details["timeout"] = timeout
            
        super().__init__(
            message=message,
            error_code="TIMEOUT_ERROR",
            server=server,
            tool=tool,
            details=details,
        )


class ValidationError(MCPError):
    """驗證錯誤"""
    
    def __init__(
        self,
        message: str = "資料驗證失敗",
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        details = details or {}
        if field is not None:
            details["field"] = field
        if value is not None:
            details["value"] = value
            
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class AuthenticationError(MCPError):
    """認證錯誤"""
    
    def __init__(
        self,
        message: str = "認證失敗",
        server: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            server=server,
            details=details,
        )


class AuthorizationError(MCPError):
    """授權錯誤"""
    
    def __init__(
        self,
        message: str = "權限不足",
        server: Optional[str] = None,
        tool: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            server=server,
            tool=tool,
            details=details,
        )


class ServerError(MCPError):
    """伺服器錯誤"""
    
    def __init__(
        self,
        message: str = "伺服器內部錯誤",
        status_code: Optional[int] = None,
        server: Optional[str] = None,
        tool: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        details = details or {}
        if status_code is not None:
            details["status_code"] = status_code
            
        super().__init__(
            message=message,
            error_code="SERVER_ERROR",
            server=server,
            tool=tool,
            details=details,
        )


class CircuitBreakerError(MCPError):
    """熔斷器錯誤"""
    
    def __init__(
        self,
        message: str = "熔斷器開啟，請求被拒絕",
        server: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="CIRCUIT_BREAKER_ERROR",
            server=server,
            details=details,
        )


class RateLimitError(MCPError):
    """速率限制錯誤"""
    
    def __init__(
        self,
        message: str = "請求頻率超出限制",
        retry_after: Optional[float] = None,
        server: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        details = details or {}
        if retry_after is not None:
            details["retry_after"] = retry_after
            
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            server=server,
            details=details,
        )


class ConfigurationError(MCPError):
    """配置錯誤"""
    
    def __init__(
        self,
        message: str = "配置錯誤",
        config_key: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        details = details or {}
        if config_key is not None:
            details["config_key"] = config_key
            
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details=details,
        )


# 錯誤碼映射表
ERROR_CODE_MAPPING = {
    "CONNECTION_ERROR": ConnectionError,
    "TIMEOUT_ERROR": TimeoutError,
    "VALIDATION_ERROR": ValidationError,
    "AUTHENTICATION_ERROR": AuthenticationError,
    "AUTHORIZATION_ERROR": AuthorizationError,
    "SERVER_ERROR": ServerError,
    "CIRCUIT_BREAKER_ERROR": CircuitBreakerError,
    "RATE_LIMIT_ERROR": RateLimitError,
    "CONFIGURATION_ERROR": ConfigurationError,
}


def create_error_from_code(
    error_code: str,
    message: str,
    **kwargs: Any,
) -> MCPError:
    """
    根據錯誤碼建立對應的錯誤實例
    
    Args:
        error_code: 錯誤碼
        message: 錯誤訊息
        **kwargs: 額外參數
        
    Returns:
        對應的錯誤實例
    """
    error_class = ERROR_CODE_MAPPING.get(error_code, MCPError)
    return error_class(message=message, **kwargs)