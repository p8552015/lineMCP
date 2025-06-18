"""
Simple MCP 客戶端適配器

將現有的 SimpleMCPClient 適配到統一介面。
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


class SimpleMCPAdapter(BaseMCPClient):
    """
    Simple MCP 客戶端適配器
    
    將現有的 SimpleMCPClient 包裝成符合新介面的客戶端。
    """

    def __init__(self, simple_client=None, config: Dict[str, Any] | None = None):
        """
        初始化適配器
        
        Args:
            simple_client: 現有的 SimpleMCPClient 實例
            config: 配置選項
        """
        super().__init__(config)
        
        # 延遲載入以避免循環導入
        if simple_client is None:
            try:
                # 嘗試多種導入路徑
                import sys
                import os
                
                # 添加 bot 應用路徑
                bot_path = os.path.join(os.getcwd(), 'apps', 'bot')
                if os.path.exists(bot_path) and bot_path not in sys.path:
                    sys.path.insert(0, bot_path)
                
                from src.services.simple_mcp_client import get_simple_mcp_client
                self._simple_client = get_simple_mcp_client()
            except ImportError as e:
                # 如果無法導入原有客戶端，使用內建的簡化實作
                self._simple_client = self._create_fallback_client()
        else:
            self._simple_client = simple_client

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
            # 呼叫 simple 客戶端
            result = await self._simple_client.call_tool(
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
                        "simple_adapter": True,
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
                        "simple_adapter": True,
                    },
                )
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return MCPResponse(
                call_id=call_id,
                status=MCPStatusCode.ERROR,
                error=str(e),
                error_code="SIMPLE_ADAPTER_ERROR",
                duration_ms=duration_ms,
                metadata={
                    "server": server,
                    "tool": tool,
                    "simple_adapter": True,
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
        # Simple 客戶端不支援串流，返回單一回應
        response = await self.call_tool(server, tool, params, options=options)
        yield response

    async def health_check(self, server: str | None = None) -> HealthStatus:
        """實作健康檢查"""
        start_time = time.time()
        
        try:
            if server:
                # 檢查特定伺服器
                connected = await self._simple_client.connect_to_server(server)
                server_status = (
                    HealthStatusLevel.HEALTHY if connected 
                    else HealthStatusLevel.UNHEALTHY
                )
                servers = {server: server_status}
                overall = server_status
            else:
                # Simple 客戶端只支援 SQLite
                servers = {}
                
                try:
                    connected = await self._simple_client.connect_to_server("sqlite")
                    servers["sqlite"] = (
                        HealthStatusLevel.HEALTHY if connected 
                        else HealthStatusLevel.UNHEALTHY
                    )
                except Exception:
                    servers["sqlite"] = HealthStatusLevel.UNHEALTHY
                
                overall = servers["sqlite"]
            
            response_time_ms = (time.time() - start_time) * 1000
            
            return HealthStatus(
                overall=overall,
                servers=servers,
                response_time_ms=response_time_ms,
                details={
                    "adapter": "simple",
                    "client_type": type(self._simple_client).__name__,
                    "database_path": getattr(self._simple_client, 'db_path', None),
                },
            )
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            
            return HealthStatus(
                overall=HealthStatusLevel.UNKNOWN,
                servers={},
                response_time_ms=response_time_ms,
                details={
                    "adapter": "simple",
                    "error": str(e),
                },
            )

    async def list_tools(self, server: str) -> List[Dict[str, Any]]:
        """實作工具列表"""
        try:
            tools = await self._simple_client.list_tools(server)
            
            # 轉換為標準格式
            if isinstance(tools, list):
                if tools and isinstance(tools[0], str):
                    # 如果是字符串列表，轉換為標準格式
                    return [
                        {
                            "name": tool,
                            "description": f"Simple SQLite tool: {tool}",
                            "parameters": self._get_tool_parameters(tool),
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

    def _create_fallback_client(self):
        """創建 fallback 客戶端（如果無法導入原有客戶端）"""
        class FallbackSimpleClient:
            """簡化的 SQLite 客戶端 fallback 實作"""
            
            def __init__(self):
                self.db_path = "/Users/yen/Desktop/lineMCP/apps/servers/src/sqlite/test.db"
            
            async def call_tool(self, server_name: str, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
                """模擬工具呼叫"""
                if server_name != "sqlite":
                    return {"success": False, "error": f"不支援的伺服器: {server_name}"}
                
                if tool_name == "list_tables":
                    return {"success": True, "data": ["machines", "machine_utilization", "machine_faults"]}
                elif tool_name in ["read_query", "execute_query"]:
                    query = parameters.get("query", "")
                    if not query:
                        return {"success": False, "error": "查詢不能為空"}
                    return {"success": True, "data": [{"result": "模擬查詢結果"}]}
                else:
                    return {"success": False, "error": f"不支援的工具: {tool_name}"}
            
            async def list_tools(self, server_name: str) -> List[str]:
                if server_name == "sqlite":
                    return ["list_tables", "read_query", "execute_query"]
                return []
            
            async def connect_to_server(self, server_name: str) -> bool:
                return server_name == "sqlite"
            
            async def close_all_connections(self):
                pass
        
        return FallbackSimpleClient()

    def _get_tool_parameters(self, tool_name: str) -> Dict[str, Any]:
        """獲取工具參數規格"""
        if tool_name == "list_tables":
            return {
                "type": "object",
                "properties": {},
                "required": [],
            }
        elif tool_name in ["read_query", "execute_query"]:
            return {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL 查詢語句",
                    }
                },
                "required": ["query"],
            }
        else:
            return {"type": "object", "properties": {}}

    async def close(self) -> None:
        """關閉客戶端"""
        try:
            if hasattr(self._simple_client, 'close_all_connections'):
                await self._simple_client.close_all_connections()
        except Exception:
            pass  # 忽略關閉錯誤
        
        await super().close()