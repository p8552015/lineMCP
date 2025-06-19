#!/usr/bin/env python3
"""
簡化的 HTTP MCP 橋接器
直接提供 SQLite 工具而不是橋接到 STDIO
"""

import asyncio
import json
import sqlite3
import os
from typing import Any, Dict, List
from aiohttp import web
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleMCPServer:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db_exists()
        
    def _ensure_db_exists(self):
        """確保資料庫檔案存在"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        if not os.path.exists(self.db_path):
            # 創建空的 SQLite 資料庫
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS machines (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    status TEXT,
                    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # 插入測試資料
            conn.execute("""
                INSERT OR REPLACE INTO machines (id, name, status) VALUES 
                ('M001', '包裝機1號', '運行中'),
                ('M002', '切割機2號', '停機'),
                ('M003', '焊接機3號', '維護中')
            """)
            conn.commit()
            conn.close()
            logger.info(f"Created test database at {self.db_path}")
    
    async def list_tools(self) -> Dict[str, Any]:
        """列出可用工具"""
        return {
            "jsonrpc": "2.0",
            "result": {
                "tools": [
                    {
                        "name": "read_query",
                        "description": "Execute a SELECT query on the SQLite database",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"}
                            },
                            "required": ["query"]
                        }
                    },
                    {
                        "name": "execute_query", 
                        "description": "Execute any SQL query on the SQLite database",
                        "inputSchema": {
                            "type": "object", 
                            "properties": {
                                "query": {"type": "string"}
                            },
                            "required": ["query"]
                        }
                    }
                ]
            }
        }
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """調用工具"""
        try:
            if name in ["read_query", "execute_query"]:
                query = arguments.get("query", "")
                if not query:
                    raise ValueError("Missing query parameter")
                
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(query)
                
                if query.strip().upper().startswith("SELECT"):
                    rows = cursor.fetchall()
                    result = [dict(row) for row in rows]
                else:
                    conn.commit()
                    result = {"affected_rows": cursor.rowcount}
                
                conn.close()
                
                return {
                    "jsonrpc": "2.0",
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, ensure_ascii=False, indent=2)
                            }
                        ]
                    }
                }
            else:
                raise ValueError(f"Unknown tool: {name}")
                
        except Exception as e:
            logger.error(f"Tool call error: {e}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
    
    async def handle_request(self, request: web.Request) -> web.Response:
        """處理 HTTP 請求"""
        try:
            if request.path == "/tools/list":
                result = await self.list_tools()
                return web.json_response(result)
            
            elif request.path == "/tools/call":
                data = await request.json()
                tool_name = data.get("name", "")
                arguments = data.get("arguments", {})
                
                result = await self.call_tool(tool_name, arguments)
                return web.json_response(result)
            
            else:
                # 處理通用 JSON-RPC 請求
                data = await request.json()
                method = data.get("method", "")
                params = data.get("params", {})
                
                if method == "tools/list":
                    result = await self.list_tools()
                elif method == "tools/call":
                    result = await self.call_tool(params.get("name", ""), params.get("arguments", {}))
                else:
                    result = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}"
                        }
                    }
                
                return web.json_response(result)
                
        except Exception as e:
            logger.error(f"Request handling error: {e}")
            return web.json_response({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }, status=500)


async def create_app(db_path: str) -> web.Application:
    """創建 HTTP 應用"""
    server = SimpleMCPServer(db_path)
    
    app = web.Application()
    
    # 路由
    app.router.add_post("/tools/list", server.handle_request)
    app.router.add_post("/tools/call", server.handle_request)
    app.router.add_post("/{path:.*}", server.handle_request)
    
    # 健康檢查
    async def health_check(request):
        return web.json_response({"status": "healthy", "db_path": db_path})
    app.router.add_get("/health", health_check)
    
    return app


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python http_bridge_simple.py <db_path>")
        sys.exit(1)
        
    db_path = sys.argv[1]
    port = int(os.environ.get("PORT", 3003))
    
    logger.info(f"Starting Simple MCP Server on port {port} with database {db_path}")
    
    app = asyncio.run(create_app(db_path))
    web.run_app(app, host="0.0.0.0", port=port)