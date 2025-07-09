"""
領域層
包含業務邏輯、異常定義等核心概念
"""

from .exceptions import (
    BotException,
    ValidationException,
    CommandParsingException,
    DatabaseQueryException,
    MCPConnectionException,
    AIServiceException,
    AuthenticationException,
    RateLimitException,
    ConfigurationException,
    BusinessLogicException,
    ExternalServiceException,
    create_validation_error,
    create_command_error,
    create_db_error,
    create_mcp_error,
    create_ai_error
)

__all__ = [
    'BotException',
    'ValidationException',
    'CommandParsingException', 
    'DatabaseQueryException',
    'MCPConnectionException',
    'AIServiceException',
    'AuthenticationException',
    'RateLimitException',
    'ConfigurationException',
    'BusinessLogicException',
    'ExternalServiceException',
    'create_validation_error',
    'create_command_error',
    'create_db_error',
    'create_mcp_error',
    'create_ai_error'
]