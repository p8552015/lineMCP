"""
簡單的 PostgreSQL MCP 測試
直接使用 ProductionMCPClient 測試連接
"""

import asyncio
import os

from src.services.production_mcp_client import ProductionMCPClient


async def main():
    print("🚀 PostgreSQL MCP 連接測試")
    print("=" * 50)
    
    # 設置環境變數
    os.environ["ASYNCIO_FORCE_SELECT_SELECTOR"] = "1"
    
    # 初始化客戶端
    client = ProductionMCPClient()
    
    try:
        # 連接到 PostgreSQL
        print("\n1️⃣ 連接 PostgreSQL MCP...")
        success = await client.connect_to_server("postgres")
        
        if not success:
            print("❌ 連接失敗")
            return
            
        print("✅ 連接成功")
        
        # 列出工具
        print("\n2️⃣ 列出可用工具...")
        tools_response = await client.list_tools("postgres")
        
        if isinstance(tools_response, dict) and "tools" in tools_response:
            tools = tools_response["tools"]
        elif isinstance(tools_response, list):
            tools = tools_response
        else:
            tools = []
            
        print(f"找到 {len(tools)} 個工具")
        for tool in tools:
            if isinstance(tool, dict):
                print(f"  - {tool.get('name', 'unknown')}: {tool.get('description', '')}")
            else:
                print(f"  - {tool}")
        
        # 執行簡單查詢
        print("\n3️⃣ 執行查詢...")
        result = await client.call_tool(
            "postgres",
            "query",
            {"sql": "SELECT current_database(), version()"}
        )
        
        print(f"查詢結果: {result}")
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()
        print("\n✅ 測試完成")


if __name__ == "__main__":
    asyncio.run(main())