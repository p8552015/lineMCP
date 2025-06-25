#!/usr/bin/env python3
"""
零洩漏 MCP 客戶端
徹底解決 cancel scope 和資源洩漏問題
"""

import asyncio
import os
import signal
import subprocess
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import anyio
import psutil
import structlog
from mcp import ClientSession, StdioServerParameters
from mcp.types import JSONRPCMessage
from mcp.shared.message import SessionMessage

from .security_validator import MCPSecurityValidator

logger = structlog.get_logger()


@dataclass
class ProcessInfo:
    """進程信息"""
    pid: int
    name: str
    status: str
    created_time: float


@dataclass
class ResourceTracker:
    """資源追蹤器"""
    initial_memory: float = 0.0
    initial_fds: int = 0
    initial_processes: List[ProcessInfo] = field(default_factory=list)
    
    def capture_initial_state(self):
        """捕獲初始資源狀態"""
        process = psutil.Process()
        self.initial_memory = process.memory_info().rss / 1024 / 1024
        self.initial_fds = process.num_fds()
        self.initial_processes = [
            ProcessInfo(
                pid=child.pid,
                name=child.name(),
                status=child.status(),
                created_time=child.create_time()
            )
            for child in process.children(recursive=True)
        ]
    
    def check_leaks(self) -> Dict[str, Any]:
        """檢查資源洩漏"""
        process = psutil.Process()
        current_memory = process.memory_info().rss / 1024 / 1024
        current_fds = process.num_fds()
        current_processes = [
            ProcessInfo(
                pid=child.pid,
                name=child.name(),
                status=child.status(),
                created_time=child.create_time()
            )
            for child in process.children(recursive=True)
        ]
        
        memory_leak = current_memory - self.initial_memory
        fd_leak = current_fds - self.initial_fds
        
        # 檢查新增的進程
        initial_pids = {p.pid for p in self.initial_processes}
        new_processes = [p for p in current_processes if p.pid not in initial_pids]
        
        return {
            "memory_leak_mb": memory_leak,
            "fd_leak": fd_leak,
            "new_processes": new_processes,
            "has_leaks": memory_leak > 1.0 or fd_leak > 0 or len(new_processes) > 0
        }


