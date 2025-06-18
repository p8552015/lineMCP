"""
測試 MCP 客戶端實作
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from mcp_common.clients.interface import MCPClientInterface
from mcp_common.clients.mock_client import MockMCPClient
from mcp_common.clients.factory import get_mcp_client
from mcp_common.models.base import MCPCall, MCPResponse, MCPBatchResponse
from mcp_common.models.error import MCPError, MCPTimeoutError


class TestMockMCPClient:
    """測試 Mock MCP 客戶端"""
    
    @pytest.fixture
    def client(self):
        """建立測試客戶端"""
        return MockMCPClient()
    
    @pytest.mark.asyncio
    async def test_call_tool_success(self, client):
        """測試成功呼叫工具"""
        response = await client.call_tool(
            server="test_server",
            tool="test_tool",
            params={"key": "value"}
        )
        
        assert response.status == "success"
        assert response.data["tool"] == "test_tool"
        assert response.data["params"]["key"] == "value"
    
    @pytest.mark.asyncio
    async def test_call_tool_with_error_simulation(self, client):
        """測試錯誤模擬"""
        # 模擬錯誤
        client.simulate_error = True
        
        with pytest.raises(MCPError) as exc_info:
            await client.call_tool(
                server="test_server",
                tool="test_tool",
                params={}
            )
        
        assert "模擬錯誤" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_call_tool_with_timeout_simulation(self, client):
        """測試超時模擬"""
        # 模擬超時
        client.simulate_timeout = True
        
        with pytest.raises(MCPTimeoutError):
            await client.call_tool(
                server="test_server",
                tool="test_tool",
                params={}
            )
    
    @pytest.mark.asyncio
    async def test_batch_call(self, client):
        """測試批次呼叫"""
        calls = [
            MCPCall(server="server1", tool="tool1", params={"a": 1}),
            MCPCall(server="server2", tool="tool2", params={"b": 2}),
        ]
        
        responses = await client.batch_call(calls)
        
        assert isinstance(responses, MCPBatchResponse)
        assert len(responses.responses) == 2
        assert responses.responses[0].status == "success"
        assert responses.responses[1].status == "success"
    
    @pytest.mark.asyncio
    async def test_stream_call(self, client):
        """測試串流呼叫"""
        chunks = []
        
        async for chunk in client.stream_call(
            server="test_server",
            tool="stream_tool",
            params={"count": 3}
        ):
            chunks.append(chunk)
        
        assert len(chunks) == 3
        for i, chunk in enumerate(chunks):
            assert chunk.data["chunk"] == i
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """測試健康檢查"""
        health = await client.health_check()
        
        assert health.overall == "healthy"
        assert "test_server" in health.servers
        assert health.servers["test_server"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_close(self, client):
        """測試關閉客戶端"""
        await client.close()
        # 應該不會引發錯誤


class TestClientFactory:
    """測試客戶端工廠"""
    
    def test_get_mock_client(self):
        """測試建立 Mock 客戶端"""
        client = get_mcp_client("mock")
        assert isinstance(client, MockMCPClient)
    
    def test_get_invalid_client_type(self):
        """測試無效的客戶端類型"""
        with pytest.raises(ValueError) as exc_info:
            get_mcp_client("invalid_type")
        
        assert "不支援的客戶端類型" in str(exc_info.value)
    
    @patch('mcp_common.clients.factory.HTTPMCPClient')
    def test_get_http_client(self, mock_http_client):
        """測試建立 HTTP 客戶端"""
        mock_instance = Mock()
        mock_http_client.return_value = mock_instance
        
        client = get_mcp_client("http", url="http://example.com")
        
        mock_http_client.assert_called_once_with(url="http://example.com")
        assert client == mock_instance


@pytest.mark.asyncio
class TestClientInterface:
    """測試客戶端介面合約"""
    
    async def test_interface_methods(self):
        """確保所有客戶端都實作必要的介面"""
        client = get_mcp_client("mock")
        
        # 檢查介面方法
        assert hasattr(client, 'call_tool')
        assert hasattr(client, 'batch_call')
        assert hasattr(client, 'stream_call')
        assert hasattr(client, 'health_check')
        assert hasattr(client, 'close')
        
        # 測試方法可以被呼叫
        response = await client.call_tool("server", "tool", {})
        assert isinstance(response, MCPResponse)
        
        batch_response = await client.batch_call([])
        assert isinstance(batch_response, MCPBatchResponse)
        
        health = await client.health_check()
        assert health.overall in ["healthy", "unhealthy", "degraded"]