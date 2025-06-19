"""
增強版服務工廠
使用服務註冊表實現更靈活的依賴注入
"""
from typing import Optional, Any, Dict, Type
import structlog

from .service_registry import (
    ServiceRegistry,
    ServiceProvider,
    ServiceScope,
    get_service_registry
)
from src.services.ai_model_service import AIModelService
from src.services.database_service import DatabaseService
from src.services.flex_builder import FlexBuilder
from src.services.message_formatter import MessageFormatter
from src.services.message_handler_di import MessageHandlerDI
from src.services.nl_to_sql_service import NaturalLanguageToSQLService
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


class EnhancedServiceFactory:
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
        
        self._registry.register_singleton(
            FlexBuilder,
            tags=["core", "formatting", "line"],
            metadata={"description": "LINE Flex 訊息建構器"}
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
        
        # 應用門面（延遲導入避免循環依賴）
        def create_application_facade_lazy(provider):
            from src.application.application_facade import ApplicationFacade
            return ApplicationFacade(self)
        
        # 註冊時使用字符串標識符
        self._registry.register_factory(
            "ApplicationFacade",
            create_application_facade_lazy,
            scope=ServiceScope.SINGLETON
        )
        
    def _register_infrastructure_services(self):
        """註冊基礎設施服務"""
        # 訊息處理器（使用依賴注入）
        self._registry.register_factory(
            MessageHandlerDI,
            lambda provider: self._create_message_handler(provider),
            scope=ServiceScope.TRANSIENT
        )
        
    def _create_command_executor(self, provider: ServiceProvider) -> CommandExecutor:
        """創建指令執行器"""
        context = CommandContext(
            mcp_client_factory=get_unified_mcp_client,
            ai_model_service=provider.get_required_service(AIModelService),
            nl_service=provider.get_required_service(NaturalLanguageToSQLService),
            db_service=provider.get_required_service(DatabaseService),
            formatter=provider.get_required_service(MessageFormatter),
            flex_builder=provider.get_required_service(FlexBuilder),
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
            flex_builder=provider.get_required_service(FlexBuilder),
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
            flex_builder=provider.get_required_service(FlexBuilder),
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
        
    def create_application_facade(self):
        """創建應用門面"""
        return self.get_required_service("ApplicationFacade")
        
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
        
    def get_flex_builder(self) -> FlexBuilder:
        """獲取 Flex 建構器實例"""
        return self.get_required_service(FlexBuilder)
        
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


# 全域增強版服務工廠實例
_enhanced_factory: Optional[EnhancedServiceFactory] = None


def get_enhanced_service_factory() -> EnhancedServiceFactory:
    """獲取全域增強版服務工廠實例"""
    global _enhanced_factory
    if _enhanced_factory is None:
        _enhanced_factory = EnhancedServiceFactory()
        logger.info("增強版服務工廠已創建")
    return _enhanced_factory