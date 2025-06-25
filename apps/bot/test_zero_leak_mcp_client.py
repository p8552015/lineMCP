#!/usr/bin/env python3
"""
零洩漏 MCP 客戶端測試
驗證新的零洩漏實作是否真正解決了資源洩漏問題
"""

import asyncio
import time
import gc
from typing import Dict, Any, List

import psutil
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

logger = structlog.get_logger()


class ResourceMonitor:
    """資源監控器"""
    
    def __init__(self):
        self.initial_memory = 0.0
        self.initial_fds = 0
        self.initial_processes = []
        self.measurements = []
    
    def capture_baseline(self):
        """捕獲基線資源狀態"""
        gc.collect()  # 強制垃圾回收
        process = psutil.Process()
        
        self.initial_memory = process.memory_info().rss / 1024 / 1024
        self.initial_fds = process.num_fds()
        self.initial_processes = [
            {
                "pid": child.pid,
                "name": child.name(),
                "status": child.status(),
                "created_time": child.create_time()
            }
            for child in process.children(recursive=True)
        ]
        
        logger.info("📊 基線資源狀態已捕獲",
                   memory_mb=f"{self.initial_memory:.2f}",
                   file_descriptors=self.initial_fds,
                   child_processes=len(self.initial_processes))
    
    def measure_current_state(self) -> Dict[str, Any]:
        """測量當前資源狀態"""
        gc.collect()  # 強制垃圾回收
        process = psutil.Process()
        
        current_memory = process.memory_info().rss / 1024 / 1024
        current_fds = process.num_fds()
        current_processes = [
            {
                "pid": child.pid,
                "name": child.name(),
                "status": child.status(),
                "created_time": child.create_time()
            }
            for child in process.children(recursive=True)
        ]
        
        memory_diff = current_memory - self.initial_memory
        fd_diff = current_fds - self.initial_fds
        
        # 檢查新增的進程
        initial_pids = {p["pid"] for p in self.initial_processes}
        new_processes = [p for p in current_processes if p["pid"] not in initial_pids]
        
        measurement = {
            "timestamp": time.time(),
            "memory_mb": current_memory,
            "memory_diff_mb": memory_diff,
            "file_descriptors": current_fds,
            "fd_diff": fd_diff,
            "child_processes": len(current_processes),
            "new_processes": new_processes,
            "has_leaks": memory_diff > 2.0 or fd_diff > 0 or len(new_processes) > 0
        }
        
        self.measurements.append(measurement)
        return measurement
    
    def get_leak_summary(self) -> Dict[str, Any]:
        """獲取洩漏總結"""
        if not self.measurements:
            return {"error": "沒有測量數據"}
        
        latest = self.measurements[-1]
        max_memory_diff = max(m["memory_diff_mb"] for m in self.measurements)
        max_fd_diff = max(m["fd_diff"] for m in self.measurements)
        total_new_processes = len(latest["new_processes"])
        
        return {
            "final_memory_diff_mb": latest["memory_diff_mb"],
            "max_memory_diff_mb": max_memory_diff,
            "final_fd_diff": latest["fd_diff"],
            "max_fd_diff": max_fd_diff,
            "new_processes_count": total_new_processes,
            "new_processes": latest["new_processes"],
            "has_significant_leaks": (
                latest["memory_diff_mb"] > 5.0 or 
                latest["fd_diff"] > 0 or 
                total_new_processes > 0
            ),
            "measurement_count": len(self.measurements)
        }


async def test_zero_leak_client_basic_functionality():
    """測試零洩漏客戶端基本功能"""
    logger.info("🧪 測試零洩漏客戶端基本功能")
    
    try:
        from src.services.mcp.zero_leak_mcp_client import get_zero_leak_manager
        
        manager = await get_zero_leak_manager()
        
        # 測試連接和基本操作
        result = await manager.list_tools("postgres")
        
        if result.get("success"):
            tools = result.get("result", {}).get("tools", [])
            logger.info("✅ 零洩漏客戶端基本功能正常",
                       tools_count=len(tools))
            return True
        else:
            logger.error("❌ 零洩漏客戶端基本功能失敗",
                        error=result.get("error"))
            return False
            
    except Exception as e:
        logger.error("❌ 零洩漏客戶端測試異常", error=str(e), exc_info=True)
        return False


