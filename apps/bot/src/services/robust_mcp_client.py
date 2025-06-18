"""
強健的MCP客戶端 - 解決STDIO連接問題
基於搜尋結果的最佳實踐實作
"""

import asyncio
import structlog
import subprocess
import sys
import os
from typing import Dict, Any, List, Optional
from contextlib import AsyncExitStack
import signal

logger = structlog.get_logger()


class RobustMCPClient:
    """
    強健的MCP客戶端 - 解決常見的STDIO連接問題
    """
    
    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.session = None
        self.process = None
        self.connection_timeout = 10.0  # 增加連接超時
        self.call_timeout = 15.0  # 增加調用超時
        
        # SQLite MCP Server 配置
        self.server_config = {
            'command': 'python3',
            'args': ['/Users/yen/Desktop/lineMCP/apps/servers/src/sqlite/src/mcp_server_sqlite/server.py', 
                    '/Users/yen/Desktop/lineMCP/apps/servers/src/sqlite/test.db'],
            'cwd': '/Users/yen/Desktop/lineMCP/apps/servers/src/sqlite',
            'env': {
                'PYTHONPATH': '/Users/yen/Desktop/lineMCP/apps/servers/src/sqlite/src',
                'PYTHONUNBUFFERED': '1',
                'PYTHONUTF8': '1'  # 確保UTF-8編碼
            }
        }
        
        logger.info("✅ 強健的MCP客戶端初始化完成")
    
    async def connect(self) -> bool:
        """建立MCP連接，使用多種策略避免掛起"""
        try:
            logger.info("🔗 嘗試建立強健的MCP連接")
            
            # 策略1: 先測試server是否能啟動
            if not await self._test_server_startup():
                logger.error("❌ MCP Server啟動測試失敗")
                return False
            
            # 策略2: 使用subprocess手動管理server生命週期
            if await self._connect_with_manual_process():
                logger.info("✅ 手動process連接成功")
                return True
            
            # 策略3: 回退到標準STDIO連接（短超時）
            if await self._connect_with_stdio():
                logger.info("✅ STDIO連接成功")
                return True
            
            logger.error("❌ 所有連接策略均失敗")
            return False
            
        except Exception as e:
            logger.error(f"❌ MCP連接失敗: {e}", exc_info=True)
            return False
    
    async def _test_server_startup(self) -> bool:
        """測試MCP Server是否能正常啟動"""
        try:
            logger.info("🧪 測試MCP Server啟動")
            
            # 使用短超時測試server啟動
            process = await asyncio.create_subprocess_exec(
                self.server_config['command'],
                *self.server_config['args'],
                cwd=self.server_config['cwd'],
                env={**os.environ, **self.server_config['env']},
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE
            )
            
            # 等待2秒看是否立即崩潰
            try:
                await asyncio.wait_for(process.wait(), timeout=2.0)
                # 如果process在2秒內結束，說明有問題
                stdout, stderr = await process.communicate()
                logger.error(f"❌ Server快速退出: stdout={stdout.decode()}, stderr={stderr.decode()}")
                return False
            except asyncio.TimeoutError:
                # 超時是好的，說明server正在運行
                logger.info("✅ Server啟動測試通過")
                process.terminate()
                await process.wait()
                return True
                
        except Exception as e:
            logger.error(f"❌ Server啟動測試失敗: {e}")
            return False
    
    async def _connect_with_manual_process(self) -> bool:
        """手動管理subprocess的連接方式"""
        try:
            from mcp import ClientSession
            
            logger.info("🔧 嘗試手動process連接")
            
            # 創建subprocess
            self.process = await asyncio.create_subprocess_exec(
                self.server_config['command'],
                *self.server_config['args'],
                cwd=self.server_config['cwd'],
                env={**os.environ, **self.server_config['env']},
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE
            )
            
            # 創建session
            self.session = ClientSession(self.process.stdout, self.process.stdin)
            
            # 使用超時初始化
            await asyncio.wait_for(
                self.session.initialize(),
                timeout=self.connection_timeout
            )
            
            logger.info("✅ 手動process連接建立成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 手動process連接失敗: {e}")
            await self._cleanup_manual_process()
            return False
    
    async def _connect_with_stdio(self) -> bool:
        """標準STDIO連接方式（短超時）"""
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            
            logger.info("📡 嘗試標準STDIO連接")
            
            server_params = StdioServerParameters(
                command=self.server_config['command'],
                args=self.server_config['args'],
                cwd=self.server_config.get('cwd'),
                env=self.server_config.get('env')
            )
            
            # 使用短超時建立連接
            stdio_transport = await asyncio.wait_for(
                self.exit_stack.enter_async_context(stdio_client(server_params)),
                timeout=self.connection_timeout
            )
            
            read, write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            
            # 初始化session
            await asyncio.wait_for(
                self.session.initialize(),
                timeout=self.connection_timeout
            )
            
            logger.info("✅ 標準STDIO連接建立成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 標準STDIO連接失敗: {e}")
            return False
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """強健的工具調用"""
        if not self.session:
            return {"success": False, "error": "未建立連接"}
        
        try:
            # 檢查process是否仍在運行（如果使用手動process）
            if self.process and self.process.returncode is not None:
                logger.error("❌ Server process已終止")
                return {"success": False, "error": "Server process已終止"}
            
            logger.info(f"🛠️ 調用工具: {tool_name}")
            
            # 使用超時調用
            result = await asyncio.wait_for(
                self.session.call_tool(tool_name, parameters),
                timeout=self.call_timeout
            )
            
            if hasattr(result, 'content'):
                logger.info(f"✅ 工具調用成功: {tool_name}")
                return {
                    "success": True,
                    "data": result.content,
                    "is_error": getattr(result, 'isError', False)
                }
            else:
                return {
                    "success": True,
                    "data": result,
                    "is_error": False
                }
                
        except asyncio.TimeoutError:
            logger.error(f"⏰ 工具調用超時: {tool_name}")
            return {"success": False, "error": f"工具調用超時: {tool_name}"}
        except Exception as e:
            logger.error(f"❌ 工具調用失敗: {tool_name} - {e}")
            return {"success": False, "error": str(e)}
    
    async def list_tools(self) -> List[str]:
        """列出可用工具"""
        if not self.session:
            return []
        
        try:
            result = await asyncio.wait_for(
                self.session.list_tools(),
                timeout=self.call_timeout
            )
            return [tool.name for tool in result.tools]
        except Exception as e:
            logger.error(f"❌ 列出工具失敗: {e}")
            return []
    
    async def _cleanup_manual_process(self):
        """清理手動管理的process"""
        if self.process:
            try:
                if self.process.returncode is None:
                    self.process.terminate()
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except Exception as e:
                logger.warning(f"⚠️ 清理process時發生錯誤: {e}")
                if self.process.returncode is None:
                    self.process.kill()
            finally:
                self.process = None
    
    async def close(self):
        """關閉連接"""
        try:
            if self.session:
                await self.session.close()
                self.session = None
            
            await self._cleanup_manual_process()
            await self.exit_stack.aclose()
            
            logger.info("✅ MCP連接已關閉")
        except Exception as e:
            logger.warning(f"⚠️ 關閉連接時發生錯誤: {e}")


# 單例實例
_robust_mcp_client = None

async def get_robust_mcp_client() -> RobustMCPClient:
    """獲取強健的MCP客戶端實例"""
    global _robust_mcp_client
    if _robust_mcp_client is None:
        _robust_mcp_client = RobustMCPClient()
        # 嘗試連接
        if not await _robust_mcp_client.connect():
            logger.error("❌ 無法建立MCP連接")
    return _robust_mcp_client