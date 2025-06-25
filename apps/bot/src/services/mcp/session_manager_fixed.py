#!/usr/bin/env python3
"""
修復版 MCP 會話管理器
解決 asyncio cancel scope 問題的根本方案
"""

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Optional

import structlog
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .security_validator import MCPSecurityValidator

logger = structlog.get_logger()


@dataclass
class MCPRequest:
    """MCP 請求數據類"""
    method: str
    params: Dict[str, Any]
    timeout: float = 30.0


class SingleTaskMCPSession:
    """
    單任務 MCP 會話管理器
    確保整個 stdio_client 生命週期在同一任務中
    """

    def __init__(self, server_name: str, server_params: StdioServerParameters):
        self.server_name = server_name
        self.server_params = server_params
        self._request_queue = asyncio.Queue()
        self._response_futures: Dict[str, asyncio.Future] = {}
        self._session_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        self._running = False

    async def start(self):
        """啟動會話任務"""
        if self._running:
            return

        self._running = True
        self._session_task = asyncio.create_task(self._session_loop())
        logger.info(f"✅ 單任務會話已啟動: {self.server_name}")

    async def stop(self):
        """停止會話任務"""
        if not self._running:
            return

        self._running = False
        self._shutdown_event.set()

        if self._session_task:
            try:
                await asyncio.wait_for(self._session_task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ 會話停止超時，強制取消: {self.server_name}")
                self._session_task.cancel()
                try:
                    await self._session_task
                except asyncio.CancelledError:
                    pass

        logger.info(f"✅ 單任務會話已停止: {self.server_name}")

    async def execute_request(self, method: str, params: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        """執行 MCP 請求"""
        if not self._running:
            raise RuntimeError(f"會話未啟動: {self.server_name}")

        request_id = f"{method}_{asyncio.get_event_loop().time()}"
        future = asyncio.Future()
        self._response_futures[request_id] = future

        request = MCPRequest(method=method, params=params, timeout=timeout)
        await self._request_queue.put((request_id, request))

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._response_futures.pop(request_id, None)
            raise asyncio.TimeoutError(f"MCP 請求超時: {method}")

    async def _session_loop(self):
        """會話主循環 - 確保整個 stdio_client 生命週期在此任務中"""
        try:
            # 關鍵：整個 stdio_client 生命週期在同一任務中
            async with stdio_client(self.server_params) as (read_stream, write_stream):
                session = ClientSession(read_stream, write_stream)
                await session.initialize()

                logger.info(f"🔗 MCP 會話已初始化: {self.server_name}")

                while self._running and not self._shutdown_event.is_set():
                    try:
                        # 等待請求或關閉信號
                        request_task = asyncio.create_task(self._request_queue.get())
                        shutdown_task = asyncio.create_task(self._shutdown_event.wait())

                        done, pending = await asyncio.wait(
                            [request_task, shutdown_task],
                            return_when=asyncio.FIRST_COMPLETED,
                            timeout=1.0  # 定期檢查
                        )

                        # 取消未完成的任務
                        for task in pending:
                            task.cancel()
                            try:
                                await task
                            except asyncio.CancelledError:
                                pass

                        if shutdown_task in done:
                            logger.info(f"🛑 收到關閉信號: {self.server_name}")
                            break

                        if request_task in done:
                            request_id, request = await request_task
                            await self._handle_request(session, request_id, request)

                    except asyncio.TimeoutError:
                        # 定期檢查，繼續循環
                        continue
                    except Exception as e:
                        logger.error(f"❌ 會話循環錯誤: {self.server_name}, {e}")
                        break

                logger.info(f"🔄 會話循環結束: {self.server_name}")

        except Exception as e:
            logger.error(f"❌ 會話創建失敗: {self.server_name}, {e}")
            # 通知所有等待的請求
            for future in self._response_futures.values():
                if not future.done():
                    future.set_exception(e)
        finally:
            # 清理所有待處理的響應
            for future in self._response_futures.values():
                if not future.done():
                    future.set_exception(RuntimeError("會話已關閉"))
            self._response_futures.clear()

    async def _handle_request(self, session: ClientSession, request_id: str, request: MCPRequest):
        """處理單個請求"""
        future = self._response_futures.get(request_id)
        if not future:
            logger.warning(f"⚠️ 找不到請求的 Future: {request_id}")
            return

        try:
            # 執行實際的 MCP 請求
            if request.method == "tools/list":
                result = await session.list_tools()
            elif request.method == "tools/call":
                tool_name = request.params.get("name")
                tool_params = request.params.get("arguments", {})
                result = await session.call_tool(tool_name, tool_params)
            else:
                raise ValueError(f"不支援的方法: {request.method}")

            # 設置結果
            response = {
                "success": True,
                "result": result
            }
            future.set_result(response)

        except Exception as e:
            logger.error(f"❌ 請求處理失敗: {request_id}, {e}")
            response = {
                "success": False,
                "error": str(e)
            }
            future.set_result(response)
        finally:
            self._response_futures.pop(request_id, None)


class FixedMCPSessionManager:
    """
    修復版 MCP 會話管理器
    使用單任務模式避免 cancel scope 問題
    """

    def __init__(self):
        self._sessions: Dict[str, SingleTaskMCPSession] = {}
        self._security_validator = MCPSecurityValidator()
        logger.info("🛡️ 修復版 MCP 會話管理器已初始化")

    async def get_session(self, server_name: str) -> SingleTaskMCPSession:
        """獲取或創建會話"""
        if server_name in self._sessions:
            return self._sessions[server_name]

        # 驗證服務器配置
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

        # 創建和啟動會話
        session = SingleTaskMCPSession(server_name, server_params)
        await session.start()

        self._sessions[server_name] = session
        logger.info(f"✅ 會話已創建: {server_name}")
        return session

    async def call_tool(self, server_name: str, tool_name: str, tool_params: Dict[str, Any]) -> Dict[str, Any]:
        """調用工具"""
        session = await self.get_session(server_name)
        return await session.execute_request("tools/call", {
            "name": tool_name,
            "arguments": tool_params
        })

    async def list_tools(self, server_name: str) -> Dict[str, Any]:
        """列出工具"""
        session = await self.get_session(server_name)
        return await session.execute_request("tools/list", {})

    async def close_session(self, server_name: str):
        """關閉指定會話"""
        session = self._sessions.pop(server_name, None)
        if session:
            await session.stop()
            logger.info(f"✅ 會話已關閉: {server_name}")

    async def close_all_sessions(self):
        """關閉所有會話"""
        session_names = list(self._sessions.keys())
        for server_name in session_names:
            await self.close_session(server_name)
        logger.info("✅ 所有會話已關閉")


# 全局實例
_fixed_manager: Optional[FixedMCPSessionManager] = None


async def get_fixed_mcp_manager() -> FixedMCPSessionManager:
    """獲取修復版 MCP 會話管理器"""
    global _fixed_manager
    if _fixed_manager is None:
        _fixed_manager = FixedMCPSessionManager()
    return _fixed_manager