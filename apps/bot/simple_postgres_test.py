#!/usr/bin/env python3
"""
簡化的 PostgreSQL MCP 測試
"""

import asyncio
import os
import sys

# 確保能導入項目模組
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_postgres_basic():
    """基本 PostgreSQL 測試"""
    try:
        from src.services.mcp.client_manager import get_mcp_client_manager
        
        print("🐘 開始基本 PostgreSQL MCP 測試")
        
        # 獲取管理器
        manager = await get_mcp_client_manager()
        print("✅ MCP 客戶端管理器已創建")
        
        # 測試工具列表
        print("📋 測試 PostgreSQL 工具列表...")
        tools_result = await manager.list_tools("postgres")
        
        if tools_result.get("success"):
            tools = tools_result.get("tools", [])
            print(f"✅ PostgreSQL 工具列表獲取成功，共 {len(tools)} 個工具")
            
            for tool in tools:
                print(f"🔧 工具: {tool.get('name')} - {tool.get('description', '')[:50]}")
        else:
            print(f"❌ PostgreSQL 工具列表獲取失敗: {tools_result.get('error')}")
            return False
        
        # 測試簡單查詢
        print("🔍 測試簡單查詢...")
        result = await manager.call_tool("postgres", "query", 
                                       {"sql": "SELECT COUNT(*) as total FROM employees"})
        
        if result.get("success"):
            print("✅ 查詢執行成功")
            content = result.get("content", [])
            if content:
                print(f"📊 查詢結果: {content}")
        else:
            print(f"❌ 查詢執行失敗: {result.get('error')}")
            return False
        
        print("🎉 PostgreSQL MCP 基本測試完成！")
        return True
        
    except Exception as e:
        print(f"❌ 測試過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主函數"""
    print("🚀 開始 PostgreSQL MCP 簡化測試")
    
    success = await test_postgres_basic()
    
    if success:
        print("✅ 測試成功！PostgreSQL MCP 整合正常")
        return 0
    else:
        print("❌ 測試失敗！需要進一步調查")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 測試被用戶中斷")
        sys.exit(130)
    except Exception as e:
        print(f"❌ 程序執行失敗: {e}")
        sys.exit(1)