"""
MCP 模擬客戶端

用於測試和開發的模擬客戶端實作。
"""

import asyncio
import time
from typing import Any, AsyncIterator
from uuid import uuid4

from ..models.base import (
    MCPResponse,
    MCPCall,
    CallOptions,
    HealthStatus,
    HealthStatusLevel,
    MCPStatusCode,
)
from .interface import BaseMCPClient


class MockMCPClient(BaseMCPClient):
    """
    模擬 MCP 客戶端
    
    提供可預測的回應，用於測試和開發。
    """

    def __init__(
        self,
        mock_responses: dict[str, Any] | None = None,
        mock_delays: dict[str, float] | None = None,
        mock_errors: dict[str, Exception] | None = None,
        config: dict[str, Any] | None = None,
    ):
        """
        初始化模擬客戶端
        
        Args:
            mock_responses: 模擬回應資料，格式為 {server/tool: response_data}
            mock_delays: 模擬延遲時間，格式為 {server/tool: delay_seconds}
            mock_errors: 模擬錯誤，格式為 {server/tool: exception}
            config: 客戶端配置
        """
        super().__init__(config)
        
        self.mock_responses = mock_responses or {}
        self.mock_delays = mock_delays or {}
        self.mock_errors = mock_errors or {}
        
        # 預設的工具列表
        self.default_tools = [
            {
                "name": "test_tool",
                "description": "測試工具",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "測試訊息"}
                    },
                    "required": ["message"],
                },
            },
            {
                "name": "echo",
                "description": "回音工具，返回輸入的內容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "要回音的文字"}
                    },
                    "required": ["text"],
                },
            },
        ]

    def _get_mock_key(self, server: str, tool: str) -> str:
        """生成模擬資料的鍵"""
        return f"{server}/{tool}"

    async def call_tool(
        self,
        server: str,
        tool: str,
        params: dict[str, Any],
        *,
        options: CallOptions | None = None,
    ) -> MCPResponse:
        """模擬工具呼叫"""
        start_time = time.time()
        call_id = str(uuid4())
        mock_key = self._get_mock_key(server, tool)
        
        # 模擬延遲
        delay = self.mock_delays.get(mock_key, 0.1)
        await asyncio.sleep(delay)
        
        # 檢查是否有模擬錯誤
        if mock_key in self.mock_errors:
            error = self.mock_errors[mock_key]
            duration_ms = (time.time() - start_time) * 1000
            
            return MCPResponse(
                call_id=call_id,
                status=MCPStatusCode.ERROR,
                error=str(error),
                error_code=type(error).__name__,
                duration_ms=duration_ms,
                metadata={
                    "server": server,
                    "tool": tool,
                    "mock": True,
                },
            )
        
        # 生成模擬回應
        if mock_key in self.mock_responses:
            response_data = self.mock_responses[mock_key]
        elif tool == "echo":
            response_data = {"echo": params}
        elif tool == "test_tool":
            response_data = {
                "message": f"測試工具收到: {params}",
                "timestamp": int(time.time()),
            }
        else:
            response_data = {
                "result": f"模擬回應來自 {server}/{tool}",
                "params": params,
                "timestamp": int(time.time()),
            }
        
        duration_ms = (time.time() - start_time) * 1000
        
        return MCPResponse(
            call_id=call_id,
            status=MCPStatusCode.SUCCESS,
            data=response_data,
            duration_ms=duration_ms,
            metadata={
                "server": server,
                "tool": tool,
                "mock": True,
            },
        )

    async def batch_call(self, calls: list[MCPCall]) -> list[MCPResponse]:
        """模擬批次呼叫"""
        if not calls:
            return []
        
        # 並行執行所有呼叫
        tasks = [
            self.call_tool(
                server=call.server,
                tool=call.tool,
                params=call.params,
                options=call.options,
            )
            for call in calls
        ]
        
        return await asyncio.gather(*tasks)

    async def stream_call(
        self,
        server: str,
        tool: str,
        params: dict[str, Any],
        *,
        options: CallOptions | None = None,
    ) -> AsyncIterator[MCPResponse]:
        """模擬串流呼叫"""
        call_id = str(uuid4())
        mock_key = self._get_mock_key(server, tool)
        
        # 檢查是否有模擬錯誤
        if mock_key in self.mock_errors:
            error = self.mock_errors[mock_key]
            yield MCPResponse(
                call_id=call_id,
                status=MCPStatusCode.ERROR,
                error=str(error),
                error_code=type(error).__name__,
                metadata={
                    "server": server,
                    "tool": tool,
                    "mock": True,
                    "stream": True,
                },
            )
            return
        
        # 生成多個串流回應
        chunk_count = 5  # 預設生成 5 個資料塊
        
        for i in range(chunk_count):
            await asyncio.sleep(0.1)  # 模擬串流延遲
            
            if mock_key in self.mock_responses:
                chunk_data = self.mock_responses[mock_key]
                if isinstance(chunk_data, list) and i < len(chunk_data):
                    data = chunk_data[i]
                else:
                    data = chunk_data
            else:
                data = {
                    "chunk": i + 1,
                    "total": chunk_count,
                    "data": f"串流資料 {i + 1}",
                    "params": params,
                }
            
            yield MCPResponse(
                call_id=call_id,
                status=MCPStatusCode.SUCCESS,
                data=data,
                metadata={
                    "server": server,
                    "tool": tool,
                    "mock": True,
                    "stream": True,
                    "chunk_index": i,
                },
            )

    async def health_check(self, server: str | None = None) -> HealthStatus:
        """模擬健康檢查"""
        start_time = time.time()
        
        if server:
            # 檢查特定伺服器
            servers_to_check = [server]
        else:
            # 檢查所有已知伺服器
            servers_to_check = list(set(
                key.split("/")[0] 
                for key in self.mock_responses.keys()
            )) or ["mock_server"]
        
        server_statuses = {}
        for srv in servers_to_check:
            # 模擬一些伺服器可能不健康
            if srv.endswith("_unhealthy"):
                server_statuses[srv] = HealthStatusLevel.UNHEALTHY
            elif srv.endswith("_degraded"):
                server_statuses[srv] = HealthStatusLevel.DEGRADED
            else:
                server_statuses[srv] = HealthStatusLevel.HEALTHY
        
        # 計算整體狀態
        if all(status == HealthStatusLevel.HEALTHY for status in server_statuses.values()):
            overall = HealthStatusLevel.HEALTHY
        elif any(status == HealthStatusLevel.HEALTHY for status in server_statuses.values()):
            overall = HealthStatusLevel.DEGRADED
        else:
            overall = HealthStatusLevel.UNHEALTHY
        
        response_time_ms = (time.time() - start_time) * 1000
        
        return HealthStatus(
            overall=overall,
            servers=server_statuses,
            response_time_ms=response_time_ms,
            details={
                "mock": True,
                "checked_servers": servers_to_check,
            },
        )

    async def list_tools(self, server: str) -> list[dict[str, Any]]:
        """模擬工具列表"""
        # 檢查是否有自訂工具列表
        tools_key = f"{server}/tools"
        if tools_key in self.mock_responses:
            tools = self.mock_responses[tools_key]
            if isinstance(tools, list):
                return tools
        
        # 返回預設工具列表
        return self.default_tools

    async def close(self) -> None:
        """關閉模擬客戶端"""
        await super().close()

    def set_mock_response(self, server: str, tool: str, response: Any) -> None:
        """設定模擬回應"""
        mock_key = self._get_mock_key(server, tool)
        self.mock_responses[mock_key] = response

    def set_mock_delay(self, server: str, tool: str, delay: float) -> None:
        """設定模擬延遲"""
        mock_key = self._get_mock_key(server, tool)
        self.mock_delays[mock_key] = delay

    def set_mock_error(self, server: str, tool: str, error: Exception) -> None:
        """設定模擬錯誤"""
        mock_key = self._get_mock_key(server, tool)
        self.mock_errors[mock_key] = error

    def clear_mocks(self) -> None:
        """清除所有模擬設定"""
        self.mock_responses.clear()
        self.mock_delays.clear()
        self.mock_errors.clear()