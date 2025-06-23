"""
核心服務註冊模組
負責註冊系統核心服務：AI模型、OpenAI客戶端、訊息格式化器、MCP相關服務
"""

from typing import Any

import structlog

from src.services.ai_model_service import AIModelService
from src.services.mcp_response_parser import MCPResponseParser
from src.services.message_formatter import MessageFormatter
from src.services.openai_client import OpenAIClient
from src.services.unified_mcp_client import get_unified_mcp_client

from .service_registry import ServiceRegistry, ServiceScope

logger = structlog.get_logger()


def register_core_services(registry: ServiceRegistry) -> None:
    """
    註冊核心服務

    Args:
        registry: 服務註冊表實例
    """
    logger.debug("開始註冊核心服務")

    # AI 和 OpenAI 服務
    registry.register_singleton(
        AIModelService, tags=["core", "ai"], metadata={"description": "AI 模型服務"}
    )

    registry.register_singleton(
        OpenAIClient,
        tags=["core", "ai", "external"],
        metadata={"description": "OpenAI 客戶端"},
    )

    # 訊息格式化服務
    registry.register_singleton(
        MessageFormatter,
        tags=["core", "formatting"],
        metadata={"description": "訊息格式化器"},
    )

    # MCP 相關服務
    registry.register_factory(
        type[Any],  # MCP Client type
        lambda provider: get_unified_mcp_client,
        scope=ServiceScope.SINGLETON,
    )

    registry.register_singleton(
        MCPResponseParser,
        tags=["core", "mcp", "parsing"],
        metadata={"description": "MCP 回應解析器"},
    )

    logger.info("核心服務註冊完成", service_count=5)
