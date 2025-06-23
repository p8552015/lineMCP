"""
監控應用服務
負責系統監控、效能追蹤和健康檢查
"""

import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

import structlog

from .base_service import BaseApplicationService

logger = structlog.get_logger()


@dataclass
class PerformanceMetric:
    """效能指標數據類"""

    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: dict[str, str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = {}


@dataclass
class HealthStatus:
    """健康狀態數據類"""

    component: str
    status: str  # healthy, unhealthy, degraded, unknown
    message: str
    details: dict[str, Any] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()


class MonitoringApplicationService(BaseApplicationService):
    """
    監控應用服務

    職責：
    - 收集和聚合系統效能指標
    - 執行健康檢查和可用性監控
    - 提供監控儀表板數據
    - 管理警報和通知
    """

    def __init__(self, service_context, retention_hours: int = 24):
        """
        初始化監控服務

        Args:
            service_context: 應用服務上下文
            retention_hours: 指標保留時間（小時）
        """
        super().__init__("monitoring")
        self.service_context = service_context
        self.retention_hours = retention_hours

        # 效能指標存儲
        self._metrics: list[PerformanceMetric] = []
        self._max_metrics = 10000  # 最大指標數量

        # 健康檢查結果
        self._health_statuses: dict[str, HealthStatus] = {}

        # 系統統計
        self._system_stats = {
            "start_time": datetime.now(),
            "total_requests": 0,
            "error_count": 0,
            "last_health_check": None,
        }

        # 效能基線
        self._performance_baselines = {
            "avg_response_time": 1.0,  # 秒
            "max_memory_usage": 500,  # MB
            "max_cpu_usage": 80,  # 百分比
            "error_rate_threshold": 5.0,  # 百分比
        }

    async def _initialize_service(self) -> None:
        """初始化監控服務"""
        # 記錄服務啟動指標
        self.record_metric("service.startup", 1, "count", {"service": "monitoring"})

        # 執行初始健康檢查
        await self.perform_comprehensive_health_check()

        self.logger.info("監控服務已初始化")

    def record_metric(
        self,
        name: str,
        value: float,
        unit: str = "count",
        tags: dict[str, str] | None = None,
    ) -> None:
        """
        記錄效能指標

        Args:
            name: 指標名稱
            value: 指標值
            unit: 單位
            tags: 標籤
        """
        metric = PerformanceMetric(
            name=name, value=value, unit=unit, timestamp=datetime.now(), tags=tags or {}
        )

        self._metrics.append(metric)

        # 限制指標數量
        if len(self._metrics) > self._max_metrics:
            # 移除舊指標
            cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
            self._metrics = [m for m in self._metrics if m.timestamp > cutoff_time]

        self.logger.debug("記錄效能指標", metric_name=name, value=value, unit=unit)

    def record_request_metrics(
        self, duration: float, status: str = "success", endpoint: str | None = None
    ) -> None:
        """
        記錄請求相關指標

        Args:
            duration: 請求持續時間（秒）
            status: 請求狀態
            endpoint: 端點名稱
        """
        self._system_stats["total_requests"] += 1

        if status == "error":
            self._system_stats["error_count"] += 1

        tags = {"status": status}
        if endpoint:
            tags["endpoint"] = endpoint

        # 記錄響應時間
        self.record_metric("request.duration", duration, "seconds", tags)

        # 記錄請求計數
        self.record_metric("request.count", 1, "count", tags)

        # 檢查是否超過基線
        if duration > self._performance_baselines["avg_response_time"]:
            self.record_metric("request.slow", 1, "count", tags)

    async def perform_comprehensive_health_check(self) -> dict[str, Any]:
        """
        執行全面的健康檢查

        Returns:
            健康檢查結果
        """
        self.logger.info("開始執行全面健康檢查")

        start_time = time.time()
        overall_status = "healthy"
        component_results = {}

        # 檢查應用服務上下文
        try:
            context_health = await self.service_context.health_check_all()
            component_results["application_services"] = context_health

            if context_health["overall_status"] != "healthy":
                overall_status = "degraded"

        except Exception as e:
            component_results["application_services"] = {
                "status": "error",
                "error": str(e),
            }
            overall_status = "unhealthy"

        # 檢查系統資源
        system_health = self._check_system_resources()
        component_results["system_resources"] = system_health

        if system_health["status"] != "healthy":
            overall_status = "degraded"

        # 檢查效能指標
        performance_health = self._check_performance_metrics()
        component_results["performance"] = performance_health

        if performance_health["status"] != "healthy":
            overall_status = "degraded"

        # 彙總結果
        health_result = {
            "overall_status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "check_duration": time.time() - start_time,
            "components": component_results,
            "summary": self._generate_health_summary(component_results),
        }

        # 更新健康狀態
        self._update_health_status(
            "system_overall", overall_status, f"整體系統狀態: {overall_status}"
        )

        self._system_stats["last_health_check"] = datetime.now()

        # 記錄健康檢查指標
        self.record_metric("health_check.duration", time.time() - start_time, "seconds")

        self.record_metric(
            "health_check.status", 1 if overall_status == "healthy" else 0, "boolean"
        )

        self.logger.info(
            "健康檢查完成",
            overall_status=overall_status,
            duration=time.time() - start_time,
        )

        return health_result

    def _check_system_resources(self) -> dict[str, Any]:
        """檢查系統資源"""
        try:
            import psutil

            # 獲取 CPU 使用率
            cpu_percent = psutil.cpu_percent(interval=1)

            # 獲取記憶體使用率
            memory = psutil.virtual_memory()
            memory_mb = memory.used / 1024 / 1024
            memory_percent = memory.percent

            # 獲取磁碟使用率
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent

            # 記錄資源指標
            self.record_metric("system.cpu.usage", cpu_percent, "percent")
            self.record_metric("system.memory.usage", memory_mb, "mb")
            self.record_metric("system.memory.percent", memory_percent, "percent")
            self.record_metric("system.disk.percent", disk_percent, "percent")

            # 評估健康狀態
            status = "healthy"
            issues = []

            if cpu_percent > self._performance_baselines["max_cpu_usage"]:
                status = "degraded"
                issues.append(f"高 CPU 使用率: {cpu_percent:.1f}%")

            if memory_mb > self._performance_baselines["max_memory_usage"]:
                status = "degraded"
                issues.append(f"高記憶體使用: {memory_mb:.1f}MB")

            if disk_percent > 90:
                status = "degraded"
                issues.append(f"磁碟空間不足: {disk_percent:.1f}%")

            return {
                "status": status,
                "cpu_percent": cpu_percent,
                "memory_mb": memory_mb,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent,
                "issues": issues,
            }

        except ImportError:
            return {
                "status": "unknown",
                "message": "psutil 未安裝，無法獲取系統資源資訊",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _check_performance_metrics(self) -> dict[str, Any]:
        """檢查效能指標"""
        try:
            # 計算最近1小時的統計
            cutoff_time = datetime.now() - timedelta(hours=1)
            recent_metrics = [m for m in self._metrics if m.timestamp > cutoff_time]

            # 分析響應時間
            response_times = [
                m.value for m in recent_metrics if m.name == "request.duration"
            ]

            # 計算錯誤率
            total_requests = self._system_stats["total_requests"]
            error_count = self._system_stats["error_count"]
            error_rate = (error_count / max(total_requests, 1)) * 100

            status = "healthy"
            issues = []

            # 檢查響應時間
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                self.record_metric(
                    "performance.avg_response_time", avg_response_time, "seconds"
                )

                if avg_response_time > self._performance_baselines["avg_response_time"]:
                    status = "degraded"
                    issues.append(f"平均響應時間過長: {avg_response_time:.2f}s")

            # 檢查錯誤率
            if error_rate > self._performance_baselines["error_rate_threshold"]:
                status = "degraded"
                issues.append(f"錯誤率過高: {error_rate:.1f}%")

            return {
                "status": status,
                "avg_response_time": (
                    sum(response_times) / len(response_times) if response_times else 0
                ),
                "error_rate": error_rate,
                "total_requests": total_requests,
                "recent_metrics_count": len(recent_metrics),
                "issues": issues,
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _generate_health_summary(
        self, component_results: dict[str, Any]
    ) -> dict[str, Any]:
        """生成健康檢查摘要"""
        total_components = len(component_results)
        healthy_components = 0
        degraded_components = 0
        unhealthy_components = 0

        for component, result in component_results.items():
            status = result.get("status", "unknown")
            if status == "healthy":
                healthy_components += 1
            elif status in ["degraded", "warning"]:
                degraded_components += 1
            else:
                unhealthy_components += 1

        return {
            "total_components": total_components,
            "healthy": healthy_components,
            "degraded": degraded_components,
            "unhealthy": unhealthy_components,
            "health_percentage": (healthy_components / max(total_components, 1)) * 100,
        }

    def _update_health_status(self, component: str, status: str, message: str) -> None:
        """更新組件健康狀態"""
        self._health_statuses[component] = HealthStatus(
            component=component,
            status=status,
            message=message,
            timestamp=datetime.now(),
        )

    def get_dashboard_data(self) -> dict[str, Any]:
        """獲取監控儀表板數據"""
        # 計算最近統計
        cutoff_time = datetime.now() - timedelta(hours=1)
        recent_metrics = [m for m in self._metrics if m.timestamp > cutoff_time]

        # 按指標類型分組
        metrics_by_type = {}
        for metric in recent_metrics:
            if metric.name not in metrics_by_type:
                metrics_by_type[metric.name] = []
            metrics_by_type[metric.name].append(metric.value)

        # 計算彙總統計
        aggregated_metrics = {}
        for name, values in metrics_by_type.items():
            if values:
                aggregated_metrics[name] = {
                    "count": len(values),
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "latest": values[-1],
                }

        return {
            "timestamp": datetime.now().isoformat(),
            "system_uptime": (
                datetime.now() - self._system_stats["start_time"]
            ).total_seconds(),
            "total_requests": self._system_stats["total_requests"],
            "error_count": self._system_stats["error_count"],
            "error_rate": (
                self._system_stats["error_count"]
                / max(self._system_stats["total_requests"], 1)
            )
            * 100,
            "last_health_check": (
                self._system_stats["last_health_check"].isoformat()
                if self._system_stats["last_health_check"]
                else None
            ),
            "recent_metrics_count": len(recent_metrics),
            "aggregated_metrics": aggregated_metrics,
            "health_statuses": {
                name: asdict(status) for name, status in self._health_statuses.items()
            },
        }

    def get_performance_report(self, hours: int = 24) -> dict[str, Any]:
        """獲取效能報告"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        relevant_metrics = [m for m in self._metrics if m.timestamp > cutoff_time]

        # 分析不同類型的指標
        response_times = [
            m.value for m in relevant_metrics if m.name == "request.duration"
        ]
        error_counts = [
            m.value
            for m in relevant_metrics
            if m.name == "request.count" and m.tags.get("status") == "error"
        ]

        report = {
            "period_hours": hours,
            "total_metrics": len(relevant_metrics),
            "performance_summary": {
                "avg_response_time": (
                    sum(response_times) / len(response_times) if response_times else 0
                ),
                "max_response_time": max(response_times) if response_times else 0,
                "min_response_time": min(response_times) if response_times else 0,
                "total_requests": len(
                    [m for m in relevant_metrics if m.name == "request.count"]
                ),
                "total_errors": len(error_counts),
            },
            "performance_baselines": self._performance_baselines,
            "recommendations": self._generate_performance_recommendations(
                relevant_metrics
            ),
        }

        return report

    def _generate_performance_recommendations(
        self, metrics: list[PerformanceMetric]
    ) -> list[str]:
        """生成效能建議"""
        recommendations = []

        # 分析響應時間
        response_times = [m.value for m in metrics if m.name == "request.duration"]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            slow_requests = [t for t in response_times if t > 2.0]

            if avg_time > self._performance_baselines["avg_response_time"]:
                recommendations.append(
                    f"平均響應時間 {avg_time:.2f}s 超過基線 "
                    f"{self._performance_baselines['avg_response_time']}s，建議優化查詢或增加快取"
                )

            if len(slow_requests) > len(response_times) * 0.1:
                recommendations.append(
                    f"有 {len(slow_requests)} 個慢請求（>2s），建議檢查資料庫查詢效能"
                )

        # 分析錯誤率
        error_rate = (
            self._system_stats["error_count"]
            / max(self._system_stats["total_requests"], 1)
        ) * 100

        if error_rate > self._performance_baselines["error_rate_threshold"]:
            recommendations.append(
                f"錯誤率 {error_rate:.1f}% 超過基線 "
                f"{self._performance_baselines['error_rate_threshold']}%，建議檢查錯誤日誌"
            )

        return recommendations

    async def _perform_health_checks(self) -> dict[str, dict[str, Any]]:
        """執行健康檢查"""
        checks = {}

        # 檢查指標收集
        checks["metrics_collection"] = {
            "status": "healthy",
            "total_metrics": len(self._metrics),
            "retention_hours": self.retention_hours,
        }

        # 檢查系統統計
        uptime_hours = (
            datetime.now() - self._system_stats["start_time"]
        ).total_seconds() / 3600
        checks["system_statistics"] = {
            "status": "healthy",
            "uptime_hours": uptime_hours,
            "total_requests": self._system_stats["total_requests"],
            "error_rate": (
                self._system_stats["error_count"]
                / max(self._system_stats["total_requests"], 1)
            )
            * 100,
        }

        return checks

    async def _shutdown_service(self) -> None:
        """關閉服務"""
        # 記錄關閉指標
        self.record_metric("service.shutdown", 1, "count", {"service": "monitoring"})

        # 清理數據
        self._metrics.clear()
        self._health_statuses.clear()

        self.logger.info("監控服務已關閉")
