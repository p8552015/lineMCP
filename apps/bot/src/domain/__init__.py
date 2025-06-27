"""
領域層
包含業務邏輯、異常定義等核心概念
"""

from .exceptions import (
    AIServiceError,
    AuthenticationError,
    BotError,
    BusinessLogicError,
    CommandParsingError,
    ConfigurationError,
    DatabaseQueryError,
    ExternalServiceError,
    MCPConnectionError,
    RateLimitError,
    ValidationError,
    create_ai_error,
    create_command_error,
    create_db_error,
    create_mcp_error,
    create_validation_error,
)

__all__ = [
    "BotError",
    "ValidationError",
    "CommandParsingError",
    "DatabaseQueryError",
    "MCPConnectionError",
    "AIServiceError",
    "AuthenticationError",
    "RateLimitError",
    "ConfigurationError",
    "BusinessLogicError",
    "ExternalServiceError",
    "create_validation_error",
    "create_command_error",
    "create_db_error",
    "create_mcp_error",
    "create_ai_error",
]
