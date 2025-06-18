"""
簡化的 MCP 客戶端 - 現已使用統一的 mcp_common 實作
向後相容包裝，透明地使用新的企業級客戶端
"""
import structlog
from typing import Dict, Any, List, Optional

from src.services.unified_mcp_client import get_unified_mcp_client

logger = structlog.get_logger()


class SimpleMCPClient:
    """簡化 MCP 客戶端 - 使用統一客戶端實作"""
    
    def __init__(self):
        """初始化客戶端"""
        self._unified_client = get_unified_mcp_client(client_type="simple")
        logger.info("✅ 簡化 MCP 客戶端已初始化（使用統一實作）")
    
    async def call_tool(self, server_name: str, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """呼叫 MCP 工具"""
        return await self._unified_client.call_tool_legacy(
            server_name=server_name,
            tool_name=tool_name,
            parameters=parameters
        )
    
    async def list_tools(self, server_name: str) -> List[str]:
        """列出可用工具"""
        return await self._unified_client.list_tools(server_name)
    
    async def connect_to_server(self, server_name: str) -> bool:
        """連接到伺服器"""
        try:
            # 嘗試呼叫健康檢查來驗證連接
            health = await self._unified_client.health_check(server_name)
            return health.get("overall") in ["healthy", "degraded"]
        except Exception:
            return False
    
    async def get_server_info(self, server_name: str) -> Dict[str, Any]:
        """獲取伺服器資訊"""
        try:
            tools = await self._unified_client.list_tools(server_name)
            return {
                "tools": [{"name": tool, "description": f"{tool} 工具"} for tool in tools],
                "resources": [],
                "server_info": f"伺服器: {server_name}"
            }
        except Exception as e:
            logger.error(f"獲取伺服器資訊失敗: {e}")
            return {}
    
    async def close_all_connections(self):
        """清理連接"""
        await self._unified_client.close_all_connections()


# 單例模式
_simple_mcp_client = None


def get_simple_mcp_client() -> SimpleMCPClient:
    """獲取簡化 MCP 客戶端實例"""
    global _simple_mcp_client
    if _simple_mcp_client is None:
        _simple_mcp_client = SimpleMCPClient()
    return _simple_mcp_client