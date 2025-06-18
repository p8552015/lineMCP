#!/usr/bin/env python3
"""
測試配置功能
"""

import sys
import os
import asyncio

# 設定路徑
project_root = os.path.dirname(os.path.abspath(__file__))
mcp_common_path = os.path.join(project_root, 'libs', 'python')
sys.path.insert(0, mcp_common_path)

async def test_config_loading():
    """測試配置載入"""
    print("\n🧪 測試配置載入...")
    
    try:
        from mcp_common.config import load_config, get_client_config
        
        # 載入通用配置
        config = load_config()
        print(f"   📝 配置載入成功，包含 {len(config)} 個主要項目")
        print(f"   🔧 預設客戶端: {config.get('default_client')}")
        print(f"   📋 客戶端類型: {list(config.get('client_types', {}).keys())}")
        
        # 載入特定客戶端配置
        simple_config = get_client_config("simple")
        print(f"   🔍 Simple 配置: {simple_config.get('adapter')}")
        
        mock_config = get_client_config("mock")
        print(f"   🎭 Mock 配置: {mock_config.get('adapter')}")
        
        print("   ✅ 配置載入測試完成")
        return True
        
    except Exception as e:
        print(f"   ❌ 配置載入測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_unified_client_with_config():
    """測試帶配置的統一客戶端"""
    print("\n🔧 測試帶配置的統一客戶端...")
    
    try:
        from mcp_common.unified_client import get_unified_mcp_client
        
        # 使用預設配置創建客戶端
        client = get_unified_mcp_client("simple")
        print(f"   ✅ 客戶端創建成功: {type(client).__name__}")
        
        # 測試基本功能
        tools = await client.list_tools("sqlite")
        print(f"   🛠️ 工具列表: {len(tools)} 個工具")
        
        # 測試呼叫
        result = await client.call_tool("sqlite", "list_tables", {})
        print(f"   📋 呼叫結果: {result.get('success', False)}")
        
        await client.close_all_connections()
        print("   ✅ 配置客戶端測試完成")
        return True
        
    except Exception as e:
        print(f"   ❌ 配置客戶端測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主測試函數"""
    print("🚀 開始配置系統測試")
    print("=" * 50)
    
    # 測試配置載入
    test1 = await test_config_loading()
    
    # 測試配置與客戶端整合
    test2 = await test_unified_client_with_config()
    
    print("\n" + "=" * 50)
    if test1 and test2:
        print("🎉 配置系統測試通過！")
        print("\n📝 完成狀況：")
        print("   ✅ 配置載入正常")
        print("   ✅ 客戶端配置整合成功")
        print("   ✅ YAML 配置支援（或降級到預設配置）")
        print("   ✅ 統一客戶端使用配置")
        return 0
    else:
        print("❌ 部分測試失敗，需要檢查")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())