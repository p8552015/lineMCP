"""
MCP 連接池管理器
實施連接池、健康檢查、自動恢復機制
"""

import asyncio
import contextlib
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class ConnectionStatus(Enum):
    """連接狀態枚舉"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    FAILED = "failed"
    RECOVERING = "recovering"


@dataclass
class ConnectionMetrics:
    """連接指標"""

    connection_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_success_time: float = 0.0
    last_failure_time: float = 0.0
    average_response_time: float = 0.0
    current_status: ConnectionStatus = ConnectionStatus.DISCONNECTED

    @property
    def success_rate(self) -> float:
        """成功率"""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0

    @property
    def is_healthy(self) -> bool:
        """連接是否健康"""
        if self.current_status != ConnectionStatus.CONNECTED:
            return False

        # 最近5分鐘有成功記錄
        recent_success = time.time() - self.last_success_time < 300
        # 成功率 > 80%
        good_success_rate = self.success_rate > 0.8

        return recent_success and good_success_rate


@dataclass
class ConnectionInfo:
    """連接資訊"""

    server_name: str
    process: asyncio.subprocess.Process | None = None
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    metrics: ConnectionMetrics | None = None
    last_health_check: float = 0.0
    recovery_attempts: int = 0
    max_recovery_attempts: int = 3

    def __post_init__(self):
        if self.metrics is None:
            self.metrics = ConnectionMetrics()


class MCPConnectionPool:
    """MCP 連接池管理器"""

    def __init__(self, max_connections: int = 5, health_check_interval: int = 30):
        """
        初始化連接池

        Args:
            max_connections: 最大連接數
            health_check_interval: 健康檢查間隔(秒)
        """
        self.max_connections = max_connections
        self.health_check_interval = health_check_interval

        # 連接管理
        self.connections: dict[str, ConnectionInfo] = {}
        self.connection_lock = asyncio.Lock()

        # 健康檢查任務
        self.health_check_task: asyncio.Task | None = None
        self.is_running = False

        logger.info(
            "🏊 MCP 連接池管理器初始化完成",
            max_connections=max_connections,
            health_check_interval=health_check_interval,
        )

    async def start(self):
        """啟動連接池監控"""
        if self.is_running:
            return

        self.is_running = True
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("🚀 連接池監控已啟動")

    async def stop(self):
        """停止連接池監控"""
        self.is_running = False

        if self.health_check_task:
            self.health_check_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.health_check_task

        # 關閉所有連接
        await self._close_all_connections()
        logger.info("🛑 連接池監控已停止")

    async def get_connection(self, server_name: str) -> ConnectionInfo | None:
        """取得連接"""
        async with self.connection_lock:
            if server_name not in self.connections:
                self.connections[server_name] = ConnectionInfo(server_name=server_name)

            connection = self.connections[server_name]

            # 檢查連接狀態
            if (
                connection.status == ConnectionStatus.CONNECTED
                and connection.metrics is not None
                and connection.metrics.is_healthy
            ):
                return connection

            # 需要建立或恢復連接
            if connection.status in [
                ConnectionStatus.DISCONNECTED,
                ConnectionStatus.FAILED,
            ]:
                await self._establish_connection(connection)

            return (
                connection if connection.status == ConnectionStatus.CONNECTED else None
            )

    async def record_success(self, server_name: str, response_time: float):
        """記錄成功操作"""
        async with self.connection_lock:
            if server_name in self.connections:
                connection = self.connections[server_name]
                metrics = connection.metrics

                if metrics is not None:
                    metrics.success_count += 1
                    metrics.last_success_time = time.time()

                    # 更新平均回應時間
                    if metrics.average_response_time == 0:
                        metrics.average_response_time = response_time
                    else:
                        metrics.average_response_time = (
                            metrics.average_response_time + response_time
                        ) / 2

                    logger.debug(
                        "📊 記錄成功操作",
                        server=server_name,
                        response_time=response_time,
                        success_rate=metrics.success_rate,
                    )

    async def record_failure(self, server_name: str, error: str):
        """記錄失敗操作"""
        async with self.connection_lock:
            if server_name in self.connections:
                connection = self.connections[server_name]
                metrics = connection.metrics

                if metrics is not None:
                    metrics.failure_count += 1
                    metrics.last_failure_time = time.time()

                    # 如果失敗率過高，標記為失敗狀態
                    if metrics.success_rate < 0.5 and metrics.failure_count > 3:
                        connection.status = ConnectionStatus.FAILED

                    logger.warning(
                        "⚠️ 記錄失敗操作",
                        server=server_name,
                        error=error,
                        success_rate=metrics.success_rate,
                    )

    async def get_pool_status(self) -> dict[str, Any]:
        """取得連接池狀態"""
        async with self.connection_lock:
            pool_status: dict[str, Any] = {
                "total_connections": len(self.connections),
                "healthy_connections": sum(
                    1
                    for conn in self.connections.values()
                    if conn.metrics is not None and conn.metrics.is_healthy
                ),
                "connections": {},
            }

            for server_name, connection in self.connections.items():
                metrics = connection.metrics
                pool_status["connections"][server_name] = {
                    "status": connection.status.value,
                    "is_healthy": metrics.is_healthy if metrics is not None else False,
                    "success_rate": (
                        metrics.success_rate if metrics is not None else 0.0
                    ),
                    "success_count": (
                        metrics.success_count if metrics is not None else 0
                    ),
                    "failure_count": (
                        metrics.failure_count if metrics is not None else 0
                    ),
                    "average_response_time": (
                        metrics.average_response_time if metrics is not None else 0.0
                    ),
                    "recovery_attempts": connection.recovery_attempts,
                }

            return pool_status

    async def _health_check_loop(self):
        """健康檢查循環"""
        while self.is_running:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("❌ 健康檢查異常", error=str(e))
                await asyncio.sleep(5)  # 短暫等待後重試

    async def _perform_health_checks(self):
        """執行健康檢查"""
        async with self.connection_lock:
            for _server_name, connection in self.connections.items():
                await self._check_connection_health(connection)

    async def _check_connection_health(self, connection: ConnectionInfo):
        """檢查單個連接健康狀態"""
        current_time = time.time()

        # 跳過最近檢查過的連接
        if current_time - connection.last_health_check < self.health_check_interval:
            return

        connection.last_health_check = current_time

        # 檢查進程狀態
        if connection.process and connection.process.returncode is not None:
            logger.warning(
                "⚠️ 檢測到進程已退出",
                server=connection.server_name,
                return_code=connection.process.returncode,
            )
            connection.status = ConnectionStatus.FAILED
            connection.process = None

        # 嘗試恢復失敗的連接
        if connection.status == ConnectionStatus.FAILED:
            await self._attempt_recovery(connection)

    async def _attempt_recovery(self, connection: ConnectionInfo):
        """嘗試恢復連接"""
        if connection.recovery_attempts >= connection.max_recovery_attempts:
            logger.error(
                "❌ 連接恢復次數已達上限",
                server=connection.server_name,
                attempts=connection.recovery_attempts,
            )
            return

        connection.recovery_attempts += 1
        connection.status = ConnectionStatus.RECOVERING

        logger.info(
            "🔄 嘗試恢復連接",
            server=connection.server_name,
            attempt=connection.recovery_attempts,
        )

        success = await self._establish_connection(connection)
        if success:
            connection.recovery_attempts = 0  # 重置恢復計數
            logger.info("✅ 連接恢復成功", server=connection.server_name)
        else:
            logger.warning(
                "⚠️ 連接恢復失敗",
                server=connection.server_name,
                attempt=connection.recovery_attempts,
            )

    async def _establish_connection(self, connection: ConnectionInfo) -> bool:
        """建立連接"""
        connection.status = ConnectionStatus.CONNECTING

        try:
            # 標記為已連接 - 實際連接邏輯由 ProductionMCPClient 處理
            # 這裡只是更新連接池狀態，不執行實際連接
            connection.status = ConnectionStatus.CONNECTED
            if connection.metrics is not None:
                connection.metrics.connection_count += 1

            logger.info("🏊 連接池標記連接成功", server=connection.server_name)
            return True

        except Exception as e:
            connection.status = ConnectionStatus.FAILED
            logger.error(
                "❌ 連接池標記失敗", server=connection.server_name, error=str(e)
            )
            return False

    async def _close_all_connections(self):
        """關閉所有連接"""
        for connection in self.connections.values():
            if connection.process:
                try:
                    connection.process.terminate()
                    await asyncio.wait_for(connection.process.wait(), timeout=5.0)
                except TimeoutError:
                    if connection.process:
                        connection.process.kill()
                except Exception as e:
                    logger.error(
                        "❌ 關閉連接異常", server=connection.server_name, error=str(e)
                    )

            connection.status = ConnectionStatus.DISCONNECTED

        self.connections.clear()


# 全域連接池實例
_global_connection_pool: MCPConnectionPool | None = None


def get_connection_pool() -> MCPConnectionPool:
    """取得全域連接池實例"""
    global _global_connection_pool
    if _global_connection_pool is None:
        _global_connection_pool = MCPConnectionPool()
    return _global_connection_pool
