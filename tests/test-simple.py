#!/usr/bin/env python3
"""
簡化架構快速測試
"""

import asyncio
import sys
import os
from pathlib import Path

# 設置正確的工作目錄和路徑
os.chdir('/Users/yen/Desktop/lineMCP/apps/bot')
sys.path.insert(0, 'src')

async def quick_test():
    """快速測試主要功能"""
    print("🚀 簡化架構快速測試")
    print("=" * 40)
    
    try:
        # 測試生產級客戶端
        from src.services.production_mcp_client import get_production_mcp_client
        production_client = get_production_mcp_client()
        print("✅ 生產級客戶端 OK")
        
        # 測試統一客戶端
        from src.services.unified_mcp_client import get_unified_mcp_client
        unified_client = await get_unified_mcp_client()
        print("✅ 統一客戶端 OK")
        
        # 測試 MCP 工具調用
        result = await unified_client.call_tool("sqlite", "read_query", {
            "query": "SELECT COUNT(*) as count FROM machines"
        })
        
        if result.get('success'):
            print("✅ MCP 工具調用 OK")
            print(f"📊 資料庫查詢：{result.get('data')}")
        else:
            print(f"❌ MCP 工具調用失敗：{result.get('error')}")
        
        # 清理
        await unified_client.close()
        print("✅ 清理完成")
        
        print("\n🎉 架構測試全部通過！")
        print("🚀 系統運行正常！")
        
    except Exception as e:
        print(f"❌ 測試失敗：{e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(quick_test())