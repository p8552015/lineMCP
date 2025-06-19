#!/usr/bin/env python3
"""
測試MCP連接的簡單腳本
"""

import asyncio
import sys
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_mcp_connection():
    """測試MCP SQLite Server連接"""
    
    # SQLite MCP Server 配置
    server_params = StdioServerParameters(
        command='python3',
        args=['/Users/yen/Desktop/lineMCP/apps/servers/src/sqlite/src/mcp_server_sqlite/server.py', 
              '/Users/yen/Desktop/lineMCP/apps/servers/src/sqlite/test.db'],
        cwd='/Users/yen/Desktop/lineMCP/apps/servers/src/sqlite',
        env={'PYTHONPATH': '/Users/yen/Desktop/lineMCP/apps/servers/src/sqlite/src'}
    )
    
    print(f"🔧 測試配置:")
    print(f"   Command: {server_params.command}")
    print(f"   Args: {server_params.args}")
    print(f"   CWD: {server_params.cwd}")
    print(f"   Env: {server_params.env}")
    
    try:
        print("📡 嘗試建立STDIO連接...")
        async with stdio_client(server_params) as (read_stream, write_stream):
            print("✅ STDIO連接建立成功")
            
            # 建立 session
            session = ClientSession(read_stream, write_stream)
            print("🔗 初始化MCP session...")
            await session.initialize()
            print("✅ MCP session初始化完成")
            
            # 列出工具
            print("📋 列出可用工具...")
            tools_result = await session.list_tools()
            available_tools = [tool.name for tool in tools_result.tools]
            print(f"📋 可用工具: {available_tools}")
            
            # 測試 read_query 工具
            if 'read_query' in available_tools:
                print("🛠️ 測試 read_query 工具...")
                result = await session.call_tool('read_query', {
                    'query': 'SELECT machine_id, machine_name FROM machines LIMIT 3'
                })
                print(f"✅ 查詢結果: {result.content}")
            else:
                print("❌ read_query 工具不可用")
                
    except Exception as e:
        print(f"❌ 連接失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_connection())