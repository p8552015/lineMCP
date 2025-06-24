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

        assert client.client_type == "production"
        assert client._client == mock_client
        mock_get_production_client.assert_called_once()

    @patch("src.services.unified_mcp_client.get_production_mcp_client")
    def test_client_type_forced_to_production(self, mock_get_production_client):
        """測試客戶端類型強制設為production"""
        mock_client = MagicMock()
        mock_get_production_client.return_value = mock_client

        # 即使傳入其他類型，也會強制設為production
        client = UnifiedMCPClient(client_type="other")

        assert client.client_type == "production"

    def test_get_server_name_sqlite_tools(self):
        """測試SQLite工具的伺服器名稱推斷"""
        with patch("src.services.unified_mcp_client.get_production_mcp_client"):
            client = UnifiedMCPClient()

            sqlite_tools = [
                "read_query",
                "write_query",
                "list_tables",
                "describe_table",
            ]
            for tool in sqlite_tools:
                assert client._get_server_name(tool) == "sqlite"

    def test_get_server_name_default(self):
        """測試預設伺服器名稱"""
        with patch("src.services.unified_mcp_client.get_production_mcp_client"):
            client = UnifiedMCPClient()

            assert client._get_server_name("unknown_tool") == "sqlite"

    @pytest.mark.asyncio
    @patch("src.services.unified_mcp_client.get_production_mcp_client")
    async def test_call_tool_success(self, mock_get_production_client):
        """測試成功調用工具"""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {"success": True, "data": "test_result"}
        mock_get_production_client.return_value = mock_client

        client = UnifiedMCPClient()
        result = await client.call_tool("sqlite", "read_query", {"query": "SELECT 1"})

        assert result["success"] is True
        assert result["data"] == "test_result"
        mock_client.call_tool.assert_called_once_with(
            "sqlite", "read_query", {"query": "SELECT 1"}
        )

    @pytest.mark.asyncio
    @patch("src.services.unified_mcp_client.get_production_mcp_client")
    async def test_call_tool_failure(self, mock_get_production_client):
        """測試工具調用失敗"""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {"success": False, "error": "test_error"}
        mock_get_production_client.return_value = mock_client

        client = UnifiedMCPClient()
        result = await client.call_tool("sqlite", "read_query", {"query": "SELECT 1"})

        assert result["success"] is False
        assert result["error"] == "test_error"

    @pytest.mark.asyncio
    @patch("src.services.unified_mcp_client.get_production_mcp_client")
    async def test_call_tool_exception(self, mock_get_production_client):
        """測試工具調用異常"""
        mock_client = AsyncMock()
        mock_client.call_tool.side_effect = Exception("connection_error")
        mock_get_production_client.return_value = mock_client

        client = UnifiedMCPClient()
        result = await client.call_tool("sqlite", "read_query", {"query": "SELECT 1"})

        assert result["success"] is False
        assert "connection_error" in result["error"]

    @pytest.mark.asyncio
    @patch("src.services.unified_mcp_client.get_production_mcp_client")
    async def test_call_tool_server_auto_inference(self, mock_get_production_client):
        """測試自動推斷伺服器名稱"""
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {"success": True}
        mock_get_production_client.return_value = mock_client

        client = UnifiedMCPClient()
        await client.call_tool("auto", "read_query", {"query": "SELECT 1"})

        # 應該調用sqlite伺服器
        mock_client.call_tool.assert_called_once_with(
            "sqlite", "read_query", {"query": "SELECT 1"}
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
        result = await client.list_tools("sqlite")

        assert result["success"] is True
        assert result["tools"] == ["read_query", "write_query"]
        mock_client.list_tools.assert_called_once_with("sqlite")

    @pytest.mark.asyncio
    @patch("src.services.unified_mcp_client.get_production_mcp_client")
    async def test_list_tools_exception(self, mock_get_production_client):
        """測試列出工具異常"""
        mock_client = AsyncMock()
        mock_client.list_tools.side_effect = Exception("server_error")
        mock_get_production_client.return_value = mock_client

        client = UnifiedMCPClient()
        result = await client.list_tools("sqlite")

        assert result["success"] is False
        assert "server_error" in result["error"]

    @pytest.mark.asyncio
    @patch("src.services.unified_mcp_client.get_production_mcp_client")
    async def test_get_server_info_success(self, mock_get_production_client):
        """測試成功獲取伺服器信息"""
        mock_client = AsyncMock()
        mock_client.list_tools.return_value = {
            "success": True,
            "tools": [{"name": "read_query", "description": "Read data"}],
        }
        mock_get_production_client.return_value = mock_client

        client = UnifiedMCPClient()
        result = await client.get_server_info("sqlite")

        assert result["success"] is True
        assert result["server_name"] == "sqlite"
        assert result["protocol"] == "STDIO (Production Fixed)"
        assert result["connection_type"] == "生產級 STDIO 修復版"
        assert result["mcp_compliant"] is True
        assert "tools" in result

    @pytest.mark.asyncio
    @patch("src.services.unified_mcp_client.get_production_mcp_client")
    async def test_get_server_info_failure(self, mock_get_production_client):
        """測試獲取伺服器信息失敗"""
        mock_client = AsyncMock()
        mock_client.list_tools.return_value = {
            "success": False,
            "error": "connection_failed",
        }
        mock_get_production_client.return_value = mock_client

        client = UnifiedMCPClient()
        result = await client.get_server_info("sqlite")

        assert result["success"] is False
        assert result["error"] == "connection_failed"

    @pytest.mark.asyncio
    @patch("src.services.unified_mcp_client.get_production_mcp_client")
    async def test_close_success(self, mock_get_production_client):
        """測試成功關閉連接"""
        mock_client = AsyncMock()
        mock_client.close_all_connections.return_value = None
        mock_get_production_client.return_value = mock_client

        client = UnifiedMCPClient()
        await client.close()

        mock_client.close_all_connections.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.unified_mcp_client.get_production_mcp_client")
    async def test_close_with_warning(self, mock_get_production_client):
        """測試關閉連接時的警告"""
        mock_client = AsyncMock()
        mock_client.close_all_connections.side_effect = Exception("close_warning")
        mock_get_production_client.return_value = mock_client

        client = UnifiedMCPClient()
        # 應該不會拋出異常，只是記錄警告
        await client.close()

        mock_client.close_all_connections.assert_called_once()


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

        result = await call_mcp_tool("sqlite", "read_query", {"query": "SELECT 1"})

        assert result["success"] is True
        assert result["data"] == "test"
        mock_client.call_tool.assert_called_once_with(
            "sqlite", "read_query", {"query": "SELECT 1"}
        )

    @pytest.mark.asyncio
    @patch("src.services.unified_mcp_client.get_unified_mcp_client")
    async def test_list_mcp_tools_compatibility(self, mock_get_client):
        """測試向下兼容的工具列表函數"""
        from src.services.unified_mcp_client import list_mcp_tools

        mock_client = AsyncMock()
        mock_client.list_tools.return_value = {"success": True, "tools": ["read_query"]}
        mock_get_client.return_value = mock_client

        result = await list_mcp_tools("sqlite")

        assert result["success"] is True
        assert result["tools"] == ["read_query"]
        mock_client.list_tools.assert_called_once_with("sqlite")

    @pytest.mark.asyncio
    @patch("src.services.unified_mcp_client.get_unified_mcp_client")
    async def test_list_mcp_tools_default_server(self, mock_get_client):
        """測試向下兼容函數的默認伺服器"""
        from src.services.unified_mcp_client import list_mcp_tools

        mock_client = AsyncMock()
        mock_client.list_tools.return_value = {"success": True, "tools": []}
        mock_get_client.return_value = mock_client

        await list_mcp_tools()  # 不傳參數，應該使用默認的sqlite

        mock_client.list_tools.assert_called_once_with("sqlite")
