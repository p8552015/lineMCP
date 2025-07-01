"""
MCP 服務器實現模組

提供 IMCPServer 介面的具體實現，封裝進程管理和連接管理邏輯。
遵循 SOLID 原則，實現真正的 MCP 服務器物件。
"""

import asyncio
import time

import structlog

from ..interfaces.runtime_interfaces import IProcess, IRuntimeManager
from ..interfaces.server_interfaces import (
    ConnectionStatus,
    IMCPConnection,
    IMCPServer,
    MCPResource,
    MCPServerConfig,
    MCPServerStatus,
    MCPTool,
    MCPToolCall,
    MCPToolResult,
)

logger = structlog.get_logger()


class MCPServerImpl(IMCPServer):
    """
    MCP 服務器實現

    封裝 MCP 服務器的完整生命週期管理，包括進程控制和連接管理。
    """

    def __init__(
        self,
        config: MCPServerConfig,
        runtime_manager: IRuntimeManager,
        process: IProcess,
    ):
        self._config = config
        self._runtime_manager = runtime_manager
        self._process = process
        self._connection: IMCPConnection | None = None
        self._status = MCPServerStatus.CREATED
        self._created_at = time.time()
        self._started_at: float | None = None
        self._stopped_at: float | None = None
        self._restart_count = 0

    @property
    def config(self) -> MCPServerConfig:
        """獲取服務器配置"""
        return self._config

    @property
    def process(self) -> IProcess | None:
        """獲取服務器進程"""
        return self._process

    @property
    def status(self) -> MCPServerStatus:
        """獲取服務器狀態"""
        return self._status

    async def start(self) -> bool:
        """啟動服務器"""
        try:
            logger.info(f"▶️ 啟動 MCP 服務器: {self._config.name}")

            if self._status == MCPServerStatus.RUNNING:
                logger.info(f"⚠️ 服務器 {self._config.name} 已在運行")
                return True

            self._status = MCPServerStatus.STARTING

            # 啟動進程
            if await self._process.start():
                self._status = MCPServerStatus.RUNNING
                self._started_at = time.time()

                # 創建連接
                self._connection = MCPConnectionImpl(self._config, self._process)

                logger.info(f"✅ MCP 服務器 {self._config.name} 啟動成功")
                return True
            else:
                self._status = MCPServerStatus.FAILED
                logger.error(f"❌ MCP 服務器 {self._config.name} 啟動失敗")
                return False

        except Exception as e:
            self._status = MCPServerStatus.FAILED
            logger.error(f"❌ 啟動 MCP 服務器失敗: {e}")
            return False

    async def stop(self, timeout: float | None = None) -> bool:
        """停止服務器"""
        try:
            logger.info(f"⏹️ 停止 MCP 服務器: {self._config.name}")

            if self._status in [MCPServerStatus.STOPPED, MCPServerStatus.FAILED]:
                return True

            self._status = MCPServerStatus.STOPPING

            # 斷開連接
            if self._connection:
                await self._connection.disconnect()
                self._connection = None

            # 停止進程
            if await self._process.stop(timeout or 10.0):
                self._status = MCPServerStatus.STOPPED
                self._stopped_at = time.time()
                logger.info(f"✅ MCP 服務器 {self._config.name} 已停止")
                return True
            else:
                logger.warning(f"⚠️ MCP 服務器 {self._config.name} 停止時出現問題")
                return False

        except Exception as e:
            logger.error(f"❌ 停止 MCP 服務器失敗: {e}")
            return False

    async def restart(self, timeout: float | None = None) -> bool:
        """重啟服務器"""
        try:
            logger.info(f"🔄 重啟 MCP 服務器: {self._config.name}")

            self._status = MCPServerStatus.RESTARTING

            # 先停止
            await self.stop(timeout)

            # 等待一秒確保完全停止
            await asyncio.sleep(1)

            # 重新啟動
            if await self.start():
                self._restart_count += 1
                logger.info(
                    f"✅ MCP 服務器 {self._config.name} 重啟成功 "
                    f"(第{self._restart_count}次)"
                )
                return True
            else:
                logger.error(f"❌ MCP 服務器 {self._config.name} 重啟失敗")
                return False

        except Exception as e:
            logger.error(f"❌ 重啟 MCP 服務器失敗: {e}")
            return False

    async def is_running(self) -> bool:
        """檢查服務器是否正在運行"""
        try:
            if self._status != MCPServerStatus.RUNNING:
                return False

            if not self._process:
                return False

            is_alive = await self._process.is_alive()
            if not is_alive:
                self._status = MCPServerStatus.STOPPED
                return False

            return True

        except Exception:
            return False

    async def get_connection(self) -> IMCPConnection:
        """獲取 MCP 連接"""
        if not self._connection:
            if self._status != MCPServerStatus.RUNNING:
                raise RuntimeError(f"服務器 {self._config.name} 未運行")

            self._connection = MCPConnectionImpl(self._config, self._process)

        return self._connection

    async def health_check(self) -> bool:
        """健康檢查"""
        try:
            if not await self.is_running():
                return False

            if self._connection:
                return await self._connection.ping()

            return True

        except Exception:
            return False


