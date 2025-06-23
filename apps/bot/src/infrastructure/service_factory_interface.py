"""
服務工廠介面定義
"""

from abc import ABC, abstractmethod
from typing import Any


class IServiceFactory(ABC):
    """
    服務工廠抽象介面

    定義了服務工廠必須實現的基本方法
    """

    @abstractmethod
    def get_service(self, service_type: type) -> Any | None:
        """
        獲取服務實例

        Args:
            service_type: 服務類型

        Returns:
            服務實例，如果不存在則返回 None
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def initialize(self, config: dict[str, Any] | None = None) -> None:
        """
        初始化服務工廠

        Args:
            config: 配置字典
        """
        pass
