#!/usr/bin/env python3
"""
新 MCP 架構測試腳本
驗證官方 SDK 重構的正確性和性能
"""

import asyncio
import time
from typing import List, Dict, Any

import structlog

# 配置日誌
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

from src.services.mcp import get_mcp_client_manager
from src.services.unified_mcp_client import get_unified_mcp_client

logger = structlog.get_logger()


async def test_new_architecture():
    """測試新架構的基本功能"""
    logger.info("🚀 開始測試新 MCP 架構")
    
    try:
        # 1. 測試新的客戶端管理器
        logger.info("📋 測試 1: MCP 客戶端管理器")
        manager = await get_mcp_client_manager()
        
        # 健康檢查
        health = await manager.health_check()
        logger.info("健康檢查結果", health=health)
        
        # 獲取統計信息
        stats = manager.get_statistics()
        logger.info("系統統計", stats=stats)
        
        # 2. 測試工具列表
        logger.info("📋 測試 2: 工具列表")
        tools_result = await manager.list_tools("sqlite")
        logger.info("工具列表", result=tools_result)
        
        # 3. 測試向下兼容性
        logger.info("📋 測試 3: 向下兼容性")
        client = await get_unified_mcp_client()
        
        # 測試服務器信息
        server_info = await client.get_server_info("sqlite")
        logger.info("服務器信息", info=server_info)
        
        logger.info("✅ 新架構基本測試完成")
        return True
        
    except Exception as e:
        logger.error("❌ 新架構測試失敗", error=str(e), exc_info=True)
        return False


async def test_concurrent_safety():
    """測試並發安全性"""
    logger.info("🔀 開始並發安全性測試")
    
    try:
        manager = await get_mcp_client_manager()
        
        # 創建多個並發請求
        tasks = []
        request_count = 10
        
        for i in range(request_count):
            task = manager.list_tools("sqlite")
            tasks.append(task)
        
        # 執行並發請求
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # 分析結果
        successful_requests = 0
        failed_requests = 0
        
        for result in results:
            if isinstance(result, Exception):
                failed_requests += 1
                logger.error("並發請求失敗", error=str(result))
            else:
                if result.get("success"):
                    successful_requests += 1
                else:
                    failed_requests += 1
        
        success_rate = successful_requests / request_count * 100
        avg_time = (end_time - start_time) / request_count
        
        logger.info("並發測試結果",
                   total_requests=request_count,
                   successful=successful_requests,
                   failed=failed_requests,
                   success_rate=f"{success_rate:.1f}%",
                   avg_response_time=f"{avg_time:.3f}s",
                   total_time=f"{end_time - start_time:.3f}s")
        
        # 驗證是否解決了並發問題
        if success_rate >= 90:
            logger.info("✅ 並發安全性測試通過")
            return True
        else:
            logger.error("❌ 並發安全性測試失敗")
            return False
            
    except Exception as e:
        logger.error("❌ 並發測試失敗", error=str(e), exc_info=True)
        return False


async def test_error_recovery():
    """測試錯誤恢復機制"""
    logger.info("🔄 開始錯誤恢復測試")
    
    try:
        manager = await get_mcp_client_manager()
        
        # 1. 測試無效服務器
        logger.info("測試無效服務器處理")
        invalid_result = await manager.call_tool("invalid_server", "test_tool", {})
        
        if not invalid_result.get("success"):
            logger.info("✅ 無效服務器正確被拒絕")
        else:
            logger.error("❌ 無效服務器未被拒絕")
            return False
        
        # 2. 測試無效工具
        logger.info("測試無效工具處理")
        invalid_tool_result = await manager.call_tool("sqlite", "invalid_tool", {})
        
        if not invalid_tool_result.get("success"):
            logger.info("✅ 無效工具正確被拒絕")
        else:
            logger.info("⚠️ 無效工具結果", result=invalid_tool_result)
        
        # 3. 測試系統恢復能力
        logger.info("測試系統恢復能力")
        recovery_result = await manager.list_tools("sqlite")
        
        if recovery_result.get("success"):
            logger.info("✅ 系統恢復能力正常")
            return True
        else:
            logger.error("❌ 系統恢復失敗")
            return False
            
    except Exception as e:
        logger.error("❌ 錯誤恢復測試失敗", error=str(e), exc_info=True)
        return False


async def test_performance_baseline():
    """建立性能基線"""
    logger.info("📊 開始性能基線測試")
    
    try:
        manager = await get_mcp_client_manager()
        
        # 預熱
        await manager.list_tools("sqlite")
        
        # 單個請求性能
        start_time = time.time()
        result = await manager.list_tools("sqlite")
        single_request_time = time.time() - start_time
        
        logger.info("單個請求性能",
                   time=f"{single_request_time:.3f}s",
                   success=result.get("success"))
        
        # 批量請求性能
        batch_size = 5
        start_time = time.time()
        
        tasks = [manager.list_tools("sqlite") for _ in range(batch_size)]
        results = await asyncio.gather(*tasks)
        
        batch_time = time.time() - start_time
        avg_batch_time = batch_time / batch_size
        
        successful_batch = sum(1 for r in results if r.get("success"))
        
        logger.info("批量請求性能",
                   batch_size=batch_size,
                   total_time=f"{batch_time:.3f}s",
                   avg_time=f"{avg_batch_time:.3f}s",
                   successful=successful_batch,
                   success_rate=f"{successful_batch/batch_size*100:.1f}%")
        
        # 性能評估
        if single_request_time < 5.0 and avg_batch_time < 5.0:
            logger.info("✅ 性能基線達標")
            return True
        else:
            logger.error("❌ 性能基線未達標")
            return False
            
    except Exception as e:
        logger.error("❌ 性能測試失敗", error=str(e), exc_info=True)
        return False


async def main():
    """主測試函數"""
    logger.info("🎯 開始新 MCP 架構全面測試")
    
    test_results = {}
    
    # 執行所有測試
    tests = [
        ("基本功能", test_new_architecture),
        ("並發安全性", test_concurrent_safety),
        ("錯誤恢復", test_error_recovery),
        ("性能基線", test_performance_baseline),
    ]
    
    for test_name, test_func in tests:
        logger.info(f"📋 執行測試: {test_name}")
        try:
            result = await test_func()
            test_results[test_name] = result
            status = "✅ 通過" if result else "❌ 失敗"
            logger.info(f"測試結果: {test_name} - {status}")
        except Exception as e:
            test_results[test_name] = False
            logger.error(f"測試異常: {test_name}", error=str(e))
    
    # 輸出總結
    passed_tests = sum(test_results.values())
    total_tests = len(test_results)
    
    logger.info("🏁 測試總結",
               passed=passed_tests,
               total=total_tests,
               success_rate=f"{passed_tests/total_tests*100:.1f}%",
               results=test_results)
    
    if passed_tests == total_tests:
        logger.info("🎉 所有測試通過！新 MCP 架構重構成功")
        return True
    else:
        logger.error("⚠️ 部分測試失敗，需要進一步調查")
        return False


if __name__ == "__main__":
    asyncio.run(main())