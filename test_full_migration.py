#!/usr/bin/env python3
"""
完整的 MCP 客戶端遷移測試
驗證所有功能都正常工作
"""

import sys
import os
import asyncio

# 設定路徑
project_root = os.path.dirname(os.path.abspath(__file__))
mcp_common_path = os.path.join(project_root, 'libs', 'python')
bot_path = os.path.join(project_root, 'apps', 'bot')

sys.path.insert(0, mcp_common_path)
sys.path.insert(0, bot_path)

async def test_mcp_common_module():
    """測試 mcp_common 模組"""
    print("\n📦 測試 mcp_common 模組...")
    
    try:
        # 基本導入
        from mcp_common import get_mcp_client
        from mcp_common.unified_client import get_simple_mcp_client, get_unified_mcp_client
        from mcp_common.config import load_config
        
        print("   ✅ 所有模組導入成功")
        
        # 測試工廠函數
        client1 = get_mcp_client()
        client2 = get_simple_mcp_client()
        client3 = get_unified_mcp_client("simple")
        
        print(f"   🏭 工廠函數測試成功")
        print(f"      - get_mcp_client: {type(client1).__name__}")
        print(f"      - get_simple_mcp_client: {type(client2).__name__}")
        print(f"      - get_unified_mcp_client: {type(client3).__name__}")
        
        # 測試配置
        config = load_config()
        print(f"   ⚙️ 配置載入成功，客戶端類型：{list(config['client_types'].keys())}")
        
        # 清理
        try:
            if hasattr(client1, 'close_all_connections'):
                await client1.close_all_connections()
            else:
                await client1.close()
        except Exception:
            pass
            
        await client2.close_all_connections()
        await client3.close_all_connections()
        
        print("   ✅ mcp_common 模組測試完成")
        return True
        
    except Exception as e:
        print(f"   ❌ mcp_common 模組測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_unified_client_features():
    """測試統一客戶端的各種功能"""
    print("\n🔧 測試統一客戶端功能...")
    
    try:
        from mcp_common.unified_client import get_simple_mcp_client
        
        client = get_simple_mcp_client()
        
        # 測試 1: 工具列表
        tools = await client.list_tools("sqlite")
        print(f"   📋 工具列表：{len(tools)} 個工具")
        assert len(tools) > 0, "應該有可用工具"
        
        # 測試 2: 統一介面呼叫
        result1 = await client.call_tool("sqlite", "list_tables", {})
        print(f"   🔧 統一介面呼叫：{result1.get('success', False)}")
        assert result1.get('success'), "統一介面呼叫應該成功"
        
        # 測試 3: Legacy 介面呼叫
        result2 = await client.call_tool_legacy("sqlite", "list_tables", {})
        print(f"   🔄 Legacy 介面呼叫：{result2.get('success', False)}")
        assert result2.get('success'), "Legacy 介面呼叫應該成功"
        
        # 測試 4: 連接測試
        connected = await client.connect_to_server("sqlite")
        print(f"   🔌 連接測試：{connected}")
        
        # 測試 5: 伺服器資訊
        info = await client.get_server_info("sqlite")
        print(f"   ℹ️ 伺服器資訊：{len(info.get('tools', []))} 個工具")
        
        # 測試 6: 健康檢查
        health = await client.health_check("sqlite")
        print(f"   💊 健康檢查：{health.overall}")
        
        await client.close_all_connections()
        print("   ✅ 統一客戶端功能測試完成")
        return True
        
    except Exception as e:
        print(f"   ❌ 統一客戶端功能測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_bot_integration():
    """測試 Bot 應用的整合"""
    print("\n🤖 測試 Bot 應用整合...")
    
    try:
        # 測試 MCP 設定模組
        from src.services.mcp_setup import setup_mcp_common_path, get_mcp_client_import_status
        
        mcp_path = setup_mcp_common_path()
        status = get_mcp_client_import_status()
        
        print(f"   📂 MCP 路徑設定：{status['success']}")
        print(f"   📍 路徑：{mcp_path}")
        
        # 測試在 Bot 環境中使用統一客戶端
        from mcp_common.unified_client import get_simple_mcp_client
        
        client = get_simple_mcp_client()
        result = await client.call_tool("sqlite", "list_tables", {})
        
        print(f"   🔧 Bot 環境呼叫：{result.get('success', False)}")
        
        await client.close_all_connections()
        print("   ✅ Bot 應用整合測試完成")
        return True
        
    except Exception as e:
        print(f"   ❌ Bot 應用整合測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_compatibility_layer():
    """測試向後相容性"""
    print("\n🔄 測試向後相容性...")
    
    try:
        from mcp_common.unified_client import get_simple_mcp_client
        
        client = get_simple_mcp_client()
        
        # 測試各種呼叫格式
        formats = [
            ("統一格式", lambda: client.call_tool("sqlite", "list_tables", {})),
            ("Legacy 格式", lambda: client.call_tool_legacy("sqlite", "list_tables", {})),
        ]
        
        results = []
        for name, call_func in formats:
            try:
                result = await call_func()
                success = result.get('success', False)
                results.append(success)
                print(f"   ✅ {name}：{success}")
            except Exception as e:
                results.append(False)
                print(f"   ❌ {name}：{e}")
        
        await client.close_all_connections()
        
        # 檢查所有格式都成功
        all_success = all(results)
        print(f"   📊 相容性測試結果：{len([r for r in results if r])}/{len(results)} 成功")
        
        if all_success:
            print("   ✅ 向後相容性測試完成")
        else:
            print("   ⚠️ 部分相容性測試失敗")
        
        return all_success
        
    except Exception as e:
        print(f"   ❌ 向後相容性測試失敗: {e}")
        return False

async def test_error_handling():
    """測試錯誤處理"""
    print("\n🛡️ 測試錯誤處理...")
    
    try:
        from mcp_common.unified_client import get_simple_mcp_client
        
        client = get_simple_mcp_client()
        
        # 測試無效伺服器
        try:
            result = await client.call_tool("invalid_server", "some_tool", {})
            success = not result.get('success', True)  # 應該失敗
            print(f"   🚫 無效伺服器處理：{'正確' if success else '錯誤'}")
        except Exception:
            print(f"   🚫 無效伺服器處理：正確（拋出異常）")
            success = True
        
        # 測試無效工具
        try:
            result = await client.call_tool("sqlite", "invalid_tool", {})
            tool_success = not result.get('success', True)  # 應該失敗
            print(f"   🔧 無效工具處理：{'正確' if tool_success else '錯誤'}")
        except Exception:
            print(f"   🔧 無效工具處理：正確（拋出異常）")
            tool_success = True
        
        await client.close_all_connections()
        
        overall_success = success and tool_success
        if overall_success:
            print("   ✅ 錯誤處理測試完成")
        else:
            print("   ⚠️ 錯誤處理需要改進")
        
        return overall_success
        
    except Exception as e:
        print(f"   ❌ 錯誤處理測試失敗: {e}")
        return False

async def main():
    """主測試函數"""
    print("🚀 開始完整的 MCP 客戶端遷移測試")
    print("=" * 60)
    
    tests = [
        ("mcp_common 模組", test_mcp_common_module),
        ("統一客戶端功能", test_unified_client_features),
        ("Bot 應用整合", test_bot_integration),
        ("向後相容性", test_compatibility_layer),
        ("錯誤處理", test_error_handling),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 執行測試：{test_name}")
        result = await test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 60)
    print("📊 測試結果總結：")
    print("-" * 40)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"   {test_name}：{status}")
        if result:
            passed += 1
    
    print(f"\n📈 總計：{passed}/{total} 測試通過")
    
    if passed == total:
        print("\n🎉 所有測試通過！MCP 客戶端遷移成功！")
        print("\n📝 遷移完成摘要：")
        print("   ✅ 統一客戶端介面已實作")
        print("   ✅ 向後相容性已確保")
        print("   ✅ 配置系統已建立")
        print("   ✅ Bot 應用已遷移")
        print("   ✅ 錯誤處理已完善")
        print("   ✅ 所有功能測試通過")
        
        print("\n🎯 建議後續工作：")
        print("   • 在生產環境中測試")
        print("   • 監控效能指標")
        print("   • 完善文檔")
        print("   • 訓練團隊使用新介面")
        
        return 0
    else:
        print(f"\n❌ {total-passed} 個測試失敗，需要進一步檢查")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())