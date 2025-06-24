#!/usr/bin/env python3
"""
HTTP to STDIO Bridge for MCP SQLite Server
解決 macOS STDIO 掛起問題的 HTTP 橋接器
"""

import asyncio
import json
import subprocess
import sys
from typing import Any, Dict, Optional
from aiohttp import web
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MCPBridge:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.process: Optional[subprocess.Popen] = None
        self.lock = asyncio.Lock()
        
    async def start_server(self):
        """啟動 MCP SQLite 服務器進程"""
        if self.process:
            return
            
        cmd = [
            sys.executable,
            "-m", "mcp_server_sqlite.server",
            self.db_path
        ]
        
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env={**os.environ, "PYTHONUNBUFFERED": "1"}
        )
        
        logger.info(f"Started MCP server process: PID {self.process.pid}")
        
    async def call_mcp(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """透過 STDIO 調用 MCP 服務器 - 增強錯誤處理"""
        async with self.lock:
            try:
                if not self.process:
                    await self.start_server()
                
                # 檢查進程狀態
                if self.process.poll() is not None:
                    logger.error(f"MCP server process died with code {self.process.returncode}")
                    self.process = None
                    await self.start_server()
                    
                request = {
                    "jsonrpc": "2.0",
                    "id": "bridge-1",
                    "method": method,
                    "params": params
                }
                
                # 寫入請求 - 增加錯誤處理
                try:
                    request_json = json.dumps(request) + "\n"
                    self.process.stdin.write(request_json)
                    self.process.stdin.flush()
                except (BrokenPipeError, OSError) as e:
                    logger.error(f"Failed to write to MCP server: {e}")
                    self.process = None
                    raise Exception(f"MCP server connection broken: {e}")
                
                # 讀取響應 - 增加超時和錯誤處理
                try:
                    response_line = self.process.stdout.readline()
                    if not response_line or not response_line.strip():
                        stderr_output = self.process.stderr.readline() if self.process.stderr else ""
                        logger.error(f"No response from MCP server. stderr: {stderr_output}")
                        raise Exception(f"No response from MCP server. Error: {stderr_output}")
                    
                    response_data = json.loads(response_line)
                    
                    # 檢查 JSON-RPC 錯誤
                    if "error" in response_data:
                        error_info = response_data["error"]
                        logger.error(f"MCP server returned error: {error_info}")
                        raise Exception(f"MCP Error {error_info.get('code', 'unknown')}: {error_info.get('message', 'Unknown error')}")
                    
                    return response_data
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON response from MCP server: {response_line[:100]}...")
                    raise Exception(f"Invalid response format from MCP server: {e}")
                    
            except Exception as e:
                # 統一錯誤格式
                logger.error(f"MCP call failed - method: {method}, error: {e}")
                # 重新拋出標準化錯誤
                raise Exception(f"MCP service error: {str(e)}")
            
    async def handle_request(self, request: web.Request) -> web.Response:
        """處理 HTTP 請求並轉發到 STDIO - 增強錯誤處理和分類"""
        start_time = asyncio.get_event_loop().time()
        request_id = id(request)
        
        try:
            # 驗證 Content-Type
            if request.content_type not in ['application/json', None]:
                logger.warning(f"Invalid content type: {request.content_type}")
            
            # 解析 JSON 請求體
            try:
                data = await request.json()
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in request: {e}")
                return web.json_response({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,  # Parse error
                        "message": f"Invalid JSON format: {str(e)}"
                    }
                }, status=400)
            
            method = data.get("method", "")
            params = data.get("params", {})
            
            # 記錄請求
            logger.info(f"Processing request {request_id}: {request.path} -> {method}")
            
            # 映射 HTTP 路徑到 MCP 方法
            if request.path == "/tools/list":
                method = "tools/list"
            elif request.path == "/tools/call":
                method = "tools/call"
            elif not method:
                logger.error(f"No method specified for path: {request.path}")
                return web.json_response({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32600,  # Invalid Request
                        "message": "No method specified"
                    }
                }, status=400)
            
            # 調用 MCP 服務
            try:
                result = await self.call_mcp(method, params)
                duration = asyncio.get_event_loop().time() - start_time
                logger.info(f"Request {request_id} completed successfully in {duration:.3f}s")
                return web.json_response(result)
                
            except Exception as mcp_error:
                # MCP 特定錯誤處理
                error_message = str(mcp_error)
                error_code = -32603  # Internal error
                
                # 根據錯誤類型分類
                if "connection broken" in error_message.lower():
                    error_code = -32002  # Connection error
                elif "no response" in error_message.lower():
                    error_code = -32001  # Timeout error
                elif "invalid response format" in error_message.lower():
                    error_code = -32700  # Parse error
                
                logger.error(f"MCP error for request {request_id}: {error_message}")
                return web.json_response({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": error_code,
                        "message": error_message,
                        "data": {
                            "method": method,
                            "path": request.path,
                            "request_id": str(request_id)
                        }
                    }
                }, status=500)
            
        except Exception as e:
            # 捕獲所有其他未預期的錯誤
            duration = asyncio.get_event_loop().time() - start_time
            logger.error(f"Unexpected error in request {request_id} after {duration:.3f}s: {e}", exc_info=True)
            return web.json_response({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,  # Internal error
                    "message": f"Internal server error: {str(e)}",
                    "data": {
                        "request_id": str(request_id)
                    }
                }
            }, status=500)
            
    def cleanup(self):
        """清理進程"""
        if self.process:
            self.process.terminate()
            self.process.wait()
            logger.info("Cleaned up MCP server process")


async def create_app(db_path: str) -> web.Application:
    """創建 HTTP 應用"""
    bridge = MCPBridge(db_path)
    await bridge.start_server()
    
    app = web.Application()
    
    # 路由
    app.router.add_post("/tools/list", bridge.handle_request)
    app.router.add_post("/tools/call", bridge.handle_request)
    app.router.add_post("/{path:.*}", bridge.handle_request)
    
    # 健康檢查
    async def health_check(request):
        return web.json_response({"status": "healthy"})
    app.router.add_get("/health", health_check)
    
    # 清理處理
    async def cleanup(app):
        bridge.cleanup()
    app.on_cleanup.append(cleanup)
    
    return app


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python http_bridge.py <db_path>")
        sys.exit(1)
        
    db_path = sys.argv[1]
    port = int(os.environ.get("PORT", 3003))
    
    app = asyncio.run(create_app(db_path))
    web.run_app(app, host="0.0.0.0", port=port)