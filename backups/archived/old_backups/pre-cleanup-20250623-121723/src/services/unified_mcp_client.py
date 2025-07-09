"""
統一 MCP 客戶端 - 重構為生產級實作
基於 ultimate-stdio-test.py 的成功模式，簡化為單一可靠實作
"""

from typing import Any

import structlog

from .production_mcp_client import get_production_mcp_client

logger = structlog.get_logger()


class UnifiedMCPClient:
    """統一 MCP 客戶端 - 使用生產級實作"""

    def __init__(self, client_type: str = "production", **kwargs):
        """
        初始化統一客戶端

        Args:
            client_type: 客戶端類型 (固定為 "production")
            **kwargs: 額外配置參數（向下兼容）
        """
        self.client_type = "production"  # 強制使用生產級客戶端
        self._client = get_production_mcp_client()

        logger.info("✅ 統一客戶端已重構為生產級實作")

    def _get_server_name(self, tool_name: str) -> str:
        """根據工具名稱推斷服務器名稱"""
        # 根據工具名稱映射到服務器
        if tool_name in ["read_query", "write_query", "list_tables", "describe_table"]:
            return "sqlite"

        # 預設使用 sqlite
        return "sqlite"

    async def call_tool(
        self, server: str, tool: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """
        呼叫 MCP 工具（統一介面）

        Args:
            server: 伺服器名稱（向下兼容，自動推斷）
            tool: 工具名稱
            params: 參數字典

        Returns:
            標準化回應字典
        """
        try:
            # 自動推斷服務器名稱（向下兼容舊代碼）
            actual_server = self._get_server_name(tool) if server == "auto" else server

            logger.info(f"🛠️ 統一客戶端調用：{actual_server}.{tool}")

            # 直接使用生產級客戶端
            result = await self._client.call_tool(actual_server, tool, params)

            if result.get("success"):
                logger.info(f"✅ 統一客戶端調用成功：{actual_server}.{tool}")
            else:
                logger.error(f"❌ 統一客戶端調用失敗：{result.get('error')}")

            return result

        except Exception as e:
            logger.error(f"❌ 統一客戶端調用異常：{e}")
            return {"success": False, "error": str(e)}

    async def list_tools(self, server: str = "sqlite") -> dict[str, Any]:
        """列出工具"""
        try:
            result = await self._client.list_tools(server)
            return result
        except Exception as e:
            logger.error(f"❌ 列出工具失敗：{e}")
            return {"success": False, "error": str(e)}

    async def get_server_info(self, server: str = "sqlite") -> dict[str, Any]:
        """獲取服務器信息"""
        try:
            tools_result = await self.list_tools(server)
            if tools_result.get("success"):
                return {
                    "success": True,
                    "server_name": server,
                    "protocol": "STDIO (Production Fixed)",
                    "tools": tools_result.get("tools", []),
                    "connection_type": "生產級 STDIO 修復版",
                    "mcp_compliant": True,
                }
            else:
                return tools_result
        except Exception as e:
            logger.error(f"❌ 獲取服務器信息失敗：{e}")
            return {"success": False, "error": str(e)}

    async def close(self):
        """關閉所有連接"""
        try:
            await self._client.close_all_connections()
            logger.info("✅ 統一客戶端已關閉所有連接")
        except Exception as e:
            logger.warning(f"⚠️ 關閉連接時發生警告：{e}")


# 單例模式
_unified_mcp_client = None


async def get_unified_mcp_client() -> UnifiedMCPClient:
    """獲取統一 MCP 客戶端實例"""
    global _unified_mcp_client
    if _unified_mcp_client is None:
        _unified_mcp_client = UnifiedMCPClient()
    return _unified_mcp_client


# 向下兼容的函數
async def call_mcp_tool(
    server: str, tool: str, params: dict[str, Any]
) -> dict[str, Any]:
    """向下兼容的工具調用函數"""
    client = await get_unified_mcp_client()
    return await client.call_tool(server, tool, params)


async def list_mcp_tools(server: str = "sqlite") -> dict[str, Any]:
    """向下兼容的工具列表函數"""
    client = await get_unified_mcp_client()
    return await client.list_tools(server)
