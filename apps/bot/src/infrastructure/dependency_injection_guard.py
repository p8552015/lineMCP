"""
依賴注入防護機制
提供裝飾器和上下文管理器來預防循環依賴
"""

import functools
import inspect
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any, TypeVar

import structlog

from .circular_dependency_detector import (
    DependencyType,
    get_circular_dependency_detector,
)

logger = structlog.get_logger()

T = TypeVar("T")


class CircularDependencyError(Exception):
    """循環依賴異常"""

    def __init__(self, cycle_path: list[str], message: str = ""):
        self.cycle_path = cycle_path
        self.message = message or f"檢測到循環依賴: {' -> '.join(cycle_path)}"
        super().__init__(self.message)


def dependency_guard(
    service_name: str = None,
    dependency_type: DependencyType = DependencyType.CONSTRUCTOR,
):
    """
    依賴注入防護裝飾器

    Args:
        service_name: 服務名稱，如果為 None 則使用類名
        dependency_type: 依賴類型
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # 確定服務名稱
            actual_service_name = service_name
            if actual_service_name is None:
                if inspect.isclass(func):
                    actual_service_name = func.__name__
                elif hasattr(func, "__self__") and hasattr(func.__self__, "__class__"):
                    actual_service_name = func.__self__.__class__.__name__
                else:
                    actual_service_name = func.__name__

            detector = get_circular_dependency_detector()

            # 開始解析
            if not detector.begin_resolution(actual_service_name):
                raise CircularDependencyError(
                    detector._resolution_stack + [actual_service_name],
                    f"循環依賴檢測：{actual_service_name} 正在解析中",
                )

            try:
                # 執行原函數
                result = func(*args, **kwargs)

                # 註冊服務類型
                if inspect.isclass(result):
                    detector.register_service_type(actual_service_name, result)
                elif hasattr(result, "__class__"):
                    detector.register_service_type(
                        actual_service_name, result.__class__
                    )

                logger.debug(f"成功創建服務: {actual_service_name}")
                return result

            finally:
                # 結束解析
                detector.end_resolution(actual_service_name)

        return wrapper

    return decorator


def service_dependency(
    from_service: str,
    to_service: str,
    dependency_type: DependencyType = DependencyType.CONSTRUCTOR,
):
    """
    聲明服務依賴關係的裝飾器

    Args:
        from_service: 依賴源服務
        to_service: 依賴目標服務
        dependency_type: 依賴類型
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            detector = get_circular_dependency_detector()

            # 添加依賴並檢測循環
            report = detector.add_dependency(from_service, to_service, dependency_type)

            # 如果檢測到循環，拋出異常
            if report.result.value == "cycle_detected":
                error_msg = f"循環依賴檢測失敗: {' -> '.join(report.cycle_path)}"
                if report.suggestions:
                    error_msg += "\n建議解決方案:\n" + "\n".join(report.suggestions)
                raise CircularDependencyError(report.cycle_path, error_msg)

            return func(*args, **kwargs)

        return wrapper

    return decorator


@contextmanager
def dependency_resolution_context(service_name: str) -> Generator[None, None, None]:
    """
    依賴解析上下文管理器

    Args:
        service_name: 正在解析的服務名稱
    """
    detector = get_circular_dependency_detector()

    if not detector.begin_resolution(service_name):
        raise CircularDependencyError(
            detector._resolution_stack + [service_name],
            f"循環依賴檢測：{service_name} 正在解析中",
        )

    try:
        yield
    finally:
        detector.end_resolution(service_name)


class DependencyInjectionGuard:
    """
    依賴注入防護類
    提供更高級的防護功能
    """

    def __init__(self):
        self.detector = get_circular_dependency_detector()

    def safe_inject(self, service_class: type[T], *args, **kwargs) -> T:
        """
        安全的依賴注入

        Args:
            service_class: 服務類
            *args, **kwargs: 構造參數

        Returns:
            服務實例

        Raises:
            CircularDependencyError: 如果檢測到循環依賴
        """
        service_name = service_class.__name__

        with dependency_resolution_context(service_name):
            # 分析構造函數依賴
            self._analyze_constructor_dependencies(service_class, args, kwargs)

            # 創建服務實例
            instance = service_class(*args, **kwargs)

            # 註冊服務類型
            self.detector.register_service_type(service_name, service_class)

            return instance

    def _analyze_constructor_dependencies(
        self, service_class: type, args: tuple, kwargs: dict
    ) -> None:
        """分析構造函數依賴"""
        signature = inspect.signature(service_class.__init__)
        service_name = service_class.__name__

        # 分析參數中的服務依賴
        bound_args = signature.bind_partial(None, *args, **kwargs)  # None for self

        for param_name, value in bound_args.arguments.items():
            if param_name == "self":
                continue

            # 檢查參數是否是服務實例
            if hasattr(value, "__class__") and hasattr(value.__class__, "__name__"):
                dependency_name = value.__class__.__name__

                # 如果依賴名稱包含服務相關關鍵字，記錄依賴
                if any(
                    keyword in dependency_name.lower()
                    for keyword in [
                        "service",
                        "factory",
                        "client",
                        "handler",
                        "manager",
                    ]
                ):

                    report = self.detector.add_dependency(
                        service_name, dependency_name, DependencyType.CONSTRUCTOR
                    )

                    if report.result.value == "cycle_detected":
                        raise CircularDependencyError(
                            report.cycle_path,
                            f"構造函數依賴循環: {service_name} -> {dependency_name}",
                        )

    def validate_factory_method(self, factory_func: Callable, *args, **kwargs) -> Any:
        """
        驗證工廠方法的安全性

        Args:
            factory_func: 工廠函數
            *args, **kwargs: 工廠參數

        Returns:
            工廠方法結果
        """
        factory_name = getattr(factory_func, "__name__", "unknown_factory")

        with dependency_resolution_context(factory_name):
            return factory_func(*args, **kwargs)

    def check_system_health(self) -> dict[str, Any]:
        """檢查系統依賴健康狀況"""
        risk_analysis = self.detector.analyze_dependency_risks()
        graph_summary = self.detector.get_dependency_graph_summary()

        health_status = {
            "status": "healthy",
            "risk_level": "low",
            "issues": [],
            "recommendations": [],
            "metrics": graph_summary,
        }

        # 評估風險等級
        if risk_analysis["high_risk_services"]:
            health_status["risk_level"] = "high"
            health_status["status"] = "warning"
            health_status["issues"].append(
                f"發現 {len(risk_analysis['high_risk_services'])} 個高風險服務"
            )

        if graph_summary["cycles_detected"] > 0:
            health_status["risk_level"] = "critical"
            health_status["status"] = "error"
            health_status["issues"].append(
                f"檢測到 {graph_summary['cycles_detected']} 個循環依賴"
            )

        health_status["recommendations"] = risk_analysis.get("recommendations", [])

        return health_status


# 全局防護實例
_global_guard: DependencyInjectionGuard | None = None


def get_dependency_guard() -> DependencyInjectionGuard:
    """獲取全局依賴注入防護實例"""
    global _global_guard
    if _global_guard is None:
        _global_guard = DependencyInjectionGuard()
    return _global_guard


# 便利函數
def safe_service_creation(service_class: type[T]) -> Callable[..., T]:
    """
    安全服務創建裝飾器工廠

    Returns:
        服務創建裝飾器
    """
    return dependency_guard(service_class.__name__, DependencyType.FACTORY)
