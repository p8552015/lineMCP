"""
統一 MCP 客戶端

提供向後相容的統一入口點，逐步遷移到新介面。
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from .clients.factory import get_mcp_client as _get_mcp_client
from .clients.interface import MCPClientInterface
from .models.base import MCPResponse, MCPStatusCode
from .models.error import MCPError, ConnectionError as MCPConnectionError

logger = logging.getLogger(__name__)

# 嘗試載入配置模組
try:
    from .config.config_loader import load_config, get_client_config
    _CONFIG_AVAILABLE = True
except ImportError:
    _CONFIG_AVAILABLE = False


@dataclass
class LegacyResponse:
    """向後相容的回應格式"""
    success: bool
    data: Any
    error: Optional[str] = None
    is_error: bool = False
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class UnifiedMCPClient:
    """
    統一 MCP 客戶端包裝器
    
    提供向後相容的介面，同時支援新的統一功能。
    """

    def __init__(self, client_type: str = "simple", config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        初始化統一客戶端
        
        Args:
            client_type: 客戶端類型 ("simple", "legacy", "http", "mock")
            config: 明確的配置字典
            **kwargs: 額外配置參數
        """
        self.client_type = client_type
        
        # 載入配置
        base_config = {}
        if _CONFIG_AVAILABLE and config is None:
            try:
                base_config = get_client_config(client_type)
                logger.debug(f"載入配置：{client_type}")
            except Exception as e:
                logger.warning(f"載入配置失敗：{e}")
                base_config = {}
        elif config is not None:
            base_config = config.copy()
        
        # 合併配置，kwargs 優先
        final_config = {**base_config, **kwargs}
        
        try:
            self._client: MCPClientInterface = _get_mcp_client(
                client_type=client_type,
                **final_config
            )
            logger.info(f"成功建立 {client_type} 客戶端")
        except Exception as e:
            logger.error(f"建立客戶端失敗：{e}")
            raise MCPError(f"無法建立 {client_type} 客戶端：{e}")
    
    def _convert_response(self, response: MCPResponse) -> LegacyResponse:
        """轉換回應格式為向後相容格式"""
        return LegacyResponse(
            success=response.status == MCPStatusCode.SUCCESS,
            data=response.data,
            error=response.error,
            is_error=response.status == MCPStatusCode.ERROR,
            duration_ms=getattr(response, 'duration_ms', None),
            metadata=getattr(response, 'metadata', {})
        )

    # 新的統一介面方法
    async def call_tool(
        self,
        server: str,
        tool: str,
        params: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        呼叫 MCP 工具（統一介面）
        
        Args:
            server: 伺服器名稱
            tool: 工具名稱
            params: 工具參數
            
        Returns:
            回應字典，包含 success, data, error 等欄位
        """
        try:
            response = await self._client.call_tool(server, tool, params, **kwargs)
            legacy_response = self._convert_response(response)
            return {
                "success": legacy_response.success,
                "data": legacy_response.data,
                "error": legacy_response.error,
                "is_error": legacy_response.is_error,
                "duration_ms": legacy_response.duration_ms,
                "metadata": legacy_response.metadata,
            }
        except Exception as e:
            logger.error(f"工具呼叫失敗 {server}.{tool}: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e),
                "is_error": True,
                "duration_ms": None,
                "metadata": {"error_type": type(e).__name__}
            }

    # 向後相容的方法（legacy 格式）
    async def call_tool_legacy(
        self,
        server_name: str,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Legacy 格式的工具呼叫
        
        為了向後相容，保持原有的參數名稱。
        """
        return await self.call_tool(server_name, tool_name, parameters)

    async def list_tools(self, server_name: str) -> List[str]:
        """列出可用工具（向後相容格式）"""
        try:
            tools = await self._client.list_tools(server_name)
            
            # 如果返回的是完整的工具資訊，只取名稱
            if tools and isinstance(tools[0], dict):
                return [tool.get("name", str(tool)) for tool in tools]
            else:
                return tools if tools else []
                
        except MCPConnectionError as e:
            logger.warning(f"連線錯誤，無法列出 {server_name} 的工具：{e}")
            return []
        except Exception as e:
            logger.error(f"列出工具失敗 {server_name}: {e}")
            return []

    async def connect_to_server(self, server_name: str) -> bool:
        """連接到伺服器（向後相容）"""
        try:
            health = await self._client.health_check(server_name)
            return health.servers.get(server_name) == "healthy"
        except MCPConnectionError:
            logger.debug(f"無法連接到 {server_name}")
            return False
        except Exception as e:
            logger.error(f"健康檢查失敗 {server_name}: {e}")
            return False

    async def get_server_info(self, server_name: str) -> Dict[str, Any]:
        """獲取伺服器資訊（向後相容）"""
        try:
            tools = await self._client.list_tools(server_name)
            
            # 轉換為 legacy 格式
            formatted_tools = []
            for tool in tools:
                if isinstance(tool, dict):
                    formatted_tools.append({
                        "name": tool.get("name", ""),
                        "description": tool.get("description", ""),
                    })
                else:
                    formatted_tools.append({
                        "name": str(tool),
                        "description": f"Tool: {tool}",
                    })
            
            return {
                "tools": formatted_tools,
                "resources": [],  # 新介面暫不支援 resources
                "server_info": server_name,
            }
            
        except Exception as e:
            logger.error(f"獲取伺服器資訊失敗 {server_name}: {e}")
            return {"tools": [], "resources": [], "server_info": server_name}

    async def close_all_connections(self):
        """關閉所有連接（向後相容）"""
        try:
            await self._client.close()
        except Exception as e:
            logger.error(f"關閉連接失敗: {e}")

    # 新介面方法的直接委派
    async def batch_call(self, calls):
        """批次呼叫"""
        return await self._client.batch_call(calls)

    async def stream_call(self, server, tool, params, **kwargs):
        """串流呼叫"""
        async for response in self._client.stream_call(server, tool, params, **kwargs):
            yield response

    async def health_check(self, server=None):
        """健康檢查"""
        return await self._client.health_check(server)

    async def close(self):
        """關閉客戶端"""
        await self.close_all_connections()

    def __enter__(self):
        """同步上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """同步上下文管理器出口"""
        # 同步版本無法處理 async close，留空
        pass

    async def __aenter__(self):
        """非同步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同步上下文管理器出口"""
        await self.close()


def get_unified_mcp_client(client_type: str = "simple", **kwargs) -> UnifiedMCPClient:
    """
    建立統一 MCP 客戶端實例
    
    Args:
        client_type: 客戶端類型
        **kwargs: 額外配置
        
    Returns:
        統一客戶端實例
    """
    return UnifiedMCPClient(client_type=client_type, **kwargs)


# 向後相容的工廠函數
def get_mcp_client(**kwargs) -> UnifiedMCPClient:
    """
    向後相容的客戶端工廠函數
    
    替換原有的 get_mcp_client() 和 get_simple_mcp_client()
    """
    # 預設使用 simple 類型以保持向後相容
    return get_unified_mcp_client(client_type="simple", **kwargs)


def get_simple_mcp_client() -> UnifiedMCPClient:
    """
    向後相容的 Simple MCP 客戶端
    
    直接替換原有的 get_simple_mcp_client()
    """
    return get_unified_mcp_client(client_type="simple")