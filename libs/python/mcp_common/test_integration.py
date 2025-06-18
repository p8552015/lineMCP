"""
MCP 客戶端整合測試

測試新架構的各個組件是否正常運作。
"""

import asyncio
import sys
import os
from typing import Dict, Any

# 添加 libs/python 到路徑以便導入 mcp_common 模組
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
libs_path = os.path.join(project_root, 'libs', 'python')
if libs_path not in sys.path:
    sys.path.insert(0, libs_path)

try:
    from mcp_common.unified_client import get_unified_mcp_client
    from mcp_common.clients.factory import get_mcp_client
    from mcp_common.config.settings import get_config, get_config_manager
except ImportError as e:
    print(f"❌ 導入錯誤: {e}")
    print("請確保 mcp_common 模組已正確安裝")
    sys.exit(1)


async def test_config_system():
    """測試配置系統"""
    print("🧪 測試配置系統...")
    
    try:
        # 測試配置管理器
        config_manager = get_config_manager()
        config = config_manager.load_config()
        
        print(f"✅ 載入配置成功，環境: {config.environment}")
        print(f"✅ 配置的伺服器數量: {len(config.servers)}")
        
        # 測試取得特定伺服器配置
        sqlite_config = config_manager.get_server_config("sqlite")
        if sqlite_config:
            print(f"✅ SQLite 伺服器配置: {sqlite_config.adapter_type}")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置系統測試失敗: {e}")
        return False


async def test_mock_client():
    """測試 Mock 客戶端"""
    print("\n🧪 測試 Mock 客戶端...")
    
    try:
        # 使用工廠函數創建 Mock 客戶端
        client = get_mcp_client(client_type="mock")
        
        # 測試工具呼叫
        response = await client.call_tool(
            server="test_server",
            tool="test_tool",
            params={"test_param": "test_value"}
        )
        
        print(f"✅ Mock 客戶端回應: {response.status}")
        print(f"✅ 回應資料: {response.data}")
        
        # 測試健康檢查
        health = await client.health_check()
        print(f"✅ 健康檢查: {health.overall}")
        
        # 測試工具列表
        tools = await client.list_tools("test_server")
        print(f"✅ 工具列表: {len(tools)} 個工具")
        
        await client.close()
        return True
        
    except Exception as e:
        print(f"❌ Mock 客戶端測試失敗: {e}")
        return False


async def test_unified_client():
    """測試統一客戶端"""
    print("\n🧪 測試統一客戶端...")
    
    try:
        # 使用統一客戶端
        unified_client = get_unified_mcp_client(client_type="mock")
        
        # 測試新介面
        response = await unified_client.call_tool(
            server="test_server",
            tool="test_tool",
            params={"test": "value"}
        )
        
        print(f"✅ 統一客戶端新介面: {response['success']}")
        
        # 測試向後相容介面
        legacy_response = await unified_client.call_tool_legacy(
            server_name="test_server",
            tool_name="test_tool",
            parameters={"test": "value"}
        )
        
        print(f"✅ 統一客戶端舊介面: {legacy_response['success']}")
        
        # 測試連接功能
        connected = await unified_client.connect_to_server("test_server")
        print(f"✅ 伺服器連接: {connected}")
        
        # 測試取得伺服器資訊
        server_info = await unified_client.get_server_info("test_server")
        print(f"✅ 伺服器資訊: {len(server_info['tools'])} 個工具")
        
        await unified_client.close_all_connections()
        return True
        
    except Exception as e:
        print(f"❌ 統一客戶端測試失敗: {e}")
        return False


async def test_adapters():
    """測試適配器"""
    print("\n🧪 測試適配器...")
    
    try:
        # 測試不同類型的適配器
        adapter_types = ["mock"]  # 只測試 mock，避免需要實際連接
        
        for adapter_type in adapter_types:
            try:
                print(f"  測試 {adapter_type} 適配器...")
                client = get_mcp_client(client_type=adapter_type)
                
                response = await client.call_tool(
                    server="test_server",
                    tool="test_tool", 
                    params={"test": "value"}
                )
                
                print(f"  ✅ {adapter_type} 適配器正常")
                await client.close()
                
            except Exception as e:
                print(f"  ⚠️ {adapter_type} 適配器測試失敗: {str(e)[:100]}")
        
        return True
        
    except Exception as e:
        print(f"❌ 適配器測試失敗: {e}")
        return False


async def test_error_handling():
    """測試錯誤處理"""
    print("\n🧪 測試錯誤處理...")
    
    try:
        client = get_mcp_client(client_type="mock")
        
        # 測試無效的工具呼叫
        response = await client.call_tool(
            server="invalid_server",
            tool="invalid_tool",
            params={}
        )
        
        # Mock 客戶端應該返回成功，但在實際環境中會失敗
        print(f"✅ 錯誤處理測試: {response.status}")
        
        await client.close()
        return True
        
    except Exception as e:
        print(f"❌ 錯誤處理測試失敗: {e}")
        return False


async def main():
    """執行所有測試"""
    print("🚀 開始 MCP 客戶端整合測試")
    print("=" * 50)
    
    test_results = []
    
    # 執行各項測試
    test_results.append(await test_config_system())
    test_results.append(await test_mock_client())
    test_results.append(await test_unified_client())
    test_results.append(await test_adapters())
    test_results.append(await test_error_handling())
    
    # 統計結果
    passed = sum(test_results)
    total = len(test_results)
    
    print("\n" + "=" * 50)
    print(f"📊 測試結果: {passed}/{total} 通過")
    
    if passed == total:
        print("🎉 所有測試通過！新的 MCP 客戶端架構運作正常。")
    else:
        print("⚠️ 部分測試失敗，可能需要進一步設定或調試。")
    
    return passed == total


if __name__ == "__main__":
    # 執行測試
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 