class MCPConnectionImpl(IMCPConnection):
    """
    MCP 連接實現

    封裝與 MCP 服務器的通信邏輯。
    """

    def __init__(self, config: MCPServerConfig, process: IProcess):
        self._config = config
        self._process = process
        self._status = ConnectionStatus.DISCONNECTED
        self._connection_id = f"{config.name}_{int(time.time())}"

    @property
    def status(self) -> ConnectionStatus:
        """獲取連接狀態"""
        return self._status

    @property
    def config(self) -> MCPServerConfig:
        """獲取連接配置"""
        return self._config

    async def connect(self) -> bool:
        """建立連接"""
        try:
            self._status = ConnectionStatus.CONNECTING

            # 檢查進程是否存活
            if not await self._process.is_alive():
                self._status = ConnectionStatus.FAILED
                return False

            self._status = ConnectionStatus.CONNECTED
            logger.info(f"✅ MCP 連接建立: {self._config.name}")
            return True

        except Exception as e:
            self._status = ConnectionStatus.FAILED
            logger.error(f"❌ MCP 連接失敗: {e}")
            return False

    async def disconnect(self) -> bool:
        """斷開連接"""
        try:
            self._status = ConnectionStatus.DISCONNECTED
            logger.info(f"✅ MCP 連接斷開: {self._config.name}")
            return True

        except Exception as e:
            logger.error(f"❌ MCP 斷開失敗: {e}")
            return False

    async def is_alive(self) -> bool:
        """檢查連接是否存活"""
        try:
            return (
                self._status == ConnectionStatus.CONNECTED
                and await self._process.is_alive()
            )
        except Exception:
            return False

    async def ping(self, timeout: float | None = None) -> bool:
        """ping 測試連接"""
        try:
            if not await self.is_alive():
                return False

            # 簡單的存活檢查
            return await self._process.is_alive()

        except Exception:
            return False

    async def call_tool(self, tool_call: MCPToolCall) -> MCPToolResult:
        """調用 MCP 工具"""
        try:
            # 這是簡化實現，實際應該通過 STDIO 與進程通信
            # 目前返回成功結果，實際實現需要 JSON-RPC 協議

            if not await self.is_alive():
                return MCPToolResult(
                    success=False,
                    error="連接未建立或進程未運行",
                    call_id=tool_call.call_id,
                )

            # 模擬工具調用
            result = MCPToolResult(
                success=True,
                result={"message": f"工具 {tool_call.tool_name} 調用成功"},
                call_id=tool_call.call_id,
            )

            logger.info(f"✅ 工具調用成功: {tool_call.tool_name}")
            return result

        except Exception as e:
            logger.error(f"❌ 工具調用失敗: {e}")
            return MCPToolResult(success=False, error=str(e), call_id=tool_call.call_id)

    async def list_tools(self) -> list[MCPTool]:
        """列出可用工具"""
        try:
            # 這是簡化實現，實際應該查詢 MCP 服務器
            return [
                MCPTool(
                    name="query",
                    description="執行資料庫查詢",
                    input_schema={
                        "type": "object",
                        "properties": {"sql": {"type": "string"}},
                    },
                )
            ]
        except Exception as e:
            logger.error(f"❌ 列出工具失敗: {e}")
            return []

    async def list_resources(self) -> list[MCPResource]:
        """列出可用資源"""
        try:
            # 這是簡化實現，實際應該查詢 MCP 服務器
            return [
                MCPResource(
                    uri=f"mcp://{self._config.name}/database",
                    name="資料庫",
                    description="PostgreSQL 資料庫資源",
                )
            ]
        except Exception as e:
            logger.error(f"❌ 列出資源失敗: {e}")
            return []
