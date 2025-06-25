#!/usr/bin/env python3
"""
簡化的零洩漏 MCP 客戶端測試
快速驗證基本功能
"""

import asyncio
import time
import os
import sys

# 添加路徑以便導入
sys.path.append('/Users/yen/Desktop/lineMCP/apps/bot')

from src.services.mcp.zero_leak_mcp_client import get_zero_leak_manager


async def simple_test():
    """簡單的零洩漏客戶端測試"""
    print("🧪 開始簡單零洩漏測試")
    
    try:
        # 測試獲取管理器
        print("📋 獲取零洩漏管理器...")
        manager = await get_zero_leak_manager()
        print("✅ 管理器獲取成功")
        
        # 測試基本連接
        print("🔌 測試 PostgreSQL 連接...")
        start_time = time.time()
        
        try:
            result = await asyncio.wait_for(
                manager.list_tools("postgres"), 
                timeout=30.0
            )
            
            connection_time = time.time() - start_time
            print(f"⏱️ 連接時間: {connection_time:.2f}s")
            
            if result.get("success"):
                tools = result.get("result", {}).get("tools", [])
                print(f"✅ 連接成功，發現 {len(tools)} 個工具")
                
                # 測試簡單查詢
                print("🔍 測試簡單查詢...")
                query_start = time.time()
                
                query_result = await asyncio.wait_for(
                    manager.call_tool("postgres", "query", {"sql": "SELECT 1 as test"}),
                    timeout=15.0
                )
                
                query_time = time.time() - query_start
                print(f"⏱️ 查詢時間: {query_time:.2f}s")
                
                if query_result.get("success"):
                    print("✅ 查詢成功")
                    print("🎉 零洩漏客戶端基本功能正常")
                    return True
                else:
                    print(f"❌ 查詢失敗: {query_result.get('error')}")
                    return False
            else:
                print(f"❌ 連接失敗: {result.get('error')}")
                return False
                
        except asyncio.TimeoutError:
            print("❌ 操作超時")
            return False
            
    except Exception as e:
        print(f"❌ 測試異常: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 清理
        try:
            print("🧹 執行清理...")
            await manager.close_all()
            print("✅ 清理完成")
        except Exception as e:
            print(f"⚠️ 清理異常: {e}")


async def main():
    """主函數"""
    print("🚀 開始零洩漏 MCP 客戶端簡化測試")
    
    success = await simple_test()
    
    if success:
        print("🎉 測試成功！零洩漏客戶端正常工作")
        return 0
    else:
        print("❌ 測試失敗")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))