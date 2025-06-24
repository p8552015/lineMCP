"""
增強版服務工廠
使用服務註冊表實現更靈活的依賴注入
重構為模組化架構以提升可維護性
"""

from typing import Any

import structlog

from src.services.ai_model_service_enhanced import EnhancedAIModelService
from src.services.database_service import DatabaseService
from src.services.message_formatter import MessageFormatter

# 為兼容性保留的導入
from src.services.message_handler_di import MessageHandlerDI
from src.services.nl_to_sql.builders.query_template_manager import QueryTemplateManager
from src.services.nl_to_sql.builders.sql_query_builder import SQLQueryBuilder
from src.services.nl_to_sql.interfaces.parsing_interfaces import IParser
from src.services.nl_to_sql.interfaces.query_builder_interfaces import IQueryBuilder
from src.services.nl_to_sql.interfaces.statistics_interfaces import (
    IConfiguration,
    IStatistics,
)
from src.services.nl_to_sql.parsers.ai_enhanced_parser import AIEnhancedParser
from src.services.nl_to_sql.parsers.composite_parser import CompositeParser
from src.services.nl_to_sql.parsers.rule_based_parser import RuleBasedParser

# 為了獲取方法需要的導入
from src.services.nl_to_sql.services.configuration_service import ConfigurationService
from src.services.nl_to_sql.services.query_statistics_service import (
    QueryStatisticsService,
)
from src.services.nl_to_sql_service import NaturalLanguageToSQLService
from src.services.openai_client import OpenAIClient

from .application_services_registry import register_application_services

# 模組化註冊器
from .core_services_registry import register_core_services
from .infrastructure_services_registry import register_infrastructure_services
from .service_factory_interface import IServiceFactory
from .service_registry import (
    ServiceProvider,
    ServiceRegistry,
    ServiceScope,
    get_service_registry,
)

logger = structlog.get_logger()


