import socket
from typing import Any
from urllib.parse import urlparse

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from src.settings import get_settings

settings = get_settings()
logger = structlog.get_logger()


def get_tracer(name: str = __name__):
    """獲取追蹤器"""
    return trace.get_tracer(name)


def _check_otlp_endpoint_availability(endpoint: str, timeout: float = 2.0) -> bool:
    """
    檢查 OTLP 端點是否可用

    Args:
        endpoint: OTLP 端點 URL
        timeout: 連接超時時間（秒）

    Returns:
        bool: 端點是否可用
    """
    try:
        parsed = urlparse(endpoint)
        host = parsed.hostname or "localhost"
        port = parsed.port or 4317

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()

        return result == 0

    except Exception as e:
        logger.debug("OTLP 端點可用性檢查失敗", endpoint=endpoint, error=str(e))
        return False


def _setup_telemetry_exporter(tracer_provider: TracerProvider) -> str | None:
    """
    設置遙測導出器（增強版本）

    Args:
        tracer_provider: 追蹤提供者

    Returns:
        str | None: 使用的導出器類型，None 表示沒有導出器
    """
    # 檢查是否啟用 OpenTelemetry
    if not settings.otel_enabled:
        logger.info("OpenTelemetry 已禁用，跳過遙測導出器設置")
        return None

    # 如果配置了端點，嘗試使用 OTLP
    if settings.otel_exporter_otlp_endpoint:
        endpoint = settings.otel_exporter_otlp_endpoint

        # 根據配置決定是否檢查端點可用性
        endpoint_available = True
        if settings.otel_auto_detect_endpoint:
            endpoint_available = _check_otlp_endpoint_availability(endpoint)

        if endpoint_available:
            try:
                logger.info("設置 OTLP 導出器", endpoint=endpoint)
                otlp_exporter = OTLPSpanExporter(
                    endpoint=endpoint, insecure=True, timeout=5
                )
                span_processor = BatchSpanProcessor(
                    otlp_exporter,
                    max_queue_size=512,
                    max_export_batch_size=64,
                    export_timeout_millis=3000,
                )
                tracer_provider.add_span_processor(span_processor)
                return "otlp"

            except Exception as e:
                logger.warning("OTLP 導出器設置失敗", endpoint=endpoint, error=str(e))
        else:
            logger.info("OTLP 端點不可用", endpoint=endpoint)

    # 自動檢測常見的 OTLP 端點
    if not settings.otel_exporter_otlp_endpoint and settings.otel_auto_detect_endpoint:
        common_endpoints = [
            "http://localhost:4317",
            "http://jaeger:4317",
            "http://otel-collector:4317",
        ]

        for endpoint in common_endpoints:
            if _check_otlp_endpoint_availability(endpoint):
                try:
                    logger.info("自動檢測到 OTLP 端點", endpoint=endpoint)
                    otlp_exporter = OTLPSpanExporter(
                        endpoint=endpoint, insecure=True, timeout=5
                    )
                    span_processor = BatchSpanProcessor(otlp_exporter)
                    tracer_provider.add_span_processor(span_processor)
                    return "otlp_auto"

                except Exception as e:
                    logger.debug(
                        "自動檢測的端點設置失敗", endpoint=endpoint, error=str(e)
                    )

    # 降級策略：使用控制台導出器（僅在開發環境且啟用時）
    if settings.app_env == "development" and settings.otel_fallback_to_console:
        try:
            logger.debug("降級為控制台追蹤導出器")
            console_exporter = ConsoleSpanExporter()
            span_processor = BatchSpanProcessor(console_exporter)
            tracer_provider.add_span_processor(span_processor)
            return "console"
        except Exception as e:
            logger.debug("控制台導出器設置失敗", error=str(e))

    logger.info("未設置任何追蹤導出器，僅使用本地追蹤")
    return None


def setup_observability():
    """
    設置觀測性（增強容錯版本）
    """
    try:
        # 設置結構化日誌
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        logger.info("結構化日誌設置完成")

    except Exception as e:
        # 如果結構化日誌設置失敗，使用標準日誌記錄
        print(f"結構化日誌設置失敗: {e}")

    # 檢查是否啟用 OpenTelemetry
    if not settings.otel_enabled:
        logger.info("OpenTelemetry 已禁用，僅使用結構化日誌")
        return

    try:
        # 設置 OpenTelemetry 資源
        resource = Resource.create(
            {
                "service.name": settings.otel_service_name,
                "service.version": "1.0.0",
                "deployment.environment": settings.app_env,
            }
        )

        tracer_provider = TracerProvider(resource=resource)

        # 設置追蹤導出器（帶容錯機制）
        exporter_type = _setup_telemetry_exporter(tracer_provider)

        trace.set_tracer_provider(tracer_provider)

        # 設置 HTTP 客戶端儀表（僅在有導出器時）
        if exporter_type:
            try:
                HTTPXClientInstrumentor().instrument()
                logger.debug("HTTP 客戶端儀表設置完成")
            except Exception as e:
                logger.debug("HTTP 客戶端儀表設置失敗", error=str(e))

        logger.info(
            "OpenTelemetry 追蹤設置完成",
            enabled=settings.otel_enabled,
            exporter_type=exporter_type or "none",
            service_name=settings.otel_service_name,
            auto_detect=settings.otel_auto_detect_endpoint,
        )

    except Exception as e:
        logger.warning("OpenTelemetry 設置失敗，繼續使用基本日誌", error=str(e))


def get_telemetry_health() -> dict:
    """
    獲取遙測系統健康狀況

    Returns:
        dict: 健康狀況信息
    """
    health_status: dict[str, Any] = {
        "telemetry_enabled": True,
        "otlp_endpoint": settings.otel_exporter_otlp_endpoint,
        "otlp_available": False,
        "service_name": settings.otel_service_name,
        "environment": settings.app_env,
        "recommendations": [],
    }

    try:
        # 檢查 OTLP 端點可用性
        if settings.otel_exporter_otlp_endpoint:
            health_status["otlp_available"] = _check_otlp_endpoint_availability(
                settings.otel_exporter_otlp_endpoint
            )

            if not health_status["otlp_available"]:
                health_status["recommendations"].append(
                    "考慮啟動 OTLP 收集器或禁用 OTLP 導出以減少日誌噪音"
                )

        # 檢查追蹤提供者狀態
        tracer_provider = trace.get_tracer_provider()
        if hasattr(tracer_provider, "_span_processors"):
            processor_count = len(tracer_provider._span_processors)
            health_status["active_processors"] = processor_count

            if processor_count == 0:
                health_status["recommendations"].append(
                    "沒有活動的追蹤處理器，考慮設置適當的導出器"
                )

    except Exception as e:
        health_status["error"] = str(e)
        health_status["recommendations"].append("遙測系統檢查失敗，請檢查配置")

    return health_status
