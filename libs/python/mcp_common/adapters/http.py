"""
HTTP 協議適配器

實現 HTTP/HTTPS 方式與 MCP 伺服器通訊的適配器。
"""

import json
from typing import Any, AsyncIterator, Dict, List, Optional
import httpx
from urllib.parse import urljoin

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


class HTTPAdapter(BaseProtocolAdapter):
    """
    HTTP 協議適配器
    
    透過 HTTP/HTTPS 與 MCP 伺服器通訊。
    """

    def __init__(self, config: Dict[str, Any] | None = None):
        """
        初始化 HTTP 適配器
        
        Args:
            config: 適配器配置
        """
        super().__init__(config)
        self.protocol = "http"
        
        # HTTP 客戶端配置
        self._client: Optional[httpx.AsyncClient] = None
        self._timeout = config.get("timeout", 30.0) if config else 30.0
        self._max_retries = config.get("max_retries", 3) if config else 3
        self._base_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "mcp-common-http-adapter/1.0",
        }
        
        # 自訂標頭
        if config and "headers" in config:
            self._base_headers.update(config["headers"])

    async def _get_client(self) -> httpx.AsyncClient:
        """取得或建立 HTTP 客戶端"""
        if self._client is None:
            # 連線池設定
            limits = httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
                keepalive_expiry=30,
            )
            
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                limits=limits,
                headers=self._base_headers,
                follow_redirects=True,
            )
        
        return self._client

    def _build_url(self, base_url: str, endpoint: str) -> str:
        """建構完整的 API URL"""
        if not base_url.startswith(("http://", "https://")):
            base_url = f"http://{base_url}"
        
        return urljoin(base_url.rstrip("/") + "/", endpoint.lstrip("/"))

    async def call_tool(
        self,
        server_url: str,
        tool: str,
        params: Dict[str, Any],
        *,
        options: CallOptions | None = None,
    ) -> MCPResponse:
        """實作 HTTP 工具呼叫"""
        client = await self._get_client()
        
        # 建構請求 URL 和資料
        url = self._build_url(server_url, f"/mcp/tools/{tool}")
        
        request_data = {
            "tool": tool,
            "params": params,
        }
        
        # 處理選項
        headers = {}
        if options and options.headers:
            headers.update(options.headers)
        
        timeout = options.timeout if options else self._timeout
        
        try:
            response = await client.post(
                url,
                json=request_data,
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
            
            result_data = response.json()
            
            return MCPResponse(
                call_id=result_data.get("id", ""),
                status=MCPStatusCode.SUCCESS,
                data=result_data.get("data"),
                duration_ms=result_data.get("duration_ms"),
                metadata={
                    "protocol": "http",
                    "server_url": server_url,
                    "http_status": response.status_code,
                },
            )
            
        except httpx.TimeoutException:
            raise MCPRequestError(f"HTTP 請求超時: {url}", "TIMEOUT")
        
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP 錯誤 {e.response.status_code}: {e.response.text}"
            raise MCPRequestError(error_message, f"HTTP_{e.response.status_code}")
        
        except httpx.RequestError as e:
            raise MCPConnectionError(f"HTTP 連線錯誤: {str(e)}", "CONNECTION_ERROR")
        
        except json.JSONDecodeError:
            raise MCPRequestError("伺服器回應格式錯誤", "INVALID_RESPONSE")

    async def batch_call(
        self,
        server_url: str,
        calls: List[MCPCall],
    ) -> List[MCPResponse]:
        """實作 HTTP 批次呼叫"""
        client = await self._get_client()
        
        # 建構批次請求
        url = self._build_url(server_url, "/mcp/batch")
        
        batch_data = {
            "calls": [
                {
                    "id": call.id,
                    "tool": call.tool,
                    "params": call.params,
                }
                for call in calls
            ]
        }
        
        try:
            response = await client.post(
                url,
                json=batch_data,
                timeout=self._timeout * 2,  # 批次請求允許更長時間
            )
            response.raise_for_status()
            
            result_data = response.json()
            responses = []
            
            for result in result_data.get("results", []):
                responses.append(MCPResponse(
                    call_id=result.get("id", ""),
                    status=MCPStatusCode.SUCCESS if result.get("success") else MCPStatusCode.ERROR,
                    data=result.get("data"),
                    error=result.get("error"),
                    duration_ms=result.get("duration_ms"),
                    metadata={
                        "protocol": "http",
                        "server_url": server_url,
                        "batch": True,
                    },
                ))
            
            return responses
            
        except Exception as e:
            # 如果批次失敗，回傳錯誤回應
            return [
                MCPResponse(
                    call_id=call.id,
                    status=MCPStatusCode.ERROR,
                    error=f"批次請求失敗: {str(e)}",
                    metadata={
                        "protocol": "http",
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
        """實作 HTTP 串流呼叫（Server-Sent Events）"""
        client = await self._get_client()
        
        # 建構 SSE 請求
        url = self._build_url(server_url, f"/mcp/stream/{tool}")
        
        request_data = {
            "tool": tool,
            "params": params,
        }
        
        headers = {
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
        }
        
        if options and options.headers:
            headers.update(options.headers)
        
        try:
            async with client.stream(
                "POST",
                url,
                json=request_data,
                headers=headers,
                timeout=httpx.Timeout(None),  # 串流無超時限制
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue
                    
                    try:
                        data = json.loads(line[6:])  # 移除 "data: " 前綴
                        
                        yield MCPResponse(
                            call_id=data.get("id", ""),
                            status=MCPStatusCode.SUCCESS,
                            data=data.get("data"),
                            metadata={
                                "protocol": "http",
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
                    "protocol": "http",
                    "server_url": server_url,
                    "stream": True,
                },
            )

    async def health_check(self, server_url: str) -> HealthStatus:
        """實作 HTTP 健康檢查"""
        client = await self._get_client()
        
        # 檢查多個健康檢查端點
        health_endpoints = ["/mcp/health", "/health", "/ping"]
        
        import time
        start_time = time.time()
        
        for endpoint in health_endpoints:
            try:
                url = self._build_url(server_url, endpoint)
                response = await client.get(url, timeout=5.0)
                
                if response.status_code == 200:
                    response_time_ms = (time.time() - start_time) * 1000
                    
                    return HealthStatus(
                        overall=HealthStatusLevel.HEALTHY,
                        servers={server_url: HealthStatusLevel.HEALTHY},
                        response_time_ms=response_time_ms,
                        details={
                            "protocol": "http",
                            "endpoint": endpoint,
                            "status_code": response.status_code,
                        },
                    )
                    
            except Exception:
                continue  # 嘗試下一個端點
        
        # 所有端點都失敗
        response_time_ms = (time.time() - start_time) * 1000
        
        return HealthStatus(
            overall=HealthStatusLevel.UNHEALTHY,
            servers={server_url: HealthStatusLevel.UNHEALTHY},
            response_time_ms=response_time_ms,
            details={
                "protocol": "http",
                "error": "所有健康檢查端點都無法連接",
            },
        )

    async def list_tools(self, server_url: str) -> List[Dict[str, Any]]:
        """實作 HTTP 工具清單查詢"""
        client = await self._get_client()
        
        url = self._build_url(server_url, "/mcp/tools")
        
        try:
            response = await client.get(url)
            response.raise_for_status()
            
            data = response.json()
            return data.get("tools", [])
            
        except Exception as e:
            raise MCPRequestError(f"無法取得工具清單: {str(e)}", "LIST_TOOLS_ERROR")

    async def close(self) -> None:
        """關閉 HTTP 客戶端"""
        if self._client:
            await self._client.aclose()
            self._client = None
        
        await super().close()

    async def __aenter__(self):
        """非同步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同步上下文管理器出口"""
        await self.close() 