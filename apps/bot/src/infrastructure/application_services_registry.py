"""
應用服務註冊模組
負責註冊應用層服務：訊息處理、查詢、監控等應用服務
"""

import structlog

from src.application.base_service import ApplicationServiceContext
from src.application.messaging_service import MessagingApplicationService
from src.application.monitoring_service import MonitoringApplicationService
from src.application.query_service import QueryApplicationService
from src.domain.command_handler import CommandContext
from src.services.ai_model_service import AIModelService
from src.services.database_service import DatabaseService
from src.services.mcp_response_parser import MCPResponseParser
from src.services.message_formatter import MessageFormatter
from src.services.nl_to_sql_service import NaturalLanguageToSQLService
from src.services.openai_client import OpenAIClient
from src.services.unified_mcp_client import get_unified_mcp_client

from .service_registry import ServiceProvider, ServiceRegistry, ServiceScope

logger = structlog.get_logger()


def register_application_services(registry: ServiceRegistry) -> None:
    """
    註冊應用服務

    Args:
        registry: 服務註冊表實例
    """
    logger.debug("開始註冊應用服務")

    # 應用服務上下文
    registry.register_singleton(
        ApplicationServiceContext,
        tags=["application", "context"],
        metadata={"description": "應用服務上下文"},
    )

    # 訊息處理應用服務
    registry.register_factory(
        MessagingApplicationService,
        lambda provider: _create_messaging_service(provider),
        scope=ServiceScope.SINGLETON,
    )

    # 查詢應用服務
    registry.register_factory(
        QueryApplicationService,
        lambda provider: QueryApplicationService(
            mcp_client_factory=get_unified_mcp_client,
            db_service=provider.get_required_service(DatabaseService),
            response_parser=provider.get_required_service(MCPResponseParser),
        ),
        scope=ServiceScope.SINGLETON,
    )

    # 監控應用服務
    registry.register_factory(
        MonitoringApplicationService,
        lambda provider: MonitoringApplicationService(
            service_context=provider.get_required_service(ApplicationServiceContext)
        ),
        scope=ServiceScope.SINGLETON,
    )

    logger.info("應用服務註冊完成", service_count=4)


def _create_messaging_service(provider: ServiceProvider) -> MessagingApplicationService:
    """創建訊息處理應用服務"""
    context = CommandContext(
        mcp_client_factory=get_unified_mcp_client,
        ai_model_service=provider.get_required_service(AIModelService),
        nl_service=provider.get_required_service(NaturalLanguageToSQLService),
        db_service=provider.get_required_service(DatabaseService),
        formatter=provider.get_required_service(MessageFormatter),
        openai_client=provider.get_service(OpenAIClient),
    )

    return MessagingApplicationService(
        command_context=context,
        nl_service=provider.get_required_service(NaturalLanguageToSQLService),
        message_formatter=provider.get_required_service(MessageFormatter),
    )
