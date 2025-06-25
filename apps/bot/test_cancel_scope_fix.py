#!/usr/bin/env python3
"""
Cancel Scope 錯誤修復驗證測試
驗證使用 ProductionMCPClient 是否能避免 cancel scope 錯誤
"""

import asyncio
import sys
import time
from pathlib import Path

# 添加專案根目錄到路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import structlog

# 配置日誌
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


async def test_cancel_scope_fix():
    """測試 cancel scope 修復"""
    logger.info("🔧 測試 Cancel Scope 錯誤修復")
    
    try:
        # 測試 1: 導入統一客戶端（現在是代理）
        logger.info("📦 測試導入統一客戶端...")
        from src.services.unified_mcp_client import get_unified_mcp_client
        logger.info("✅ 統一客戶端導入成功")
        
        # 測試 2: 創建客戶端實例
        logger.info("🏗️ 測試創建客戶端實例...")
        client = await get_unified_mcp_client()
        logger.info("✅ 客戶端實例創建成功")
        
        # 測試 3: 連接到 PostgreSQL 服務器
        logger.info("🔌 測試連接到 PostgreSQL 服務器...")
        connection_start = time.time()
        success = await client.connect_to_server("postgres")
        connection_time = time.time() - connection_start
        
        if success:
            logger.info(f"✅ PostgreSQL 連接成功 (耗時: {connection_time:.2f}s)")
        else:
            logger.warning(f"⚠️ PostgreSQL 連接失敗 (耗時: {connection_time:.2f}s)")
        
        # 測試 4: 列出可用工具
        logger.info("📋 測試列出可用工具...")
        tools_start = time.time()
        tools = await client.list_tools("postgres")
        tools_time = time.time() - tools_start
        
        logger.info(f"✅ 工具列表取得成功 (耗時: {tools_time:.2f}s)")
        logger.info(f"📊 可用工具數量: {len(tools)}")
        
        for tool in tools[:3] if tools else []:  # 只顯示前3個
            logger.info(f"   🔧 {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
        
        # 測試 5: 執行簡單查詢
        logger.info("🔍 測試執行基本查詢...")
        query_start = time.time()
        result = await client.call_tool(
            "postgres",
            "read_query", 
            {"query": "SELECT 1 as test_connection"}
        )
        query_time = time.time() - query_start
        
        logger.info(f"✅ 查詢執行成功 (耗時: {query_time:.2f}s)")
        logger.info(f"📊 查詢結果: {result}")
        
        # 測試 6: 關閉客戶端（檢查是否出現 cancel scope 錯誤）
        logger.info("🔐 測試關閉客戶端...")
        close_start = time.time()
        await client.close()
        close_time = time.time() - close_start
        
        logger.info(f"✅ 客戶端關閉成功 (耗時: {close_time:.2f}s)")
        logger.info("🎉 所有測試通過，未出現 cancel scope 錯誤！")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 測試失敗: {str(e)}")
        logger.error(f"🔍 錯誤類型: {type(e).__name__}")
        
        # 檢查是否為 cancel scope 錯誤
        if "cancel scope" in str(e).lower():
            logger.error("🚨 仍然存在 cancel scope 錯誤！修復失敗。")
        else:
            logger.warning("⚠️ 其他類型錯誤，但沒有 cancel scope 錯誤")
            
        return False


async def main():
    """主要測試函數"""
    logger.info("🚀 啟動 Cancel Scope 修復驗證測試")
    
    success = await test_cancel_scope_fix()
    
    if success:
        logger.info("🏆 測試結論：Cancel Scope 錯誤已成功修復！")
        sys.exit(0)
    else:
        logger.error("💥 測試結論：Cancel Scope 錯誤仍然存在")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())