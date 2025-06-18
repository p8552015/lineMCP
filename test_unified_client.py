#!/usr/bin/env python3
"""
測試統一 MCP 客戶端

驗證新的統一介面是否正確運作。
"""

import asyncio
import sys
import os

# 添加路徑以導入 mcp_common
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs', 'python'))

from mcp_common.unified_client import get_unified_mcp_client, get_simple_mcp_client


async def test_unified_client():
    """測試統一客戶端"""
    print("🧪 測試統一 MCP 客戶端")
    print("=" * 50)
    
    # 測試 1: 使用新的統一介面
    print("\n1. 測試統一介面 (Simple 適配器)")
    try:
        client = get_unified_mcp_client(client_type="simple")
        
        # 測試健康檢查
        print("   📡 健康檢查...")
        health = await client.health_check()
        print(f"   整體狀態: {health.overall}")
        print(f"   伺服器狀態: {health.servers}")
        
        # 測試工具列表
        print("   📋 列出工具...")
        tools = await client.list_tools("sqlite")
        print(f"   可用工具: {tools}")
        
        # 測試工具呼叫
        print("   🔧 呼叫工具...")
        response = await client.call_tool(
            server="sqlite",
            tool="list_tables",
            params={}
        )
        print(f"   回應: {response}")
        
        await client.close_all_connections()
        print("   ✅ 統一介面測試完成")
        
    except Exception as e:
        print(f"   ❌ 統一介面測試失敗: {e}")
    
    # 測試 2: 向後相容介面
    print("\n2. 測試向後相容介面")
    try:
        client = get_simple_mcp_client()
        
        # 使用 legacy 格式的方法呼叫
        print("   🔄 Legacy 格式呼叫...")
        result = await client.call_tool_legacy(
            server_name="sqlite",
            tool_name="list_tables",
            parameters={}
        )
        print(f"   Legacy 回應: {result}")
        
        # 測試連接
        print("   🔌 測試連接...")
        connected = await client.connect_to_server("sqlite")
        print(f"   連接狀態: {connected}")
        
        # 測試伺服器資訊
        print("   ℹ️ 取得伺服器資訊...")
        info = await client.get_server_info("sqlite")
        print(f"   伺服器資訊: {info}")
        
        await client.close_all_connections()
        print("   ✅ 向後相容測試完成")
        
    except Exception as e:
        print(f"   ❌ 向後相容測試失敗: {e}")
    
    # 測試 3: Mock 客戶端
    print("\n3. 測試 Mock 客戶端")
    try:
        client = get_unified_mcp_client(client_type="mock")
        
        # 測試模擬呼叫
        print("   🎭 模擬呼叫...")
        response = await client.call_tool(
            server="test_server",
            tool="echo",
            params={"text": "Hello, MCP!"}
        )
        print(f"   模擬回應: {response}")
        
        await client.close_all_connections()
        print("   ✅ Mock 客戶端測試完成")
        
    except Exception as e:
        print(f"   ❌ Mock 客戶端測試失敗: {e}")
    
    print("\n🏁 所有測試完成")


async def test_configuration():
    """測試配置載入"""
    print("\n🔧 測試配置載入")
    print("=" * 30)
    
    try:
        from mcp_common.clients.factory import get_mcp_client
        
        # 測試不同配置
        configs = [
            {"client_type": "simple"},
            {"client_type": "mock"},
            {
                "client_type": "simple",
                "servers": {"test": "http://localhost:8080"}
            }
        ]
        
        for i, config in enumerate(configs, 1):
            print(f"   {i}. 測試配置: {config}")
            try:
                client = get_mcp_client(config=config)
                health = await client.health_check()
                print(f"      狀態: {health.overall}")
                await client.close()
                print(f"      ✅ 配置 {i} 測試成功")
            except Exception as e:
                print(f"      ❌ 配置 {i} 測試失敗: {e}")
    
    except Exception as e:
        print(f"   ❌ 配置測試失敗: {e}")


if __name__ == "__main__":
    print("🚀 啟動 MCP 統一客戶端測試")
    asyncio.run(test_unified_client())
    asyncio.run(test_configuration())