"""
簡單的可工作測試腳本

透過正確設定 Python 路徑來測試 mcp_common 模組。
"""

import asyncio
import sys
import os

# 將 libs/python 添加到 Python 路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
libs_dir = os.path.dirname(current_dir)
if libs_dir not in sys.path:
    sys.path.insert(0, libs_dir)

print(f"📁 當前目錄: {current_dir}")
print(f"📂 添加到 Python 路徑: {libs_dir}")

def test_basic_imports():
    """測試基本導入"""
    print("\n🧪 測試基本導入...")
    
    try:
        # 使用絕對導入
        import mcp_common
        print("✅ mcp_common 模組導入成功")
        
        from mcp_common.models.base import MCPResponse, MCPCall, MCPStatusCode
        print("✅ 基本模型導入成功")
        
        from mcp_common.models.error import MCPError
        print("✅ 錯誤模型導入成功")
        
        from mcp_common.models.query import QueryType, QueryRequest
        print("✅ 查詢模型導入成功")
        
        from mcp_common.clients.mock_client import MockMCPClient
        print("✅ Mock 客戶端導入成功")
        
        from mcp_common.clients.factory import get_mcp_client
        print("✅ 工廠函數導入成功")
        
        from mcp_common.config.settings import ServerConfig, MCPClientConfig
        print("✅ 配置模型導入成功")
        
        return True
        
    except ImportError as e:
        print(f"❌ 導入失敗: {e}")
        return False


async def test_mock_client_basic():
    """測試 Mock 客戶端基本功能"""
    print("\n🧪 測試 Mock 客戶端...")
    
    try:
        from mcp_common.clients.mock_client import MockMCPClient
        
        # 創建客戶端
        client = MockMCPClient()
        
        # 測試工具呼叫
        response = await client.call_tool(
            server="test_server",
            tool="test_tool", 
            params={"key": "value"}
        )
        
        print(f"✅ 工具呼叫狀態: {response.status}")
        print(f"✅ 回應 ID: {response.call_id}")
        
        # 測試健康檢查
        health = await client.health_check()
        print(f"✅ 健康檢查狀態: {health.overall}")
        
        # 測試工具列表
        tools = await client.list_tools("test_server")
        print(f"✅ 可用工具數量: {len(tools)}")
        
        await client.close()
        return True
        
    except Exception as e:
        print(f"❌ Mock 客戶端測試失敗: {e}")
        return False


def test_config_system():
    """測試配置系統"""
    print("\n🧪 測試配置系統...")
    
    try:
        from mcp_common.config.settings import ServerConfig, MCPClientConfig
        
        # 測試伺服器配置
        server_config = ServerConfig(
            name="test_server",
            adapter_type="mock",  # 使用 mock 類型
            timeout=30.0
        )
        print(f"✅ 伺服器配置: {server_config.name} ({server_config.adapter_type})")
        
        # 測試客戶端配置
        client_config = MCPClientConfig(
            environment="development",
            servers={"test": server_config}
        )
        print(f"✅ 客戶端配置環境: {client_config.environment}")
        print(f"✅ 配置的伺服器數量: {len(client_config.servers)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置測試失敗: {e}")
        return False


async def test_factory_client():
    """測試工廠函數創建的客戶端"""
    print("\n🧪 測試工廠客戶端...")
    
    try:
        from mcp_common.clients.factory import get_mcp_client
        
        # 使用工廠函數創建客戶端
        client = get_mcp_client(client_type="mock")
        
        # 測試功能
        response = await client.call_tool(
            server="factory_test",
            tool="test_tool",
            params={"factory": "test"}
        )
        
        print(f"✅ 工廠客戶端狀態: {response.status}")
        print(f"✅ 執行時間: {response.duration_ms:.2f} ms")
        
        await client.close()
        return True
        
    except Exception as e:
        print(f"❌ 工廠客戶端測試失敗: {e}")
        return False


def test_data_models():
    """測試資料模型"""
    print("\n🧪 測試資料模型...")
    
    try:
        from mcp_common.models.base import MCPResponse, MCPCall, MCPStatusCode
        from mcp_common.models.query import QueryRequest, QueryType
        
        # 測試回應模型
        response = MCPResponse(
            call_id="test123",
            status=MCPStatusCode.SUCCESS,
            data={"result": "test"},
            duration_ms=100.0
        )
        print(f"✅ 回應模型狀態: {response.status}")
        
        # 測試查詢模型
        query = QueryRequest(
            id="query123",
            type=QueryType.SINGLE
        )
        print(f"✅ 查詢模型類型: {query.type}")
        print(f"✅ 查詢 ID: {query.id}")
        
        return True
        
    except Exception as e:
        print(f"❌ 資料模型測試失敗: {e}")
        return False


async def main():
    """執行所有測試"""
    print("🚀 開始 MCP Common 模組測試")
    print("=" * 50)
    
    test_results = []
    
    # 執行測試
    test_results.append(test_basic_imports())
    test_results.append(test_config_system())
    test_results.append(test_data_models())
    test_results.append(await test_mock_client_basic())
    test_results.append(await test_factory_client())
    
    # 統計結果
    passed = sum(test_results)
    total = len(test_results)
    
    print("\n" + "=" * 50)
    print(f"📊 測試結果: {passed}/{total} 通過")
    
    if passed == total:
        print("🎉 所有測試通過！MCP Common 模組運作正常。")
        print("\n📋 驗證的功能:")
        print("  ✅ 模組正確導入")
        print("  ✅ 配置系統運作")
        print("  ✅ 資料模型驗證")
        print("  ✅ Mock 客戶端功能")
        print("  ✅ 工廠函數創建客戶端")
        print("\n🔧 下一步建議:")
        print("  1. 安裝模組: pip install -e .")
        print("  2. 在其他專案中導入: from mcp_common import get_mcp_client")
        print("  3. 整合到現有的 bot 應用程式中")
    else:
        print("⚠️ 部分測試失敗，需要進一步調試。")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 