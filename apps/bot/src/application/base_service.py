"""
應用服務基礎類
定義應用服務層的通用介面和行為
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

import structlog

from src.utils.observability import get_tracer

logger = structlog.get_logger()
tracer = get_tracer(__name__)


class BaseApplicationService(ABC):
    """
    應用服務基礎抽象類

    應用服務層的職責：
    - 協調多個領域服務
    - 處理業務流程和工作流
    - 管理事務和一致性
    - 提供外部介面適配
    """

    def __init__(self, name: str):
        """
        初始化應用服務

        Args:
            name: 服務名稱，用於日誌和追蹤
        """
        self.name = name
        self.logger = logger.bind(service=name)
        self._initialized = False

    async def initialize(self) -> None:
        """
        初始化服務
        子類可以覆寫此方法進行特定初始化
        """
        if self._initialized:
            return

        self.logger.info("正在初始化應用服務")
        await self._initialize_service()
        self._initialized = True
        self.logger.info("應用服務初始化完成")

    @abstractmethod
    async def _initialize_service(self) -> None:
        """
        具體的初始化邏輯，由子類實現
        """
        pass

    @property
    def is_initialized(self) -> bool:
        """檢查服務是否已初始化"""
        return self._initialized

    def get_service_info(self) -> Dict[str, Any]:
        """
        獲取服務資訊

        Returns:
            服務基本資訊
        """
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "initialized": self._initialized,
            "description": self.__doc__.strip().split("\n")[0] if self.__doc__ else "",
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        健康檢查

        Returns:
            健康狀態資訊
        """
        with tracer.start_as_current_span("health_check") as span:
            span.set_attribute("service.name", self.name)

            try:
                # 基本健康檢查
                health_data: Dict[str, Any] = {
                    "service": self.name,
                    "status": "healthy" if self._initialized else "not_initialized",
                    "checks": {},
                }

                # 執行具體的健康檢查
                if self._initialized:
                    service_checks = await self._perform_health_checks()
                    if isinstance(service_checks, dict):
                        health_data["checks"].update(service_checks)

                # 評估整體健康狀態
                if health_data["checks"]:
                    failed_checks = [
                        k
                        for k, v in health_data["checks"].items()
                        if v.get("status") != "healthy"
                    ]
                    if failed_checks:
                        health_data["status"] = "unhealthy"
                        health_data["failed_checks"] = failed_checks

                return health_data

            except Exception as e:
                self.logger.error("健康檢查失敗", error=str(e))
                return {"service": self.name, "status": "error", "error": str(e)}

    async def _perform_health_checks(self) -> Dict[str, Dict[str, Any]]:
        """
        執行具體的健康檢查
        子類可以覆寫此方法

        Returns:
            健康檢查結果字典
        """
        return {}

    async def shutdown(self) -> None:
        """
        關閉服務
        清理資源和連接
        """
        if not self._initialized:
            return

        self.logger.info("正在關閉應用服務")
        try:
            await self._shutdown_service()
        except Exception as e:
            self.logger.error("關閉服務時發生錯誤", error=str(e))
        finally:
            self._initialized = False
            self.logger.info("應用服務已關閉")

    @abstractmethod
    async def _shutdown_service(self) -> None:
        """
        具體的關閉邏輯，由子類實現
        """
        pass


class ApplicationServiceContext:
    """
    應用服務上下文
    提供跨服務的共享資源和配置
    """

    def __init__(self):
        self.services: Dict[str, BaseApplicationService] = {}
        self.shared_config: Dict[str, Any] = {}
        self._initialized = False

    def register_service(self, service: BaseApplicationService) -> None:
        """
        註冊應用服務

        Args:
            service: 要註冊的應用服務
        """
        if service.name in self.services:
            raise ValueError(f"服務 '{service.name}' 已經註冊")

        self.services[service.name] = service
        logger.info("已註冊應用服務", service_name=service.name)

    def get_service(self, name: str) -> Optional[BaseApplicationService]:
        """
        獲取應用服務

        Args:
            name: 服務名稱

        Returns:
            應用服務實例，如果不存在則返回 None
        """
        return self.services.get(name)

    async def initialize_all(self) -> None:
        """初始化所有已註冊的服務"""
        if self._initialized:
            return

        logger.info("正在初始化所有應用服務")

        for service in self.services.values():
            try:
                await service.initialize()
            except Exception as e:
                logger.error("初始化服務失敗", service=service.name, error=str(e))
                raise

        self._initialized = True
        logger.info("所有應用服務初始化完成")

    async def shutdown_all(self) -> None:
        """關閉所有服務"""
        if not self._initialized:
            return

        logger.info("正在關閉所有應用服務")

        # 反向順序關閉服務
        for service in reversed(list(self.services.values())):
            try:
                await service.shutdown()
            except Exception as e:
                logger.error("關閉服務失敗", service=service.name, error=str(e))

        self._initialized = False
        logger.info("所有應用服務已關閉")

    async def health_check_all(self) -> Dict[str, Any]:
        """對所有服務進行健康檢查"""
        results: Dict[str, Any] = {
            "overall_status": "healthy",
            "services": {},
            "summary": {
                "total": len(self.services),
                "healthy": 0,
                "unhealthy": 0,
                "errors": 0,
            },
        }

        for service_name, service in self.services.items():
            try:
                health_result = await service.health_check()
                results["services"][service_name] = health_result

                status = health_result.get("status", "unknown")
                if status == "healthy":
                    results["summary"]["healthy"] += 1
                elif status == "unhealthy":
                    results["summary"]["unhealthy"] += 1
                    results["overall_status"] = "degraded"
                else:
                    results["summary"]["errors"] += 1
                    results["overall_status"] = "critical"

            except Exception as e:
                results["services"][service_name] = {"status": "error", "error": str(e)}
                results["summary"]["errors"] += 1
                results["overall_status"] = "critical"

        return results

    def get_context_info(self) -> Dict[str, Any]:
        """獲取上下文資訊"""
        return {
            "initialized": self._initialized,
            "total_services": len(self.services),
            "service_names": list(self.services.keys()),
            "shared_config_keys": list(self.shared_config.keys()),
        }


# 全域應用服務上下文
_application_context: Optional[ApplicationServiceContext] = None


def get_application_context() -> ApplicationServiceContext:
    """獲取全域應用服務上下文"""
    global _application_context
    if _application_context is None:
        _application_context = ApplicationServiceContext()
    return _application_context
