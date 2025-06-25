#!/usr/bin/env python3
"""
遵循 SOLID 原則的零洩漏 MCP 客戶端
重構版本，解決原版本的 SOLID 原則違反問題
"""

import asyncio
import os
import shutil
import subprocess
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import anyio
import psutil
import structlog
from mcp import ClientSession, StdioServerParameters

from .interfaces import (
    IResourceTracker, ICommandResolver, IProcessManager, 
    ISecurityValidator, IMCPClient, IMCPClientManager,
    IMCPClientFactory, IConfigurationProvider,
    ResourceState, MCPConnectionConfig
)

logger = structlog.get_logger()


class ProductionResourceTracker(IResourceTracker):
    """生產級資源追蹤器 - 單一職責：監控資源狀態"""
    
    def __init__(self):
        self._baseline_memory = 0.0
        self._baseline_fds = 0
        self._baseline_processes = 0
    
    def capture_baseline(self) -> None:
        """捕獲基線資源狀態"""
        process = psutil.Process()
        self._baseline_memory = process.memory_info().rss / 1024 / 1024
        self._baseline_fds = process.num_fds()
        self._baseline_processes = len(process.children(recursive=True))
        
        logger.debug("📊 基線資源狀態已捕獲",
                    memory_mb=f"{self._baseline_memory:.2f}",
                    file_descriptors=self._baseline_fds,
                    child_processes=self._baseline_processes)
    
    def check_current_state(self) -> ResourceState:
        """檢查當前資源狀態"""
        process = psutil.Process()
        current_memory = process.memory_info().rss / 1024 / 1024
        current_fds = process.num_fds()
        current_processes = len(process.children(recursive=True))
        
        memory_diff = current_memory - self._baseline_memory
        fd_diff = current_fds - self._baseline_fds
        process_diff = current_processes - self._baseline_processes
        
        has_leaks = memory_diff > 2.0 or fd_diff > 0 or process_diff > 0
        
        return ResourceState(
            memory_mb=memory_diff,
            file_descriptors=fd_diff,
            child_processes=process_diff,
            has_leaks=has_leaks
        )
    
    def has_leaks(self) -> bool:
        """檢查是否有洩漏"""
        return self.check_current_state().has_leaks


class NodeCommandResolver(ICommandResolver):
    """Node.js 命令解析器 - 單一職責：解析 Node.js 相關命令路徑"""
    
    def __init__(self):
        self._common_paths = [
            "/Users/yen/.nvm/versions/node/v22.16.0/bin",
            "/usr/local/bin",
            "/opt/homebrew/bin"
        ]
    
    def resolve_command(self, command: str) -> str:
        """解析命令的完整路徑"""
        if not self.supports_command(command):
            return command
        
        # 首先嘗試系統路徑
        system_path = shutil.which(command)
        if system_path:
            logger.debug(f"🔧 找到系統命令: {system_path}")
            return system_path
        
        # 嘗試常見路徑
        for base_path in self._common_paths:
            full_path = os.path.join(base_path, command)
            if os.path.exists(full_path):
                logger.debug(f"🔧 找到預設命令: {full_path}")
                return full_path
        
        logger.warning(f"⚠️ 無法解析命令路徑: {command}")
        return command
    
    def supports_command(self, command: str) -> bool:
        """檢查是否支援此命令"""
        return command in ["node", "npm", "npx", "yarn"]


class AnyIOProcessManager(IProcessManager):
    """AnyIO 進程管理器 - 單一職責：管理 AnyIO 進程生命週期"""
    
    async def start_process(self, config: MCPConnectionConfig) -> anyio.abc.Process:
        """啟動進程"""
        full_command = [config.command] + config.args
        
        # 準備環境變數
        env = dict(config.env)
        if "PATH" not in env:
            env["PATH"] = os.environ.get("PATH", "")
        
        logger.info(f"🚀 啟動進程: {' '.join(full_command)}")
        
        process = await anyio.open_process(
            full_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=config.cwd,
        )
        
        logger.info(f"✅ 進程已啟動: PID {process.pid}")
        return process
    
    async def stop_process(self, process: anyio.abc.Process) -> None:
        """停止進程"""
        if process.returncode is not None:
            return
        
        pid = process.pid
        logger.debug(f"🔄 嘗試優雅終止進程 {pid}")
        
        try:
            process.terminate()
            await asyncio.wait_for(process.wait(), timeout=3.0)
            logger.debug(f"✅ 進程 {pid} 已優雅終止")
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ 進程 {pid} 優雅終止超時，將強制終止")
            await self.force_cleanup(process)
    
    async def force_cleanup(self, process: anyio.abc.Process) -> None:
        """強制清理進程"""
        if process.returncode is not None:
            return
        
        pid = process.pid
        
        try:
            # 強制終止
            logger.warning(f"🔨 強制終止進程 {pid}")
            process.kill()
            
            try:
                await asyncio.wait_for(process.wait(), timeout=2.0)
                logger.debug(f"✅ 進程 {pid} 已強制終止")
                return
            except asyncio.TimeoutError:
                logger.error(f"❌ 進程 {pid} 強制終止失敗")
            
            # 系統級強制清理（最後手段）
            if psutil.pid_exists(pid):
                logger.warning(f"🗡️ 使用系統級終止進程 {pid}")
                sys_process = psutil.Process(pid)
                sys_process.kill()
                sys_process.wait(timeout=1.0)
                logger.debug(f"✅ 進程 {pid} 已系統級終止")
                
        except Exception as e:
            logger.error(f"❌ 進程清理失敗: {e}")


