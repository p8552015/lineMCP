#!/usr/bin/env python3
"""
在 bot 環境中測試簡單的遷移
避免複雜的依賴問題
"""

import sys
import os
import asyncio

# 設定路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
mcp_common_path = os.path.join(project_root, 'libs', 'python')

# 添加路徑
if mcp_common_path not in sys.path:
    sys.path.insert(0, mcp_common_path)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

print(f"📂 當前目錄: {current_dir}")
print(f"📂 專案根目錄: {project_root}")

async def test_direct_import():
    """直接測試新的統一客戶端"""
    print("\n🧪 測試新的統一客戶端...")
    
    try:
        from mcp_common.unified_client import get_simple_mcp_client
        
        # 創建客戶端
        client = get_simple_mcp_client()
        print(f"   ✅ 客戶端創建成功: {type(client).__name__}")
        
        # 測試工具列表
        tools = await client.list_tools("sqlite")
        print(f"   🔧 可用工具: {tools}")
        
        # 測試呼叫（向後相容格式）
        result = await client.call_tool_legacy("sqlite", "list_tables", {})
        print(f"   📋 Legacy 呼叫成功: {result.get('success', False)}")
        
        # 測試新格式呼叫
        result2 = await client.call_tool("sqlite", "list_tables", {})
        print(f"   📋 新格式呼叫成功: {result2.get('success', False)}")
        
        # 測試連接
        connected = await client.connect_to_server("sqlite")
        print(f"   🔌 連接測試: {connected}")
        
        await client.close_all_connections()
        print("   ✅ 統一客戶端測試完成")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 統一客戶端測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_mock_comparison():
    """測試 Mock 客戶端比較"""
    print("\n🎭 測試 Mock 客戶端...")
    
    try:
        from mcp_common.unified_client import get_unified_mcp_client
        
        # 創建 Mock 客戶端
        mock_client = get_unified_mcp_client(client_type="mock")
        print(f"   ✅ Mock 客戶端創建成功: {type(mock_client).__name__}")
        
        # 測試呼叫
        result = await mock_client.call_tool("test_server", "echo", {"text": "Hello MCP!"})
        print(f"   🎭 Mock 呼叫結果: {result.get('success', False)}")
        print(f"   📦 Mock 回應資料: {result.get('data', {})}")
        
        await mock_client.close_all_connections()
        print("   ✅ Mock 客戶端測試完成")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Mock 客戶端測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主測試函數"""
    print("🚀 開始 Bot 環境遷移測試")
    print("=" * 50)
    
    # 測試統一客戶端
    test1 = await test_direct_import()
    
    # 測試 Mock 客戶端
    test2 = await test_mock_comparison()
    
    print("\n" + "=" * 50)
    if test1 and test2:
        print("🎉 Bot 環境測試通過！可以開始遷移！")
        print("\n📝 下一步：")
        print("   1. 更新 message_handler.py 中的導入")
        print("   2. 確保所有功能正常")
        print("   3. 測試完整的工作流程")
        return 0
    else:
        print("❌ 部分測試失敗，需要檢查")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())