"""
進程生命週期管理器

提供統一的進程生命週期管理功能，包括：
- 進程監控和健康檢查
- 自動重啟機制
- 資源清理和垃圾回收
- 進程池管理
- 異常處理和恢復

遵循 SOLID 原則：
- SRP: 專注於進程生命週期管理
- OCP: 對新的監控策略擴展開放
- LSP: 提供統一的進程管理介面
- ISP: 介面隔離，專注生命週期功能
- DIP: 依賴抽象的 IProcess 介面
"""

import asyncio
import signal
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from ..interfaces.runtime_interfaces import IProcess
from ..interfaces.server_interfaces import MCPServerConfig

logger = structlog.get_logger()


class LifecycleState(Enum):
    """進程生命週期狀態"""

    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    RESTARTING = "restarting"
    MONITORING = "monitoring"


class RestartPolicy(Enum):
    """重啟策略"""

    NEVER = "never"  # 從不重啟
    ON_FAILURE = "on_failure"  # 失敗時重啟
    ALWAYS = "always"  # 總是重啟
    UNLESS_STOPPED = "unless_stopped"  # 除非手動停止


@dataclass
class LifecycleConfig:
    """生命週期配置"""

    # 健康檢查配置
    health_check_interval: float = 10.0  # 健康檢查間隔（秒）
    health_check_timeout: float = 5.0  # 健康檢查超時（秒）
    health_check_retries: int = 3  # 健康檢查重試次數

    # 重啟配置
    restart_policy: RestartPolicy = RestartPolicy.ON_FAILURE
    max_restart_attempts: int = 5  # 最大重啟次數
    restart_delay: float = 2.0  # 重啟延遲（秒）
    backoff_multiplier: float = 1.5  # 退避倍數
    max_restart_delay: float = 60.0  # 最大重啟延遲（秒）

    # 停止配置
    graceful_shutdown_timeout: float = 10.0  # 優雅停止超時
    force_kill_timeout: float = 5.0  # 強制終止超時

    # 監控配置
    resource_monitoring: bool = True  # 是否監控資源使用
    memory_limit_mb: int | None = None  # 記憶體限制（MB）
    cpu_limit_percent: float | None = None  # CPU 限制（百分比）


@dataclass
class ProcessMetrics:
    """進程指標"""

    pid: int | None = None
    start_time: float | None = None
    uptime: float = 0.0
    restart_count: int = 0
    last_restart_time: float | None = None
    health_check_count: int = 0
    failed_health_checks: int = 0
    last_health_check: float | None = None
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0

    def update_uptime(self):
        """更新運行時間"""
        if self.start_time:
            self.uptime = time.time() - self.start_time


@dataclass
class ManagedProcess:
    """被管理的進程"""

    process: IProcess
    config: LifecycleConfig
    server_config: MCPServerConfig | None = None
    state: LifecycleState = LifecycleState.CREATED
    metrics: ProcessMetrics = field(default_factory=ProcessMetrics)

    # 回調函數
    on_state_change: (
        Callable[["ManagedProcess", LifecycleState, LifecycleState], None] | None
    ) = None
    on_health_check_failed: Callable[["ManagedProcess"], None] | None = None
    on_restart: Callable[["ManagedProcess"], None] | None = None

    def set_state(self, new_state: LifecycleState):
        """設置狀態並觸發回調"""
        old_state = self.state
        self.state = new_state

        if self.on_state_change:
            try:
                self.on_state_change(self, old_state, new_state)
            except Exception as e:
                logger.error(f"❌ 狀態變更回調失敗: {e}")


