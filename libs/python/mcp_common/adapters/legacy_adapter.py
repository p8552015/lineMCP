"""
Legacy MCP 客戶端適配器

將現有的 MCPClient 適配到統一介面。
"""

import time
from typing import Any, AsyncIterator, Dict, List
from uuid import uuid4

from ..models.base import (
    MCPResponse,
    MCPCall,
    CallOptions,
    HealthStatus,
    HealthStatusLevel,
    MCPStatusCode,
)
from ..models.error import MCPError
from ..clients.interface import BaseMCPClient


class LegacyMCPAdapter(BaseMCPClient):
    """
    Legacy MCP 客戶端適配器
    
    將現有的 MCPClient 包裝成符合新介面的客戶端。
    """

    def __init__(self, legacy_client=None, config: Dict[str, Any] | None = None):
        """
        初始化適配器
        
        Args:
            legacy_client: 現有的 MCPClient 實例
            config: 配置選項
        """
        super().__init__(config)
        
        # 延遲載入以避免循環導入
        if legacy_client is None:
            try:
                from src.services.mcp_client import get_mcp_client
                self._legacy_client = get_mcp_client()
            except ImportError:
                raise MCPError("無法導入 legacy MCP client")
        else:
            self._legacy_client = legacy_client

    async def call_tool(
        self,
        server: str,
        tool: str,
        params: Dict[str, Any],
        *,
        options: CallOptions | None = None,
    ) -> MCPResponse:
        """實作工具呼叫"""
        start_time = time.time()
        call_id = str(uuid4())
        
        try:
            # 呼叫 legacy 客戶端
            result = await self._legacy_client.call_tool(
                server_name=server,
                tool_name=tool,
                parameters=params,
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            # 轉換回應格式
            if result.get("success"):
                return MCPResponse(
                    call_id=call_id,
                    status=MCPStatusCode.SUCCESS,
                    data=result.get("data"),
                    duration_ms=duration_ms,
                    metadata={
                        "server": server,
                        "tool": tool,
                        "legacy_adapter": True,
                    },
                )
            else:
                return MCPResponse(
                    call_id=call_id,
                    status=MCPStatusCode.ERROR,
                    error=result.get("error", "未知錯誤"),
                    duration_ms=duration_ms,
                    metadata={
                        "server": server,
                        "tool": tool,
                        "legacy_adapter": True,
                    },
                )
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return MCPResponse(
                call_id=call_id,
                status=MCPStatusCode.ERROR,
                error=str(e),
                error_code="LEGACY_ADAPTER_ERROR",
                duration_ms=duration_ms,
                metadata={
                    "server": server,
                    "tool": tool,
                    "legacy_adapter": True,
                },
            )

    async def batch_call(self, calls: List[MCPCall]) -> List[MCPResponse]:
        """實作批次呼叫（序列執行）"""
        responses = []
        
        for call in calls:
            response = await self.call_tool(
                server=call.server,
                tool=call.tool,
                params=call.params,
                options=call.options,
            )
            responses.append(response)
        
        return responses

    async def stream_call(
        self,
        server: str,
        tool: str,
        params: Dict[str, Any],
        *,
        options: CallOptions | None = None,
    ) -> AsyncIterator[MCPResponse]:
        """實作串流呼叫（模擬）"""
        # Legacy 客戶端不支援串流，返回單一回應
        response = await self.call_tool(server, tool, params, options=options)
        yield response

    async def health_check(self, server: str | None = None) -> HealthStatus:
        """實作健康檢查"""
        start_time = time.time()
        
        try:
            if server:
                # 檢查特定伺服器
                connected = await self._legacy_client.connect_to_server(server)
                server_status = (
                    HealthStatusLevel.HEALTHY if connected 
                    else HealthStatusLevel.UNHEALTHY
                )
                servers = {server: server_status}
                overall = server_status
            else:
                # 檢查所有已知伺服器
                servers = {}
                available_servers = getattr(self._legacy_client, 'servers', {})
                
                for srv_name in available_servers.keys():
                    try:
                        connected = await self._legacy_client.connect_to_server(srv_name)
                        servers[srv_name] = (
                            HealthStatusLevel.HEALTHY if connected 
                            else HealthStatusLevel.UNHEALTHY
                        )
                    except Exception:
                        servers[srv_name] = HealthStatusLevel.UNHEALTHY
                
                # 計算整體狀態
                if not servers:
                    overall = HealthStatusLevel.UNKNOWN
                elif all(status == HealthStatusLevel.HEALTHY for status in servers.values()):
                    overall = HealthStatusLevel.HEALTHY
                elif any(status == HealthStatusLevel.HEALTHY for status in servers.values()):
                    overall = HealthStatusLevel.DEGRADED
                else:
                    overall = HealthStatusLevel.UNHEALTHY
            
            response_time_ms = (time.time() - start_time) * 1000
            
            return HealthStatus(
                overall=overall,
                servers=servers,
                response_time_ms=response_time_ms,
                details={
                    "adapter": "legacy",
                    "client_type": type(self._legacy_client).__name__,
                },
            )
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            
            return HealthStatus(
                overall=HealthStatusLevel.UNKNOWN,
                servers={},
                response_time_ms=response_time_ms,
                details={
                    "adapter": "legacy",
                    "error": str(e),
                },
            )

    async def list_tools(self, server: str) -> List[Dict[str, Any]]:
        """實作工具列表"""
        try:
            tools = await self._legacy_client.list_tools(server)
            
            # 轉換為標準格式
            if isinstance(tools, list):
                if tools and isinstance(tools[0], str):
                    # 如果是字符串列表，轉換為標準格式
                    return [
                        {
                            "name": tool,
                            "description": f"Legacy tool: {tool}",
                            "parameters": {},
                        }
                        for tool in tools
                    ]
                else:
                    # 假設已經是正確格式
                    return tools
            else:
                return []
                
        except Exception as e:
            raise MCPError(f"取得工具列表失敗: {e}", server=server)

    async def close(self) -> None:
        """關閉客戶端"""
        try:
            if hasattr(self._legacy_client, 'close_all_connections'):
                await self._legacy_client.close_all_connections()
        except Exception:
            pass  # 忽略關閉錯誤
        
        await super().close()