async def test_zero_leak_client_resource_management():
    """測試零洩漏客戶端資源管理"""
    logger.info("🔬 測試零洩漏客戶端資源管理")
    
    monitor = ResourceMonitor()
    monitor.capture_baseline()
    
    try:
        from src.services.mcp.zero_leak_mcp_client import get_zero_leak_manager
        
        # 執行多次會話創建和關閉
        session_count = 5
        successful_sessions = 0
        
        for i in range(session_count):
            logger.info(f"🔄 執行第 {i+1}/{session_count} 次會話測試")
            
            try:
                manager = await get_zero_leak_manager()
                
                # 測試查詢
                result = await manager.call_tool(
                    "postgres", 
                    "query", 
                    {"sql": "SELECT COUNT(*) FROM machines"}
                )
                
                if result.get("success"):
                    successful_sessions += 1
                    logger.info(f"✅ 會話 {i+1} 成功")
                else:
                    logger.warning(f"⚠️ 會話 {i+1} 查詢失敗")
                
                # 強制關閉客戶端測試資源清理
                await manager.close_client("postgres")
                
                # 測量資源狀態
                measurement = monitor.measure_current_state()
                logger.info(f"📊 會話 {i+1} 後資源狀態",
                           memory_diff_mb=f"{measurement['memory_diff_mb']:.2f}",
                           fd_diff=measurement['fd_diff'],
                           new_processes=len(measurement['new_processes']))
                
            except Exception as e:
                logger.error(f"❌ 會話 {i+1} 異常", error=str(e))
        
        # 最終資源檢查
        final_measurement = monitor.measure_current_state()
        leak_summary = monitor.get_leak_summary()
        
        logger.info("🏁 零洩漏客戶端資源管理測試完成",
                   successful_sessions=successful_sessions,
                   total_sessions=session_count,
                   success_rate=f"{successful_sessions/session_count*100:.1f}%")
        
        logger.info("📈 最終資源洩漏報告",
                   **leak_summary)
        
        # 評估結果
        is_zero_leak = not leak_summary.get("has_significant_leaks", True)
        session_success = successful_sessions >= session_count * 0.8
        
        return is_zero_leak and session_success
        
    except Exception as e:
        logger.error("❌ 零洩漏客戶端資源管理測試失敗", error=str(e), exc_info=True)
        return False


async def test_zero_leak_client_performance():
    """測試零洩漏客戶端性能"""
    logger.info("⚡ 測試零洩漏客戶端性能")
    
    try:
        from src.services.mcp.zero_leak_mcp_client import get_zero_leak_manager
        
        manager = await get_zero_leak_manager()
        
        # 單次查詢性能
        start_time = time.time()
        result = await manager.call_tool(
            "postgres", 
            "query", 
            {"sql": "SELECT * FROM employees LIMIT 5"}
        )
        single_query_time = time.time() - start_time
        
        logger.info("⏱️ 單次查詢性能",
                   time=f"{single_query_time:.3f}s",
                   success=result.get("success"))
        
        # 並發查詢性能
        concurrent_tasks = [
            manager.call_tool("postgres", "query", {"sql": "SELECT COUNT(*) FROM machines"}),
            manager.call_tool("postgres", "query", {"sql": "SELECT COUNT(*) FROM employees"}),
            manager.call_tool("postgres", "query", {"sql": "SELECT COUNT(*) FROM products"})
        ]
        
        start_time = time.time()
        concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        concurrent_time = time.time() - start_time
        
        successful_concurrent = sum(
            1 for r in concurrent_results 
            if not isinstance(r, Exception) and r.get("success")
        )
        
        logger.info("🔄 並發查詢性能",
                   task_count=len(concurrent_tasks),
                   total_time=f"{concurrent_time:.3f}s",
                   successful=successful_concurrent,
                   success_rate=f"{successful_concurrent/len(concurrent_tasks)*100:.1f}%")
        
        # 性能評估
        performance_ok = (
            single_query_time < 15.0 and  # 寬鬆一些，因為是零洩漏實作
            concurrent_time < 20.0 and
            successful_concurrent >= len(concurrent_tasks) * 0.8
        )
        
        return performance_ok
        
    except Exception as e:
        logger.error("❌ 零洩漏客戶端性能測試失敗", error=str(e), exc_info=True)
        return False


