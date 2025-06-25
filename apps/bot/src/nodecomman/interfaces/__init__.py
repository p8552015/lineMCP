"""
介面抽象層

定義符合 SOLID 原則的核心抽象介面：
- 運行時管理介面
- MCP 服務器介面
- 環境驗證介面

遵循 ISP (介面隔離原則)，每個介面專注特定職責。
"""

from .runtime_interfaces import IRuntimeManager, RuntimeType, RuntimeInfo
from .server_interfaces import IMCPServerFactory, MCPServerConfig, IMCPServer
from .validation_interfaces import IEnvironmentValidator, ValidationResult, IDependencyManager

__all__ = [
    "IRuntimeManager",
    "RuntimeType", 
    "RuntimeInfo",
    "IMCPServerFactory",
    "MCPServerConfig",
    "IMCPServer",
    "IEnvironmentValidator",
    "ValidationResult",
    "IDependencyManager",
]