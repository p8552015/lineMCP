"""
增強版服務工廠
使用服務註冊表實現更靈活的依賴注入
重構為模組化架構以提升可維護性
"""

import time
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
from src.services.unified_mcp_client import get_unified_mcp_client

# 整合 nodecomman 架構
try:
    from src.services.enhanced_mcp_client import get_enhanced_mcp_client
    from src.config.enhanced_mcp_config import get_enhanced_mcp_config
    ENHANCED_MCP_AVAILABLE = True
except ImportError:
    ENHANCED_MCP_AVAILABLE = False

# 循環依賴檢測
from .circular_dependency_detector import get_circular_dependency_detector
from .dependency_injection_guard import (
    DependencyInjectionGuard,
    dependency_guard,
    get_dependency_guard,
)

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
        
        # 循環依賴檢測器
        self._dependency_detector = get_circular_dependency_detector()
        self._dependency_guard = get_dependency_guard()

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
        
        # 註冊 nodecomman 增強服務
        self._register_enhanced_mcp_services()

        # 創建服務提供者
        self._provider = self._registry.create_provider()

        self._initialized = True
        logger.info("服務工廠初始化完成")

    def get_service(self, service_type: type) -> Any | None:
        """
        獲取服務實例（帶循環依賴檢測）

        Args:
            service_type: 服務類型

        Returns:
            服務實例
        """
        if not self._initialized:
            self.initialize()

        # 使用依賴防護進行安全注入
        service_name = getattr(service_type, '__name__', str(service_type))
        
        try:
            # 檢查是否正在解析此服務（避免循環）
            if not self._dependency_detector.begin_resolution(service_name):
                logger.warning(f"檢測到循環依賴，跳過服務創建: {service_name}")
                return None
            
            try:
                service = self._provider.get_service(service_type)
                if service:
                    self._dependency_detector.register_service_type(service_name, service_type)
                return service
            finally:
                self._dependency_detector.end_resolution(service_name)
                
        except Exception as e:
            logger.warning(f"服務獲取失敗 {service_name}: {e}")
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
            "service_types": [getattr(t, "__name__", str(t)) for t in all_descriptors],
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
    
    def get_dependency_health_report(self) -> dict[str, Any]:
        """
        獲取依賴健康狀況報告
        
        Returns:
            包含循環依賴檢測、風險分析等的健康報告
        """
        try:
            # 獲取系統健康狀況
            health_status = self._dependency_guard.check_system_health()
            
            # 獲取註冊表資訊
            registry_info = self.get_registry_info()
            
            # 獲取依賴圖摘要
            graph_summary = self._dependency_detector.get_dependency_graph_summary()
            
            # 獲取風險分析
            risk_analysis = self._dependency_detector.analyze_dependency_risks()
            
            report = {
                "timestamp": time.time(),
                "overall_status": health_status["status"],
                "risk_level": health_status["risk_level"],
                "factory_info": {
                    "initialized": self._initialized,
                    "provider_available": self._provider is not None,
                    "registry_services": registry_info["total_services"]
                },
                "dependency_graph": graph_summary,
                "risk_analysis": {
                    "high_risk_services": len(risk_analysis.get("high_risk_services", [])),
                    "total_dependencies": risk_analysis.get("total_dependencies", 0),
                    "recommendations": risk_analysis.get("recommendations", [])
                },
                "issues": health_status.get("issues", []),
                "recommendations": health_status.get("recommendations", [])
            }
            
            # 添加具體的高風險服務詳情
            if risk_analysis.get("high_risk_services"):
                report["high_risk_services_detail"] = risk_analysis["high_risk_services"][:5]  # 顯示前5個
            
            return report
            
        except Exception as e:
            logger.error(f"獲取依賴健康報告失敗: {e}")
            return {
                "timestamp": time.time(),
                "overall_status": "error",
                "error": str(e),
                "factory_info": {
                    "initialized": self._initialized,
                    "provider_available": self._provider is not None
                }
            }
    
    def _register_enhanced_mcp_services(self):
        """註冊 nodecomman 增強 MCP 服務"""
        if not ENHANCED_MCP_AVAILABLE:
            logger.info("⚠️ nodecomman 增強服務不可用，跳過註冊")
            return
        
        try:
            logger.info("📋 註冊 nodecomman 增強 MCP 服務")
            
            # 註冊增強型 MCP 客戶端
            self._registry.register(
                service_type=type(get_enhanced_mcp_client()),
                implementation=lambda: get_enhanced_mcp_client(),
                scope=ServiceScope.SINGLETON,
                tags=["mcp", "enhanced", "nodecomman"],
                metadata={
                    "description": "增強型 MCP 客戶端，整合 nodecomman 架構",
                    "features": ["multi-runtime", "lifecycle-management", "fallback-support"],
                    "version": "1.0.0"
                }
            )
            
            # 註冊增強型 MCP 配置
            self._registry.register(
                service_type=type(get_enhanced_mcp_config()),
                implementation=lambda: get_enhanced_mcp_config(),
                scope=ServiceScope.SINGLETON,
                tags=["config", "enhanced", "nodecomman"],
                metadata={
                    "description": "增強型 MCP 配置管理，支援運行時檢測和驗證",
                    "features": ["runtime-detection", "config-validation", "optimization-suggestions"],
                    "version": "1.0.0"
                }
            )
            
            logger.info("✅ nodecomman 增強服務註冊完成")
            
        except Exception as e:
            logger.error(f"❌ 註冊 nodecomman 增強服務失敗: {e}")
    
    # 基本 MCP 服務方法（與原有服務工廠兼容）
    def get_mcp_config(self):
        """獲取 MCP 配置管理器"""
        from src.config.mcp_config import get_mcp_config
        return get_mcp_config()
    
    def get_mcp_connection_pool(self):
        """獲取 MCP 連接池"""
        from src.services.mcp_connection_pool import get_connection_pool
        return get_connection_pool()
    
    def get_enhanced_mcp_client(self):
        """獲取增強型 MCP 客戶端"""
        if ENHANCED_MCP_AVAILABLE:
            return get_enhanced_mcp_client()
        else:
            # 回退到統一 MCP 客戶端
            logger.warning("⚠️ 增強型 MCP 客戶端不可用，使用統一 MCP 客戶端")
            return get_unified_mcp_client()
    
    def get_enhanced_mcp_config(self):
        """獲取增強型 MCP 配置"""
        if ENHANCED_MCP_AVAILABLE:
            return get_enhanced_mcp_config()
        else:
            # 回退到基礎配置
            logger.warning("⚠️ 增強型 MCP 配置不可用，使用基礎配置")
            from src.config.mcp_config import get_mcp_config
            return get_mcp_config()

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

    def get_application_facade(self):
        """獲取應用門面實例"""
        from src.application.application_facade import ApplicationFacade
        return ApplicationFacade(self)


# 全域增強版服務工廠實例
_enhanced_factory: EnhancedServiceFactory | None = None


def get_enhanced_service_factory() -> EnhancedServiceFactory:
    """獲取全域增強版服務工廠實例"""
    global _enhanced_factory
    if _enhanced_factory is None:
        _enhanced_factory = EnhancedServiceFactory()
        logger.info("增強版服務工廠已創建")
    return _enhanced_factory
