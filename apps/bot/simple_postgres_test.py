#\!/usr/bin/env python3
"""
簡化的 PostgreSQL MCP 測試
使用現有的統一 MCP 客戶端來驗證連接
"""

import asyncio
import sys
import os

# 添加路徑
sys.path.append('/Users/yen/Desktop/lineMCP/apps/bot')

from src.services.unified_mcp_client import UnifiedMCPClient
from src.config.mcp_config import get_mcp_config

async def test_postgres_connection():
    """測試 PostgreSQL MCP 連接"""
    print("🧪 測試 PostgreSQL MCP 連接...")
    
    try:
        # 獲取配置
        mcp_config = get_mcp_config()
        postgres_config = mcp_config.get_server_config("postgres")
        
        if not postgres_config:
            print("❌ 未找到 postgres 配置")
            return False
        
        print(f"📋 配置檢查: {postgres_config.name}")
        print(f"   命令: {postgres_config.command}")
        print(f"   參數: {postgres_config.args}")
        
        # 創建統一客戶端
        client = UnifiedMCPClient()
        
        # 測試工具列表（會自動建立連接）
        print("📋 獲取工具列表...")
        tools_result = await client.list_tools("postgres")
        
        if tools_result.get("success"):
            tools = tools_result.get("result", {}).get("tools", [])
            print(f"🔧 可用工具: {len(tools)} 個")
            for tool in tools:
                print(f"   - {tool.get('name', 'unknown')}")
            
            # 測試簡單查詢
            print("🔍 執行測試查詢...")
            query_result = await client.call_tool("postgres", "query", {"sql": "SELECT 1 as test"})
            
            if query_result.get("success"):
                print("✅ 查詢測試成功")
                print(f"📊 結果: {query_result.get('result')}")
                return True
            else:
                print(f"❌ 查詢失敗: {query_result.get('error')}")
                return False
        else:
            print(f"❌ 工具列表獲取失敗: {tools_result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理
        try:
            await client.close()
            print("🧹 連接已清理")
        except:
            pass

async def main():
    """主函數"""
    print("🚀 開始 PostgreSQL MCP 簡化測試")
    
    success = await test_postgres_connection()
    
    if success:
        print("🎉 PostgreSQL MCP 測試成功")
        return 0
    else:
        print("❌ PostgreSQL MCP 測試失敗")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))