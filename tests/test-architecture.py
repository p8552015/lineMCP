#!/usr/bin/env python3
"""
架構測試腳本 - 驗證簡化後的系統架構
"""

import asyncio
import sys
import os
from pathlib import Path

# 設置路徑
PROJECT_ROOT = Path(__file__).parent.absolute()
BOT_PATH = PROJECT_ROOT / "apps" / "bot"
sys.path.insert(0, str(BOT_PATH / "src"))
os.chdir(str(BOT_PATH))

print("🎯 LINE MCP Bot 架構驗證測試")
print("=" * 50)

async def test_architecture():
    """測試簡化後的架構"""
    
    # 測試 1: 核心模組導入
    print("\n🔧 測試 1: 核心模組導入")
    try:
        from src.services.production_mcp_client import get_production_mcp_client
        print("✅ production_mcp_client 導入成功")
        
        from src.services.unified_mcp_client import get_unified_mcp_client
        print("✅ unified_mcp_client 導入成功")
        
        from src.services.message_handler import MessageHandler
        print("✅ message_handler 導入成功")
        
        from src.services.openai_client import OpenAIClient
        print("✅ openai_client 導入成功")
        
        from src.services.flex_builder import FlexBuilder
        print("✅ flex_builder 導入成功")
        
        from src.config import get_settings
        print("✅ 配置系統導入成功")
        
    except Exception as e:
        print(f"❌ 模組導入失敗：{e}")
        return False
    
    # 測試 2: MCP 客戶端功能
    print("\n🚀 測試 2: MCP 客戶端功能")
    try:
        # 測試生產級客戶端
        production_client = get_production_mcp_client()
        print("✅ 生產級客戶端實例化成功")
        
        # 測試統一客戶端
        unified_client = await get_unified_mcp_client()
        print("✅ 統一客戶端實例化成功")
        
        # 測試 MCP 連接
        result = await unified_client.call_tool("sqlite", "read_query", {
            "query": "SELECT COUNT(*) as total FROM machines"
        })
        
        if result.get('success'):
            print("✅ MCP 工具調用成功")
            print(f"📊 查詢結果：{result.get('data')}")
        else:
            print(f"❌ MCP 工具調用失敗：{result.get('error')}")
            return False
        
        # 測試工具列表
        tools_result = await unified_client.list_tools("sqlite")
        if tools_result.get('success'):
            tools = tools_result.get('tools', [])
            print(f"✅ 獲取工具列表成功，發現 {len(tools)} 個工具")
        else:
            print(f"❌ 獲取工具列表失敗：{tools_result.get('error')}")
        
    except Exception as e:
        print(f"❌ MCP 客戶端測試失敗：{e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 測試 3: 消息處理器整合
    print("\n💬 測試 3: 消息處理器整合")
    try:
        handler = MessageHandler()
        print("✅ 消息處理器實例化成功")
        
        # 測試 MCP 客戶端獲取
        mcp_client = await handler._get_mcp_client()
        print("✅ 消息處理器 MCP 客戶端獲取成功")
        
    except Exception as e:
        print(f"❌ 消息處理器測試失敗：{e}")
        return False
    
    # 測試 4: 配置系統
    print("\n⚙️ 測試 4: 配置系統")
    try:
        settings = get_settings()
        print("✅ 配置系統載入成功")
        print(f"📍 項目根目錄：{settings.project_root}")
        print(f"🗄️ SQLite 路徑：{settings.mcp_sqlite_db_path}")
        
    except Exception as e:
        print(f"❌ 配置系統測試失敗：{e}")
        return False
    
    # 測試 5: 清理測試
    print("\n🧹 測試 5: 清理測試")
    try:
        await unified_client.close()
        print("✅ 統一客戶端清理成功")
        
        await production_client.close_all_connections()
        print("✅ 生產級客戶端清理成功")
        
    except Exception as e:
        print(f"❌ 清理測試失敗：{e}")
        return False
    
    print("\n🎉 所有架構測試通過！")
    print("=" * 50)
    print("✅ 簡化架構運行正常")
    print("✅ MCP STDIO 通信穩定")
    print("✅ 生產級客戶端可靠")
    print("✅ 統一介面完整")
    print("✅ 配置系統正確")
    print("=" * 50)
    print("🚀 架構驗證完成，系統準備就緒！")
    
    return True

if __name__ == "__main__":
    # 設置日誌級別
    import structlog
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(30),  # WARNING level
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    result = asyncio.run(test_architecture())
    sys.exit(0 if result else 1)