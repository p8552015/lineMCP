#!/usr/bin/env python3
"""
簡化測試，驗證基礎功能
"""

import asyncio
import sys
import os

# 添加路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs', 'python'))


async def test_basic_imports():
    """測試基礎導入"""
    print("🧪 測試基礎導入")
    
    try:
        # 測試基礎模型
        from mcp_common.models.base import MCPStatusCode, HealthStatusLevel
        print(f"   ✅ 狀態碼: {list(MCPStatusCode)}")
        print(f"   ✅ 健康狀態: {list(HealthStatusLevel)}")
        
        # 測試錯誤模型
        from mcp_common.models.error import MCPError, ConnectionError
        print("   ✅ 錯誤模型導入成功")
        
        # 測試介面
        from mcp_common.clients.interface import MCPClientInterface
        print("   ✅ 客戶端介面導入成功")
        
        # 測試模擬客戶端
        from mcp_common.clients.mock_client import MockMCPClient
        client = MockMCPClient()
        print("   ✅ 模擬客戶端創建成功")
        
        # 簡單測試
        response = await client.call_tool("test", "echo", {"text": "hello"})
        print(f"   ✅ 模擬呼叫成功: {response.status}")
        
        await client.close()
        print("   ✅ 客戶端關閉成功")
        
    except Exception as e:
        print(f"   ❌ 導入測試失敗: {e}")
        import traceback
        traceback.print_exc()


async def test_factory():
    """測試工廠方法"""
    print("\n🏭 測試工廠方法")
    
    try:
        from mcp_common.clients.factory import get_mcp_client
        
        # 測試 mock 客戶端
        client = get_mcp_client(client_type="mock")
        print("   ✅ Mock 客戶端創建成功")
        
        # 測試基本功能
        health = await client.health_check()
        print(f"   ✅ 健康檢查: {health.overall}")
        
        tools = await client.list_tools("test_server")
        print(f"   ✅ 工具列表: {len(tools)} 個工具")
        
        await client.close()
        print("   ✅ 工廠測試完成")
        
    except Exception as e:
        print(f"   ❌ 工廠測試失敗: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🚀 啟動簡化測試")
    asyncio.run(test_basic_imports())
    asyncio.run(test_factory())