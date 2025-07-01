"""
服務註冊表
提供動態服務註冊和解析機制
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class ServiceScope(Enum):
    """服務作用域"""

    SINGLETON = "singleton"  # 單例（全域唯一實例）
    TRANSIENT = "transient"  # 瞬態（每次請求創建新實例）
    SCOPED = "scoped"  # 作用域（同一請求內共享）


@dataclass
class ServiceDescriptor:
    """服務描述符"""

    service_type: type
    implementation: type | Callable | Any
    scope: ServiceScope = ServiceScope.SINGLETON
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        if self.tags is None:
            self.tags : list[Any] = []
        if self.metadata is None:
            self.metadata = {}


class IServiceProvider(ABC):
    """服務提供者介面"""

    @abstractmethod
    def get_service(self, service_type: type) -> Any:
        """獲取服務實例"""
        pass

    @abstractmethod
    def get_required_service(self, service_type: type) -> Any:
        """獲取必需的服務實例（找不到時拋出異常）"""
        pass

    @abstractmethod
    def get_services(self, service_type: type) -> list[Any]:
        """獲取指定類型的所有服務實例"""
        pass


class ServiceRegistry:
    """
    服務註冊表
    管理服務的註冊和生命週期
    """

    def __init__(self):
        self._descriptors: dict[type, list[ServiceDescriptor]] = {}
        self._singletons: dict[type, Any] = {}
        self._factories: dict[type, Callable] = {}

    def register(
        self,
        service_type: type,
        implementation: type | Callable | Any = None,
        scope: ServiceScope = ServiceScope.SINGLETON,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ServiceRegistry":
        """
        註冊服務

        Args:
            service_type: 服務介面類型
            implementation: 實現類型、工廠函數或實例
            scope: 服務作用域
            tags: 服務標籤
            metadata: 服務元數據

        Returns:
            服務註冊表實例（支援鏈式調用）
        """
        if implementation is None:
            implementation = service_type

        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            scope=scope,
            tags=tags or [],
            metadata=metadata or {},
        )

        if service_type not in self._descriptors:
            self._descriptors[service_type] : list[Any] = []

        self._descriptors[service_type].append(descriptor)

        logger.info(
            "服務已註冊",
            service_type=getattr(service_type, "__name__", str(service_type)),
            implementation=self._get_implementation_name(implementation),
            scope=scope.value,
        )

        return self

    def register_singleton(
        self,
        service_type: type,
        implementation: type | Callable | Any = None,
        **kwargs,
    ) -> "ServiceRegistry":
        """註冊單例服務"""
        return self.register(
            service_type, implementation, ServiceScope.SINGLETON, **kwargs
        )

    def register_transient(
        self,
        service_type: type,
        implementation: type | Callable | Any = None,
        **kwargs,
    ) -> "ServiceRegistry":
        """註冊瞬態服務"""
        return self.register(
            service_type, implementation, ServiceScope.TRANSIENT, **kwargs
        )

    def register_scoped(
        self,
        service_type: type,
        implementation: type | Callable | Any = None,
        **kwargs,
    ) -> "ServiceRegistry":
        """註冊作用域服務"""
        return self.register(
            service_type, implementation, ServiceScope.SCOPED, **kwargs
        )

    def register_factory(
        self,
        service_type: type,
        factory: Callable[["ServiceProvider"], Any],
        scope: ServiceScope = ServiceScope.SINGLETON,
    ) -> "ServiceRegistry":
        """
        註冊工廠函數

        Args:
            service_type: 服務類型
            factory: 工廠函數，接收 ServiceProvider 作為參數
            scope: 服務作用域
        """
        self._factories[service_type] = factory
        return self.register(service_type, factory, scope)

    def register_instance(self, service_type: type, instance: Any) -> "ServiceRegistry":
        """註冊已存在的實例作為單例"""
        self._singletons[service_type] = instance
        return self.register(service_type, instance, ServiceScope.SINGLETON)

    def unregister(self, service_type: type) -> bool:
        """
        取消註冊服務

        Args:
            service_type: 服務類型

        Returns:
            是否成功取消註冊
        """
        if service_type in self._descriptors:
            del self._descriptors[service_type]

            # 清理相關資源
            if service_type in self._singletons:
                del self._singletons[service_type]
            if service_type in self._factories:
                del self._factories[service_type]

            logger.info("服務已取消註冊", service_type=service_type.__name__)
            return True

        return False

    def has_service(self, service_type: type) -> bool:
        """檢查是否已註冊指定服務"""
        return service_type in self._descriptors

    def get_descriptor(self, service_type: type) -> ServiceDescriptor | None:
        """獲取服務描述符"""
        descriptors = self._descriptors.get(service_type, [])
        return descriptors[0] if descriptors else None

    def get_descriptors(self, service_type: type) -> list[ServiceDescriptor]:
        """獲取指定類型的所有服務描述符"""
        return self._descriptors.get(service_type, [])

    def get_all_descriptors(self) -> dict[type, list[ServiceDescriptor]]:
        """獲取所有服務描述符"""
        return self._descriptors.copy()

    def get_services_by_tag(self, tag: str) -> list[ServiceDescriptor]:
        """根據標籤獲取服務"""
        results : list[Any] = []
        for descriptors in self._descriptors.values():
            for descriptor in descriptors:
                if descriptor.tags is not None and tag in descriptor.tags:
                    results.append(descriptor)
        return results

    def create_provider(
        self, scope_context: dict[str, Any] | None = None
    ) -> "ServiceProvider":
        """
        創建服務提供者

        Args:
            scope_context: 作用域上下文（用於 SCOPED 服務）

        Returns:
            服務提供者實例
        """
        return ServiceProvider(self, scope_context)

    def clear(self):
        """清除所有註冊的服務"""
        self._descriptors.clear()
        self._singletons.clear()
        self._factories.clear()
        logger.info("服務註冊表已清空")

    def _get_implementation_name(self, implementation: Any) -> str:
        """獲取實現的名稱"""
        if hasattr(implementation, "__name__"):
            return str(implementation.__name__)
        elif hasattr(implementation, "__class__"):
            return str(implementation.__class__.__name__)
        else:
            return str(implementation)


class ServiceProvider(IServiceProvider):
    """
    服務提供者
    負責解析和創建服務實例
    """

    def __init__(
        self, registry: ServiceRegistry, scope_context: dict[str, Any] | None = None
    ):
        self._registry = registry
        self._scope_context = scope_context or {}
        self._scoped_instances: dict[type, Any] = {}

    def get_service(self, service_type: type) -> Any | None:
        """
        獲取服務實例

        Args:
            service_type: 服務類型

        Returns:
            服務實例，如果找不到則返回 None
        """
        descriptor = self._registry.get_descriptor(service_type)
        if not descriptor:
            return None

        return self._resolve_service(descriptor)

    def get_required_service(self, service_type: type) -> Any:
        """
        獲取必需的服務實例

        Args:
            service_type: 服務類型

        Returns:
            服務實例

        Raises:
            ValueError: 找不到服務時拋出
        """
        service = self.get_service(service_type)
        if service is None:
            raise ValueError(f"找不到必需的服務: {service_type.__name__}")
        return service

    def get_services(self, service_type: type) -> list[Any]:
        """
        獲取指定類型的所有服務實例

        Args:
            service_type: 服務類型

        Returns:
            服務實例列表
        """
        descriptors = self._registry.get_descriptors(service_type)
        return [self._resolve_service(desc) for desc in descriptors]

    def _resolve_service(self, descriptor: ServiceDescriptor) -> Any:
        """解析服務實例"""
        # 單例服務
        if descriptor.scope == ServiceScope.SINGLETON:
            if descriptor.service_type in self._registry._singletons:
                return self._registry._singletons[descriptor.service_type]

            instance = self._create_instance(descriptor)
            self._registry._singletons[descriptor.service_type] = instance
            return instance

        # 作用域服務
        elif descriptor.scope == ServiceScope.SCOPED:
            if descriptor.service_type in self._scoped_instances:
                return self._scoped_instances[descriptor.service_type]

            instance = self._create_instance(descriptor)
            self._scoped_instances[descriptor.service_type] = instance
            return instance

        # 瞬態服務
        else:
            return self._create_instance(descriptor)

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """創建服務實例"""
        implementation = descriptor.implementation

        # 如果是實例，直接返回
        if not isinstance(implementation, type) and not callable(implementation):
            return implementation

        # 如果是工廠函數
        if descriptor.service_type in self._registry._factories:
            factory = self._registry._factories[descriptor.service_type]
            return factory(self)

        # 如果是可調用對象（函數或類）
        if callable(implementation):
            # 嘗試自動注入依賴
            try:
                return self._auto_wire(implementation)
            except Exception as e:
                logger.error(
                    "創建服務實例失敗",
                    service_type=descriptor.service_type.__name__,
                    error=str(e),
                )
                raise

        raise ValueError(f"無法創建服務實例: {descriptor.service_type.__name__}")

    def _auto_wire(self, implementation: Callable) -> Any:
        """
        自動注入依賴
        分析構造函數參數並自動解析依賴
        """
        import inspect

        # 如果是函數，檢查是否需要參數
        if not inspect.isclass(implementation):
            try:
                sig = inspect.signature(implementation)
                if len(sig.parameters) > 0:
                    # 函數需要參數但這裡是 _auto_wire 路徑，
                    # 可能應該使用 register_factory
                    # 降級為 debug 級別，避免干擾正常日誌
                    logger.debug(
                        "函數需要參數但使用了 _auto_wire 路徑",
                        function=getattr(
                            implementation, "__name__", str(implementation)
                        ),
                        parameters=list(sig.parameters.keys()),
                    )
                    # 嘗試注入 self (ServiceProvider)
                    if len(sig.parameters) == 1 and "provider" in sig.parameters:
                        return implementation(self)
                return implementation()
            except Exception as e:
                logger.error(
                    "函數自動注入失敗",
                    function=getattr(implementation, "__name__", str(implementation)),
                    error=str(e),
                )
                raise

        # 獲取構造函數簽名
        sig = inspect.signature(implementation.__init__)
        kwargs = {}

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            # 嘗試根據類型註解解析依賴
            if param.annotation != inspect.Parameter.empty:
                service = self.get_service(param.annotation)
                if service is not None:
                    kwargs[param_name] = service
                elif param.default == inspect.Parameter.empty:
                    # 必需參數但找不到服務
                    raise ValueError(f"無法解析依賴: {param_name} ({param.annotation})")

        return implementation(**kwargs)


# 全域服務註冊表
_global_registry: ServiceRegistry | None = None


def get_service_registry() -> ServiceRegistry:
    """獲取全域服務註冊表"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ServiceRegistry()
    return _global_registry


def get_service_provider(
    scope_context: dict[str, Any] | None = None
) -> ServiceProvider:
    """獲取服務提供者"""
    registry = get_service_registry()
    return registry.create_provider(scope_context)
