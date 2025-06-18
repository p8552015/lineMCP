"""
MCP Common Library

提供統一的 MCP 客戶端介面、協議適配器和可觀測性工具。
"""

__version__ = "0.1.0"
__author__ = "MCP Development Team"

# 客戶端相關
from .clients.factory import get_mcp_client as create_client
from .clients.interface import MCPClientInterface
from .clients.mock_client import MockMCPClient
from .unified_client import UnifiedMCPClient, get_unified_mcp_client, get_mcp_client

# 資料模型
from .models.base import (
    MCPCall,
    MCPResponse,
    BatchResult as MCPBatchResponse,
    HealthStatus as MCPHealthCheck,
    ServerInfo as ServerStatus
)
from .models.error import (
    MCPError,
    TimeoutError as MCPTimeoutError,
    ConnectionError as MCPConnectionError,
    ValidationError as MCPValidationError
)
from .models.query import (
    QueryRequest as MCPQuery,
    QueryResult as MCPQueryResult,
    QueryStats as MCPQueryMetadata,
    StreamQueryChunk as MCPStreamChunk
)

# 配置管理
from .config.settings import (
    ServerConfig,
    ConnectionConfig,
    ObservabilityConfig,
    MCPClientConfig,
    ConfigManager,
    get_config_manager,
    get_config,
    get_server_config
)

# 連接管理
from .connection.pool import ConnectionPool
from .connection.circuit import CircuitBreaker, CircuitState
from .connection.health import HealthChecker, HealthStatus
from .connection.retry import RetryStrategy, ExponentialBackoff, retry_with_strategy

# 適配器
from .adapters.base import BaseProtocolAdapter
from .adapters.http import HTTPAdapter
from .adapters.websocket import WebSocketAdapter
from .adapters.stdio import STDIOAdapter
from .adapters.simple_adapter import SimpleAdapter
from .adapters.legacy_adapter import LegacyAdapter

# 可觀測性
from .observability.metrics import (
    MCPMetrics,
    get_global_metrics,
    configure_global_metrics,
    with_metrics
)
from .observability.tracing import (
    MCPTracing,
    get_global_tracing
)

__all__ = [
    # 版本資訊
    "__version__",
    "__author__",
    
    # 客戶端
    "get_mcp_client",
    "get_unified_mcp_client",
    "create_client",
    "UnifiedMCPClient",
    "MCPClientInterface",
    "MockMCPClient",
    
    # 資料模型
    "MCPCall",
    "MCPResponse",
    "MCPStreamChunk",
    "MCPBatchResponse",
    "MCPHealthCheck",
    "ServerStatus",
    
    # 錯誤類型
    "MCPError",
    "MCPTimeoutError",
    "MCPConnectionError",
    "MCPValidationError",
    
    # 查詢模型
    "MCPQuery",
    "MCPQueryResult",
    "MCPQueryMetadata",
    
    # 配置
    "ServerConfig",
    "ConnectionConfig",
    "ObservabilityConfig",
    "MCPClientConfig",
    "ConfigManager",
    "get_config_manager",
    "get_config",
    "get_server_config",
    
    # 連接管理
    "ConnectionPool",
    "CircuitBreaker",
    "CircuitState",
    "HealthChecker",
    "HealthStatus",
    "RetryStrategy", 
    "ExponentialBackoff",
    "retry_with_strategy",
    
    # 適配器
    "BaseProtocolAdapter",
    "HTTPAdapter",
    "WebSocketAdapter",
    "STDIOAdapter",
    "SimpleAdapter",
    "LegacyAdapter",
    
    # 可觀測性
    "MCPMetrics",
    "get_global_metrics",
    "configure_global_metrics",
    "with_metrics",
    "MCPTracing",
    "get_global_tracing",
]