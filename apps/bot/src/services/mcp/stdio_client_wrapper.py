#!/usr/bin/env python3
"""
MCP STDIO 客戶端包裝器
解決 MCP Python SDK 的 asyncio cancel scope 錯誤
"""

import asyncio
import contextlib
import sys
from typing import Any, AsyncGenerator, Dict, Optional, Tuple

import anyio
import structlog
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters

logger = structlog.get_logger()


class SafeSTDIOClient:
    """
    安全的 STDIO 客戶端包裝器
    解決 MCP SDK 的 cancel scope 問題
    """

    def __init__(self):
        self._process: Optional[anyio.abc.Process] = None
        self._read_stream: Optional[MemoryObjectReceiveStream] = None
        self._write_stream: Optional[MemoryObjectSendStream] = None
        self._task_group: Optional[anyio.abc.TaskGroup] = None
        self._cancel_scope: Optional[anyio.CancelScope] = None
        self._session: Optional[ClientSession] = None
        self._closed = False

    async def __aenter__(self) -> Tuple[MemoryObjectReceiveStream, MemoryObjectSendStream]:
        """安全的進入上下文"""
        return await self.connect()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """安全的退出上下文"""
        await self.close()

    async def connect(self, server_params: StdioServerParameters) -> Tuple[MemoryObjectReceiveStream, MemoryObjectSendStream]:
        """
        建立 STDIO 連接
        
        Args:
            server_params: 服務器參數
            
        Returns:
            讀寫流的元組
        """
        try:
            # 檢查是否已連接
            if self._read_stream and self._write_stream:
                return self._read_stream, self._write_stream

            logger.info("🔌 開始建立 STDIO 連接")

            # 創建子進程
            self._process = await anyio.open_process(
                command=server_params.command,
                args=server_params.args,
                stdin=anyio.subprocess.PIPE,
                stdout=anyio.subprocess.PIPE,
                stderr=anyio.subprocess.PIPE,
                env=server_params.env,
                cwd=server_params.cwd,
            )

            # 使用原始 stdio_client 建立流
            from mcp.client.stdio import stdio_client
            
            # 直接使用 MCP 的 stdio_client 但在我們的任務上下文中
            stdio_context = stdio_client(server_params)
            self._read_stream, self._write_stream = await stdio_context.__aenter__()

            logger.info("✅ STDIO 連接已建立")
            return self._read_stream, self._write_stream

        except Exception as e:
            logger.error(f"❌ STDIO 連接失敗: {e}")
            await self._cleanup_process()
            raise

    async def create_session(self) -> ClientSession:
        """
        創建客戶端會話
        
        Returns:
            客戶端會話
        """
        if not self._read_stream or not self._write_stream:
            raise RuntimeError("STDIO 連接尚未建立")

        self._session = ClientSession(self._read_stream, self._write_stream)
        await self._session.initialize()
        
        logger.info("✅ MCP 會話已初始化")
        return self._session

    async def close(self):
        """安全地關閉連接"""
        if self._closed:
            return

        logger.info("🔄 開始關閉 STDIO 連接")
        self._closed = True

        # 關閉會話
        if self._session:
            try:
                # 使用 asyncio.wait_for 避免無限等待
                await asyncio.wait_for(self._session.close(), timeout=5.0)
                logger.info("✅ MCP 會話已關閉")
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"⚠️ 會話關閉超時或失敗: {e}")
            finally:
                self._session = None

        # 關閉流
        await self._cleanup_streams()

        # 關閉進程
        await self._cleanup_process()

        logger.info("✅ STDIO 連接已完全關閉")

    async def _cleanup_streams(self):
        """清理流資源"""
        if self._write_stream:
            try:
                await self._write_stream.aclose()
            except Exception as e:
                logger.warning(f"⚠️ 寫流關閉失敗: {e}")
            finally:
                self._write_stream = None

        if self._read_stream:
            try:
                await self._read_stream.aclose()
            except Exception as e:
                logger.warning(f"⚠️ 讀流關閉失敗: {e}")
            finally:
                self._read_stream = None

    async def _cleanup_process(self):
        """清理進程資源"""
        if not self._process:
            return

        try:
            # 嘗試優雅關閉
            if self._process.returncode is None:
                self._process.terminate()
                
                # 等待進程結束，最多 3 秒
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=3.0)
                    logger.info("✅ 進程已優雅關閉")
                except asyncio.TimeoutError:
                    logger.warning("⚠️ 進程關閉超時，強制終止")
                    self._process.kill()
                    
                    # 再等待 1 秒
                    try:
                        await asyncio.wait_for(self._process.wait(), timeout=1.0)
                    except asyncio.TimeoutError:
                        logger.error("❌ 進程強制終止失敗")

        except Exception as e:
            logger.warning(f"⚠️ 進程清理失敗: {e}")
        finally:
            self._process = None


class FixedStdioClientManager:
    """
    修復版本的 STDIO 客戶端管理器
    避免 cancel scope 問題
    """

    def __init__(self):
        self._clients: Dict[str, SafeSTDIOClient] = {}
        self._sessions: Dict[str, ClientSession] = {}

    async def get_session(self, server_name: str, server_params: StdioServerParameters) -> ClientSession:
        """
        獲取或創建會話
        
        Args:
            server_name: 服務器名稱
            server_params: 服務器參數
            
        Returns:
            客戶端會話
        """
        # 檢查是否已有會話
        if server_name in self._sessions:
            return self._sessions[server_name]

        # 創建新的客戶端
        client = SafeSTDIOClient()
        
        try:
            # 建立連接
            read_stream, write_stream = await client.connect(server_params)
            
            # 創建會話
            session = await client.create_session()
            
            # 保存引用
            self._clients[server_name] = client
            self._sessions[server_name] = session
            
            logger.info(f"✅ 會話已創建: {server_name}")
            return session
            
        except Exception as e:
            # 清理失敗的客戶端
            await client.close()
            logger.error(f"❌ 會話創建失敗: {server_name}, {e}")
            raise

    async def close_session(self, server_name: str):
        """關閉指定會話"""
        client = self._clients.pop(server_name, None)
        session = self._sessions.pop(server_name, None)
        
        if client:
            await client.close()
            logger.info(f"✅ 會話已關閉: {server_name}")

    async def close_all(self):
        """關閉所有會話"""
        server_names = list(self._clients.keys())
        
        # 並行關閉所有會話
        close_tasks = [self.close_session(name) for name in server_names]
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        logger.info("✅ 所有會話已關閉")


# 全局實例
_stdio_manager: Optional[FixedStdioClientManager] = None


async def get_fixed_stdio_manager() -> FixedStdioClientManager:
    """獲取修復版本的 STDIO 管理器"""
    global _stdio_manager
    if _stdio_manager is None:
        _stdio_manager = FixedStdioClientManager()
    return _stdio_manager


@contextlib.asynccontextmanager
async def safe_stdio_client(server_params: StdioServerParameters) -> AsyncGenerator[Tuple[BufferedByteReceiveStream, BufferedByteSendStream], None]:
    """
    安全的 stdio_client 替代實作
    避免 cancel scope 問題
    """
    client = SafeSTDIOClient()
    try:
        streams = await client.connect(server_params)
        yield streams
    finally:
        await client.close()