#!/usr/bin/env python3
"""簡單測試新 MCP 架構"""

import asyncio
from src.services.mcp import get_mcp_client_manager

async def simple_test():
    print("🚀 開始簡單測試")
    
    try:
        # 測試客戶端管理器
        manager = await get_mcp_client_manager()
        print(f"✅ 客戶端管理器創建成功: {type(manager)}")
        
        # 測試統計信息
        stats = manager.get_statistics()
        print(f"📊 統計信息: {stats}")
        
        # 測試健康檢查
        health = await manager.health_check()
        print(f"💚 健康檢查: {health.get('overall_status', 'unknown')}")
        
        print("✅ 基本測試完成")
        return True
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(simple_test())
    print(f"🏁 測試結果: {'成功' if result else '失敗'}")