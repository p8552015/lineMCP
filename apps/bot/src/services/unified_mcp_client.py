"""
統一 MCP 客戶端 - 重構為官方 SDK 架構
基於官方 MCP Python SDK，解決並發安全性和生產環境可靠性問題
"""

from typing import Any

import structlog

from .mcp import get_mcp_client_manager

logger = structlog.get_logger()


class UnifiedMCPClient:
    """統一 MCP 客戶端 - 使用官方 SDK 架構"""

    def __init__(self, client_type: str = "official", **kwargs):
        """
        初始化統一客戶端

        Args:
            client_type: 客戶端類型 (固定為 "official")
            **kwargs: 額外配置參數（向下兼容）
        """
        self.client_type = "official"  # 使用官方 SDK 架構
        self._manager = None  # 延遲初始化

        logger.info("✅ 統一客戶端已重構為官方 SDK 架構")

    def _get_server_name(self, tool_name: str) -> str:
        """根據工具名稱推斷服務器名稱"""
        # 根據工具名稱映射到服務器
        if tool_name in ["read_query", "write_query", "list_tables", "describe_table"]:
            return "postgres"

        # 預設使用 postgres
        return "postgres"

    async def _get_manager(self):
        """獲取 MCP 客戶端管理器（延遲初始化）"""
        if self._manager is None:
            self._manager = await get_mcp_client_manager()
        return self._manager

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

            # 使用新的 MCP 客戶端管理器
            manager = await self._get_manager()
            result = await manager.call_tool(actual_server, tool, params)

            if result.get("success"):
                logger.info(f"✅ 統一客戶端調用成功：{actual_server}.{tool}")
            else:
                logger.error(f"❌ 統一客戶端調用失敗：{result.get('error')}")

            return result

        except Exception as e:
            logger.error(f"❌ 統一客戶端調用異常：{e}")
            return {"success": False, "error": str(e)}

    async def list_tools(self, server: str = "postgres") -> dict[str, Any]:
        """列出工具"""
        try:
            manager = await self._get_manager()
            result = await manager.list_tools(server)
            return result
        except Exception as e:
            logger.error(f"❌ 列出工具失敗：{e}")
            return {"success": False, "error": str(e)}

    async def get_server_info(self, server: str = "postgres") -> dict[str, Any]:
        """獲取服務器信息"""
        try:
            manager = await self._get_manager()
            result = await manager.get_server_info(server)
            
            # 更新協議信息以反映新架構
            if result.get("success"):
                result["protocol"] = "STDIO (官方 MCP SDK)"
                result["connection_type"] = "官方 SDK + 並發安全架構"
                result["architecture"] = "會話池 + 請求隊列"
            
            return result
        except Exception as e:
            logger.error(f"❌ 獲取服務器信息失敗：{e}")
            return {"success": False, "error": str(e)}

    async def close(self):
        """關閉所有連接"""
        try:
            if self._manager:
                await self._manager.close_all_connections()
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


async def list_mcp_tools(server: str = "postgres") -> dict[str, Any]:
    """向下兼容的工具列表函數"""
    client = await get_unified_mcp_client()
    return await client.list_tools(server)
