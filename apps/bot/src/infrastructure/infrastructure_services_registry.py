"""
基礎設施服務註冊模組
負責註冊基礎設施和領域服務：數據庫、NL-to-SQL、指令執行器、訊息處理器等
"""

import structlog

from src.domain.command_executor import CommandExecutor
from src.domain.command_handler import CommandContext
from src.services.ai_model_service import AIModelService
from src.services.database_service import DatabaseService
from src.services.message_formatter import MessageFormatter
from src.services.message_handler_di import MessageHandlerDI
from src.services.nl_to_sql.builders.query_template_manager import QueryTemplateManager
from src.services.nl_to_sql.builders.sql_query_builder import SQLQueryBuilder

# NL-to-SQL SOLID 重構組件
from src.services.nl_to_sql.interfaces.parsing_interfaces import IParser
from src.services.nl_to_sql.interfaces.query_builder_interfaces import (
    IQueryBuilder,
    ITemplateManager,
)
from src.services.nl_to_sql.interfaces.statistics_interfaces import (
    IConfiguration,
    IStatistics,
)
from src.services.nl_to_sql.parsers.ai_enhanced_parser import AIEnhancedParser
from src.services.nl_to_sql.parsers.composite_parser import CompositeParser
from src.services.nl_to_sql.parsers.rule_based_parser import RuleBasedParser
from src.services.nl_to_sql.services.configuration_service import ConfigurationService
from src.services.nl_to_sql.services.query_statistics_service import (
    QueryStatisticsService,
)
from src.services.nl_to_sql_service import NaturalLanguageToSQLService
from src.services.openai_client import OpenAIClient
from src.services.unified_mcp_client import get_unified_mcp_client

from .service_registry import ServiceProvider, ServiceRegistry, ServiceScope

logger = structlog.get_logger()


def register_infrastructure_services(registry: ServiceRegistry) -> None:
    """
    註冊基礎設施和領域服務

    Args:
        registry: 服務註冊表實例
    """
    logger.debug("開始註冊基礎設施和領域服務")

    # 註冊領域服務
    _register_domain_services(registry)

    # 註冊基礎設施服務
    _register_infrastructure_services(registry)

    # 註冊 NL-to-SQL 服務
    _register_nl_to_sql_services(registry)

    logger.info("基礎設施和領域服務註冊完成")


def _register_domain_services(registry: ServiceRegistry) -> None:
    """註冊領域服務"""
    logger.debug("註冊領域服務")

    # 自然語言處理服務
    registry.register_factory(
        NaturalLanguageToSQLService,
        lambda provider: NaturalLanguageToSQLService(
            provider.get_required_service(AIModelService)
        ),
        scope=ServiceScope.SINGLETON,
    )

    # 新一代 MCP 客戶端管理器（暫時註解，避免異步問題）
    # registry.register_factory(
    #     "mcp_client_manager",
    #     lambda provider: get_mcp_client_manager(),
    #     scope=ServiceScope.SINGLETON,
    # )

    # 資料庫服務（保持向下兼容）
    registry.register_factory(
        DatabaseService,
        lambda provider: DatabaseService(get_unified_mcp_client),
        scope=ServiceScope.SINGLETON,
    )

    # 指令執行器（瞬態，每次創建新實例）
    registry.register_factory(
        CommandExecutor,
        lambda provider: _create_command_executor(provider),
        scope=ServiceScope.TRANSIENT,
    )


def _register_infrastructure_services(registry: ServiceRegistry) -> None:
    """註冊基礎設施服務"""
    logger.debug("註冊基礎設施服務")

    # 訊息處理器（使用依賴注入）
    registry.register_factory(
        MessageHandlerDI,
        lambda provider: _create_message_handler(provider),
        scope=ServiceScope.TRANSIENT,
    )


