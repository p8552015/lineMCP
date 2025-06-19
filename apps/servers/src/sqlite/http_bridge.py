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
        """透過 STDIO 調用 MCP 服務器"""
        async with self.lock:
            if not self.process:
                await self.start_server()
                
            request = {
                "jsonrpc": "2.0",
                "id": "bridge-1",
                "method": method,
                "params": params
            }
            
            # 寫入請求
            self.process.stdin.write(json.dumps(request) + "\n")
            self.process.stdin.flush()
            
            # 讀取響應
            response_line = self.process.stdout.readline()
            if not response_line:
                raise Exception("No response from MCP server")
                
            return json.loads(response_line)
            
    async def handle_request(self, request: web.Request) -> web.Response:
        """處理 HTTP 請求並轉發到 STDIO"""
        try:
            data = await request.json()
            method = data.get("method", "")
            params = data.get("params", {})
            
            # 映射 HTTP 路徑到 MCP 方法
            if request.path == "/tools/list":
                method = "tools/list"
            elif request.path == "/tools/call":
                method = "tools/call"
                
            result = await self.call_mcp(method, params)
            
            return web.json_response(result)
            
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return web.json_response({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
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