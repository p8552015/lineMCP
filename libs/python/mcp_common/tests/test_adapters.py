"""
測試協定適配器
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import json

from mcp_common.adapters.base import BaseProtocolAdapter
from mcp_common.adapters.http import HTTPAdapter
from mcp_common.adapters.websocket import WebSocketAdapter
from mcp_common.adapters.stdio import STDIOAdapter
from mcp_common.adapters.simple_adapter import SimpleAdapter
from mcp_common.adapters.legacy_adapter import LegacyAdapter
from mcp_common.models.base import MCPCall, MCPResponse
from mcp_common.models.error import MCPError, MCPTimeoutError


class TestBaseProtocolAdapter:
    """測試基礎協定適配器"""
    
    def test_abstract_methods(self):
        """測試抽象方法"""
        # 不能直接實例化抽象類別
        with pytest.raises(TypeError):
            BaseProtocolAdapter()
    
    @pytest.mark.asyncio
    async def test_adapter_interface(self):
        """測試適配器介面"""
        # 建立具體實作
        class ConcreteAdapter(BaseProtocolAdapter):
            async def connect(self):
                pass
            
            async def disconnect(self):
                pass
            
            async def send_request(self, call: MCPCall) -> MCPResponse:
                return MCPResponse(
                    status="success",
                    data={"result": "ok"},
                    call_id=call.id
                )
            
            async def health_check(self) -> bool:
                return True
        
        adapter = ConcreteAdapter()
        
        # 測試發送請求
        call = MCPCall(server="test", tool="test", params={})
        response = await adapter.send_request(call)
        assert response.status == "success"
        
        # 測試健康檢查
        health = await adapter.health_check()
        assert health is True


class TestHTTPAdapter:
    """測試 HTTP 適配器"""
    
    @pytest.fixture
    def adapter(self):
        """建立測試適配器"""
        return HTTPAdapter(
            base_url="http://localhost:8080",
            timeout=30.0,
            headers={"Authorization": "Bearer token"}
        )
    
    @pytest.mark.asyncio
    async def test_connect(self, adapter):
        """測試連接"""
        with patch('aiohttp.ClientSession') as mock_session:
            await adapter.connect()
            assert adapter._session is not None
    
    @pytest.mark.asyncio
    async def test_disconnect(self, adapter):
        """測試斷開連接"""
        mock_session = Mock()
        mock_session.close = AsyncMock()
        adapter._session = mock_session
        
        await adapter.disconnect()
        mock_session.close.assert_called_once()
        assert adapter._session is None
    
    @pytest.mark.asyncio
    async def test_send_request_success(self, adapter):
        """測試成功發送請求"""
        # 模擬 HTTP 回應
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "status": "success",
            "data": {"result": "test_result"}
        })
        
        mock_session = Mock()
        mock_session.post = AsyncMock(return_value=mock_response)
        adapter._session = mock_session
        
        # 發送請求
        call = MCPCall(server="test", tool="test_tool", params={"key": "value"})
        response = await adapter.send_request(call)
        
        # 驗證結果
        assert response.status == "success"
        assert response.data["result"] == "test_result"
        
        # 驗證請求參數
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert call_args[0][0] == "http://localhost:8080/mcp/call"
        assert call_args[1]["json"]["tool"] == "test_tool"
        assert call_args[1]["timeout"] == 30.0
    
    @pytest.mark.asyncio
    async def test_send_request_http_error(self, adapter):
        """測試 HTTP 錯誤"""
        mock_response = Mock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        
        mock_session = Mock()
        mock_session.post = AsyncMock(return_value=mock_response)
        adapter._session = mock_session
        
        call = MCPCall(server="test", tool="test", params={})
        
        with pytest.raises(MCPError) as exc_info:
            await adapter.send_request(call)
        
        assert "HTTP 500" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_send_request_timeout(self, adapter):
        """測試請求超時"""
        mock_session = Mock()
        mock_session.post = AsyncMock(side_effect=asyncio.TimeoutError())
        adapter._session = mock_session
        
        call = MCPCall(server="test", tool="test", params={})
        
        with pytest.raises(MCPTimeoutError):
            await adapter.send_request(call)
    
    @pytest.mark.asyncio
    async def test_health_check(self, adapter):
        """測試健康檢查"""
        mock_response = Mock()
        mock_response.status = 200
        
        mock_session = Mock()
        mock_session.get = AsyncMock(return_value=mock_response)
        adapter._session = mock_session
        
        health = await adapter.health_check()
        assert health is True
        
        # 測試不健康狀態
        mock_response.status = 503
        health = await adapter.health_check()
        assert health is False


class TestWebSocketAdapter:
    """測試 WebSocket 適配器"""
    
    @pytest.fixture
    def adapter(self):
        """建立測試適配器"""
        return WebSocketAdapter(
            url="ws://localhost:8080",
            reconnect_interval=1.0
        )
    
    @pytest.mark.asyncio
    async def test_connect(self, adapter):
        """測試連接"""
        mock_ws = Mock()
        
        with patch('websockets.connect', AsyncMock(return_value=mock_ws)):
            await adapter.connect()
            assert adapter._websocket == mock_ws
            assert adapter._connected is True
    
    @pytest.mark.asyncio
    async def test_disconnect(self, adapter):
        """測試斷開連接"""
        mock_ws = Mock()
        mock_ws.close = AsyncMock()
        adapter._websocket = mock_ws
        adapter._connected = True
        
        await adapter.disconnect()
        
        mock_ws.close.assert_called_once()
        assert adapter._websocket is None
        assert adapter._connected is False
    
    @pytest.mark.asyncio
    async def test_send_request(self, adapter):
        """測試發送請求"""
        # 設定模擬 WebSocket
        mock_ws = Mock()
        mock_ws.send = AsyncMock()
        mock_ws.recv = AsyncMock(return_value=json.dumps({
            "id": "123",
            "status": "success",
            "data": {"result": "ok"}
        }))
        
        adapter._websocket = mock_ws
        adapter._connected = True
        
        # 發送請求
        call = MCPCall(id="123", server="test", tool="test", params={})
        response = await adapter.send_request(call)
        
        # 驗證結果
        assert response.status == "success"
        assert response.data["result"] == "ok"
        
        # 驗證發送的訊息
        mock_ws.send.assert_called_once()
        sent_data = json.loads(mock_ws.send.call_args[0][0])
        assert sent_data["id"] == "123"
        assert sent_data["tool"] == "test"
    
    @pytest.mark.asyncio
    async def test_auto_reconnect(self, adapter):
        """測試自動重連"""
        # 第一次連接失敗
        connect_attempts = 0
        
        async def mock_connect(*args, **kwargs):
            nonlocal connect_attempts
            connect_attempts += 1
            if connect_attempts == 1:
                raise ConnectionError("Connection failed")
            return Mock()
        
        with patch('websockets.connect', mock_connect):
            # 啟動重連任務
            reconnect_task = asyncio.create_task(adapter._reconnect_loop())
            
            # 等待重連
            await asyncio.sleep(2)
            
            # 應該已經重連成功
            assert adapter._connected is True
            assert connect_attempts >= 2
            
            # 清理
            reconnect_task.cancel()
            try:
                await reconnect_task
            except asyncio.CancelledError:
                pass


class TestSTDIOAdapter:
    """測試 STDIO 適配器"""
    
    @pytest.fixture
    def adapter(self):
        """建立測試適配器"""
        return STDIOAdapter(
            command=["python", "-m", "mcp_server"],
            working_dir="/tmp"
        )
    
    @pytest.mark.asyncio
    async def test_connect(self, adapter):
        """測試連接"""
        mock_process = Mock()
        mock_process.stdin = Mock()
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        
        with patch('asyncio.create_subprocess_exec', AsyncMock(return_value=mock_process)):
            await adapter.connect()
            assert adapter._process == mock_process
    
    @pytest.mark.asyncio
    async def test_disconnect(self, adapter):
        """測試斷開連接"""
        mock_process = Mock()
        mock_process.terminate = Mock()
        mock_process.wait = AsyncMock()
        adapter._process = mock_process
        
        await adapter.disconnect()
        
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once()
        assert adapter._process is None
    
    @pytest.mark.asyncio
    async def test_send_request(self, adapter):
        """測試發送請求"""
        # 模擬進程
        mock_process = Mock()
        
        # 模擬 stdin 寫入
        mock_stdin = Mock()
        mock_stdin.write = Mock()
        mock_stdin.drain = AsyncMock()
        mock_process.stdin = mock_stdin
        
        # 模擬 stdout 讀取
        mock_stdout = Mock()
        mock_stdout.readline = AsyncMock(return_value=json.dumps({
            "id": "123",
            "status": "success",
            "data": {"result": "ok"}
        }).encode() + b'\n')
        mock_process.stdout = mock_stdout
        
        adapter._process = mock_process
        
        # 發送請求
        call = MCPCall(id="123", server="test", tool="test", params={})
        response = await adapter.send_request(call)
        
        # 驗證結果
        assert response.status == "success"
        assert response.data["result"] == "ok"
        
        # 驗證寫入的資料
        mock_stdin.write.assert_called_once()
        written_data = mock_stdin.write.call_args[0][0]
        assert b"test" in written_data
        assert b"123" in written_data


class TestSimpleAdapter:
    """測試簡單適配器"""
    
    @pytest.fixture
    def adapter(self):
        """建立測試適配器"""
        mock_client = Mock()
        mock_client.call_tool_legacy = AsyncMock(return_value={
            "success": True,
            "result": {"data": "test"}
        })
        return SimpleAdapter(simple_client=mock_client)
    
    @pytest.mark.asyncio
    async def test_send_request_success(self, adapter):
        """測試成功發送請求"""
        call = MCPCall(
            server="sqlite",
            tool="query",
            params={"sql": "SELECT 1"}
        )
        
        response = await adapter.send_request(call)
        
        assert response.status == "success"
        assert response.data["data"] == "test"
        
        # 驗證呼叫參數
        adapter._simple_client.call_tool_legacy.assert_called_once_with(
            server_name="sqlite",
            tool_name="query",
            parameters={"sql": "SELECT 1"}
        )
    
    @pytest.mark.asyncio
    async def test_send_request_failure(self, adapter):
        """測試請求失敗"""
        adapter._simple_client.call_tool_legacy = AsyncMock(return_value={
            "success": False,
            "error": "Database error"
        })
        
        call = MCPCall(server="sqlite", tool="query", params={})
        response = await adapter.send_request(call)
        
        assert response.status == "error"
        assert response.error == "Database error"


class TestLegacyAdapter:
    """測試遺留適配器"""
    
    @pytest.fixture
    def adapter(self):
        """建立測試適配器"""
        mock_client = Mock()
        mock_client.call_tool = AsyncMock(return_value={
            "success": True,
            "data": {"result": "legacy"}
        })
        return LegacyAdapter(legacy_client=mock_client)
    
    @pytest.mark.asyncio
    async def test_send_request(self, adapter):
        """測試發送請求"""
        call = MCPCall(
            server="legacy_server",
            tool="legacy_tool",
            params={"param": "value"}
        )
        
        response = await adapter.send_request(call)
        
        assert response.status == "success"
        assert response.data["result"] == "legacy"
        
        # 驗證呼叫參數
        adapter._legacy_client.call_tool.assert_called_once_with(
            "legacy_server",
            "legacy_tool",
            {"param": "value"}
        )
    
    @pytest.mark.asyncio
    async def test_health_check(self, adapter):
        """測試健康檢查"""
        adapter._legacy_client.health_check = AsyncMock(return_value=True)
        
        health = await adapter.health_check()
        assert health is True