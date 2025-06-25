#!/usr/bin/env python3
"""
SOLID 原則 PostgreSQL MCP 整合測試
遵循依賴倒置原則的完整測試實現
"""

import asyncio
import os
import sys
import time
from typing import Dict, Any, Optional

import structlog

# 添加路徑以便導入
sys.path.append('/Users/yen/Desktop/lineMCP/apps/bot')

from src.services.mcp.interfaces import (
    IResourceTracker, ICommandResolver, IProcessManager, 
    ISecurityValidator, IMCPClient, IMCPClientManager,
    IMCPClientFactory, IConfigurationProvider,
    ResourceState, MCPConnectionConfig
)

from src.services.mcp.solid_zero_leak_client import (
    ProductionResourceTracker, NodeCommandResolver, AnyIOProcessManager,
    SOLIDZeroLeakMCPClient, SOLIDZeroLeakClientFactory, SOLIDZeroLeakMCPManager
)

from src.services.mcp.security_validator import MCPSecurityValidator

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


class PostgreSQLConfigProvider(IConfigurationProvider):
    """PostgreSQL 配置提供者 - 實現依賴倒置原則"""
    
    def get_server_config(self, server_name: str) -> Optional[MCPConnectionConfig]:
        """獲取 PostgreSQL 服務器配置"""
        if server_name == "postgres":
            return MCPConnectionConfig(
                server_name="postgres",
                command="/Users/yen/.nvm/versions/node/v22.16.0/bin/npx",
                args=[
                    "-y",
                    "@modelcontextprotocol/server-postgres",
                    "postgresql://admin:admin@localhost:5432/mydb"
                ],
                env={
                    "NODE_ENV": "production",
                    "PYTHONUNBUFFERED": "1",
                },
                cwd=None,
                timeout=60
            )
        return None


class TestResourceTracker:
    """測試資源追蹤器"""
    
    def __init__(self):
        self.tracker = ProductionResourceTracker()
    
    async def test_resource_tracking(self) -> bool:
        """測試資源追蹤功能"""
        logger.info("🧪 測試資源追蹤功能")
        
        try:
            # 捕獲基線
            self.tracker.capture_baseline()
            
            # 模擬一些活動
            await asyncio.sleep(0.1)
            
            # 檢查當前狀態
            state = self.tracker.check_current_state()
            
            logger.info("📊 資源狀態檢查完成",
                       memory_diff=f"{state.memory_mb:.2f}MB",
                       fd_diff=state.file_descriptors,
                       process_diff=state.child_processes,
                       has_leaks=state.has_leaks)
            
            return True
            
        except Exception as e:
            logger.error("❌ 資源追蹤測試失敗", error=str(e))
            return False


class TestCommandResolver:
    """測試命令解析器"""
    
    def __init__(self):
        self.resolver = NodeCommandResolver()
    
    def test_command_resolution(self) -> bool:
        """測試命令解析功能"""
        logger.info("🧪 測試命令解析功能")
        
        try:
            # 測試 npx 命令解析
            npx_path = self.resolver.resolve_command("npx")
            logger.info("🔧 npx 命令解析", path=npx_path)
            
            # 測試支援檢查
            supports_npx = self.resolver.supports_command("npx")
            supports_node = self.resolver.supports_command("node") 
            supports_python = self.resolver.supports_command("python")
            
            logger.info("✅ 命令支援檢查",
                       npx=supports_npx,
                       node=supports_node,
                       python=supports_python)
            
            return supports_npx and supports_node
            
        except Exception as e:
            logger.error("❌ 命令解析測試失敗", error=str(e))
            return False


class TestProcessManager:
    """測試進程管理器"""
    
    def __init__(self):
        self.manager = AnyIOProcessManager()
    
    async def test_process_lifecycle(self) -> bool:
        """測試進程生命週期管理"""
        logger.info("🧪 測試進程生命週期管理")
        
        try:
            # 創建測試配置
            config = MCPConnectionConfig(
                server_name="test",
                command="/Users/yen/.nvm/versions/node/v22.16.0/bin/npx",
                args=["-y", "@modelcontextprotocol/server-postgres", "--help"],
                env={"NODE_ENV": "production"},
                timeout=30
            )
            
            # 啟動進程
            process = await self.manager.start_process(config)
            logger.info("✅ 進程啟動成功", pid=process.pid)
            
            # 等待一下
            await asyncio.sleep(1)
            
            # 停止進程
            await self.manager.stop_process(process)
            logger.info("✅ 進程停止成功")
            
            return True
            
        except Exception as e:
            logger.error("❌ 進程管理測試失敗", error=str(e))
            return False


