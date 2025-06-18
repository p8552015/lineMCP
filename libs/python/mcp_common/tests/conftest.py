"""
Pytest 配置和共用夾具
"""

import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock

# 確保專案路徑在 Python 路徑中
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def event_loop():
    """建立事件迴圈供整個測試會話使用"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_client():
    """建立模擬的 MCP 客戶端"""
    from mcp_common.clients.mock_client import MockMCPClient
    return MockMCPClient()


@pytest.fixture
def mock_adapter():
    """建立模擬的協定適配器"""
    from mcp_common.adapters.base import BaseProtocolAdapter
    from mcp_common.models.base import MCPResponse
    
    adapter = Mock(spec=BaseProtocolAdapter)
    adapter.connect = AsyncMock()
    adapter.disconnect = AsyncMock()
    adapter.send_request = AsyncMock(return_value=MCPResponse(
        status="success",
        data={"result": "test"},
        call_id="test-id"
    ))
    adapter.health_check = AsyncMock(return_value=True)
    
    return adapter


@pytest.fixture
def server_config():
    """建立測試伺服器配置"""
    from mcp_common.config.settings import ServerConfig
    
    return ServerConfig(
        name="test_server",
        adapter_type="http",
        url="http://localhost:8080",
        timeout=30.0,
        retry_attempts=3
    )


@pytest.fixture
def client_config():
    """建立測試客戶端配置"""
    from mcp_common.config.settings import MCPClientConfig, ServerConfig
    
    return MCPClientConfig(
        environment="testing",
        debug=True,
        servers={
            "test_server": ServerConfig(
                name="test_server",
                adapter_type="mock"
            )
        }
    )


@pytest.fixture
def sample_call():
    """建立範例 MCP 呼叫"""
    from mcp_common.models.base import MCPCall
    
    return MCPCall(
        server="test_server",
        tool="test_tool",
        params={"key": "value"},
        timeout=30.0
    )


@pytest.fixture
def sample_response():
    """建立範例 MCP 回應"""
    from mcp_common.models.base import MCPResponse
    
    return MCPResponse(
        status="success",
        data={"result": "test_result"},
        call_id="test-123",
        execution_time=0.5
    )


@pytest.fixture
def metrics():
    """建立測試用的指標收集器"""
    from mcp_common.observability.metrics import MCPMetrics
    
    return MCPMetrics(enabled=True)


@pytest.fixture
def tracing():
    """建立測試用的追蹤配置器"""
    from mcp_common.observability.tracing import MCPTracing
    
    return MCPTracing(
        service_name="test-service",
        enabled=True
    )


# 測試輔助函數
async def async_return(value):
    """非同步返回值的輔助函數"""
    return value


def create_mock_session():
    """建立模擬的 aiohttp session"""
    session = Mock()
    session.close = AsyncMock()
    session.get = AsyncMock()
    session.post = AsyncMock()
    return session


def create_mock_websocket():
    """建立模擬的 websocket 連接"""
    ws = Mock()
    ws.close = AsyncMock()
    ws.send = AsyncMock()
    ws.recv = AsyncMock()
    return ws


def create_mock_process():
    """建立模擬的子進程"""
    process = Mock()
    process.terminate = Mock()
    process.wait = AsyncMock()
    process.stdin = Mock()
    process.stdout = Mock()
    process.stderr = Mock()
    return process


# 標記跳過慢速測試
def pytest_configure(config):
    """配置 pytest"""
    config.addinivalue_line(
        "markers", "slow: 標記為慢速測試，可以使用 -m 'not slow' 跳過"
    )
    config.addinivalue_line(
        "markers", "integration: 整合測試"
    )
    config.addinivalue_line(
        "markers", "unit: 單元測試"
    )