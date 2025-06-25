#!/usr/bin/env python3
"""
PostgreSQL MCP 整合測試
驗證新的 PostgreSQL MCP 服務器連接和功能
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


async def test_postgres_connection():
    """測試 PostgreSQL MCP 連接"""
    logger.info("🐘 開始測試 PostgreSQL MCP 連接")
    
    try:
        manager = await get_mcp_client_manager()
        
        # 測試工具列表
        logger.info("📋 測試 PostgreSQL 工具列表")
        tools_result = await manager.list_tools("postgres")
        
        if tools_result.get("success"):
            tools = tools_result.get("tools", [])
            logger.info("✅ PostgreSQL 工具列表獲取成功", tool_count=len(tools))
            
            for tool in tools:
                logger.info("🔧 可用工具", 
                          name=tool.get("name"), 
                          description=tool.get("description", "")[:100])
        else:
            logger.error("❌ PostgreSQL 工具列表獲取失敗", error=tools_result.get("error"))
            return False
        
        return True
        
    except Exception as e:
        logger.error("❌ PostgreSQL 連接測試失敗", error=str(e), exc_info=True)
        return False


async def test_postgres_queries():
    """測試 PostgreSQL 查詢功能"""
    logger.info("🔍 開始測試 PostgreSQL 查詢功能")
    
    try:
        manager = await get_mcp_client_manager()
        
        # 測試查詢列表
        test_queries = [
            {
                "name": "employees_count",
                "sql": "SELECT COUNT(*) as total_employees FROM employees",
                "description": "員工總數查詢"
            },
            {
                "name": "department_summary", 
                "sql": "SELECT department, COUNT(*) as emp_count, AVG(salary) as avg_salary FROM employees GROUP BY department",
                "description": "部門統計查詢"
            },
            {
                "name": "machine_status",
                "sql": "SELECT status, COUNT(*) as count FROM machines GROUP BY status",
                "description": "機台狀態統計"
            },
            {
                "name": "product_inventory",
                "sql": "SELECT category, SUM(stock) as total_stock, COUNT(*) as product_count FROM products GROUP BY category",
                "description": "產品庫存統計"
            }
        ]
        
        successful_queries = 0
        
        for query_test in test_queries:
            logger.info(f"🔍 執行查詢: {query_test['name']}")
            
            try:
                result = await manager.call_tool(
                    "postgres", 
                    "query", 
                    {"sql": query_test["sql"]}
                )
                
                if result.get("success"):
                    successful_queries += 1
                    logger.info(f"✅ 查詢成功: {query_test['name']}")
                    
                    # 顯示結果摘要
                    content = result.get("content", [])
                    if content and isinstance(content, list):
                        for item in content[:3]:  # 只顯示前3個結果
                            if isinstance(item, dict) and item.get("type") == "text":
                                text_content = item.get("text", "")
                                logger.info(f"📊 查詢結果摘要: {text_content[:200]}...")
                else:
                    logger.error(f"❌ 查詢失敗: {query_test['name']}", 
                               error=result.get("error"))
                    
            except Exception as e:
                logger.error(f"❌ 查詢異常: {query_test['name']}", error=str(e))
        
        success_rate = successful_queries / len(test_queries) * 100
        logger.info("🏁 PostgreSQL 查詢測試完成",
                   successful=successful_queries,
                   total=len(test_queries),
                   success_rate=f"{success_rate:.1f}%")
        
        return success_rate >= 75  # 75% 以上成功率視為通過
        
    except Exception as e:
        logger.error("❌ PostgreSQL 查詢測試失敗", error=str(e), exc_info=True)
        return False


async def test_postgres_standalone():
    """測試 PostgreSQL 獨立運行"""
    logger.info("🐘 測試 PostgreSQL 獨立運行")
    
    try:
        manager = await get_mcp_client_manager()
        
        # 測試 PostgreSQL 連接
        postgres_result = await manager.list_tools("postgres")
        
        postgres_ok = not isinstance(postgres_result, Exception) and postgres_result.get("success")
        
        logger.info("🔄 PostgreSQL 獨立測試結果",
                   postgres_status="✅ 正常" if postgres_ok else "❌ 失敗")
        
        if postgres_ok:
            # 執行複雜查詢測試
            complex_queries = [
                {"sql": "SELECT COUNT(*) FROM machines", "desc": "機台計數"},
                {"sql": "SELECT COUNT(*) FROM employees", "desc": "員工計數"},
                {"sql": "SELECT COUNT(*) FROM products", "desc": "產品計數"},
            ]
            
            successful_queries = 0
            for query in complex_queries:
                try:
                    result = await manager.call_tool("postgres", "query", query)
                    if result.get("success"):
                        successful_queries += 1
                        logger.info(f"✅ 查詢成功: {query['desc']}")
                    else:
                        logger.error(f"❌ 查詢失敗: {query['desc']}")
                except Exception as e:
                    logger.error(f"❌ 查詢異常: {query['desc']}, 錯誤: {e}")
            
            logger.info("📊 複雜查詢測試完成",
                       successful=successful_queries,
                       total=len(complex_queries))
        
        return postgres_ok
        
    except Exception as e:
        logger.error("❌ PostgreSQL 獨立測試失敗", error=str(e), exc_info=True)
        return False


async def test_postgres_performance():
    """測試 PostgreSQL 性能"""
    logger.info("⚡ 開始 PostgreSQL 性能測試")
    
    try:
        manager = await get_mcp_client_manager()
        
        # 單次查詢性能
        start_time = time.time()
        result = await manager.call_tool("postgres", "query", 
                                       {"sql": "SELECT * FROM employees LIMIT 10"})
        single_query_time = time.time() - start_time
        
        logger.info("⏱️ 單次查詢性能",
                   time=f"{single_query_time:.3f}s",
                   success=result.get("success"))
        
        # 並發查詢性能
        batch_size = 3
        start_time = time.time()
        
        tasks = [
            manager.call_tool("postgres", "query", {"sql": "SELECT COUNT(*) FROM employees"}),
            manager.call_tool("postgres", "query", {"sql": "SELECT COUNT(*) FROM products"}),
            manager.call_tool("postgres", "query", {"sql": "SELECT COUNT(*) FROM machines"})
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        batch_time = time.time() - start_time
        
        successful_batch = sum(1 for r in results 
                              if not isinstance(r, Exception) and r.get("success"))
        
        logger.info("🔄 並發查詢性能",
                   batch_size=batch_size,
                   total_time=f"{batch_time:.3f}s",
                   avg_time=f"{batch_time/batch_size:.3f}s",
                   successful=successful_batch,
                   success_rate=f"{successful_batch/batch_size*100:.1f}%")
        
        # 性能評估
        performance_ok = (single_query_time < 10.0 and 
                         batch_time < 15.0 and 
                         successful_batch >= batch_size * 0.8)
        
        return performance_ok
        
    except Exception as e:
        logger.error("❌ PostgreSQL 性能測試失敗", error=str(e), exc_info=True)
        return False


async def test_unified_client_compatibility():
    """測試統一客戶端的 PostgreSQL 支援"""
    logger.info("🔗 測試統一客戶端 PostgreSQL 支援")
    
    try:
        client = await get_unified_mcp_client()
        
        # 測試服務器信息
        server_info = await client.get_server_info("postgres")
        
        if server_info.get("success"):
            logger.info("✅ 統一客戶端 PostgreSQL 支援正常",
                       protocol=server_info.get("protocol"),
                       architecture=server_info.get("architecture"),
                       tools_count=len(server_info.get("tools", [])))
            return True
        else:
            logger.error("❌ 統一客戶端 PostgreSQL 支援失敗", 
                        error=server_info.get("error"))
            return False
            
    except Exception as e:
        logger.error("❌ 統一客戶端測試失敗", error=str(e), exc_info=True)
        return False


async def main():
    """主測試函數"""
    logger.info("🎯 開始 PostgreSQL MCP 整合測試")
    
    test_results = {}
    
    # 執行所有測試
    tests = [
        ("PostgreSQL 連接", test_postgres_connection),
        ("PostgreSQL 查詢", test_postgres_queries),
        ("PostgreSQL 獨立運行", test_postgres_standalone),
        ("PostgreSQL 性能", test_postgres_performance),
        ("統一客戶端支援", test_unified_client_compatibility),
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
    
    logger.info("🏁 PostgreSQL MCP 整合測試總結",
               passed=passed_tests,
               total=total_tests,
               success_rate=f"{passed_tests/total_tests*100:.1f}%",
               results=test_results)
    
    if passed_tests == total_tests:
        logger.info("🎉 所有測試通過！PostgreSQL MCP 整合成功")
        return True
    else:
        logger.error("⚠️ 部分測試失敗，需要進一步調查")
        return False


if __name__ == "__main__":
    asyncio.run(main())