def _register_nl_to_sql_services(registry: ServiceRegistry) -> None:
    """註冊 NL-to-SQL SOLID 重構服務"""
    logger.info("註冊 NL-to-SQL SOLID 重構服務")

    # 1. 配置和統計服務（基礎服務）
    registry.register_singleton(
        ConfigurationService,
        tags=["nl-to-sql", "configuration", "core"],
        metadata={"description": "NL-to-SQL 配置管理服務"},
    )

    registry.register_singleton(
        QueryStatisticsService,
        tags=["nl-to-sql", "statistics", "monitoring"],
        metadata={"description": "查詢統計追蹤服務"},
    )

    # 2. 模板管理器（依賴配置服務）
    registry.register_factory(
        QueryTemplateManager,
        lambda provider: QueryTemplateManager(
            configuration=provider.get_required_service(ConfigurationService)
        ),
        scope=ServiceScope.SINGLETON,
    )

    # 3. 查詢建構器（依賴模板管理器）
    registry.register_factory(
        SQLQueryBuilder,
        lambda provider: SQLQueryBuilder(
            template_manager=provider.get_required_service(QueryTemplateManager)
        ),
        scope=ServiceScope.SINGLETON,
    )

    # 4. 解析器（依賴配置服務）
    registry.register_factory(
        RuleBasedParser,
        lambda provider: RuleBasedParser(
            configuration=provider.get_required_service(ConfigurationService)
        ),
        scope=ServiceScope.SINGLETON,
    )

    registry.register_factory(
        AIEnhancedParser,
        lambda provider: AIEnhancedParser(
            ai_model_service=provider.get_required_service(AIModelService)
        ),
        scope=ServiceScope.SINGLETON,
    )

    # 5. 組合解析器（策略協調器）
    registry.register_factory(
        CompositeParser,
        lambda provider: _create_composite_parser(provider),
        scope=ServiceScope.SINGLETON,
    )

    # 6. 介面註冊（供依賴注入使用）
    registry.register_factory(
        IConfiguration,
        lambda provider: provider.get_required_service(ConfigurationService),
        scope=ServiceScope.SINGLETON,
    )
    registry.register_factory(
        IStatistics,
        lambda provider: provider.get_required_service(QueryStatisticsService),
        scope=ServiceScope.SINGLETON,
    )
    registry.register_factory(
        ITemplateManager,
        lambda provider: provider.get_required_service(QueryTemplateManager),
        scope=ServiceScope.SINGLETON,
    )
    registry.register_factory(
        IQueryBuilder,
        lambda provider: provider.get_required_service(SQLQueryBuilder),
        scope=ServiceScope.SINGLETON,
    )
    registry.register_factory(
        IParser,
        lambda provider: provider.get_required_service(CompositeParser),  # 預設使用組合解析器
        scope=ServiceScope.SINGLETON,
    )

    logger.info("NL-to-SQL SOLID 重構服務註冊完成")


def _create_composite_parser(provider: ServiceProvider) -> CompositeParser:
    """創建組合解析器並配置策略"""
    composite_parser = CompositeParser()

    # 🔥 修復：AI 解析器優先，權重更高
    # 添加 AI 增強解析器（優先）
    ai_parser = provider.get_required_service(AIEnhancedParser)
    composite_parser.add_parser(ai_parser, weight=2.0)

    # 添加規則解析器（備用）
    rule_parser = provider.get_required_service(RuleBasedParser)
    composite_parser.add_parser(rule_parser, weight=1.0)

    # 🔥 修復：降低回退門檻，讓更多查詢能被 AI 處理
    composite_parser.set_fallback_threshold(0.3)

    logger.info(
        "組合解析器配置完成（AI 優先）",
        parser_count=2,
        fallback_threshold=0.3,
        ai_weight=2.0,
        rule_weight=1.0,
    )

    return composite_parser


def _create_command_executor(provider: ServiceProvider) -> CommandExecutor:
    """創建指令執行器"""
    context = CommandContext(
        mcp_client_factory=get_unified_mcp_client,
        ai_model_service=provider.get_required_service(AIModelService),
        nl_service=provider.get_required_service(NaturalLanguageToSQLService),
        db_service=provider.get_required_service(DatabaseService),
        formatter=provider.get_required_service(MessageFormatter),
        service_factory=None,  # 避免循環依賴，與 MessagingApplicationService 保持一致
        openai_client=provider.get_service(OpenAIClient),
    )

    executor = CommandExecutor(context)
    executor.initialize()
    return executor


def _create_message_handler(provider: ServiceProvider) -> MessageHandlerDI:
    """創建訊息處理器"""
    return MessageHandlerDI(
        mcp_client_factory=get_unified_mcp_client,
        ai_model_service=provider.get_required_service(AIModelService),
        nl_service=provider.get_required_service(NaturalLanguageToSQLService),
        db_service=provider.get_required_service(DatabaseService),
        formatter=provider.get_required_service(MessageFormatter),
        openai_client=provider.get_service(OpenAIClient),
    )
