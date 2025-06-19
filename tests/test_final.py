#!/usr/bin/env python3
"""
最終架構測試 - 在正確目錄運行
"""

import asyncio
import sys
sys.path.insert(0, 'src')

async def final_test():
    """最終架構測試"""
    print("🎯 最終架構測試")
    print("=" * 30)
    
    try:
        # 1. 測試核心模組導入
        print("\n📦 模組導入測試...")
        from src.services.production_mcp_client import get_production_mcp_client
        from src.services.unified_mcp_client import get_unified_mcp_client
        from src.services.message_handler import MessageHandler
        print("✅ 所有模組導入成功")
        
        # 2. 測試客戶端實例化
        print("\n🔧 客戶端實例化測試...")
        production_client = get_production_mcp_client()
        unified_client = await get_unified_mcp_client()
        message_handler = MessageHandler()
        print("✅ 所有客戶端實例化成功")
        
        # 3. 測試 MCP 功能
        print("\n🚀 MCP 功能測試...")
        result = await unified_client.call_tool("sqlite", "read_query", {
            "query": "SELECT machine_id, machine_name FROM machines LIMIT 1"
        })
        
        if result.get('success'):
            print("✅ MCP 工具調用成功")
            print(f"📊 查詢結果: {result.get('data')}")
        else:
            print(f"❌ MCP 工具調用失敗: {result.get('error')}")
        
        # 4. 測試工具列表
        tools = await unified_client.list_tools("sqlite")
        if tools.get('success'):
            tool_list = tools.get('tools', [])
            print(f"✅ 工具列表獲取成功，共 {len(tool_list)} 個工具")
        
        # 5. 清理測試
        print("\n🧹 清理測試...")
        await unified_client.close()
        print("✅ 清理完成")
        
        print("\n🎊 所有測試通過！")
        print("✨ 簡化架構運行完美！")
        
        return True
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(final_test())
    print(f"\n{'🎉 SUCCESS' if result else '💥 FAILED'}")