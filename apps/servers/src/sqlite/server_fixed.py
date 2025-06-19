#!/usr/bin/env python3
"""
修復版 SQLite MCP Server
解決 macOS KqueueSelector STDIO 掛起問題
"""

import asyncio
import selectors
import sys
import os

# 必須在導入其他模組前應用修復
def apply_macos_fix():
    """在 MCP Server 端應用 macOS 修復"""
    if sys.platform == 'darwin' or os.environ.get('ASYNCIO_FORCE_SELECT_SELECTOR'):
        try:
            # 檢查是否需要修復
            selector = selectors.SelectSelector()
            loop = asyncio.SelectorEventLoop(selector)
            asyncio.set_event_loop(loop)
            print(f"🔧 MCP Server: 已切換到 SelectSelector（macOS 修復）", file=sys.stderr)
            return True
        except Exception as e:
            print(f"⚠️ MCP Server: 修復警告 - {e}", file=sys.stderr)
    return False

# 應用修復
apply_macos_fix()

# 現在可以安全導入 MCP 模組
try:
    from mcp_server_sqlite.server import main as mcp_main
    print("✅ MCP Server: SQLite 模組導入成功", file=sys.stderr)
    
    async def original_main():
        """包裝原始 main 函數"""
        if len(sys.argv) < 2:
            print("Usage: python server_fixed.py <db_path>", file=sys.stderr)
            sys.exit(1)
        
        db_path = sys.argv[1]
        await mcp_main(db_path)
        
except ImportError as e:
    print(f"❌ MCP Server: 無法導入 SQLite 模組 - {e}", file=sys.stderr)
    # 回退到基本實作
    import sqlite3
    import json
    from typing import Any, Dict, List
    
    async def run_basic_server(db_path: str):
        """基本的 STDIO MCP Server 實作"""
        print(f"🚀 MCP Server: 啟動基本 SQLite 服務器 {db_path}", file=sys.stderr)
        
        # 確保資料庫存在
        if not os.path.exists(db_path):
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            conn = sqlite3.connect(db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS machines (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    status TEXT,
                    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                INSERT OR REPLACE INTO machines (id, name, status) VALUES 
                ('M001', '包裝機1號', '運行中'),
                ('M002', '切割機2號', '停機'),
                ('M003', '焊接機3號', '維護中')
            """)
            conn.commit()
            conn.close()
            print("✅ MCP Server: 測試資料庫已創建", file=sys.stderr)
        
        # 基本的 STDIO 協議處理
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                if not line:
                    break
                
                request = json.loads(line.strip())
                method = request.get('method', '')
                params = request.get('params', {})
                request_id = request.get('id', 'unknown')
                
                if method == 'tools/list':
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "tools": [
                                {
                                    "name": "read_query",
                                    "description": "Execute a SELECT query",
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
                elif method == 'tools/call':
                    tool_name = params.get('name', '')
                    arguments = params.get('arguments', {})
                    
                    if tool_name == 'read_query':
                        query = arguments.get('query', '')
                        try:
                            conn = sqlite3.connect(db_path)
                            conn.row_factory = sqlite3.Row
                            cursor = conn.cursor()
                            cursor.execute(query)
                            rows = cursor.fetchall()
                            result = [dict(row) for row in rows]
                            conn.close()
                            
                            response = {
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "result": {
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": json.dumps(result, ensure_ascii=False)
                                        }
                                    ]
                                }
                            }
                        except Exception as e:
                            response = {
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "error": {
                                    "code": -32603,
                                    "message": str(e)
                                }
                            }
                    else:
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32601,
                                "message": f"Unknown tool: {tool_name}"
                            }
                        }
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Unknown method: {method}"
                        }
                    }
                
                print(json.dumps(response), flush=True)
                
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"❌ MCP Server: 錯誤 - {e}", file=sys.stderr)
                continue
    
    async def original_main():
        """基本服務器主函式"""
        if len(sys.argv) < 2:
            print("Usage: python server_fixed.py <db_path>", file=sys.stderr)
            sys.exit(1)
        
        db_path = sys.argv[1]
        await run_basic_server(db_path)


async def main():
    """修復版主函式"""
    try:
        # 再次確認修復已應用
        current_loop = asyncio.get_event_loop()
        selector = getattr(current_loop, '_selector', None)
        if selector:
            selector_type = type(selector).__name__
            print(f"🔍 MCP Server: 使用選擇器 - {selector_type}", file=sys.stderr)
        
        # 調用原始主函式
        await original_main()
        
    except KeyboardInterrupt:
        print("🛑 MCP Server: 被用戶中斷", file=sys.stderr)
    except Exception as e:
        print(f"❌ MCP Server: 運行錯誤 - {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)


if __name__ == "__main__":
    # 確保在主程序中也應用修復
    apply_macos_fix()
    
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ MCP Server: 啟動失敗 - {e}", file=sys.stderr)
        sys.exit(1)