async def test_zero_leak_vs_original_comparison():
    """對比零洩漏客戶端與原始客戶端"""
    logger.info("⚖️ 零洩漏客戶端 vs 原始客戶端對比測試")
    
    comparison_results = {
        "zero_leak": {"functional": False, "has_leaks": True, "error_count": 0},
        "original": {"functional": False, "has_leaks": True, "error_count": 0}
    }
    
    # 測試零洩漏客戶端
    logger.info("🧪 測試零洩漏客戶端")
    try:
        from src.services.mcp.zero_leak_mcp_client import get_zero_leak_manager
        
        monitor = ResourceMonitor()
        monitor.capture_baseline()
        
        manager = await get_zero_leak_manager()
        result = await manager.call_tool("postgres", "query", {"sql": "SELECT COUNT(*) FROM machines"})
        
        comparison_results["zero_leak"]["functional"] = result.get("success", False)
        await manager.close_client("postgres")
        
        leak_summary = monitor.get_leak_summary()
        comparison_results["zero_leak"]["has_leaks"] = leak_summary.get("has_significant_leaks", True)
        
        logger.info("✅ 零洩漏客戶端測試完成",
                   functional=comparison_results["zero_leak"]["functional"],
                   has_leaks=comparison_results["zero_leak"]["has_leaks"])
        
    except Exception as e:
        comparison_results["zero_leak"]["error_count"] = 1
        logger.error("❌ 零洩漏客戶端測試失敗", error=str(e))
    
    # 測試原始客戶端
    logger.info("🧪 測試原始客戶端")
    try:
        from src.services.unified_mcp_client import get_unified_mcp_client
        
        monitor = ResourceMonitor()
        monitor.capture_baseline()
        
        client = await get_unified_mcp_client()
        result = await client.call_tool("postgres", "query", {"sql": "SELECT COUNT(*) FROM machines"})
        
        comparison_results["original"]["functional"] = result.get("success", False)
        
        # 等待一下讓資源洩漏顯現
        await asyncio.sleep(2)
        
        leak_summary = monitor.get_leak_summary()
        comparison_results["original"]["has_leaks"] = leak_summary.get("has_significant_leaks", True)
        
        logger.info("✅ 原始客戶端測試完成",
                   functional=comparison_results["original"]["functional"],
                   has_leaks=comparison_results["original"]["has_leaks"])
        
    except Exception as e:
        comparison_results["original"]["error_count"] = 1
        logger.error("❌ 原始客戶端測試失敗", error=str(e))
    
    # 對比結果
    logger.info("📊 零洩漏 vs 原始客戶端對比結果", **comparison_results)
    
    # 判斷零洩漏客戶端是否更好
    zero_leak_better = (
        comparison_results["zero_leak"]["functional"] and
        not comparison_results["zero_leak"]["has_leaks"] and
        comparison_results["zero_leak"]["error_count"] == 0
    )
    
    return zero_leak_better