class SOLIDZeroLeakMCPClient(IMCPClient):
    """
    遵循 SOLID 原則的零洩漏 MCP 客戶端
    單一職責：管理 MCP 客戶端連接和通信
    """
    
    def __init__(
        self,
        config: MCPConnectionConfig,
        resource_tracker: IResourceTracker,
        process_manager: IProcessManager,
        command_resolver: ICommandResolver
    ):
        self._config = config
        self._resource_tracker = resource_tracker
        self._process_manager = process_manager
        self._command_resolver = command_resolver
        
        self._process: Optional[anyio.abc.Process] = None
        self._session: Optional[ClientSession] = None
        self._io_task: Optional[asyncio.Task] = None
        self._closed = False
    
    async def connect(self) -> None:
        """建立連接"""
        if self._session:
            return
        
        self._resource_tracker.capture_baseline()
        logger.info(f"🔌 開始建立零洩漏連接: {self._config.server_name}")
        
        try:
            # 解析命令路徑
            resolved_command = self._command_resolver.resolve_command(self._config.command)
            connection_config = MCPConnectionConfig(
                server_name=self._config.server_name,
                command=resolved_command,
                args=self._config.args,
                env=self._config.env,
                cwd=self._config.cwd,
                timeout=self._config.timeout
            )
            
            # 啟動進程
            self._process = await self._process_manager.start_process(connection_config)
            
            # 設置 I/O 流
            await self._setup_io_streams()
            
            logger.info(f"✅ 零洩漏連接已建立: {self._config.server_name}")
            
        except Exception as e:
            logger.error(f"❌ 連接建立失敗: {e}")
            await self._cleanup()
            raise
    
    async def _setup_io_streams(self) -> None:
        """設置 I/O 流 - 私有方法，單一職責"""
        if not self._process:
            raise RuntimeError("進程未啟動")
        
        # 創建內存對象流
        read_send, read_recv = anyio.create_memory_object_stream(100)
        write_send, write_recv = anyio.create_memory_object_stream(100)
        
        # 啟動 I/O 任務
        self._io_task = asyncio.create_task(
            self._handle_io(read_send, write_recv)
        )
        
        # 創建會話
        self._session = ClientSession(read_recv, write_send)
        await self._session.initialize()
    
    async def _handle_io(self, read_send, write_recv) -> None:
        """處理 I/O 操作 - 私有方法，單一職責"""
        try:
            async with anyio.create_task_group() as tg:
                tg.start_soon(self._stdout_reader, read_send)
                tg.start_soon(self._stdin_writer, write_recv)
        except Exception as e:
            logger.error(f"❌ I/O 處理錯誤: {e}")
    
    async def _stdout_reader(self, read_send) -> None:
        """讀取標準輸出 - 私有方法，單一職責"""
        if not self._process or not self._process.stdout:
            return
        
        try:
            async with read_send:
                buffer = ""
                
                while True:
                    try:
                        chunk_bytes = await self._process.stdout.receive(1024)
                        if not chunk_bytes:
                            break
                        
                        chunk = chunk_bytes.decode('utf-8', errors='ignore')
                        lines = (buffer + chunk).split('\n')
                        buffer = lines.pop()
                        
                        for line in lines:
                            await self._process_json_line(line.strip(), read_send)
                            
                    except anyio.EndOfStream:
                        logger.debug("📤 標準輸出流結束")
                        break
                    except anyio.ClosedResourceError:
                        logger.debug("📤 標準輸出資源已關閉")
                        break
                    except Exception as e:
                        logger.error(f"❌ 讀取標準輸出錯誤: {e}")
                        break
                        
        except Exception as e:
            logger.error(f"❌ 標準輸出讀取錯誤: {e}")
    
    async def _process_json_line(self, line: str, read_send) -> None:
        """處理 JSON 行 - 私有方法，單一職責"""
        if not line:
            return
        
        try:
            from mcp.types import JSONRPCMessage
            from mcp.shared.message import SessionMessage
            
            message = JSONRPCMessage.model_validate_json(line)
            session_message = SessionMessage(message)
            await read_send.send(session_message)
        except Exception as e:
            logger.warning(f"⚠️ JSON 解析失敗: {line[:100]}..., {e}")
    
    async def _stdin_writer(self, write_recv) -> None:
        """寫入標準輸入 - 私有方法，單一職責"""
        if not self._process or not self._process.stdin:
            return
        
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
                        
        except Exception as e:
            logger.error(f"❌ 標準輸入寫入錯誤: {e}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """調用工具"""
        if not self._session:
            raise RuntimeError("會話未連接")
        
        try:
            result = await self._session.call_tool(tool_name, arguments)
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"❌ 工具調用失敗: {tool_name}, {e}")
            return {"success": False, "error": str(e)}
    
    async def list_tools(self) -> Dict[str, Any]:
        """列出工具"""
        if not self._session:
            raise RuntimeError("會話未連接")
        
        try:
            result = await self._session.list_tools()
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"❌ 工具列表獲取失敗: {e}")
            return {"success": False, "error": str(e)}
    
    async def close(self) -> None:
        """關閉連接"""
        if self._closed:
            return
        
        logger.info(f"🔄 開始關閉零洩漏客戶端: {self._config.server_name}")
        self._closed = True
        
        await self._cleanup()
        
        # 檢查資源洩漏
        if self._resource_tracker.has_leaks():
            state = self._resource_tracker.check_current_state()
            logger.warning(f"⚠️ 檢測到資源洩漏: {state}")
        else:
            logger.info(f"✅ 無資源洩漏: {self._config.server_name}")
    
    async def _cleanup(self) -> None:
        """清理資源 - 私有方法，單一職責"""
        cleanup_tasks = []
        
        # 1. 關閉會話
        if self._session:
            cleanup_tasks.append(self._cleanup_session())
        
        # 2. 清理 I/O 任務
        if self._io_task:
            cleanup_tasks.append(self._cleanup_io_task())
        
        # 3. 停止進程
        if self._process:
            cleanup_tasks.append(self._process_manager.stop_process(self._process))
        
        # 並行執行所有清理任務
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
    
    async def _cleanup_session(self) -> None:
        """清理會話 - 私有方法，單一職責"""
        try:
            if self._session:
                await asyncio.wait_for(self._session.close(), timeout=3.0)
                logger.debug("✅ 會話已關閉")
        except Exception as e:
            logger.warning(f"⚠️ 會話關閉失敗: {e}")
        finally:
            self._session = None
    
    async def _cleanup_io_task(self) -> None:
        """清理 I/O 任務 - 私有方法，單一職責"""
        try:
            if self._io_task and not self._io_task.done():
                self._io_task.cancel()
                await asyncio.wait_for(self._io_task, timeout=2.0)
                logger.debug("✅ I/O 任務已取消")
        except Exception as e:
            logger.warning(f"⚠️ I/O 任務清理失敗: {e}")
        finally:
            self._io_task = None


class SOLIDZeroLeakClientFactory(IMCPClientFactory):
    """
    遵循 SOLID 原則的零洩漏客戶端工廠
    單一職責：創建零洩漏客戶端
    """
    
    def create_client(
        self, 
        config: MCPConnectionConfig,
        resource_tracker: IResourceTracker,
        process_manager: IProcessManager,
        security_validator: ISecurityValidator
    ) -> IMCPClient:
        """創建 MCP 客戶端"""
        # 安全驗證
        if not security_validator.validate_config(config):
            raise ValueError(f"配置驗證失敗: {config.server_name}")
        
        # 創建命令解析器
        command_resolver = NodeCommandResolver()
        
        # 創建客戶端
        return SOLIDZeroLeakMCPClient(
            config=config,
            resource_tracker=resource_tracker,
            process_manager=process_manager,
            command_resolver=command_resolver
        )


class SOLIDZeroLeakMCPManager(IMCPClientManager):
    """
    遵循 SOLID 原則的零洩漏 MCP 管理器
    單一職責：管理多個零洩漏客戶端
    """
    
    def __init__(
        self,
        client_factory: IMCPClientFactory,
        security_validator: ISecurityValidator,
        config_provider: IConfigurationProvider
    ):
        self._client_factory = client_factory
        self._security_validator = security_validator
        self._config_provider = config_provider
        self._clients: Dict[str, IMCPClient] = {}
        self._resource_tracker = ProductionResourceTracker()
        self._process_manager = AnyIOProcessManager()
        
        logger.info("🛡️ SOLID 零洩漏 MCP 管理器已初始化")
    
    async def get_client(self, server_name: str) -> IMCPClient:
        """獲取客戶端"""
        if server_name in self._clients:
            return self._clients[server_name]
        
        # 獲取配置
        config = self._config_provider.get_server_config(server_name)
        if not config:
            raise ValueError(f"找不到服務器配置: {server_name}")
        
        # 創建客戶端
        client = self._client_factory.create_client(
            config=config,
            resource_tracker=self._resource_tracker,
            process_manager=self._process_manager,
            security_validator=self._security_validator
        )
        
        # 連接
        await client.connect()
        
        self._clients[server_name] = client
        logger.info(f"✅ SOLID 零洩漏客戶端已創建: {server_name}")
        return client
    
    async def close_client(self, server_name: str) -> None:
        """關閉指定客戶端"""
        client = self._clients.pop(server_name, None)
        if client:
            await client.close()
            logger.info(f"✅ SOLID 零洩漏客戶端已關閉: {server_name}")
    
    async def close_all(self) -> None:
        """關閉所有客戶端"""
        server_names = list(self._clients.keys())
        close_tasks = [self.close_client(name) for name in server_names]
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        logger.info("✅ 所有 SOLID 零洩漏客戶端已關閉")