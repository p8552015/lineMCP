"""
測試統一MCP客戶端
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.unified_mcp_client import UnifiedMCPClient, get_unified_mcp_client


class TestUnifiedMCPClient:
    """統一MCP客戶端測試"""

    @patch("src.services.unified_mcp_client.get_production_mcp_client")
    def test_initialization(self, mock_get_production_client):
        """測試客戶端初始化"""
        mock_client = MagicMock()
        mock_get_production_client.return_value = mock_client

        client = UnifiedMCPClient()

        # 檢查實際存在的屬性
        assert client._production_client == mock_client
        mock_get_production_client.assert_called_once()

    @patch("src.services.unified_mcp_client.get_production_mcp_client")
    def test_kwargs_handling(self, mock_get_production_client):
        """測試額外參數處理（向下兼容）"""
        mock_client = MagicMock()
        mock_get_production_client.return_value = mock_client

        # 額外參數應該被忽略（向下兼容）
        client = UnifiedMCPClient(client_type="other", extra_param="test")

        # 檢查客戶端正常初始化
        assert client._production_client == mock_client

    @patch("src.services.unified_mcp_client.get_production_mcp_client")
    def test_api_consistency_server_configs(self, mock_get_production_client):
        """測試 API 一致性 - server_configs 屬性"""
        mock_client = MagicMock()
        mock_client.server_configs = {"postgres": {"protocol": "stdio"}}
        mock_get_production_client.return_value = mock_client

        client = UnifiedMCPClient()

        # 測試 server_configs 屬性
        configs = client.server_configs
        assert configs == {"postgres": {"protocol": "stdio"}}

    @patch("src.services.unified_mcp_client.get_production_mcp_client")
    def test_api_consistency_list_servers(self, mock_get_production_client):
        """測試 API 一致性 - list_servers 方法"""
        mock_client = MagicMock()
        mock_client.list_servers.return_value = ["postgres", "context7"]
        mock_get_production_client.return_value = mock_client

        client = UnifiedMCPClient()

        # 測試 list_servers 方法
        servers = client.list_servers()
        assert servers == ["postgres", "context7"]
        mock_client.list_servers.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.unified_mcp_client.get_production_mcp_client")
    async def test_call_tool_success(self, mock_get_production_client):
        """測試成功調用工具"""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {"success": True, "data": "test_result"}
        mock_get_production_client.return_value = mock_client

        client = UnifiedMCPClient()
        result = await client.call_tool("postgres", "query", {"sql": "SELECT 1"})

        assert result["success"] is True
        assert result["data"] == "test_result"
        mock_client.call_tool.assert_called_once_with(
            "postgres", "query", {"sql": "SELECT 1"}, None
        )

    @pytest.mark.asyncio
    @patch("src.services.unified_mcp_client.get_production_mcp_client")
    async def test_call_tool_failure(self, mock_get_production_client):
        """測試工具調用失敗"""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {"success": False, "error": "test_error"}
        mock_get_production_client.return_value = mock_client

        client = UnifiedMCPClient()
        result = await client.call_tool("postgres", "query", {"sql": "SELECT 1"})

        assert result["success"] is False
        assert result["error"] == "test_error"

    @pytest.mark.asyncio
    @patch("src.services.unified_mcp_client.get_production_mcp_client")
    async def test_call_tool_exception(self, mock_get_production_client):
        """測試工具調用異常 - 生產級客戶端會返回錯誤字典"""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "success": False,
            "error": "connection_error",
        }
        mock_get_production_client.return_value = mock_client

        client = UnifiedMCPClient()
        result = await client.call_tool("postgres", "query", {"sql": "SELECT 1"})

        assert result["success"] is False
        assert "connection_error" in result["error"]

    @pytest.mark.asyncio
    @patch("src.services.unified_mcp_client.get_production_mcp_client")
    async def test_call_tool_with_auto_server(self, mock_get_production_client):
        """測試使用 auto 作為服務器名稱"""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {"success": True}
        mock_get_production_client.return_value = mock_client

        client = UnifiedMCPClient()
        result = await client.call_tool("auto", "read_query", {"query": "SELECT 1"})

        # auto 應該直接傳遞給底層客戶端
        assert result["success"] is True
        mock_client.call_tool.assert_called_once_with(
            "auto", "read_query", {"query": "SELECT 1"}, None
        )

    @pytest.mark.asyncio
    @patch("src.services.unified_mcp_client.get_production_mcp_client")
    async def test_list_tools_success(self, mock_get_production_client):
        """測試成功列出工具"""
        mock_client = AsyncMock()
        mock_client.list_tools.return_value = {
            "success": True,
            "tools": ["read_query", "write_query"],
        }
        mock_get_production_client.return_value = mock_client

        client = UnifiedMCPClient()
        result = await client.list_tools("postgres")

        assert result["success"] is True
        assert result["tools"] == ["read_query", "write_query"]
        mock_client.list_tools.assert_called_once_with("postgres")

    @pytest.mark.asyncio
    @patch("src.services.unified_mcp_client.get_production_mcp_client")
    async def test_list_tools_exception(self, mock_get_production_client):
        """測試列出工具異常 - 生產級客戶端會返回錯誤字典"""
        mock_client = AsyncMock()
        mock_client.list_tools.return_value = {
            "success": False,
            "error": "server_error",
        }
        mock_get_production_client.return_value = mock_client

        client = UnifiedMCPClient()
        result = await client.list_tools("postgres")

        assert result["success"] is False
        assert "server_error" in result["error"]

    @pytest.mark.asyncio
    @patch("src.services.unified_mcp_client.get_production_mcp_client")
    async def test_connect_to_server(self, mock_get_production_client):
        """測試連接到服務器"""
        mock_client = AsyncMock()
        mock_client.connect_to_server.return_value = True
        mock_get_production_client.return_value = mock_client

        client = UnifiedMCPClient()
        result = await client.connect_to_server("postgres")

        assert result is True
        mock_client.connect_to_server.assert_called_once_with("postgres")

    @pytest.mark.asyncio
    @patch("src.services.unified_mcp_client.get_production_mcp_client")
    async def test_close_success(self, mock_get_production_client):
        """測試成功關閉連接"""
        mock_client = AsyncMock()
        mock_client.close.return_value = None
        mock_get_production_client.return_value = mock_client

        client = UnifiedMCPClient()
        await client.close()

        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.unified_mcp_client.get_production_mcp_client")
    async def test_close_with_warning(self, mock_get_production_client):
        """測試關閉連接時的警告"""
        mock_client = AsyncMock()
        mock_client.close.side_effect = Exception("close_warning")
        mock_get_production_client.return_value = mock_client

        client = UnifiedMCPClient()
        # 異常應該被正常拋出
        try:
            await client.close()
        except Exception:
            pass  # 預期會有異常

        mock_client.close.assert_called_once()


class TestSingletonAndUtilityFunctions:
    """測試單例和輔助函數"""

    @pytest.mark.asyncio
    @patch("src.services.unified_mcp_client.get_production_mcp_client")
    async def test_get_unified_mcp_client_singleton(self, mock_get_production_client):
        """測試單例模式"""
        mock_client = MagicMock()
        mock_get_production_client.return_value = mock_client

        # 清除可能的現有實例
        import src.services.unified_mcp_client

        src.services.unified_mcp_client._unified_mcp_client = None

        client1 = await get_unified_mcp_client()
        client2 = await get_unified_mcp_client()

        assert client1 is client2
        # 只應該調用一次生產客戶端創建
        mock_get_production_client.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.unified_mcp_client.get_unified_mcp_client")
    async def test_call_mcp_tool_compatibility(self, mock_get_client):
        """測試向下兼容的工具調用函數"""
        from src.services.unified_mcp_client import call_mcp_tool

        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {"success": True, "data": "test"}
        mock_get_client.return_value = mock_client

        result = await call_mcp_tool("postgres", "query", {"sql": "SELECT 1"})

        assert result["success"] is True
        assert result["data"] == "test"
        mock_client.call_tool.assert_called_once_with(
            "postgres", "query", {"sql": "SELECT 1"}, None
        )

    @pytest.mark.asyncio
    @patch("src.services.unified_mcp_client.get_unified_mcp_client")
    async def test_list_mcp_tools_compatibility(self, mock_get_client):
        """測試向下兼容的工具列表函數"""
        from src.services.unified_mcp_client import list_mcp_tools

        mock_client = AsyncMock()
        mock_client.list_tools.return_value = {"success": True, "tools": ["read_query"]}
        mock_get_client.return_value = mock_client

        result = await list_mcp_tools("postgres")

        assert result["success"] is True
        assert result["tools"] == ["read_query"]
        mock_client.list_tools.assert_called_once_with("postgres")

    @pytest.mark.asyncio
    @patch("src.services.unified_mcp_client.get_unified_mcp_client")
    async def test_list_mcp_tools_explicit_server(self, mock_get_client):
        """測試向下兼容函數需要明確指定服務器"""
        from src.services.unified_mcp_client import list_mcp_tools

        mock_client = AsyncMock()
        mock_client.list_tools.return_value = [
            {"name": "query", "description": "Execute query"}
        ]
        mock_get_client.return_value = mock_client

        result = await list_mcp_tools("postgres")  # 必須傳參數

        assert result == [{"name": "query", "description": "Execute query"}]
        mock_client.list_tools.assert_called_once_with("postgres")