class EnhancedServiceFactory(IServiceFactory):
    """
    增強版服務工廠

    特性：
    - 基於註冊表的服務管理
    - 支援多種服務作用域
    - 自動依賴注入
    - 服務標籤和元數據
    """

    def __init__(self, registry: ServiceRegistry | None = None):
        self._registry = registry or get_service_registry()
        self._provider: ServiceProvider | None = None
        self._initialized = False

    def initialize(self, config: dict[str, Any] | None = None):
        """
        初始化服務工廠

        Args:
            config: 配置字典
        """
        if self._initialized:
            return

        logger.info("初始化增強版服務工廠")

        # 使用模組化註冊器註冊所有服務
        register_core_services(self._registry)
        register_application_services(self._registry)
        register_infrastructure_services(self._registry)

        # 創建服務提供者
        self._provider = self._registry.create_provider()

        self._initialized = True
        logger.info("服務工廠初始化完成")

    def get_service(self, service_type: type) -> Any | None:
        """
        獲取服務實例

        Args:
            service_type: 服務類型

        Returns:
            服務實例
        """
        if not self._initialized:
            self.initialize()

        return self._provider.get_service(service_type)

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
        if not self._initialized:
            self.initialize()

        return self._provider.get_required_service(service_type)

    def create_message_handler(self) -> MessageHandlerDI:
        """創建訊息處理器"""
        return self.get_required_service(MessageHandlerDI)

    def get_registry_info(self) -> dict[str, Any]:
        """獲取註冊表資訊"""
        all_descriptors = self._registry.get_all_descriptors()

        info = {
            "total_services": sum(len(descs) for descs in all_descriptors.values()),
            "service_types": [
                getattr(t, "__name__", str(t)) for t in all_descriptors.keys()
            ],
            "by_scope": {},
            "by_tag": {},
        }

        # 按作用域分類
        for scope in ServiceScope:
            count = sum(
                1
                for descs in all_descriptors.values()
                for desc in descs
                if desc.scope == scope
            )
            info["by_scope"][scope.value] = count

        # 收集所有標籤
        all_tags = set()
        for descs in all_descriptors.values():
            for desc in descs:
                all_tags.update(desc.tags)

        # 按標籤分類
        for tag in all_tags:
            services = self._registry.get_services_by_tag(tag)
            info["by_tag"][tag] = len(services)

        return info

    # 保持與原有 ServiceFactory 的兼容性
    def get_ai_model_service(self) -> EnhancedAIModelService:
        """獲取 AI 模型服務實例"""
        return self.get_required_service(EnhancedAIModelService)

    def get_openai_client(self) -> OpenAIClient:
        """獲取 OpenAI 客戶端實例"""
        return self.get_required_service(OpenAIClient)

    def get_message_formatter(self) -> MessageFormatter:
        """獲取訊息格式化器實例"""
        return self.get_required_service(MessageFormatter)

    def get_nl_service(self) -> NaturalLanguageToSQLService:
        """獲取自然語言處理服務實例"""
        return self.get_required_service(NaturalLanguageToSQLService)

    def get_database_service(self) -> DatabaseService:
        """獲取資料庫服務實例"""
        return self.get_required_service(DatabaseService)

    async def get_mcp_client_factory(self):
        """MCP 客戶端工廠函數"""
        return await get_unified_mcp_client()

    # 新增的 SOLID 重構服務獲取方法
    def get_configuration_service(self) -> ConfigurationService:
        """獲取配置管理服務實例"""
        return self.get_required_service(ConfigurationService)

    def get_statistics_service(self) -> QueryStatisticsService:
        """獲取統計追蹤服務實例"""
        return self.get_required_service(QueryStatisticsService)

    def get_template_manager(self) -> QueryTemplateManager:
        """獲取模板管理器實例"""
        return self.get_required_service(QueryTemplateManager)

    def get_query_builder(self) -> SQLQueryBuilder:
        """獲取查詢建構器實例"""
        return self.get_required_service(SQLQueryBuilder)

    def get_rule_parser(self) -> RuleBasedParser:
        """獲取規則解析器實例"""
        return self.get_required_service(RuleBasedParser)

    def get_ai_parser(self) -> AIEnhancedParser:
        """獲取 AI 解析器實例"""
        return self.get_required_service(AIEnhancedParser)

    def get_composite_parser(self) -> CompositeParser:
        """獲取組合解析器實例"""
        return self.get_required_service(CompositeParser)

    # 介面版本的獲取方法
    def get_parser(self) -> IParser:
        """獲取預設解析器（組合解析器）"""
        return self.get_required_service(IParser)

    def get_builder(self) -> IQueryBuilder:
        """獲取預設查詢建構器"""
        return self.get_required_service(IQueryBuilder)

    def get_configuration(self) -> IConfiguration:
        """獲取配置服務介面"""
        return self.get_required_service(IConfiguration)

    def get_statistics(self) -> IStatistics:
        """獲取統計服務介面"""
        return self.get_required_service(IStatistics)

    def get_health_status(self) -> dict[str, Any]:
        """獲取服務工廠健康狀態"""
        try:
            registry_info = self.get_registry_info()
            return {
                "healthy": self._initialized and self._provider is not None,
                "services_count": registry_info.get("total_services", 0),
                "details": registry_info,
            }
        except Exception as e:
            return {"healthy": False, "services_count": 0, "error": str(e)}

    def get_ai_service(self) -> EnhancedAIModelService | None:
        """獲取 AI 服務（用於健康檢查）"""
        try:
            return self.get_service(EnhancedAIModelService)
        except Exception:
            return None


# 全域增強版服務工廠實例
_enhanced_factory: EnhancedServiceFactory | None = None


def get_enhanced_service_factory() -> EnhancedServiceFactory:
    """獲取全域增強版服務工廠實例"""
    global _enhanced_factory
    if _enhanced_factory is None:
        _enhanced_factory = EnhancedServiceFactory()
        logger.info("增強版服務工廠已創建")
    return _enhanced_factory
