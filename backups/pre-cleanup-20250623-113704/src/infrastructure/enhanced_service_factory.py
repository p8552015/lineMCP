"""
增強版服務工廠
使用服務註冊表實現更靈活的依賴注入
"""
from typing import Optional, Any, Dict, Type
import structlog

from .service_factory_interface import IServiceFactory
from .service_registry import (
    ServiceRegistry,
    ServiceProvider,
    ServiceScope,
    get_service_registry
)
from src.services.ai_model_service import AIModelService
from src.services.database_service import DatabaseService
from src.services.message_formatter import MessageFormatter
from src.services.message_handler_di import MessageHandlerDI
from src.services.nl_to_sql_service import NaturalLanguageToSQLService

# 新的 SOLID 重構組件
from src.services.nl_to_sql.interfaces.parsing_interfaces import IParser
from src.services.nl_to_sql.interfaces.query_builder_interfaces import IQueryBuilder, ITemplateManager
from src.services.nl_to_sql.interfaces.statistics_interfaces import IStatistics, IConfiguration
from src.services.nl_to_sql.parsers.rule_based_parser import RuleBasedParser
from src.services.nl_to_sql.parsers.ai_enhanced_parser import AIEnhancedParser
from src.services.nl_to_sql.parsers.composite_parser import CompositeParser
from src.services.nl_to_sql.builders.sql_query_builder import SQLQueryBuilder
from src.services.nl_to_sql.builders.query_template_manager import QueryTemplateManager
from src.services.nl_to_sql.services.configuration_service import ConfigurationService
from src.services.nl_to_sql.services.query_statistics_service import QueryStatisticsService
from src.services.openai_client import OpenAIClient
from src.services.unified_mcp_client import get_unified_mcp_client
from src.services.mcp_response_parser import MCPResponseParser
# from src.services.error_handlers import ErrorHandler  # 暫時註解掉
from src.domain.command_executor import CommandExecutor
from src.domain.command_handler import CommandContext
from src.application.messaging_service import MessagingApplicationService
from src.application.query_service import QueryApplicationService
from src.application.monitoring_service import MonitoringApplicationService
from src.application.base_service import ApplicationServiceContext

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
    
    def __init__(self, registry: Optional[ServiceRegistry] = None):
        self._registry = registry or get_service_registry()
        self._provider: Optional[ServiceProvider] = None
        self._initialized = False
        
    def initialize(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化服務工廠
        
        Args:
            config: 配置字典
        """
        if self._initialized:
            return
            
        logger.info("初始化增強版服務工廠")
        
        # 註冊所有服務
        self._register_core_services()
        self._register_domain_services()
        self._register_application_services()
        self._register_infrastructure_services()
        self._register_nl_to_sql_services()  # 新增 SOLID 重構服務
        
        # 創建服務提供者
        self._provider = self._registry.create_provider()
        
        self._initialized = True
        logger.info("服務工廠初始化完成")
        
    def _register_core_services(self):
        """註冊核心服務"""
        # AI 和 OpenAI 服務
        self._registry.register_singleton(
            AIModelService,
            tags=["core", "ai"],
            metadata={"description": "AI 模型服務"}
        )
        
        self._registry.register_singleton(
            OpenAIClient,
            tags=["core", "ai", "external"],
            metadata={"description": "OpenAI 客戶端"}
        )
        
        # 訊息格式化服務
        self._registry.register_singleton(
            MessageFormatter,
            tags=["core", "formatting"],
            metadata={"description": "訊息格式化器"}
        )
        
        # MCP 相關服務
        self._registry.register_factory(
            Type[Any],  # MCP Client type
            lambda provider: get_unified_mcp_client,
            scope=ServiceScope.SINGLETON
        )
        
        self._registry.register_singleton(
            MCPResponseParser,
            tags=["core", "mcp", "parsing"],
            metadata={"description": "MCP 回應解析器"}
        )
        
    def _register_domain_services(self):
        """註冊領域服務"""
        # 自然語言處理服務
        self._registry.register_factory(
            NaturalLanguageToSQLService,
            lambda provider: NaturalLanguageToSQLService(
                provider.get_required_service(AIModelService)
            ),
            scope=ServiceScope.SINGLETON
        )
        
        # 資料庫服務
        self._registry.register_factory(
            DatabaseService,
            lambda provider: DatabaseService(get_unified_mcp_client),
            scope=ServiceScope.SINGLETON
        )
        
        # 錯誤處理器（暫時註解掉）
        # self._registry.register_singleton(
        #     ErrorHandler,
        #     tags=["domain", "error-handling"],
        #     metadata={"description": "統一錯誤處理器"}
        # )
        
        # 指令執行器（瞬態，每次創建新實例）
        self._registry.register_factory(
            CommandExecutor,
            lambda provider: self._create_command_executor(provider),
            scope=ServiceScope.TRANSIENT
        )
        
    def _register_application_services(self):
        """註冊應用服務"""
        # 應用服務上下文
        self._registry.register_singleton(
            ApplicationServiceContext,
            tags=["application", "context"],
            metadata={"description": "應用服務上下文"}
        )
        
        # 訊息處理應用服務
        self._registry.register_factory(
            MessagingApplicationService,
            lambda provider: self._create_messaging_service(provider),
            scope=ServiceScope.SINGLETON
        )
        
        # 查詢應用服務
        self._registry.register_factory(
            QueryApplicationService,
            lambda provider: QueryApplicationService(
                mcp_client_factory=get_unified_mcp_client,
                db_service=provider.get_required_service(DatabaseService),
                response_parser=provider.get_required_service(MCPResponseParser)
            ),
            scope=ServiceScope.SINGLETON
        )
        
        # 監控應用服務
        self._registry.register_factory(
            MonitoringApplicationService,
            lambda provider: MonitoringApplicationService(
                service_context=provider.get_required_service(ApplicationServiceContext)
            ),
            scope=ServiceScope.SINGLETON
        )
        
        # 移除 ApplicationFacade 相關的註冊邏輯
        
    def _register_infrastructure_services(self):
        """註冊基礎設施服務"""
        # 訊息處理器（使用依賴注入）
        self._registry.register_factory(
            MessageHandlerDI,
            lambda provider: self._create_message_handler(provider),
            scope=ServiceScope.TRANSIENT
        )
    
    def _register_nl_to_sql_services(self):
        """註冊 NL-to-SQL SOLID 重構服務"""
        logger.info("註冊 NL-to-SQL SOLID 重構服務")
        
        # 1. 配置和統計服務（基礎服務）
        self._registry.register_singleton(
            ConfigurationService,
            tags=["nl-to-sql", "configuration", "core"],
            metadata={"description": "NL-to-SQL 配置管理服務"}
        )
        
        self._registry.register_singleton(
            QueryStatisticsService,
            tags=["nl-to-sql", "statistics", "monitoring"],
            metadata={"description": "查詢統計追蹤服務"}
        )
        
        # 2. 模板管理器（依賴配置服務）
        self._registry.register_factory(
            QueryTemplateManager,
            lambda provider: QueryTemplateManager(
                configuration=provider.get_required_service(ConfigurationService)
            ),
            scope=ServiceScope.SINGLETON
        )
        
        # 3. 查詢建構器（依賴模板管理器）
        self._registry.register_factory(
            SQLQueryBuilder,
            lambda provider: SQLQueryBuilder(
                template_manager=provider.get_required_service(QueryTemplateManager)
            ),
            scope=ServiceScope.SINGLETON
        )
        
        # 4. 解析器（依賴配置服務）
        self._registry.register_factory(
            RuleBasedParser,
            lambda provider: RuleBasedParser(
                configuration=provider.get_required_service(ConfigurationService)
            ),
            scope=ServiceScope.SINGLETON
        )
        
        self._registry.register_factory(
            AIEnhancedParser,
            lambda provider: AIEnhancedParser(
                ai_model_service=provider.get_required_service(AIModelService)
            ),
            scope=ServiceScope.SINGLETON
        )
        
        # 5. 組合解析器（策略協調器）
        self._registry.register_factory(
            CompositeParser,
            lambda provider: self._create_composite_parser(provider),
            scope=ServiceScope.SINGLETON
        )
        
        # 6. 介面註冊（供依賴注入使用）
        # 使用 register_factory 方法正確註冊介面工廠函數
        self._registry.register_factory(
            IConfiguration,
            lambda provider: provider.get_required_service(ConfigurationService),
            scope=ServiceScope.SINGLETON
        )
        self._registry.register_factory(
            IStatistics,
            lambda provider: provider.get_required_service(QueryStatisticsService),
            scope=ServiceScope.SINGLETON
        )
        self._registry.register_factory(
            ITemplateManager,
            lambda provider: provider.get_required_service(QueryTemplateManager),
            scope=ServiceScope.SINGLETON
        )
        self._registry.register_factory(
            IQueryBuilder,
            lambda provider: provider.get_required_service(SQLQueryBuilder),
            scope=ServiceScope.SINGLETON
        )
        self._registry.register_factory(
            IParser,
            lambda provider: provider.get_required_service(CompositeParser),  # 預設使用組合解析器
            scope=ServiceScope.SINGLETON
        )
        
        logger.info("NL-to-SQL SOLID 重構服務註冊完成")
    
    def _create_composite_parser(self, provider: ServiceProvider) -> CompositeParser:
        """創建組合解析器並配置策略"""
        composite_parser = CompositeParser()
        
        # 添加規則解析器
        rule_parser = provider.get_required_service(RuleBasedParser)
        composite_parser.add_parser(rule_parser, weight=1.0)
        
        # 添加 AI 增強解析器
        ai_parser = provider.get_required_service(AIEnhancedParser)
        composite_parser.add_parser(ai_parser, weight=1.2)
        
        # 設定回退門檻
        composite_parser.set_fallback_threshold(0.5)
        
        logger.info("組合解析器配置完成", 
                   parser_count=2, 
                   fallback_threshold=0.5)
        
        return composite_parser
        
    def _create_command_executor(self, provider: ServiceProvider) -> CommandExecutor:
        """創建指令執行器"""
        context = CommandContext(
            mcp_client_factory=get_unified_mcp_client,
            ai_model_service=provider.get_required_service(AIModelService),
            nl_service=provider.get_required_service(NaturalLanguageToSQLService),
            db_service=provider.get_required_service(DatabaseService),
            formatter=provider.get_required_service(MessageFormatter),
            openai_client=provider.get_service(OpenAIClient)
        )
        
        executor = CommandExecutor(context)
        executor.initialize()
        return executor
        
    def _create_messaging_service(self, provider: ServiceProvider) -> MessagingApplicationService:
        """創建訊息處理應用服務"""
        context = CommandContext(
            mcp_client_factory=get_unified_mcp_client,
            ai_model_service=provider.get_required_service(AIModelService),
            nl_service=provider.get_required_service(NaturalLanguageToSQLService),
            db_service=provider.get_required_service(DatabaseService),
            formatter=provider.get_required_service(MessageFormatter),
            openai_client=provider.get_service(OpenAIClient)
        )
        
        return MessagingApplicationService(
            command_context=context,
            nl_service=provider.get_required_service(NaturalLanguageToSQLService),
            message_formatter=provider.get_required_service(MessageFormatter)
        )
        
    def _create_message_handler(self, provider: ServiceProvider) -> MessageHandlerDI:
        """創建訊息處理器"""
        return MessageHandlerDI(
            mcp_client_factory=get_unified_mcp_client,
            ai_model_service=provider.get_required_service(AIModelService),
            nl_service=provider.get_required_service(NaturalLanguageToSQLService),
            db_service=provider.get_required_service(DatabaseService),
            formatter=provider.get_required_service(MessageFormatter),
            openai_client=provider.get_service(OpenAIClient)
        )
        
    def get_service(self, service_type: Type) -> Optional[Any]:
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
        
    def get_required_service(self, service_type: Type) -> Any:
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
        
    def get_registry_info(self) -> Dict[str, Any]:
        """獲取註冊表資訊"""
        all_descriptors = self._registry.get_all_descriptors()
        
        info = {
            "total_services": sum(len(descs) for descs in all_descriptors.values()),
            "service_types": [getattr(t, '__name__', str(t)) for t in all_descriptors.keys()],
            "by_scope": {},
            "by_tag": {}
        }
        
        # 按作用域分類
        for scope in ServiceScope:
            count = sum(
                1 for descs in all_descriptors.values()
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
    def get_ai_model_service(self) -> AIModelService:
        """獲取 AI 模型服務實例"""
        return self.get_required_service(AIModelService)
        
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


# 全域增強版服務工廠實例
_enhanced_factory: Optional[EnhancedServiceFactory] = None


def get_enhanced_service_factory() -> EnhancedServiceFactory:
    """獲取全域增強版服務工廠實例"""
    global _enhanced_factory
    if _enhanced_factory is None:
        _enhanced_factory = EnhancedServiceFactory()
        logger.info("增強版服務工廠已創建")
    return _enhanced_factory