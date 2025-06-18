"""
健康檢查模組

提供 MCP 服務器的健康狀態監控和診斷功能。
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import logging

from ..models.base import HealthStatus, HealthStatusLevel

logger = logging.getLogger(__name__)


class HealthCheckType(Enum):
    """健康檢查類型"""
    PING = "ping"
    """基本連通性檢查"""
    
    TOOL_LIST = "tool_list"
    """工具列表檢查"""
    
    SIMPLE_CALL = "simple_call"
    """簡單工具呼叫檢查"""
    
    LOAD_TEST = "load_test"
    """負載測試檢查"""


@dataclass
class HealthCheckConfig:
    """健康檢查配置"""
    enabled: bool = True
    """是否啟用健康檢查"""
    
    interval: float = 30.0
    """檢查間隔（秒）"""
    
    timeout: float = 10.0
    """單次檢查超時（秒）"""
    
    check_types: Set[HealthCheckType] = field(default_factory=lambda: {
        HealthCheckType.PING,
        HealthCheckType.TOOL_LIST
    })
    """啟用的檢查類型"""
    
    failure_threshold: int = 3
    """連續失敗閾值"""
    
    success_threshold: int = 2
    """恢復成功閾值"""
    
    degraded_threshold: float = 2.0
    """降級響應時間閾值（秒）"""


@dataclass 
class HealthCheckResult:
    """健康檢查結果"""
    server: str
    check_type: HealthCheckType
    status: HealthStatusLevel
    response_time: float
    timestamp: float
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_healthy(self) -> bool:
        """是否健康"""
        return self.status == HealthStatusLevel.HEALTHY
        
    @property
    def is_degraded(self) -> bool:
        """是否降級"""
        return self.status == HealthStatusLevel.DEGRADED


class ServerHealthTracker:
    """服務器健康狀態追蹤器"""
    
    def __init__(self, server: str, config: HealthCheckConfig):
        self.server = server
        self.config = config
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.last_check_time = 0.0
        self.recent_results: List[HealthCheckResult] = []
        self.current_status = HealthStatusLevel.UNKNOWN
        
    def record_result(self, result: HealthCheckResult):
        """記錄健康檢查結果"""
        self.recent_results.append(result)
        self.last_check_time = result.timestamp
        
        # 保持最近50個結果
        if len(self.recent_results) > 50:
            self.recent_results = self.recent_results[-50:]
            
        # 更新連續計數
        if result.is_healthy:
            self.consecutive_successes += 1
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
            self.consecutive_successes = 0
            
        # 更新整體狀態
        self._update_status()
        
    def _update_status(self):
        """更新整體健康狀態"""
        if self.consecutive_failures >= self.config.failure_threshold:
            self.current_status = HealthStatusLevel.UNHEALTHY
        elif self.consecutive_successes >= self.config.success_threshold:
            # 檢查是否降級（響應時間過長）
            if self.recent_results:
                latest = self.recent_results[-1]
                if latest.response_time > self.config.degraded_threshold:
                    self.current_status = HealthStatusLevel.DEGRADED
                else:
                    self.current_status = HealthStatusLevel.HEALTHY
        # 保持當前狀態（不夠連續成功/失敗）
        
    @property
    def average_response_time(self) -> float:
        """平均響應時間"""
        if not self.recent_results:
            return 0.0
        return sum(r.response_time for r in self.recent_results) / len(self.recent_results)
        
    @property
    def success_rate(self) -> float:
        """成功率"""
        if not self.recent_results:
            return 0.0
        successful = sum(1 for r in self.recent_results if r.is_healthy)
        return successful / len(self.recent_results)
        
    def get_status_summary(self) -> Dict[str, Any]:
        """獲取狀態摘要"""
        return {
            "server": self.server,
            "status": self.current_status,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "average_response_time": self.average_response_time,
            "success_rate": self.success_rate,
            "last_check": self.last_check_time,
            "total_checks": len(self.recent_results)
        }


class HealthChecker:
    """健康檢查器"""
    
    def __init__(self, config: Optional[HealthCheckConfig] = None):
        self.config = config or HealthCheckConfig()
        self.trackers: Dict[str, ServerHealthTracker] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
    def register_server(self, server: str):
        """註冊服務器進行健康檢查"""
        if server not in self.trackers:
            self.trackers[server] = ServerHealthTracker(server, self.config)
            logger.info(f"Registered server for health checks: {server}")
            
    def unregister_server(self, server: str):
        """取消註冊服務器"""
        if server in self.trackers:
            del self.trackers[server]
            logger.info(f"Unregistered server from health checks: {server}")
            
    async def check_server_ping(self, server: str, client) -> HealthCheckResult:
        """執行 ping 檢查"""
        start_time = time.time()
        
        try:
            # 嘗試連接測試
            connected = await asyncio.wait_for(
                client.connect_to_server(server),
                timeout=self.config.timeout
            )
            
            response_time = time.time() - start_time
            
            if connected:
                status = (HealthStatusLevel.DEGRADED 
                         if response_time > self.config.degraded_threshold 
                         else HealthStatusLevel.HEALTHY)
            else:
                status = HealthStatusLevel.UNHEALTHY
                
            return HealthCheckResult(
                server=server,
                check_type=HealthCheckType.PING,
                status=status,
                response_time=response_time,
                timestamp=time.time(),
                details={"connected": connected}
            )
            
        except asyncio.TimeoutError:
            return HealthCheckResult(
                server=server,
                check_type=HealthCheckType.PING,
                status=HealthStatusLevel.UNHEALTHY,
                response_time=time.time() - start_time,
                timestamp=time.time(),
                error="Timeout"
            )
        except Exception as e:
            return HealthCheckResult(
                server=server,
                check_type=HealthCheckType.PING,
                status=HealthStatusLevel.UNHEALTHY,
                response_time=time.time() - start_time,
                timestamp=time.time(),
                error=str(e)
            )
            
    async def check_server_tools(self, server: str, client) -> HealthCheckResult:
        """檢查工具列表"""
        start_time = time.time()
        
        try:
            tools = await asyncio.wait_for(
                client.list_tools(server),
                timeout=self.config.timeout
            )
            
            response_time = time.time() - start_time
            
            if tools and len(tools) > 0:
                status = (HealthStatusLevel.DEGRADED 
                         if response_time > self.config.degraded_threshold 
                         else HealthStatusLevel.HEALTHY)
            else:
                status = HealthStatusLevel.DEGRADED
                
            return HealthCheckResult(
                server=server,
                check_type=HealthCheckType.TOOL_LIST,
                status=status,
                response_time=response_time,
                timestamp=time.time(),
                details={"tool_count": len(tools) if tools else 0}
            )
            
        except asyncio.TimeoutError:
            return HealthCheckResult(
                server=server,
                check_type=HealthCheckType.TOOL_LIST,
                status=HealthStatusLevel.UNHEALTHY,
                response_time=time.time() - start_time,
                timestamp=time.time(),
                error="Timeout"
            )
        except Exception as e:
            return HealthCheckResult(
                server=server,
                check_type=HealthCheckType.TOOL_LIST,
                status=HealthStatusLevel.UNHEALTHY,
                response_time=time.time() - start_time,
                timestamp=time.time(),
                error=str(e)
            )
            
    async def check_server_simple_call(self, server: str, client) -> HealthCheckResult:
        """執行簡單工具呼叫檢查"""
        start_time = time.time()
        
        try:
            # 對於 SQLite，嘗試 list_tables
            if server == "sqlite":
                result = await asyncio.wait_for(
                    client.call_tool(server, "list_tables", {}),
                    timeout=self.config.timeout
                )
            else:
                # 對於其他服務器，先獲取工具列表然後嘗試第一個工具
                tools = await client.list_tools(server)
                if not tools:
                    raise Exception("No tools available")
                    
                # 嘗試呼叫第一個工具（使用空參數）
                result = await asyncio.wait_for(
                    client.call_tool(server, tools[0], {}),
                    timeout=self.config.timeout
                )
            
            response_time = time.time() - start_time
            
            # 檢查結果
            success = result.get('success', False) if hasattr(result, 'get') else bool(result)
            
            if success:
                status = (HealthStatusLevel.DEGRADED 
                         if response_time > self.config.degraded_threshold 
                         else HealthStatusLevel.HEALTHY)
            else:
                status = HealthStatusLevel.DEGRADED
                
            return HealthCheckResult(
                server=server,
                check_type=HealthCheckType.SIMPLE_CALL,
                status=status,
                response_time=response_time,
                timestamp=time.time(),
                details={"call_success": success}
            )
            
        except asyncio.TimeoutError:
            return HealthCheckResult(
                server=server,
                check_type=HealthCheckType.SIMPLE_CALL,
                status=HealthStatusLevel.UNHEALTHY,
                response_time=time.time() - start_time,
                timestamp=time.time(),
                error="Timeout"
            )
        except Exception as e:
            return HealthCheckResult(
                server=server,
                check_type=HealthCheckType.SIMPLE_CALL,
                status=HealthStatusLevel.UNHEALTHY,
                response_time=time.time() - start_time,
                timestamp=time.time(),
                error=str(e)
            )
            
    async def check_server_health(self, server: str, client) -> List[HealthCheckResult]:
        """執行服務器的所有健康檢查"""
        results = []
        
        for check_type in self.config.check_types:
            try:
                if check_type == HealthCheckType.PING:
                    result = await self.check_server_ping(server, client)
                elif check_type == HealthCheckType.TOOL_LIST:
                    result = await self.check_server_tools(server, client)
                elif check_type == HealthCheckType.SIMPLE_CALL:
                    result = await self.check_server_simple_call(server, client)
                else:
                    logger.warning(f"Unknown health check type: {check_type}")
                    continue
                    
                results.append(result)
                
                # 記錄結果到追蹤器
                if server in self.trackers:
                    self.trackers[server].record_result(result)
                    
            except Exception as e:
                logger.error(f"Health check {check_type} failed for {server}: {e}")
                
        return results
        
    def get_server_status(self, server: str) -> HealthStatusLevel:
        """獲取服務器當前狀態"""
        if server in self.trackers:
            return self.trackers[server].current_status
        return HealthStatusLevel.UNKNOWN
        
    def get_all_statuses(self) -> Dict[str, HealthStatusLevel]:
        """獲取所有服務器狀態"""
        return {
            server: tracker.current_status 
            for server, tracker in self.trackers.items()
        }
        
    def get_health_report(self) -> Dict[str, Any]:
        """獲取完整健康報告"""
        return {
            "timestamp": time.time(),
            "overall_healthy": all(
                tracker.current_status in [HealthStatusLevel.HEALTHY, HealthStatusLevel.DEGRADED]
                for tracker in self.trackers.values()
            ),
            "servers": {
                server: tracker.get_status_summary()
                for server, tracker in self.trackers.items()
            },
            "config": {
                "check_interval": self.config.interval,
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "enabled_checks": [ct.value for ct in self.config.check_types]
            }
        }
        
    async def start_monitoring(self, client):
        """開始持續監控"""
        if self._running:
            logger.warning("Health monitoring already running")
            return
            
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop(client))
        logger.info("Started health monitoring")
        
    async def stop_monitoring(self):
        """停止監控"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped health monitoring")
        
    async def _monitor_loop(self, client):
        """監控主循環"""
        while self._running:
            try:
                # 對所有註冊的服務器執行健康檢查
                for server in list(self.trackers.keys()):
                    if not self._running:
                        break
                    try:
                        await self.check_server_health(server, client)
                    except Exception as e:
                        logger.error(f"Health check failed for {server}: {e}")
                        
                # 等待下次檢查
                await asyncio.sleep(self.config.interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(self.config.interval)


# 全域健康檢查器實例
_global_health_checker: Optional[HealthChecker] = None


def get_health_checker(config: Optional[HealthCheckConfig] = None) -> HealthChecker:
    """獲取全域健康檢查器實例"""
    global _global_health_checker
    
    if _global_health_checker is None:
        _global_health_checker = HealthChecker(config)
        
    return _global_health_checker


async def quick_health_check(client, server: str, timeout: float = 5.0) -> HealthStatus:
    """快速健康檢查
    
    Args:
        client: MCP 客戶端
        server: 服務器名稱
        timeout: 超時時間
        
    Returns:
        健康狀態
    """
    start_time = time.time()
    
    try:
        # 嘗試工具列表檢查
        tools = await asyncio.wait_for(
            client.list_tools(server),
            timeout=timeout
        )
        
        response_time = (time.time() - start_time) * 1000  # 轉為毫秒
        
        if tools and len(tools) > 0:
            status = HealthStatusLevel.HEALTHY
        else:
            status = HealthStatusLevel.DEGRADED
            
        return HealthStatus(
            overall=status,
            servers={server: status},
            response_time_ms=response_time,
            details={
                "server": server,
                "tool_count": len(tools) if tools else 0,
                "check_type": "quick"
            }
        )
        
    except asyncio.TimeoutError:
        response_time = (time.time() - start_time) * 1000
        return HealthStatus(
            overall=HealthStatusLevel.UNHEALTHY,
            servers={server: HealthStatusLevel.UNHEALTHY},
            response_time_ms=response_time,
            details={
                "server": server,
                "error": "timeout",
                "check_type": "quick"
            }
        )
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return HealthStatus(
            overall=HealthStatusLevel.UNHEALTHY,
            servers={server: HealthStatusLevel.UNHEALTHY},
            response_time_ms=response_time,
            details={
                "server": server,
                "error": str(e),
                "check_type": "quick"
            }
        )