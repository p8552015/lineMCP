"""
MCP HTTP 客戶端實作

基於 httpx 的非同步 HTTP 客戶端，支援重試、熔斷器等企業級功能。
"""

import asyncio
import logging
import time
from typing import Any, AsyncIterator, Optional
from uuid import uuid4

try:
    import httpx
    from tenacity import (
        AsyncRetrying,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception_type,
    )
    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False

from ..models.base import (
    MCPResponse,
    MCPCall,
    CallOptions,
    HealthStatus,
    HealthStatusLevel,
    MCPStatusCode,
    ServerInfo,
    ToolInfo,
)
from ..models.error import (
    MCPError,
    ConnectionError,
    TimeoutError,
    ServerError,
    CircuitBreakerError,
)
from .interface import BaseMCPClient
from ..connection.circuit import CircuitBreaker
from ..connection.pool import ConnectionPool

logger = logging.getLogger(__name__)


class MCPHttpClient(BaseMCPClient):
    """
    MCP HTTP 客戶端實作
    
    功能特色：
    - 基於 httpx 的非同步 HTTP 客戶端
    - 內建重試機制與指數退避
    - 熔斷器防護
    - 連接池管理
    - 完整的錯誤處理
    - OpenTelemetry 追蹤支援
    """

    def __init__(
        self,
        servers: dict[str, str] | None = None,
        config: dict[str, Any] | None = None,
    ):
        """
        初始化 HTTP 客戶端
        
        Args:
            servers: 伺服器名稱到 URL 的映射
            config: 客戶端配置
        """
        super().__init__(config)
        
        if not HTTP_AVAILABLE:
            raise MCPError("HTTP 客戶端需要 httpx 和 tenacity 模組")
        
        self.servers = servers or {}
        self._default_options = CallOptions(**(config.get("default_options", {})))
        
        # 初始化 HTTP 客戶端配置
        client_config = config.get("http_client", {})
        limits = httpx.Limits(
            max_keepalive_connections=client_config.get("max_keepalive", 20),
            max_connections=client_config.get("max_connections", 100),
            keepalive_expiry=client_config.get("keepalive_expiry", 5),
        )
        
        self._http_client = httpx.AsyncClient(
            limits=limits,
            timeout=httpx.Timeout(
                connect=client_config.get("connect_timeout", 10.0),
                read=client_config.get("read_timeout", 30.0),
                write=client_config.get("write_timeout", 10.0),
                pool=client_config.get("pool_timeout", 5.0),
            ),
            follow_redirects=True,
            headers={
                "User-Agent": "MCP-Client/1.0",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        
        # 初始化熔斷器
        circuit_config = config.get("circuit_breaker", {})
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._circuit_config = circuit_config
        
        # 初始化連接池
        pool_config = config.get("connection_pool", {})
        self._connection_pool = ConnectionPool(**pool_config)

    def _get_circuit_breaker(self, server: str) -> CircuitBreaker:
        """獲取或建立伺服器的熔斷器"""
        if server not in self._circuit_breakers:
            self._circuit_breakers[server] = CircuitBreaker(
                failure_threshold=self._circuit_config.get("failure_threshold", 5),
                success_threshold=self._circuit_config.get("success_threshold", 3),
                timeout=self._circuit_config.get("timeout", 60),
                name=f"mcp-{server}",
            )
        return self._circuit_breakers[server]

    def _resolve_server_url(self, server: str) -> str:
        """解析伺服器 URL"""
        if server.startswith(("http://", "https://")):
            return server
        
        if server in self.servers:
            return self.servers[server]
        
        raise ConfigurationError(f"未知的伺服器: {server}")

    async def _make_request(
        self,
        method: str,
        url: str,
        server: str,
        options: CallOptions,
        **kwargs: Any,
    ) -> httpx.Response:
        """執行 HTTP 請求，包含重試與熔斷器邏輯"""
        circuit_breaker = self._get_circuit_breaker(server)
        
        # 檢查熔斷器狀態
        if options.enable_circuit_breaker and circuit_breaker.is_open:
            raise CircuitBreakerError(server=server)
        
        # 準備請求標頭
        headers = {
            **kwargs.get("headers", {}),
            **options.headers,
            "X-Request-ID": str(uuid4()),
            "X-Timestamp": str(int(time.time() * 1000)),
        }
        kwargs["headers"] = headers
        kwargs["timeout"] = options.timeout

        async def _attempt_request():
            """單次請求嘗試"""
            try:
                response = await self._http_client.request(method, url, **kwargs)
                response.raise_for_status()
                
                # 成功請求，記錄到熔斷器
                if options.enable_circuit_breaker:
                    await circuit_breaker.record_success()
                
                return response
                
            except httpx.TimeoutException as e:
                logger.warning(f"請求超時: {server} {method} {url}")
                raise TimeoutError(
                    message=f"請求超時: {e}",
                    timeout=options.timeout,
                    server=server,
                )
                
            except httpx.ConnectError as e:
                logger.warning(f"連線錯誤: {server} {method} {url}")
                error = ConnectionError(
                    message=f"連線失敗: {e}",
                    server=server,
                )
                
                # 記錄失敗到熔斷器
                if options.enable_circuit_breaker:
                    await circuit_breaker.record_failure()
                
                raise error
                
            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP 錯誤: {server} {method} {url} {e.response.status_code}")
                error = ServerError(
                    message=f"伺服器錯誤: {e.response.status_code} {e.response.text}",
                    status_code=e.response.status_code,
                    server=server,
                )
                
                # 5xx 錯誤記錄到熔斷器
                if options.enable_circuit_breaker and e.response.status_code >= 500:
                    await circuit_breaker.record_failure()
                
                raise error
                
            except Exception as e:
                logger.error(f"未預期錯誤: {server} {method} {url}: {e}")
                error = MCPError(
                    message=f"請求失敗: {e}",
                    server=server,
                )
                
                if options.enable_circuit_breaker:
                    await circuit_breaker.record_failure()
                
                raise error

        # 使用 tenacity 進行重試
        if options.max_retries > 0:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(options.max_retries + 1),
                wait=wait_exponential(
                    multiplier=options.retry_delay,
                    min=options.retry_delay,
                    max=options.retry_delay * 10,
                ),
                retry=retry_if_exception_type((TimeoutError, ConnectionError)),
                reraise=True,
            ):
                with attempt:
                    return await _attempt_request()
        else:
            return await _attempt_request()

    async def call_tool(
        self,
        server: str,
        tool: str,
        params: dict[str, Any],
        *,
        options: CallOptions | None = None,
    ) -> MCPResponse:
        """實作工具呼叫"""
        if options is None:
            options = self._default_options
        
        start_time = time.time()
        call_id = str(uuid4())
        
        try:
            url = self._resolve_server_url(server)
            
            # 構建請求
            request_data = {
                "id": call_id,
                "tool": tool,
                "params": params,
                "timestamp": int(start_time * 1000),
            }
            
            logger.info(f"呼叫工具: {server}/{tool} (id={call_id})")
            
            # 發送請求
            response = await self._make_request(
                method="POST",
                url=f"{url}/tools/{tool}",
                server=server,
                options=options,
                json=request_data,
            )
            
            # 解析回應
            response_data = response.json()
            duration_ms = (time.time() - start_time) * 1000
            
            return MCPResponse(
                call_id=call_id,
                status=MCPStatusCode.SUCCESS,
                data=response_data.get("data"),
                duration_ms=duration_ms,
                metadata={
                    "server": server,
                    "tool": tool,
                    "status_code": response.status_code,
                    "response_headers": dict(response.headers),
                },
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"工具呼叫失敗: {server}/{tool}: {e}")
            
            if isinstance(e, MCPError):
                error_message = e.message
                error_code = e.error_code
            else:
                error_message = str(e)
                error_code = "UNKNOWN_ERROR"
            
            return MCPResponse(
                call_id=call_id,
                status=MCPStatusCode.ERROR,
                error=error_message,
                error_code=error_code,
                duration_ms=duration_ms,
                metadata={
                    "server": server,
                    "tool": tool,
                },
            )

    async def batch_call(self, calls: list[MCPCall]) -> list[MCPResponse]:
        """實作批次呼叫"""
        if not calls:
            return []
        
        logger.info(f"批次呼叫: {len(calls)} 個請求")
        
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
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 處理異常結果
        results = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                call = calls[i]
                results.append(
                    MCPResponse(
                        call_id=call.id,
                        status=MCPStatusCode.ERROR,
                        error=str(response),
                        error_code="BATCH_CALL_ERROR",
                        metadata={
                            "server": call.server,
                            "tool": call.tool,
                        },
                    )
                )
            else:
                results.append(response)
        
        return results

    async def stream_call(
        self,
        server: str,
        tool: str,
        params: dict[str, Any],
        *,
        options: CallOptions | None = None,
    ) -> AsyncIterator[MCPResponse]:
        """實作串流呼叫"""
        if options is None:
            options = self._default_options
        
        call_id = str(uuid4())
        url = self._resolve_server_url(server)
        
        request_data = {
            "id": call_id,
            "tool": tool,
            "params": params,
            "stream": True,
        }
        
        logger.info(f"串流呼叫: {server}/{tool} (id={call_id})")
        
        try:
            async with self._http_client.stream(
                "POST",
                f"{url}/tools/{tool}/stream",
                json=request_data,
                timeout=options.timeout,
                headers=options.headers,
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = response.json() if hasattr(response, 'json') else eval(line)
                            yield MCPResponse(
                                call_id=call_id,
                                status=MCPStatusCode.SUCCESS,
                                data=data,
                                metadata={
                                    "server": server,
                                    "tool": tool,
                                    "stream": True,
                                },
                            )
                        except Exception as e:
                            logger.warning(f"串流資料解析錯誤: {e}")
                            yield MCPResponse(
                                call_id=call_id,
                                status=MCPStatusCode.ERROR,
                                error=f"資料解析錯誤: {e}",
                                error_code="STREAM_PARSE_ERROR",
                                metadata={
                                    "server": server,
                                    "tool": tool,
                                    "stream": True,
                                },
                            )
                            
        except Exception as e:
            logger.error(f"串流呼叫失敗: {server}/{tool}: {e}")
            yield MCPResponse(
                call_id=call_id,
                status=MCPStatusCode.ERROR,
                error=str(e),
                error_code="STREAM_ERROR",
                metadata={
                    "server": server,
                    "tool": tool,
                    "stream": True,
                },
            )

    async def health_check(self, server: str | None = None) -> HealthStatus:
        """實作健康檢查"""
        if server:
            # 檢查特定伺服器
            servers_to_check = {server: self._resolve_server_url(server)}
        else:
            # 檢查所有伺服器
            servers_to_check = {
                name: self._resolve_server_url(name)
                for name in self.servers.keys()
            }
        
        start_time = time.time()
        server_statuses = {}
        
        for server_name, server_url in servers_to_check.items():
            try:
                response = await self._http_client.get(
                    f"{server_url}/health",
                    timeout=5.0,
                )
                response.raise_for_status()
                server_statuses[server_name] = HealthStatusLevel.HEALTHY
                
            except Exception as e:
                logger.warning(f"伺服器 {server_name} 健康檢查失敗: {e}")
                server_statuses[server_name] = HealthStatusLevel.UNHEALTHY
        
        # 計算整體狀態
        if not server_statuses:
            overall = HealthStatusLevel.UNKNOWN
        elif all(status == HealthStatusLevel.HEALTHY for status in server_statuses.values()):
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
                "checked_servers": list(servers_to_check.keys()),
                "circuit_breakers": {
                    name: {
                        "state": str(cb.state),
                        "failures": cb.failure_count,
                        "successes": cb.success_count,
                    }
                    for name, cb in self._circuit_breakers.items()
                },
            },
        )

    async def list_tools(self, server: str) -> list[dict[str, Any]]:
        """實作工具列表"""
        url = self._resolve_server_url(server)
        
        try:
            response = await self._http_client.get(
                f"{url}/tools",
                timeout=self._default_options.timeout,
            )
            response.raise_for_status()
            
            tools_data = response.json()
            return tools_data.get("tools", [])
            
        except Exception as e:
            logger.error(f"取得工具列表失敗: {server}: {e}")
            raise MCPError(f"取得工具列表失敗: {e}", server=server)

    async def close(self) -> None:
        """關閉客戶端"""
        if not self._closed:
            logger.info("關閉 MCP HTTP 客戶端")
            await self._http_client.aclose()
            await self._connection_pool.close()
            await super().close()