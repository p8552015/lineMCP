#!/usr/bin/env python3
"""
只測試 mcp_common 模組
"""

import sys
import os
import asyncio

# 設定路徑
project_root = os.path.dirname(os.path.abspath(__file__))
mcp_common_path = os.path.join(project_root, 'libs', 'python')
sys.path.insert(0, mcp_common_path)

print(f"📂 專案根目錄: {project_root}")
print(f"📂 MCP Common 路徑: {mcp_common_path}")
print(f"📂 路徑存在: {os.path.exists(mcp_common_path)}")

async def test_mcp_common():
    print("\n🧪 測試 mcp_common 模組...")
    
    try:
        # 測試基礎導入
        from mcp_common import get_mcp_client
        print("   ✅ get_mcp_client 導入成功")
        
        # 測試統一客戶端
        from mcp_common.unified_client import get_simple_mcp_client
        print("   ✅ get_simple_mcp_client 導入成功")
        
        # 測試創建客戶端
        client = get_simple_mcp_client()
        print(f"   ✅ 客戶端創建成功: {type(client).__name__}")
        
        # 測試基本功能
        tools = await client.list_tools("sqlite")
        print(f"   🔧 工具列表: {tools}")
        
        # 測試呼叫
        result = await client.call_tool("sqlite", "list_tables", {})
        print(f"   📋 呼叫結果: {result.get('success', 'unknown')}")
        
        await client.close_all_connections()
        print("   ✅ 測試完成")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_mcp_common())
    if result:
        print("\n🎉 mcp_common 模組工作正常！")
    else:
        print("\n❌ mcp_common 模組有問題")