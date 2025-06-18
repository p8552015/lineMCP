"""
STDIO 協議適配器

實現 STDIO 方式與 MCP 伺服器通訊的適配器。
"""

import json
import asyncio
import subprocess
from typing import Any, AsyncIterator, Dict, List, Optional
from uuid import uuid4

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


class STDIOAdapter(BaseProtocolAdapter):
    """
    STDIO 協議適配器
    
    透過標準輸入/輸出與 MCP 伺服器進程通訊。
    """

    def __init__(self, config: Dict[str, Any] | None = None):
        """
        初始化 STDIO 適配器
        
        Args:
            config: 適配器配置，應包含伺服器執行指令
        """
        super().__init__(config)
        self.protocol = "stdio"
        
        # STDIO 配置
        self._processes: Dict[str, subprocess.Popen] = {}
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._process_lock = asyncio.Lock()
        
        # 配置參數
        self._timeout = config.get("timeout", 30.0) if config else 30.0
        self._max_retries = config.get("max_retries", 3) if config else 3
        self._server_commands = config.get("server_commands", {}) if config else {}

    async def _get_process(self, server_id: str) -> subprocess.Popen:
        """取得或啟動 MCP 伺服器進程"""
        async with self._process_lock:
            # 檢查現有進程
            if server_id in self._processes:
                process = self._processes[server_id]
                if process.poll() is None:  # 進程仍在執行
                    return process
                else:
                    # 清理已結束的進程
                    del self._processes[server_id]
            
            # 啟動新進程
            if server_id not in self._server_commands:
                raise MCPConnectionError(f"未設定伺服器 {server_id} 的執行指令", "NO_COMMAND")
            
            command = self._server_commands[server_id]
            
            try:
                # 啟動 MCP 伺服器進程
                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=0,  # 無緩衝
                )
                
                self._processes[server_id] = process
                
                # 啟動輸出處理
                asyncio.create_task(self._handle_stdout(process, server_id))
                asyncio.create_task(self._handle_stderr(process, server_id))
                
                return process
                
            except Exception as e:
                raise MCPConnectionError(f"無法啟動 MCP 伺服器 {server_id}: {str(e)}", "PROCESS_START_ERROR")

    async def _handle_stdout(self, process: subprocess.Popen, server_id: str):
        """處理伺服器標準輸出"""
        try:
            while process.poll() is None:
                line = await process.stdout.readline()
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    request_id = data.get("id")
                    
                    if request_id and request_id in self._pending_requests:
                        # 完成對應的請求
                        future = self._pending_requests.pop(request_id)
                        if not future.done():
                            future.set_result(data)
                            
                except json.JSONDecodeError:
                    continue  # 忽略非 JSON 輸出
                except Exception:
                    continue  # 忽略其他處理錯誤
                    
        except Exception:
            # 輸出處理出錯，清理進程
            if server_id in self._processes:
                del self._processes[server_id]

    async def _handle_stderr(self, process: subprocess.Popen, server_id: str):
        """處理伺服器標準錯誤輸出（記錄用）"""
        try:
            while process.poll() is None:
                line = await process.stderr.readline()
                if not line:
                    break
                
                # 可以在這裡記錄錯誤訊息
                # logger.warning(f"MCP Server {server_id} stderr: {line.strip()}")
                
        except Exception:
            pass  # 忽略錯誤輸出處理問題

    async def _send_request(
        self,
        process: subprocess.Popen,
        request_data: Dict[str, Any],
        timeout: float = None,
    ) -> Dict[str, Any]:
        """發送 STDIO 請求並等待回應"""
        request_id = request_data.get("id", str(uuid4()))
        request_data["id"] = request_id
        
        # 建立 Future 等待回應
        future = asyncio.Future()
        self._pending_requests[request_id] = future
        
        try:
            # 發送請求到 stdin
            request_json = json.dumps(request_data) + "\n"
            process.stdin.write(request_json)
            await process.stdin.drain()
            
            # 等待回應
            timeout = timeout or self._timeout
            response = await asyncio.wait_for(future, timeout=timeout)
            
            return response
            
        except asyncio.TimeoutError:
            # 清理 pending request
            self._pending_requests.pop(request_id, None)
            raise MCPRequestError(f"STDIO 請求超時: {request_id}", "TIMEOUT")
        
        except Exception as e:
            # 清理 pending request
            self._pending_requests.pop(request_id, None)
            raise MCPRequestError(f"STDIO 請求失敗: {str(e)}", "REQUEST_ERROR")

    async def call_tool(
        self,
        server_url: str,
        tool: str,
        params: Dict[str, Any],
        *,
        options: CallOptions | None = None,
    ) -> MCPResponse:
        """實作 STDIO 工具呼叫"""
        # 對於 STDIO，server_url 就是 server_id
        server_id = server_url
        process = await self._get_process(server_id)
        
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool,
                "arguments": params,
            },
        }
        
        timeout = options.timeout if options else self._timeout
        
        try:
            response_data = await self._send_request(process, request_data, timeout)
            
            # 處理 JSON-RPC 回應
            if "error" in response_data:
                error_info = response_data["error"]
                return MCPResponse(
                    call_id=response_data.get("id", ""),
                    status=MCPStatusCode.ERROR,
                    error=error_info.get("message", "未知錯誤"),
                    error_code=str(error_info.get("code", "UNKNOWN")),
                    metadata={
                        "protocol": "stdio",
                        "server_id": server_id,
                    },
                )
            else:
                return MCPResponse(
                    call_id=response_data.get("id", ""),
                    status=MCPStatusCode.SUCCESS,
                    data=response_data.get("result"),
                    metadata={
                        "protocol": "stdio",
                        "server_id": server_id,
                    },
                )
                
        except Exception as e:
            return MCPResponse(
                call_id="",
                status=MCPStatusCode.ERROR,
                error=str(e),
                metadata={
                    "protocol": "stdio",
                    "server_id": server_id,
                },
            )

    async def batch_call(
        self,
        server_url: str,
        calls: List[MCPCall],
    ) -> List[MCPResponse]:
        """實作 STDIO 批次呼叫（序列執行）"""
        # STDIO 通常不支援真正的批次請求，所以序列執行
        responses = []
        
        for call in calls:
            response = await self.call_tool(
                server_url=server_url,
                tool=call.tool,
                params=call.params,
                options=call.options,
            )
            # 更新 call_id
            response.call_id = call.id
            responses.append(response)
        
        return responses

    async def stream_call(
        self,
        server_url: str,
        tool: str,
        params: Dict[str, Any],
        *,
        options: CallOptions | None = None,
    ) -> AsyncIterator[MCPResponse]:
        """實作 STDIO 串流呼叫（模擬）"""
        # STDIO 通常不支援原生串流，回退到單一呼叫
        response = await self.call_tool(server_url, tool, params, options=options)
        yield response

    async def health_check(self, server_url: str) -> HealthStatus:
        """實作 STDIO 健康檢查"""
        import time
        start_time = time.time()
        
        server_id = server_url
        
        try:
            process = await self._get_process(server_id)
            
            # 檢查進程是否還活著
            if process.poll() is None:
                response_time_ms = (time.time() - start_time) * 1000
                
                return HealthStatus(
                    overall=HealthStatusLevel.HEALTHY,
                    servers={server_id: HealthStatusLevel.HEALTHY},
                    response_time_ms=response_time_ms,
                    details={
                        "protocol": "stdio",
                        "process_id": process.pid,
                        "command": " ".join(self._server_commands.get(server_id, [])),
                    },
                )
            else:
                # 進程已結束
                response_time_ms = (time.time() - start_time) * 1000
                
                return HealthStatus(
                    overall=HealthStatusLevel.UNHEALTHY,
                    servers={server_id: HealthStatusLevel.UNHEALTHY},
                    response_time_ms=response_time_ms,
                    details={
                        "protocol": "stdio",
                        "error": "進程已結束",
                        "exit_code": process.returncode,
                    },
                )
                
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            
            return HealthStatus(
                overall=HealthStatusLevel.UNHEALTHY,
                servers={server_id: HealthStatusLevel.UNHEALTHY},
                response_time_ms=response_time_ms,
                details={
                    "protocol": "stdio",
                    "error": str(e),
                },
            )

    async def list_tools(self, server_url: str) -> List[Dict[str, Any]]:
        """實作 STDIO 工具清單查詢"""
        server_id = server_url
        process = await self._get_process(server_id)
        
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
        }
        
        try:
            response_data = await self._send_request(process, request_data)
            
            if "error" in response_data:
                raise MCPRequestError(f"工具清單查詢失敗: {response_data['error']}", "LIST_TOOLS_ERROR")
            
            result = response_data.get("result", {})
            return result.get("tools", [])
            
        except Exception as e:
            raise MCPRequestError(f"無法取得工具清單: {str(e)}", "LIST_TOOLS_ERROR")

    async def close(self) -> None:
        """關閉所有 STDIO 進程"""
        # 取消所有 pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        
        self._pending_requests.clear()
        
        # 終止所有進程
        for server_id, process in self._processes.items():
            if process.poll() is None:  # 進程仍在執行
                try:
                    # 優雅關閉
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        # 強制終止
                        process.kill()
                        await process.wait()
                except Exception:
                    pass  # 忽略關閉錯誤
        
        self._processes.clear()
        
        await super().close()

    async def __aenter__(self):
        """非同步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同步上下文管理器出口"""
        await self.close() 