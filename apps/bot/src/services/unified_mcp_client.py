"""
統一 MCP 客戶端 - 代理到生產級實現
簡化架構，直接使用 ProductionMCPClient 避免 cancel scope 問題
"""

from typing import Any

import structlog

from .production_mcp_client import get_production_mcp_client

logger = structlog.get_logger()


class UnifiedMCPClient:
    """統一 MCP 客戶端 - 代理到 ProductionMCPClient"""

    def __init__(self, **kwargs):
        """
        初始化統一客戶端 - 代理模式

        Args:
            **kwargs: 額外配置參數（向下兼容）
        """
        # 向下兼容，忽略額外參數
        _ = kwargs
        self._production_client = get_production_mcp_client()
        logger.info("🔄 統一客戶端已簡化為生產級代理")

    async def call_tool(
        self,
        server: str,
        tool: str,
        params: dict[str, Any],
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """
        調用 MCP 工具 - 代理到生產級客戶端

        Args:
            server: 服務器名稱
            tool: 工具名稱
            params: 工具參數
            timeout: 超時時間（秒）

        Returns:
            工具執行結果
        """
        result = await self._production_client.call_tool(server, tool, params, timeout)
        return dict(result) if result is not None else {}

    async def list_tools(self, server: str) -> list[dict[str, Any]]:
        """
        列出可用工具 - 代理到生產級客戶端

        Args:
            server: 服務器名稱

        Returns:
            工具列表
        """
        result = await self._production_client.list_tools(server)
        return list(result) if result is not None else []

    async def connect_to_server(self, server_name: str) -> bool:
        """
        連接到服務器 - 代理到生產級客戶端

        Args:
            server_name: 服務器名稱

        Returns:
            連接是否成功
        """
        result = await self._production_client.connect_to_server(server_name)
        return bool(result)

    async def close(self):
        """關閉客戶端 - 代理到生產級客戶端"""
        await self._production_client.close()

    @property
    def server_configs(self) -> dict[str, Any]:
        """獲取服務器配置字典 - 提供 API 一致性"""
        result = self._production_client.server_configs
        return dict(result) if result is not None else {}

    def list_servers(self) -> list[str]:
        """列出所有可用的服務器名稱 - 提供 API 一致性"""
        result = self._production_client.list_servers()
        return list(result) if result is not None else []


# 單例模式
_unified_mcp_client = None


async def get_unified_mcp_client() -> UnifiedMCPClient:
    """統一 MCP 客戶端 - 代理到生產級實現"""
    global _unified_mcp_client
    if _unified_mcp_client is None:
        _unified_mcp_client = UnifiedMCPClient()
    return _unified_mcp_client


# 向下兼容的函數
async def call_mcp_tool(
    server: str, tool: str, params: dict[str, Any], timeout: float | None = None
) -> dict[str, Any]:
    """
    調用 MCP 工具的向下兼容函數

    Args:
        server: 服務器名稱
        tool: 工具名稱
        params: 工具參數
        timeout: 超時時間（秒）

    Returns:
        工具執行結果
    """
    client = await get_unified_mcp_client()
    return await client.call_tool(server, tool, params, timeout)


async def list_mcp_tools(server: str) -> list[dict[str, Any]]:
    """
    列出 MCP 工具的向下兼容函數

    Args:
        server: 服務器名稱

    Returns:
        工具列表
    """
    client = await get_unified_mcp_client()
    return await client.list_tools(server)
