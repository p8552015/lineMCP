"""
測試統一客戶端
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import AsyncIterator

from mcp_common.unified_client import (
    UnifiedMCPClient,
    get_unified_mcp_client,
    get_mcp_client
)
from mcp_common.models.base import (
    MCPCall,
    MCPResponse,
    MCPStreamChunk,
    MCPBatchResponse,
    MCPHealthCheck
)
from mcp_common.models.error import MCPError, MCPTimeoutError
from mcp_common.clients.mock_client import MockMCPClient
from mcp_common.adapters.base import BaseProtocolAdapter


class TestUnifiedMCPClient:
    """測試統一 MCP 客戶端"""
    
    @pytest.fixture
    def mock_adapter(self):
        """建立模擬適配器"""
        adapter = Mock(spec=BaseProtocolAdapter)
        adapter.connect = AsyncMock()
        adapter.disconnect = AsyncMock()
        adapter.send_request = AsyncMock(return_value=MCPResponse(
            status="success",
            data={"result": "test"},
            call_id="123"
        ))
        adapter.health_check = AsyncMock(return_value=True)
        return adapter
    
    @pytest.fixture
    def client(self, mock_adapter):
        """建立測試客戶端"""
        client = UnifiedMCPClient()
        client._adapters = {"test_server": mock_adapter}
        return client
    
    @pytest.mark.asyncio
    async def test_call_tool_success(self, client, mock_adapter):
        """測試成功呼叫工具"""
        response = await client.call_tool(
            server="test_server",
            tool="test_tool",
            params={"key": "value"}
        )
        
        assert response.status == "success"
        assert response.data["result"] == "test"
        
        # 驗證適配器呼叫
        mock_adapter.send_request.assert_called_once()
        call_arg = mock_adapter.send_request.call_args[0][0]
        assert isinstance(call_arg, MCPCall)
        assert call_arg.server == "test_server"
        assert call_arg.tool == "test_tool"
        assert call_arg.params == {"key": "value"}
    
    @pytest.mark.asyncio
    async def test_call_tool_with_timeout(self, client, mock_adapter):
        """測試帶超時的呼叫"""
        response = await client.call_tool(
            server="test_server",
            tool="test_tool",
            params={},
            timeout=10.0
        )
        
        # 驗證超時參數
        call_arg = mock_adapter.send_request.call_args[0][0]
        assert call_arg.timeout == 10.0
    
    @pytest.mark.asyncio
    async def test_call_tool_server_not_found(self, client):
        """測試伺服器未找到"""
        with pytest.raises(MCPError) as exc_info:
            await client.call_tool(
                server="unknown_server",
                tool="test_tool",
                params={}
            )
        
        assert "未找到伺服器" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_call_tool_adapter_error(self, client, mock_adapter):
        """測試適配器錯誤"""
        mock_adapter.send_request.side_effect = MCPError("Adapter error")
        
        with pytest.raises(MCPError) as exc_info:
            await client.call_tool(
                server="test_server",
                tool="test_tool",
                params={}
            )
        
        assert "Adapter error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_batch_call(self, client, mock_adapter):
        """測試批次呼叫"""
        # 設定多個伺服器的適配器
        adapter2 = Mock(spec=BaseProtocolAdapter)
        adapter2.send_request = AsyncMock(return_value=MCPResponse(
            status="success",
            data={"result": "test2"},
            call_id="456"
        ))
        client._adapters["server2"] = adapter2
        
        calls = [
            MCPCall(server="test_server", tool="tool1", params={"a": 1}),
            MCPCall(server="server2", tool="tool2", params={"b": 2}),
        ]
        
        response = await client.batch_call(calls, max_concurrent=2)
        
        assert isinstance(response, MCPBatchResponse)
        assert len(response.responses) == 2
        assert response.responses[0].status == "success"
        assert response.responses[1].status == "success"
        
        # 驗證兩個適配器都被呼叫
        mock_adapter.send_request.assert_called_once()
        adapter2.send_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_batch_call_with_error(self, client, mock_adapter):
        """測試批次呼叫中的錯誤處理"""
        # 第一個成功，第二個失敗
        mock_adapter.send_request.side_effect = [
            MCPResponse(status="success", data={"result": "ok"}, call_id="1"),
            MCPError("Failed")
        ]
        
        calls = [
            MCPCall(server="test_server", tool="tool1", params={}),
            MCPCall(server="test_server", tool="tool2", params={}),
        ]
        
        response = await client.batch_call(calls)
        
        assert len(response.responses) == 2
        assert response.responses[0].status == "success"
        assert response.responses[1].status == "error"
        assert response.success_count == 1
        assert response.error_count == 1
    
    @pytest.mark.asyncio
    async def test_stream_call(self, client, mock_adapter):
        """測試串流呼叫"""
        # 模擬串流回應
        async def mock_stream():
            for i in range(3):
                yield MCPStreamChunk(
                    data={"chunk": i},
                    sequence=i,
                    is_final=(i == 2)
                )
        
        mock_adapter.stream_request = AsyncMock(return_value=mock_stream())
        
        chunks = []
        async for chunk in client.stream_call(
            server="test_server",
            tool="stream_tool",
            params={}
        ):
            chunks.append(chunk)
        
        assert len(chunks) == 3
        assert chunks[0].data["chunk"] == 0
        assert chunks[2].is_final is True
    
    @pytest.mark.asyncio
    async def test_health_check_all(self, client, mock_adapter):
        """測試健康檢查所有伺服器"""
        # 添加另一個不健康的伺服器
        unhealthy_adapter = Mock(spec=BaseProtocolAdapter)
        unhealthy_adapter.health_check = AsyncMock(return_value=False)
        client._adapters["unhealthy_server"] = unhealthy_adapter
        
        health = await client.health_check()
        
        assert isinstance(health, MCPHealthCheck)
        assert health.overall == "degraded"  # 有一個不健康
        assert "test_server" in health.servers
        assert "unhealthy_server" in health.servers
        assert health.servers["test_server"].status == "healthy"
        assert health.servers["unhealthy_server"].status == "unhealthy"
    
    @pytest.mark.asyncio
    async def test_health_check_specific_server(self, client, mock_adapter):
        """測試特定伺服器的健康檢查"""
        health = await client.health_check(server="test_server")
        
        assert health.overall == "healthy"
        assert len(health.servers) == 1
        assert health.servers["test_server"].status == "healthy"
    
    @pytest.mark.asyncio
    async def test_add_adapter(self, client):
        """測試添加適配器"""
        new_adapter = Mock(spec=BaseProtocolAdapter)
        
        client.add_adapter("new_server", new_adapter)
        
        assert "new_server" in client._adapters
        assert client._adapters["new_server"] is new_adapter
    
    @pytest.mark.asyncio
    async def test_remove_adapter(self, client, mock_adapter):
        """測試移除適配器"""
        await client.remove_adapter("test_server")
        
        assert "test_server" not in client._adapters
        mock_adapter.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close(self, client, mock_adapter):
        """測試關閉客戶端"""
        # 添加多個適配器
        adapter2 = Mock(spec=BaseProtocolAdapter)
        adapter2.disconnect = AsyncMock()
        client._adapters["server2"] = adapter2
        
        await client.close()
        
        # 所有適配器都應該斷開連接
        mock_adapter.disconnect.assert_called_once()
        adapter2.disconnect.assert_called_once()
        assert len(client._adapters) == 0
    
    @pytest.mark.asyncio
    async def test_call_tool_legacy(self, client, mock_adapter):
        """測試遺留 API 相容性"""
        result = await client.call_tool_legacy(
            server_name="test_server",
            tool_name="test_tool",
            parameters={"key": "value"}
        )
        
        assert result["success"] is True
        assert result["result"]["result"] == "test"
        
        # 驗證內部呼叫了新 API
        mock_adapter.send_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_call_tool_legacy_error(self, client, mock_adapter):
        """測試遺留 API 錯誤處理"""
        mock_adapter.send_request.side_effect = MCPError("Test error")
        
        result = await client.call_tool_legacy(
            server_name="test_server",
            tool_name="test_tool",
            parameters={}
        )
        
        assert result["success"] is False
        assert "Test error" in result["error"]


class TestClientFactory:
    """測試客戶端工廠函數"""
    
    def test_get_unified_mcp_client_mock(self):
        """測試建立 Mock 客戶端"""
        client = get_unified_mcp_client(client_type="mock")
        
        assert isinstance(client, UnifiedMCPClient)
        assert "mock" in client._adapters
    
    @patch('mcp_common.unified_client.SimpleAdapter')
    def test_get_unified_mcp_client_simple(self, mock_simple_adapter):
        """測試建立簡單客戶端"""
        mock_simple_client = Mock()
        
        with patch('mcp_common.unified_client.get_simple_mcp_client', return_value=mock_simple_client):
            client = get_unified_mcp_client(client_type="simple")
        
        assert isinstance(client, UnifiedMCPClient)
        mock_simple_adapter.assert_called_once_with(simple_client=mock_simple_client)
    
    @patch('mcp_common.unified_client.LegacyAdapter')
    def test_get_unified_mcp_client_legacy(self, mock_legacy_adapter):
        """測試建立遺留客戶端"""
        mock_legacy_client = Mock()
        
        with patch('mcp_common.unified_client.get_legacy_mcp_client', return_value=mock_legacy_client):
            client = get_unified_mcp_client(client_type="legacy")
        
        assert isinstance(client, UnifiedMCPClient)
        mock_legacy_adapter.assert_called_once_with(legacy_client=mock_legacy_client)
    
    def test_get_unified_mcp_client_invalid_type(self):
        """測試無效的客戶端類型"""
        with pytest.raises(ValueError) as exc_info:
            get_unified_mcp_client(client_type="invalid")
        
        assert "不支援的客戶端類型" in str(exc_info.value)
    
    def test_get_mcp_client_alias(self):
        """測試 get_mcp_client 別名"""
        # 確認別名指向同一個函數
        assert get_mcp_client is get_unified_mcp_client


# 整合測試
class TestUnifiedClientIntegration:
    """測試統一客戶端整合"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """測試完整工作流程"""
        # 使用 Mock 客戶端進行整合測試
        client = get_unified_mcp_client(client_type="mock")
        
        try:
            # 1. 健康檢查
            health = await client.health_check()
            assert health.overall == "healthy"
            
            # 2. 單一呼叫
            response = await client.call_tool(
                server="mock",
                tool="test_tool",
                params={"input": "test"}
            )
            assert response.status == "success"
            
            # 3. 批次呼叫
            calls = [
                MCPCall(server="mock", tool="tool1", params={}),
                MCPCall(server="mock", tool="tool2", params={}),
            ]
            batch_response = await client.batch_call(calls)
            assert len(batch_response.responses) == 2
            
            # 4. 串流呼叫
            chunks = []
            async for chunk in client.stream_call(
                server="mock",
                tool="stream_tool",
                params={"count": 3}
            ):
                chunks.append(chunk)
            assert len(chunks) == 3
            
            # 5. 遺留 API
            legacy_result = await client.call_tool_legacy(
                server_name="mock",
                tool_name="legacy_tool",
                parameters={}
            )
            assert legacy_result["success"] is True
            
        finally:
            # 清理
            await client.close()
    
    @pytest.mark.asyncio
    async def test_error_handling_workflow(self):
        """測試錯誤處理工作流程"""
        client = get_unified_mcp_client(client_type="mock")
        
        # 取得 mock 適配器並設定錯誤模式
        mock_client = client._adapters["mock"]._mock_client
        mock_client.simulate_error = True
        
        try:
            # 應該引發錯誤
            with pytest.raises(MCPError):
                await client.call_tool("mock", "test", {})
            
            # 批次呼叫應該部分成功
            mock_client.simulate_error = False  # 關閉錯誤模式
            calls = [
                MCPCall(server="mock", tool="tool1", params={}),
                MCPCall(server="mock", tool="tool2", params={}),
            ]
            
            # 第二個呼叫會失敗
            mock_client.call_count = 0
            mock_client.error_on_call = 2
            
            batch_response = await client.batch_call(calls)
            assert batch_response.success_count >= 1
            
        finally:
            await client.close()