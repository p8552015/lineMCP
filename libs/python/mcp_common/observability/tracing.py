"""
MCP 客戶端 OpenTelemetry 追蹤

提供 MCP 客戶端的分散式追蹤功能。
"""

import time
from typing import Any, Dict, Optional, Union
from functools import wraps
from contextlib import contextmanager

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.trace import Status, StatusCode
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    
    # Mock 類別，當 OpenTelemetry 不可用時
    class MockSpan:
        def set_attribute(self, key: str, value: Any): pass
        def set_status(self, status: Any): pass
        def record_exception(self, exception: Exception): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
    
    class MockTracer:
        def start_span(self, name: str, **kwargs): return MockSpan()


class MCPTracing:
    """
    MCP 客戶端追蹤配置器
    
    配置和管理 MCP 客戶端的分散式追蹤功能。
    """

    def __init__(
        self,
        service_name: str = "mcp-client",
        endpoint: Optional[str] = None,
        enabled: bool = True,
        sample_rate: float = 1.0,
    ):
        """
        初始化追蹤配置器
        
        Args:
            service_name: 服務名稱
            endpoint: OTLP 導出端點
            enabled: 是否啟用追蹤
            sample_rate: 採樣率 (0.0-1.0)
        """
        self.enabled = enabled and OPENTELEMETRY_AVAILABLE
        self.service_name = service_name
        self.endpoint = endpoint
        self.sample_rate = sample_rate
        
        if not self.enabled:
            self.tracer = MockTracer()
            return
        
        # 配置 OpenTelemetry
        self._setup_tracing()

    def _setup_tracing(self):
        """配置 OpenTelemetry 追蹤"""
        # 建立 TracerProvider
        provider = TracerProvider()
        trace.set_tracer_provider(provider)
        
        # 配置 OTLP 導出器
        if self.endpoint:
            otlp_exporter = OTLPSpanExporter(
                endpoint=self.endpoint,
                insecure=True,  # 在生產環境中應該設為 False
            )
            
            span_processor = BatchSpanProcessor(otlp_exporter)
            provider.add_span_processor(span_processor)
        
        # 取得 tracer
        self.tracer = trace.get_tracer(
            __name__,
            version="1.0.0",
        )

    @contextmanager
    def start_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        kind: str = "client",
    ):
        """
        開始追蹤 span 的上下文管理器
        
        Args:
            name: Span 名稱
            attributes: 額外屬性
            kind: Span 類型
            
        Usage:
            with tracing.start_span("mcp.call_tool") as span:
                # 執行操作
                result = await client.call_tool(...)
        """
        if not self.enabled:
            yield MockSpan()
            return
        
        # 設定 span kind
        span_kind_map = {
            "client": trace.SpanKind.CLIENT,
            "server": trace.SpanKind.SERVER,
            "internal": trace.SpanKind.INTERNAL,
        }
        span_kind = span_kind_map.get(kind, trace.SpanKind.CLIENT)
        
        with self.tracer.start_as_current_span(
            name,
            kind=span_kind,
        ) as span:
            # 設定基本屬性
            span.set_attribute("service.name", self.service_name)
            span.set_attribute("service.version", "1.0.0")
            
            # 設定自訂屬性
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            
            try:
                yield span
                # 設定成功狀態
                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                # 記錄異常
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise


# 全域追蹤實例
_global_tracing: Optional[MCPTracing] = None


def get_global_tracing() -> MCPTracing:
    """取得全域追蹤實例"""
    global _global_tracing
    if _global_tracing is None:
        _global_tracing = MCPTracing()
    return _global_tracing 