class ZeroLeakMCPClient:
    """
    零洩漏 MCP 客戶端
    確保所有資源都被正確清理
    """

    def __init__(self, server_name: str, server_params: StdioServerParameters):
        self.server_name = server_name
        self.server_params = server_params
        self._process: Optional[anyio.abc.Process] = None
        self._session: Optional[ClientSession] = None
        self._resource_tracker = ResourceTracker()
        self._closed = False
        
    async def __aenter__(self):
        """進入上下文"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        await self.close()
    
    async def connect(self):
        """建立連接"""
        if self._session:
            return
            
        self._resource_tracker.capture_initial_state()
        logger.info(f"🔌 開始建立零洩漏連接: {self.server_name}")
        
        try:
            # 直接使用 anyio 創建進程，避免 MCP SDK 的問題
            # 將 command 和 args 合併成完整的命令列表
            full_command = [self.server_params.command] + (self.server_params.args or [])
            
            # 準備環境變數，確保包含 Node.js 路徑
            env = dict(self.server_params.env or {})
            if "PATH" not in env:
                import os
                env["PATH"] = os.environ.get("PATH", "")
            
            # 如果是 npx 命令但找不到，嘗試使用完整路徑
            if self.server_params.command == "npx":
                import shutil
                npx_path = shutil.which("npx")
                if npx_path:
                    full_command[0] = npx_path
                    logger.info(f"🔧 使用完整 npx 路徑: {npx_path}")
                else:
                    # 嘗試常見的 Node.js 路徑
                    common_paths = [
                        "/Users/yen/.nvm/versions/node/v22.16.0/bin/npx",
                        "/usr/local/bin/npx",
                        "/opt/homebrew/bin/npx"
                    ]
                    for path in common_paths:
                        if os.path.exists(path):
                            full_command[0] = path
                            logger.info(f"🔧 使用預設 npx 路徑: {path}")
                            break
            
            self._process = await anyio.open_process(
                full_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=self.server_params.cwd,
            )
            
            logger.info(f"✅ 進程已創建: PID {self._process.pid}")
            
            # 直接創建流，不使用有問題的 stdio_client
            assert self._process.stdin is not None
            assert self._process.stdout is not None
            
            # 創建內存對象流來模擬 MCP 的接口
            read_send, read_recv = anyio.create_memory_object_stream(100)
            write_send, write_recv = anyio.create_memory_object_stream(100)
            
            # 啟動 I/O 任務
            self._io_task = asyncio.create_task(
                self._handle_io(read_send, write_recv)
            )
            
            # 創建會話
            self._session = ClientSession(read_recv, write_send)
            await self._session.initialize()
            
            logger.info(f"✅ 零洩漏連接已建立: {self.server_name}")
            
        except Exception as e:
            logger.error(f"❌ 連接建立失敗: {e}")
            await self._force_cleanup()
            raise
    
    async def _handle_io(self, read_send, write_recv):
        """處理 I/O 操作"""
        try:
            async with anyio.create_task_group() as tg:
                tg.start_soon(self._stdout_reader, read_send)
                tg.start_soon(self._stdin_writer, write_recv)
        except Exception as e:
            logger.error(f"❌ I/O 處理錯誤: {e}")
    
    async def _stdout_reader(self, read_send):
        """讀取標準輸出"""
        assert self._process and self._process.stdout
        
        try:
            async with read_send:
                buffer = ""
                
                # 直接從進程讀取字節流
                while True:
                    try:
                        chunk_bytes = await self._process.stdout.receive(1024)
                        if not chunk_bytes:
                            break
                        
                        chunk = chunk_bytes.decode('utf-8', errors='ignore')
                        lines = (buffer + chunk).split('\n')
                        buffer = lines.pop()
                        
                        for line in lines:
                            line = line.strip()
                            if line:
                                try:
                                    message = JSONRPCMessage.model_validate_json(line)
                                    session_message = SessionMessage(message)
                                    await read_send.send(session_message)
                                except Exception as e:
                                    logger.warning(f"⚠️ JSON 解析失敗: {line[:100]}..., {e}")
                                    
                    except anyio.EndOfStream:
                        logger.debug("📤 標準輸出流結束")
                        break
                    except anyio.ClosedResourceError:
                        logger.debug("📤 標準輸出資源已關閉")
                        break
                    except Exception as e:
                        logger.error(f"❌ 讀取標準輸出錯誤: {e}")
                        break
                        
        except anyio.ClosedResourceError:
            logger.debug("📤 標準輸出讀取器已關閉")
        except Exception as e:
            logger.error(f"❌ 標準輸出讀取錯誤: {e}")
    
    async def _stdin_writer(self, write_recv):
        """寫入標準輸入"""
        assert self._process and self._process.stdin
        
        try:
            async with write_recv:
                async for session_message in write_recv:
                    try:
                        json_data = session_message.message.model_dump_json(
                            by_alias=True, exclude_none=True
                        )
                        data_to_send = (json_data + '\n').encode('utf-8')
                        await self._process.stdin.send(data_to_send)
                        
                    except anyio.ClosedResourceError:
                        logger.debug("📤 標準輸入資源已關閉")
                        break
                    except Exception as e:
                        logger.error(f"❌ 標準輸入寫入錯誤: {e}")
                        break
                        
        except anyio.ClosedResourceError:
            logger.debug("📤 標準輸入寫入器已關閉")
        except Exception as e:
            logger.error(f"❌ 標準輸入寫入錯誤: {e}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """調用工具"""
        if not self._session:
            raise RuntimeError("會話未連接")
        
        try:
            result = await self._session.call_tool(tool_name, arguments)
            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            logger.error(f"❌ 工具調用失敗: {tool_name}, {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_tools(self) -> Dict[str, Any]:
        """列出工具"""
        if not self._session:
            raise RuntimeError("會話未連接")
        
        try:
            result = await self._session.list_tools()
            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            logger.error(f"❌ 工具列表獲取失敗: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def close(self):
        """關閉連接並強制清理所有資源"""
        if self._closed:
            return
            
        logger.info(f"🔄 開始關閉零洩漏客戶端: {self.server_name}")
        self._closed = True
        
        await self._force_cleanup()
        
        # 檢查資源洩漏
        leak_info = self._resource_tracker.check_leaks()
        if leak_info["has_leaks"]:
            logger.error(f"❌ 檢測到資源洩漏: {leak_info}")
        else:
            logger.info(f"✅ 無資源洩漏: {self.server_name}")
    
    async def _force_cleanup(self):
        """強制清理所有資源"""
        cleanup_tasks = []
        
        # 1. 關閉會話
        if self._session:
            cleanup_tasks.append(self._cleanup_session())
        
        # 2. 清理 I/O 任務
        if hasattr(self, '_io_task'):
            cleanup_tasks.append(self._cleanup_io_task())
        
        # 3. 強制終止進程
        if self._process:
            cleanup_tasks.append(self._cleanup_process())
        
        # 並行執行所有清理任務
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
    
    async def _cleanup_session(self):
        """清理會話"""
        try:
            if self._session:
                await asyncio.wait_for(self._session.close(), timeout=3.0)
                logger.debug("✅ 會話已關閉")
        except Exception as e:
            logger.warning(f"⚠️ 會話關閉失敗: {e}")
        finally:
            self._session = None
    
    async def _cleanup_io_task(self):
        """清理 I/O 任務"""
        try:
            if hasattr(self, '_io_task') and not self._io_task.done():
                self._io_task.cancel()
                await asyncio.wait_for(self._io_task, timeout=2.0)
                logger.debug("✅ I/O 任務已取消")
        except Exception as e:
            logger.warning(f"⚠️ I/O 任務清理失敗: {e}")
    
    async def _cleanup_process(self):
        """強制清理進程"""
        if not self._process:
            return
            
        try:
            pid = self._process.pid
            
            # 1. 嘗試優雅關閉
            if self._process.returncode is None:
                logger.debug(f"🔄 嘗試優雅終止進程 {pid}")
                self._process.terminate()
                
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=3.0)
                    logger.debug(f"✅ 進程 {pid} 已優雅終止")
                    return
                except asyncio.TimeoutError:
                    logger.warning(f"⚠️ 進程 {pid} 優雅終止超時")
            
            # 2. 強制終止
            if self._process.returncode is None:
                logger.warning(f"🔨 強制終止進程 {pid}")
                self._process.kill()
                
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=2.0)
                    logger.debug(f"✅ 進程 {pid} 已強制終止")
                except asyncio.TimeoutError:
                    logger.error(f"❌ 進程 {pid} 強制終止失敗")
            
            # 3. 系統級強制清理（最後手段）
            try:
                if psutil.pid_exists(pid):
                    logger.warning(f"🗡️ 使用系統級終止進程 {pid}")
                    process = psutil.Process(pid)
                    process.kill()
                    process.wait(timeout=1.0)
                    logger.debug(f"✅ 進程 {pid} 已系統級終止")
            except Exception as e:
                logger.error(f"❌ 系統級進程終止失敗: {e}")
        
        except Exception as e:
            logger.error(f"❌ 進程清理失敗: {e}")
        finally:
            self._process = None


class ZeroLeakMCPManager:
    """
    零洩漏 MCP 管理器
    管理多個零洩漏客戶端
    """
    
    def __init__(self):
        self._clients: Dict[str, ZeroLeakMCPClient] = {}
        self._security_validator = MCPSecurityValidator()
        logger.info("🛡️ 零洩漏 MCP 管理器已初始化")
    
    async def get_client(self, server_name: str) -> ZeroLeakMCPClient:
        """獲取或創建客戶端"""
        if server_name in self._clients:
            return self._clients[server_name]
        
        # 獲取服務器配置
        from src.config.mcp_config import get_server_config
        server_config = get_server_config(server_name)
        if not server_config:
            raise ValueError(f"找不到服務器配置: {server_name}")
        
        # 安全驗證
        is_valid = self._security_validator.validate_server_config(
            server_name, server_config.command, server_config.args
        )
        if not is_valid:
            raise ValueError(f"服務器配置驗證失敗: {server_name}")
        
        # 創建服務器參數
        server_params = StdioServerParameters(
            command=server_config.command,
            args=server_config.args,
            env=server_config.env,
            cwd=server_config.cwd
        )
        
        # 創建和連接客戶端
        client = ZeroLeakMCPClient(server_name, server_params)
        await client.connect()
        
        self._clients[server_name] = client
        logger.info(f"✅ 零洩漏客戶端已創建: {server_name}")
        return client
    
    async def call_tool(self, server_name: str, tool_name: str, 
                       arguments: Dict[str, Any]) -> Dict[str, Any]:
        """調用工具"""
        client = await self.get_client(server_name)
        return await client.call_tool(tool_name, arguments)
    
    async def list_tools(self, server_name: str) -> Dict[str, Any]:
        """列出工具"""
        client = await self.get_client(server_name)
        return await client.list_tools()
    
    async def close_client(self, server_name: str):
        """關閉指定客戶端"""
        client = self._clients.pop(server_name, None)
        if client:
            await client.close()
            logger.info(f"✅ 零洩漏客戶端已關閉: {server_name}")
    
    async def close_all(self):
        """關閉所有客戶端"""
        server_names = list(self._clients.keys())
        close_tasks = [self.close_client(name) for name in server_names]
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        logger.info("✅ 所有零洩漏客戶端已關閉")


# 全局實例
_zero_leak_manager: Optional[ZeroLeakMCPManager] = None


async def get_zero_leak_manager() -> ZeroLeakMCPManager:
    """獲取零洩漏管理器"""
    global _zero_leak_manager
    if _zero_leak_manager is None:
        _zero_leak_manager = ZeroLeakMCPManager()
    return _zero_leak_manager


@asynccontextmanager
async def zero_leak_mcp_client(server_name: str):
    """零洩漏 MCP 客戶端上下文管理器"""
    manager = await get_zero_leak_manager()
    client = await manager.get_client(server_name)
    try:
        yield client
    finally:
        # 不在這裡關閉，由管理器統一管理
        pass