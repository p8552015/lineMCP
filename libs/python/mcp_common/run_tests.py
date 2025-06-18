#!/usr/bin/env python
"""
執行 MCP Common 測試套件
"""

import sys
import pytest
import asyncio
from pathlib import Path

# 添加專案路徑到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def run_tests():
    """執行所有測試"""
    print("🧪 執行 MCP Common 測試套件...\n")
    
    # 測試參數
    args = [
        "-v",  # 詳細輸出
        "--tb=short",  # 簡短的錯誤追蹤
        "--color=yes",  # 彩色輸出
        "tests/",  # 測試目錄
    ]
    
    # 如果有提供額外參數，添加它們
    if len(sys.argv) > 1:
        args.extend(sys.argv[1:])
    
    # 執行測試
    exit_code = pytest.main(args)
    
    if exit_code == 0:
        print("\n✅ 所有測試通過！")
    else:
        print(f"\n❌ 測試失敗，退出碼: {exit_code}")
    
    return exit_code


async def run_quick_test():
    """執行快速整合測試"""
    print("🚀 執行快速整合測試...\n")
    
    try:
        from mcp_common import get_mcp_client, MCPError
        
        # 建立 Mock 客戶端
        client = get_mcp_client("mock")
        print("✓ 成功建立 Mock 客戶端")
        
        # 測試呼叫工具
        response = await client.call_tool(
            server="test_server",
            tool="test_tool",
            params={"message": "Hello MCP!"}
        )
        print(f"✓ 工具呼叫成功: {response.status}")
        
        # 測試批次呼叫
        from mcp_common import MCPCall
        calls = [
            MCPCall(server="server1", tool="tool1", params={}),
            MCPCall(server="server2", tool="tool2", params={}),
        ]
        batch_response = await client.batch_call(calls)
        print(f"✓ 批次呼叫成功: {len(batch_response.responses)} 個回應")
        
        # 測試健康檢查
        health = await client.health_check()
        print(f"✓ 健康檢查: {health.overall}")
        
        # 關閉客戶端
        await client.close()
        print("✓ 客戶端已關閉")
        
        print("\n✅ 快速整合測試通過！")
        return 0
        
    except Exception as e:
        print(f"\n❌ 快速整合測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """主函數"""
    if "--quick" in sys.argv:
        # 執行快速測試
        sys.argv.remove("--quick")
        exit_code = asyncio.run(run_quick_test())
    else:
        # 執行完整測試套件
        exit_code = run_tests()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()