class ProcessLifecycleManager:
    """
    進程生命週期管理器

    統一管理所有 MCP 相關進程的生命週期，提供監控、重啟、清理等功能。
    """

    def __init__(self):
        self._managed_processes: dict[str, ManagedProcess] = {}
        self._monitoring_tasks: dict[str, asyncio.Task] = {}
        self._is_shutting_down = False
        self._lock = asyncio.Lock()

        # 註冊信號處理
        self._setup_signal_handlers()

        logger.info("🔄 進程生命週期管理器已初始化")

    def _setup_signal_handlers(self):
        """設置信號處理器"""
        try:
            # 在主線程中設置信號處理
            if threading.current_thread() is threading.main_thread():
                signal.signal(signal.SIGTERM, self._signal_handler)
                signal.signal(signal.SIGINT, self._signal_handler)
                logger.info("✅ 信號處理器已設置")
        except Exception as e:
            logger.warning(f"⚠️ 信號處理器設置失敗: {e}")

    def _signal_handler(self, signum, frame):
        """信號處理器"""
        logger.info(f"📡 收到信號 {signum}，開始優雅關閉")
        asyncio.create_task(self.shutdown_all())

    async def register_process(
        self,
        process_id: str,
        process: IProcess,
        config: LifecycleConfig | None = None,
        server_config: MCPServerConfig | None = None,
    ) -> bool:
        """註冊進程進行生命週期管理"""
        try:
            async with self._lock:
                if process_id in self._managed_processes:
                    logger.warning(f"⚠️ 進程 {process_id} 已存在，將被覆蓋")

                managed_process = ManagedProcess(
                    process=process,
                    config=config or LifecycleConfig(),
                    server_config=server_config,
                )

                # 設置回調
                managed_process.on_state_change = self._on_process_state_change
                managed_process.on_health_check_failed = self._on_health_check_failed
                managed_process.on_restart = self._on_process_restart

                self._managed_processes[process_id] = managed_process

                logger.info(f"✅ 進程 {process_id} 已註冊到生命週期管理")
                return True

        except Exception as e:
            logger.error(f"❌ 註冊進程 {process_id} 失敗: {e}")
            return False

    async def start_process(self, process_id: str) -> bool:
        """啟動進程並開始監控"""
        try:
            async with self._lock:
                managed_process = self._managed_processes.get(process_id)
                if not managed_process:
                    logger.error(f"❌ 進程 {process_id} 未註冊")
                    return False

                if managed_process.state in [
                    LifecycleState.RUNNING,
                    LifecycleState.STARTING,
                ]:
                    logger.info(f"ℹ️ 進程 {process_id} 已在運行")
                    return True

                logger.info(f"▶️ 啟動進程: {process_id}")
                managed_process.set_state(LifecycleState.STARTING)

                # 啟動進程
                if await managed_process.process.start():
                    managed_process.set_state(LifecycleState.RUNNING)
                    managed_process.metrics.start_time = time.time()
                    managed_process.metrics.pid = managed_process.process.info.pid

                    # 開始監控
                    await self._start_monitoring(process_id)

                    logger.info(f"✅ 進程 {process_id} 啟動成功")
                    return True
                else:
                    managed_process.set_state(LifecycleState.FAILED)
                    logger.error(f"❌ 進程 {process_id} 啟動失敗")
                    return False

        except Exception as e:
            logger.error(f"❌ 啟動進程 {process_id} 失敗: {e}")
            return False

    async def stop_process(self, process_id: str, force: bool = False) -> bool:
        """停止進程"""
        try:
            async with self._lock:
                managed_process = self._managed_processes.get(process_id)
                if not managed_process:
                    logger.warning(f"⚠️ 進程 {process_id} 未找到")
                    return True

                if managed_process.state in [
                    LifecycleState.STOPPED,
                    LifecycleState.STOPPING,
                ]:
                    logger.info(f"ℹ️ 進程 {process_id} 已停止")
                    return True

                logger.info(f"⏹️ 停止進程: {process_id}")
                managed_process.set_state(LifecycleState.STOPPING)

                # 停止監控
                await self._stop_monitoring(process_id)

                # 停止進程
                timeout = (
                    managed_process.config.force_kill_timeout
                    if force
                    else managed_process.config.graceful_shutdown_timeout
                )

                if await managed_process.process.stop(timeout):
                    managed_process.set_state(LifecycleState.STOPPED)
                    logger.info(f"✅ 進程 {process_id} 已停止")
                    return True
                else:
                    logger.warning(f"⚠️ 進程 {process_id} 停止失敗")
                    return False

        except Exception as e:
            logger.error(f"❌ 停止進程 {process_id} 失敗: {e}")
            return False

    async def restart_process(self, process_id: str) -> bool:
        """重啟進程"""
        try:
            managed_process = self._managed_processes.get(process_id)
            if not managed_process:
                logger.error(f"❌ 進程 {process_id} 未註冊")
                return False

            logger.info(f"🔄 重啟進程: {process_id}")
            managed_process.set_state(LifecycleState.RESTARTING)

            # 先停止
            await self.stop_process(process_id)

            # 等待重啟延遲
            delay = min(
                managed_process.config.restart_delay
                * (
                    managed_process.config.backoff_multiplier
                    ** managed_process.metrics.restart_count
                ),
                managed_process.config.max_restart_delay,
            )
            await asyncio.sleep(delay)

            # 重新啟動
            if await self.start_process(process_id):
                managed_process.metrics.restart_count += 1
                managed_process.metrics.last_restart_time = time.time()
                logger.info(
                    f"✅ 進程 {process_id} 重啟成功 "
                    f"(第{managed_process.metrics.restart_count}次)"
                )
                return True
            else:
                managed_process.set_state(LifecycleState.FAILED)
                logger.error(f"❌ 進程 {process_id} 重啟失敗")
                return False

        except Exception as e:
            logger.error(f"❌ 重啟進程 {process_id} 失敗: {e}")
            return False

    async def _start_monitoring(self, process_id: str):
        """開始監控進程"""
        try:
            if process_id in self._monitoring_tasks:
                # 取消現有監控任務
                self._monitoring_tasks[process_id].cancel()

            # 創建新的監控任務
            task = asyncio.create_task(self._monitor_process(process_id))
            self._monitoring_tasks[process_id] = task

            logger.info(f"👀 開始監控進程: {process_id}")

        except Exception as e:
            logger.error(f"❌ 開始監控進程 {process_id} 失敗: {e}")

    async def _stop_monitoring(self, process_id: str):
        """停止監控進程"""
        try:
            if process_id in self._monitoring_tasks:
                self._monitoring_tasks[process_id].cancel()
                del self._monitoring_tasks[process_id]
                logger.info(f"🛑 停止監控進程: {process_id}")

        except Exception as e:
            logger.error(f"❌ 停止監控進程 {process_id} 失敗: {e}")

    async def _monitor_process(self, process_id: str):
        """監控進程"""
        try:
            managed_process = self._managed_processes.get(process_id)
            if not managed_process:
                return

            logger.info(f"🔍 開始監控進程健康: {process_id}")

            while (
                not self._is_shutting_down
                and managed_process.state == LifecycleState.RUNNING
            ):
                try:
                    # 健康檢查
                    is_healthy = await self._health_check(managed_process)

                    if is_healthy:
                        managed_process.metrics.health_check_count += 1
                        managed_process.metrics.last_health_check = time.time()
                        managed_process.metrics.update_uptime()
                    else:
                        managed_process.metrics.failed_health_checks += 1

                        # 觸發健康檢查失敗回調
                        if managed_process.on_health_check_failed:
                            managed_process.on_health_check_failed(managed_process)

                        # 檢查是否需要重啟
                        await self._handle_unhealthy_process(
                            process_id, managed_process
                        )

                    # 等待下次檢查
                    await asyncio.sleep(managed_process.config.health_check_interval)

                except asyncio.CancelledError:
                    logger.info(f"📋 進程 {process_id} 監控已取消")
                    break
                except Exception as e:
                    logger.error(f"❌ 監控進程 {process_id} 時發生錯誤: {e}")
                    await asyncio.sleep(5)  # 錯誤時短暫等待

        except Exception as e:
            logger.error(f"❌ 進程監控任務失敗: {e}")

    async def _health_check(self, managed_process: ManagedProcess) -> bool:
        """執行健康檢查"""
        try:
            # 基本存活檢查
            if not await managed_process.process.is_alive():
                logger.warning(f"⚠️ 進程 {managed_process.process.info.pid} 不存在")
                return False

            # TODO: 可以添加更多健康檢查邏輯
            # - 記憶體使用檢查
            # - CPU 使用檢查
            # - 響應時間檢查

            return True

        except Exception as e:
            logger.error(f"❌ 健康檢查失敗: {e}")
            return False

    async def _handle_unhealthy_process(
        self, process_id: str, managed_process: ManagedProcess
    ):
        """處理不健康的進程"""
        try:
            restart_policy = managed_process.config.restart_policy
            restart_count = managed_process.metrics.restart_count
            max_restarts = managed_process.config.max_restart_attempts

            logger.warning(f"⚠️ 進程 {process_id} 健康檢查失敗")

            # 檢查重啟策略
            should_restart = False

            if restart_policy == RestartPolicy.ALWAYS:
                should_restart = True
            elif restart_policy == RestartPolicy.ON_FAILURE:
                should_restart = restart_count < max_restarts
            elif restart_policy == RestartPolicy.UNLESS_STOPPED:
                should_restart = managed_process.state != LifecycleState.STOPPING

            if should_restart:
                logger.info(
                    f"🔄 根據策略 {restart_policy.value} 重啟進程: {process_id}"
                )
                await self.restart_process(process_id)
            else:
                logger.warning(f"⚠️ 進程 {process_id} 達到重啟限制或策略不允許重啟")
                managed_process.set_state(LifecycleState.FAILED)

        except Exception as e:
            logger.error(f"❌ 處理不健康進程失敗: {e}")

    async def get_process_status(self, process_id: str) -> dict[str, Any] | None:
        """獲取進程狀態"""
        try:
            managed_process = self._managed_processes.get(process_id)
            if not managed_process:
                return None

            managed_process.metrics.update_uptime()

            return {
                "process_id": process_id,
                "state": managed_process.state.value,
                "pid": managed_process.metrics.pid,
                "uptime": managed_process.metrics.uptime,
                "restart_count": managed_process.metrics.restart_count,
                "health_checks": {
                    "total": managed_process.metrics.health_check_count,
                    "failed": managed_process.metrics.failed_health_checks,
                    "last_check": managed_process.metrics.last_health_check,
                },
                "config": {
                    "restart_policy": managed_process.config.restart_policy.value,
                    "max_restarts": managed_process.config.max_restart_attempts,
                    "health_check_interval": (
                        managed_process.config.health_check_interval
                    ),
                },
            }

        except Exception as e:
            logger.error(f"❌ 獲取進程狀態失敗: {e}")
            return None

    async def list_processes(self) -> dict[str, dict[str, Any]]:
        """列出所有管理的進程"""
        try:
            result = {}
            for process_id in self._managed_processes:
                status = await self.get_process_status(process_id)
                if status:
                    result[process_id] = status
            return result

        except Exception as e:
            logger.error(f"❌ 列出進程失敗: {e}")
            return {}

    async def shutdown_all(self, timeout: float = 30.0) -> bool:
        """關閉所有進程"""
        try:
            self._is_shutting_down = True
            logger.info("🛑 開始關閉所有進程")

            # 停止所有監控任務
            for task in self._monitoring_tasks.values():
                task.cancel()

            # 等待所有監控任務完成
            if self._monitoring_tasks:
                await asyncio.gather(
                    *self._monitoring_tasks.values(), return_exceptions=True
                )

            # 停止所有進程
            stop_tasks : list[Any] = []
            for process_id in list(self._managed_processes.keys()):
                task = asyncio.create_task(self.stop_process(process_id))
                stop_tasks.append(task)

            if stop_tasks:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*stop_tasks, return_exceptions=True),
                        timeout=timeout,
                    )
                except TimeoutError:
                    logger.warning("⚠️ 部分進程停止超時，將強制終止")

                    # 強制停止剩餘進程
                    for process_id in self._managed_processes:
                        await self.stop_process(process_id, force=True)

            self._managed_processes.clear()
            self._monitoring_tasks.clear()

            logger.info("✅ 所有進程已關閉")
            return True

        except Exception as e:
            logger.error(f"❌ 關閉所有進程失敗: {e}")
            return False

    def _on_process_state_change(
        self,
        managed_process: ManagedProcess,
        old_state: LifecycleState,
        new_state: LifecycleState,
    ):
        """進程狀態變更回調"""
        logger.info(f"🔄 進程狀態變更: {old_state.value} → {new_state.value}")

    def _on_health_check_failed(self, managed_process: ManagedProcess):
        """健康檢查失敗回調"""
        logger.warning(f"💔 進程健康檢查失敗: PID {managed_process.metrics.pid}")

    def _on_process_restart(self, managed_process: ManagedProcess):
        """進程重啟回調"""
        logger.info(f"🔄 進程重啟: 第{managed_process.metrics.restart_count}次")

    async def unregister_process(self, process_id: str) -> bool:
        """取消註冊進程"""
        try:
            async with self._lock:
                if process_id not in self._managed_processes:
                    return True

                # 先停止進程
                await self.stop_process(process_id)

                # 移除註冊
                del self._managed_processes[process_id]

                logger.info(f"✅ 進程 {process_id} 已取消註冊")
                return True

        except Exception as e:
            logger.error(f"❌ 取消註冊進程 {process_id} 失敗: {e}")
            return False