async def test_zero_leak_stress_test():
    """零洩漏客戶端壓力測試"""
    logger.info("💪 零洩漏客戶端壓力測試")
    
    monitor = ResourceMonitor()
    monitor.capture_baseline()
    
    try:
        from src.services.mcp.zero_leak_mcp_client import get_zero_leak_manager
        
        manager = await get_zero_leak_manager()
        
        # 壓力測試參數
        stress_iterations = 10
        queries_per_iteration = 3
        total_queries = stress_iterations * queries_per_iteration
        
        successful_queries = 0
        error_count = 0
        
        logger.info("🔥 開始壓力測試",
                   iterations=stress_iterations,
                   queries_per_iteration=queries_per_iteration,
                   total_queries=total_queries)
        
        for iteration in range(stress_iterations):
            logger.info(f"🔄 壓力測試迭代 {iteration + 1}/{stress_iterations}")
            
            # 每次迭代執行多個查詢
            batch_tasks = []
            for _ in range(queries_per_iteration):
                task = manager.call_tool(
                    "postgres", 
                    "query", 
                    {"sql": "SELECT COUNT(*) FROM machines WHERE status = 'active'"}
                )
                batch_tasks.append(task)
            
            try:
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, Exception):
                        error_count += 1
                    elif result.get("success"):
                        successful_queries += 1
                    else:
                        error_count += 1
                
                # 測量當前資源狀態
                measurement = monitor.measure_current_state()
                
                if iteration % 3 == 0:  # 每3次迭代記錄一次資源狀態
                    logger.info(f"📊 迭代 {iteration + 1} 資源狀態",
                               memory_diff_mb=f"{measurement['memory_diff_mb']:.2f}",
                               fd_diff=measurement['fd_diff'],
                               new_processes=len(measurement['new_processes']))
                
            except Exception as e:
                logger.error(f"❌ 迭代 {iteration + 1} 失敗", error=str(e))
                error_count += queries_per_iteration
        
        # 最終清理和資源檢查
        await manager.close_all()
        await asyncio.sleep(2)  # 等待清理完成
        
        final_measurement = monitor.measure_current_state()
        leak_summary = monitor.get_leak_summary()
        
        success_rate = successful_queries / total_queries * 100
        error_rate = error_count / total_queries * 100
        
        logger.info("🏁 壓力測試完成",
                   total_queries=total_queries,
                   successful_queries=successful_queries,
                   error_count=error_count,
                   success_rate=f"{success_rate:.1f}%",
                   error_rate=f"{error_rate:.1f}%")
        
        logger.info("📈 壓力測試資源洩漏報告", **leak_summary)
        
        # 評估結果
        stress_test_passed = (
            success_rate >= 80.0 and
            not leak_summary.get("has_significant_leaks", True) and
            error_rate < 20.0
        )
        
        return stress_test_passed
        
    except Exception as e:
        logger.error("❌ 壓力測試失敗", error=str(e), exc_info=True)
        return False


async def main():
    """主測試函數"""
    logger.info("🚀 開始零洩漏 MCP 客戶端完整測試")
    
    test_results = {}
    
    # 執行所有測試
    tests = [
        ("基本功能測試", test_zero_leak_client_basic_functionality),
        ("資源管理測試", test_zero_leak_client_resource_management),
        ("性能測試", test_zero_leak_client_performance),
        ("對比測試", test_zero_leak_vs_original_comparison),
        ("壓力測試", test_zero_leak_stress_test),
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
        
        # 每個測試之間等待一下，讓資源狀態穩定
        await asyncio.sleep(1)
    
    # 輸出最終總結
    passed_tests = sum(test_results.values())
    total_tests = len(test_results)
    
    logger.info("🏁 零洩漏 MCP 客戶端測試總結",
               passed=passed_tests,
               total=total_tests,
               success_rate=f"{passed_tests/total_tests*100:.1f}%",
               results=test_results)
    
    if passed_tests == total_tests:
        logger.info("🎉 所有測試通過！零洩漏 MCP 客戶端實作成功")
        return True
    elif passed_tests >= total_tests * 0.8:
        logger.info("✅ 大部分測試通過，零洩漏 MCP 客戶端基本可用")
        return True
    else:
        logger.error("❌ 多項測試失敗，零洩漏 MCP 客戶端需要進一步修復")
        return False


if __name__ == "__main__":
    asyncio.run(main())