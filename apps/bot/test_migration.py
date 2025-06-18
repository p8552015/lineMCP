#!/usr/bin/env python3
"""
測試遷移後的 message_handler.py
"""

import sys
import os
import asyncio

# 添加路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
mcp_common_path = os.path.join(project_root, 'libs', 'python')
sys.path.insert(0, current_dir)  # 添加 bot 目錄
sys.path.insert(0, mcp_common_path)  # 添加 mcp_common 路徑

print(f"   📂 當前目錄: {current_dir}")
print(f"   📂 專案根目錄: {project_root}")
print(f"   📂 MCP Common 路徑: {mcp_common_path}")
print(f"   📂 Python 路徑: {sys.path[:3]}")

async def test_message_handler_import():
    """測試 MessageHandler 導入"""
    print("🧪 測試 MessageHandler 導入...")
    
    try:
        from src.services.message_handler import MessageHandler
        print("   ✅ MessageHandler 導入成功")
        
        # 測試創建實例
        handler = MessageHandler()
        print("   ✅ MessageHandler 實例創建成功")
        
        # 檢查 MCP 客戶端類型
        client_type = type(handler.mcp_client).__name__
        print(f"   📦 MCP 客戶端類型: {client_type}")
        
        # 測試基本功能
        tools = await handler.mcp_client.list_tools("sqlite")
        print(f"   🔧 可用工具: {tools}")
        
        # 測試連接
        connected = await handler.mcp_client.connect_to_server("sqlite")
        print(f"   🔌 連接狀態: {connected}")
        
        await handler.mcp_client.close_all_connections()
        print("   ✅ MessageHandler 測試完成")
        
        return True
        
    except Exception as e:
        print(f"   ❌ MessageHandler 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_mcp_call():
    """測試 MCP 呼叫"""
    print("\n🔧 測試 MCP 工具呼叫...")
    
    try:
        from mcp_common.unified_client import get_simple_mcp_client
        
        client = get_simple_mcp_client()
        
        # 測試 list_tables
        result = await client.call_tool("sqlite", "list_tables", {})
        print(f"   📋 表格列表結果: {result}")
        
        # 檢查回應格式
        if isinstance(result, dict) and "success" in result:
            print("   ✅ 回應格式符合預期")
        else:
            print(f"   ⚠️ 回應格式異常: {type(result)}")
        
        await client.close_all_connections()
        print("   ✅ MCP 呼叫測試完成")
        
        return True
        
    except Exception as e:
        print(f"   ❌ MCP 呼叫測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主測試函數"""
    print("🚀 開始遷移測試")
    print("=" * 50)
    
    # 測試 1: MessageHandler 導入
    test1_result = await test_message_handler_import()
    
    # 測試 2: MCP 呼叫
    test2_result = await test_mcp_call()
    
    print("\n" + "=" * 50)
    if test1_result and test2_result:
        print("🎉 所有測試通過！遷移成功！")
        return 0
    else:
        print("❌ 部分測試失敗，需要檢查")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())