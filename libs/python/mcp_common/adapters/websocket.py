"""
WebSocket 協議適配器

實現 WebSocket 方式與 MCP 伺服器通訊的適配器。
"""

import json
import asyncio
from typing import Any, AsyncIterator, Dict, List, Optional
from uuid import uuid4
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from ..models.base import (
    MCPResponse,
    MCPCall,
    CallOptions,
    HealthStatus,
    HealthStatusLevel,
    MCPStatusCode,
)
from ..models.error import MCPConnectionError, MCPRequestError
from .base import BaseProtocolAdapter


class WebSocketAdapter(BaseProtocolAdapter):
    """
    WebSocket 協議適配器
    
    透過 WebSocket 與 MCP 伺服器進行雙向通訊。
    """

    def __init__(self, config: Dict[str, Any] | None = None):
        """
        初始化 WebSocket 適配器
        
        Args:
            config: 適配器配置
        """
        super().__init__(config)
        self.protocol = "websocket"
        
        # WebSocket 配置
        self._connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._connection_lock = asyncio.Lock()
        
        # 配置參數
        self._timeout = config.get("timeout", 30.0) if config else 30.0
        self._max_retries = config.get("max_retries", 3) if config else 3
        self._ping_interval = config.get("ping_interval", 20) if config else 20
        self._ping_timeout = config.get("ping_timeout", 10) if config else 10

    def _normalize_url(self, server_url: str) -> str:
        """規範化 WebSocket URL"""
        if not server_url.startswith(("ws://", "wss://")):
            # 假設使用 WebSocket 安全連線
            if "localhost" in server_url or "127.0.0.1" in server_url:
                server_url = f"ws://{server_url}"
            else:
                server_url = f"wss://{server_url}"
        
        # 確保路徑包含 MCP WebSocket 端點
        if not server_url.endswith("/mcp"):
            server_url = server_url.rstrip("/") + "/mcp"
        
        return server_url

    async def _get_connection(self, server_url: str) -> websockets.WebSocketServerProtocol:
        """取得或建立 WebSocket 連線"""
        normalized_url = self._normalize_url(server_url)
        
        async with self._connection_lock:
            # 檢查現有連線
            if normalized_url in self._connections:
                connection = self._connections[normalized_url]
                if not connection.closed:
                    return connection
                else:
                    # 清理已關閉的連線
                    del self._connections[normalized_url]
            
            # 建立新連線
            try:
                connection = await websockets.connect(
                    normalized_url,
                    ping_interval=self._ping_interval,
                    ping_timeout=self._ping_timeout,
                    timeout=self._timeout,
                    max_size=2**20,  # 1MB 最大訊息大小
                    max_queue=32,    # 最大待處理訊息數
                )
                
                self._connections[normalized_url] = connection
                
                # 啟動訊息接收處理
                asyncio.create_task(self._handle_messages(connection, normalized_url))
                
                return connection
                
            except Exception as e:
                raise MCPConnectionError(f"無法建立 WebSocket 連線: {str(e)}", "CONNECTION_ERROR")

    async def _handle_messages(self, connection: websockets.WebSocketServerProtocol, server_url: str):
        """處理 WebSocket 訊息接收"""
        try:
            async for message in connection:
                try:
                    data = json.loads(message)
                    request_id = data.get("id")
                    
                    if request_id and request_id in self._pending_requests:
                        # 完成對應的請求
                        future = self._pending_requests.pop(request_id)
                        if not future.done():
                            future.set_result(data)
                            
                except json.JSONDecodeError:
                    continue  # 忽略格式錯誤的訊息
                except Exception:
                    continue  # 忽略其他處理錯誤
                    
        except ConnectionClosed:
            # 連線關閉，清理資源
            if server_url in self._connections:
                del self._connections[server_url]
        except Exception:
            # 其他例外，同樣清理資源
            if server_url in self._connections:
                del self._connections[server_url]

    async def _send_request(
        self,
        connection: websockets.WebSocketServerProtocol,
        request_data: Dict[str, Any],
        timeout: float = None,
    ) -> Dict[str, Any]:
        """發送 WebSocket 請求並等待回應"""
        request_id = request_data.get("id", str(uuid4()))
        request_data["id"] = request_id
        
        # 建立 Future 等待回應
        future = asyncio.Future()
        self._pending_requests[request_id] = future
        
        try:
            # 發送請求
            await connection.send(json.dumps(request_data))
            
            # 等待回應
            timeout = timeout or self._timeout
            response = await asyncio.wait_for(future, timeout=timeout)
            
            return response
            
        except asyncio.TimeoutError:
            # 清理 pending request
            self._pending_requests.pop(request_id, None)
            raise MCPRequestError(f"WebSocket 請求超時: {request_id}", "TIMEOUT")
        
        except Exception as e:
            # 清理 pending request
            self._pending_requests.pop(request_id, None)
            raise MCPRequestError(f"WebSocket 請求失敗: {str(e)}", "REQUEST_ERROR")

    async def call_tool(
        self,
        server_url: str,
        tool: str,
        params: Dict[str, Any],
        *,
        options: CallOptions | None = None,
    ) -> MCPResponse:
        """實作 WebSocket 工具呼叫"""
        connection = await self._get_connection(server_url)
        
        request_data = {
            "type": "call_tool",
            "tool": tool,
            "params": params,
            "timestamp": asyncio.get_event_loop().time(),
        }
        
        timeout = options.timeout if options else self._timeout
        
        try:
            response_data = await self._send_request(connection, request_data, timeout)
            
            return MCPResponse(
                call_id=response_data.get("id", ""),
                status=MCPStatusCode.SUCCESS if response_data.get("success") else MCPStatusCode.ERROR,
                data=response_data.get("data"),
                error=response_data.get("error"),
                duration_ms=response_data.get("duration_ms"),
                metadata={
                    "protocol": "websocket",
                    "server_url": server_url,
                },
            )
            
        except Exception as e:
            return MCPResponse(
                call_id="",
                status=MCPStatusCode.ERROR,
                error=str(e),
                metadata={
                    "protocol": "websocket",
                    "server_url": server_url,
                },
            )

    async def batch_call(
        self,
        server_url: str,
        calls: List[MCPCall],
    ) -> List[MCPResponse]:
        """實作 WebSocket 批次呼叫"""
        connection = await self._get_connection(server_url)
        
        request_data = {
            "type": "batch_call",
            "calls": [
                {
                    "id": call.id,
                    "tool": call.tool,
                    "params": call.params,
                }
                for call in calls
            ],
        }
        
        try:
            response_data = await self._send_request(connection, request_data, self._timeout * 2)
            responses = []
            
            for result in response_data.get("results", []):
                responses.append(MCPResponse(
                    call_id=result.get("id", ""),
                    status=MCPStatusCode.SUCCESS if result.get("success") else MCPStatusCode.ERROR,
                    data=result.get("data"),
                    error=result.get("error"),
                    duration_ms=result.get("duration_ms"),
                    metadata={
                        "protocol": "websocket",
                        "server_url": server_url,
                        "batch": True,
                    },
                ))
            
            return responses
            
        except Exception as e:
            # 批次失敗時回傳錯誤回應
            return [
                MCPResponse(
                    call_id=call.id,
                    status=MCPStatusCode.ERROR,
                    error=f"批次請求失敗: {str(e)}",
                    metadata={
                        "protocol": "websocket",
                        "server_url": server_url,
                        "batch": True,
                    },
                )
                for call in calls
            ]

    async def stream_call(
        self,
        server_url: str,
        tool: str,
        params: Dict[str, Any],
        *,
        options: CallOptions | None = None,
    ) -> AsyncIterator[MCPResponse]:
        """實作 WebSocket 串流呼叫"""
        connection = await self._get_connection(server_url)
        
        request_data = {
            "type": "stream_call",
            "tool": tool,
            "params": params,
            "stream": True,
        }
        
        try:
            # 發送串流請求
            await connection.send(json.dumps(request_data))
            
            # 處理串流回應
            async for message in connection:
                try:
                    data = json.loads(message)
                    
                    # 檢查是否為串流資料
                    if data.get("type") == "stream_data":
                        yield MCPResponse(
                            call_id=data.get("id", ""),
                            status=MCPStatusCode.SUCCESS,
                            data=data.get("data"),
                            metadata={
                                "protocol": "websocket",
                                "server_url": server_url,
                                "stream": True,
                            },
                        )
                        
                        # 檢查是否為最後一個資料塊
                        if data.get("is_final"):
                            break
                    
                except json.JSONDecodeError:
                    continue  # 忽略格式錯誤的資料
                    
        except Exception as e:
            yield MCPResponse(
                call_id="",
                status=MCPStatusCode.ERROR,
                error=f"串流請求失敗: {str(e)}",
                metadata={
                    "protocol": "websocket",
                    "server_url": server_url,
                    "stream": True,
                },
            )

    async def health_check(self, server_url: str) -> HealthStatus:
        """實作 WebSocket 健康檢查"""
        import time
        start_time = time.time()
        
        try:
            connection = await self._get_connection(server_url)
            
            # 發送 ping 檢查連線
            pong_waiter = await connection.ping()
            await asyncio.wait_for(pong_waiter, timeout=5.0)
            
            response_time_ms = (time.time() - start_time) * 1000
            
            return HealthStatus(
                overall=HealthStatusLevel.HEALTHY,
                servers={server_url: HealthStatusLevel.HEALTHY},
                response_time_ms=response_time_ms,
                details={
                    "protocol": "websocket",
                    "connection_state": "open",
                },
            )
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            
            return HealthStatus(
                overall=HealthStatusLevel.UNHEALTHY,
                servers={server_url: HealthStatusLevel.UNHEALTHY},
                response_time_ms=response_time_ms,
                details={
                    "protocol": "websocket",
                    "error": str(e),
                },
            )

    async def list_tools(self, server_url: str) -> List[Dict[str, Any]]:
        """實作 WebSocket 工具清單查詢"""
        connection = await self._get_connection(server_url)
        
        request_data = {
            "type": "list_tools",
        }
        
        try:
            response_data = await self._send_request(connection, request_data)
            return response_data.get("tools", [])
            
        except Exception as e:
            raise MCPRequestError(f"無法取得工具清單: {str(e)}", "LIST_TOOLS_ERROR")

    async def close(self) -> None:
        """關閉所有 WebSocket 連線"""
        # 取消所有 pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        
        self._pending_requests.clear()
        
        # 關閉所有連線
        for connection in self._connections.values():
            if not connection.closed:
                await connection.close()
        
        self._connections.clear()
        
        await super().close()

    async def __aenter__(self):
        """非同步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同步上下文管理器出口"""
        await self.close() 