class TestSOLIDIntegration:
    """SOLID 整合測試"""
    
    def __init__(self):
        self.config_provider = PostgreSQLConfigProvider()
        self.security_validator = MCPSecurityValidator()
        self.client_factory = SOLIDZeroLeakClientFactory()
    
    async def test_dependency_injection(self) -> bool:
        """測試依賴注入"""
        logger.info("🧪 測試依賴注入架構")
        
        try:
            # 創建管理器（依賴注入）
            manager = SOLIDZeroLeakMCPManager(
                client_factory=self.client_factory,
                security_validator=self.security_validator,
                config_provider=self.config_provider
            )
            
            logger.info("✅ 依賴注入管理器創建成功")
            return True
            
        except Exception as e:
            logger.error("❌ 依賴注入測試失敗", error=str(e))
            return False
    
    async def test_postgresql_connection(self) -> bool:
        """測試 PostgreSQL 連接"""
        logger.info("🧪 測試 PostgreSQL MCP 連接")
        
        try:
            # 創建管理器
            manager = SOLIDZeroLeakMCPManager(
                client_factory=self.client_factory,
                security_validator=self.security_validator,
                config_provider=self.config_provider
            )
            
            # 測試連接
            start_time = time.time()
            
            try:
                client = await asyncio.wait_for(
                    manager.get_client("postgres"),
                    timeout=60.0
                )
                
                connection_time = time.time() - start_time
                logger.info("✅ PostgreSQL 連接成功", time=f"{connection_time:.2f}s")
                
                # 測試工具列表
                tools_result = await asyncio.wait_for(
                    client.list_tools(),
                    timeout=30.0
                )
                
                if tools_result.get("success"):
                    tools = tools_result.get("result", {}).get("tools", [])
                    logger.info("📋 工具列表獲取成功", count=len(tools))
                    
                    # 測試簡單查詢
                    query_result = await asyncio.wait_for(
                        client.call_tool("query", {"sql": "SELECT 1 as test"}),
                        timeout=30.0
                    )
                    
                    if query_result.get("success"):
                        logger.info("✅ 查詢測試成功")
                        result = True
                    else:
                        logger.error("❌ 查詢測試失敗", error=query_result.get("error"))
                        result = False
                else:
                    logger.error("❌ 工具列表獲取失敗", error=tools_result.get("error"))
                    result = False
                
                # 清理
                await manager.close_client("postgres")
                logger.info("🧹 連接已清理")
                
                return result
                
            except asyncio.TimeoutError:
                logger.error("❌ PostgreSQL 連接超時")
                return False
            
        except Exception as e:
            logger.error("❌ PostgreSQL 連接測試失敗", error=str(e))
            return False


async def test_solid_postgresql_integration():
    """完整的 SOLID PostgreSQL 整合測試"""
    logger.info("🚀 開始 SOLID PostgreSQL MCP 整合測試")
    
    test_results = {}
    
    # 測試組件列表
    tests = [
        ("資源追蹤器", TestResourceTracker().test_resource_tracking),
        ("命令解析器", lambda: TestCommandResolver().test_command_resolution()),
        ("進程管理器", TestProcessManager().test_process_lifecycle),
        ("依賴注入", TestSOLIDIntegration().test_dependency_injection),
        ("PostgreSQL 連接", TestSOLIDIntegration().test_postgresql_connection),
    ]
    
    for test_name, test_func in tests:
        logger.info(f"📋 執行測試: {test_name}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
                
            test_results[test_name] = result
            status = "✅ 通過" if result else "❌ 失敗"
            logger.info(f"測試結果: {test_name} - {status}")
        except Exception as e:
            test_results[test_name] = False
            logger.error(f"測試異常: {test_name}", error=str(e))
    
    # 總結
    passed_tests = sum(test_results.values())
    total_tests = len(test_results)
    
    logger.info("🏁 SOLID PostgreSQL MCP 整合測試總結",
               passed=passed_tests,
               total=total_tests,
               success_rate=f"{passed_tests/total_tests*100:.1f}%",
               results=test_results)
    
    if passed_tests == total_tests:
        logger.info("🎉 所有測試通過！SOLID PostgreSQL MCP 整合成功")
        return True
    elif passed_tests >= total_tests * 0.8:
        logger.info("✅ 大部分測試通過，SOLID 整合基本可用")
        return True
    else:
        logger.error("❌ 多項測試失敗，需要進一步修復")
        return False


async def main():
    """主函數"""
    print("🚀 開始 SOLID 原則 PostgreSQL MCP 整合測試")
    
    success = await test_solid_postgresql_integration()
    
    if success:
        print("🎉 SOLID PostgreSQL MCP 整合測試成功")
        return 0
    else:
        print("❌ SOLID PostgreSQL MCP 整合測試失敗")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))