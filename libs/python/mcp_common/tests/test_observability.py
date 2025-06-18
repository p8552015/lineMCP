"""
測試可觀測性元件
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from mcp_common.observability.metrics import (
    MCPMetrics,
    with_metrics,
    get_global_metrics,
    configure_global_metrics
)
from mcp_common.observability.tracing import (
    MCPTracing,
    get_global_tracing
)


class TestMCPMetrics:
    """測試指標收集器"""
    
    @pytest.fixture
    def metrics(self):
        """建立測試指標收集器"""
        return MCPMetrics(enabled=True)
    
    def test_create_metrics_without_prometheus(self):
        """測試在沒有 Prometheus 的情況下建立指標"""
        with patch('mcp_common.observability.metrics.PROMETHEUS_AVAILABLE', False):
            metrics = MCPMetrics(enabled=True)
            
            # 應該建立 mock 指標
            assert hasattr(metrics, 'requests_total')
            assert hasattr(metrics, 'request_duration')
            
            # 呼叫方法不應該引發錯誤
            metrics.record_request("server", "tool", "http", "success", 0.1)
            metrics.record_batch("server", 10)
            metrics.record_retry("server", "tool", "timeout")
    
    @patch('mcp_common.observability.metrics.PROMETHEUS_AVAILABLE', True)
    def test_record_request(self, metrics):
        """測試記錄請求指標"""
        # Mock Prometheus 指標
        metrics.requests_total = Mock()
        metrics.request_duration = Mock()
        
        # 記錄請求
        metrics.record_request(
            server="test_server",
            tool="test_tool",
            protocol="http",
            status="success",
            duration=0.5
        )
        
        # 驗證呼叫
        metrics.requests_total.labels.assert_called_with(
            server="test_server",
            tool="test_tool",
            status="success",
            protocol="http"
        )
        metrics.request_duration.labels.assert_called_with(
            server="test_server",
            tool="test_tool",
            protocol="http"
        )
    
    def test_record_batch(self, metrics):
        """測試記錄批次指標"""
        metrics.batch_size = Mock()
        
        metrics.record_batch("server", 25)
        
        metrics.batch_size.labels.assert_called_with(server="server")
        metrics.batch_size.labels().observe.assert_called_with(25)
    
    def test_record_retry(self, metrics):
        """測試記錄重試指標"""
        metrics.retries_total = Mock()
        
        metrics.record_retry("server", "tool", "connection_error")
        
        metrics.retries_total.labels.assert_called_with(
            server="server",
            tool="tool",
            reason="connection_error"
        )
    
    def test_set_connections_active(self, metrics):
        """測試設定活躍連線數"""
        metrics.connections_active = Mock()
        
        metrics.set_connections_active("server", "websocket", 5)
        
        metrics.connections_active.labels.assert_called_with(
            server="server",
            protocol="websocket"
        )
        metrics.connections_active.labels().set.assert_called_with(5)
    
    def test_set_pool_utilization(self, metrics):
        """測試設定連線池使用率"""
        metrics.pool_utilization = Mock()
        
        metrics.set_pool_utilization("server", 0.75)
        
        metrics.pool_utilization.labels.assert_called_with(server="server")
        metrics.pool_utilization.labels().set.assert_called_with(0.75)
    
    def test_set_circuit_breaker_state(self, metrics):
        """測試設定熔斷器狀態"""
        metrics.circuit_breaker_state = Mock()
        
        metrics.set_circuit_breaker_state("server", "open")
        
        metrics.circuit_breaker_state.labels.assert_called_with(server="server")
        metrics.circuit_breaker_state.labels().state.assert_called_with("open")
        
        # 測試無效狀態
        metrics.set_circuit_breaker_state("server", "invalid")
        metrics.circuit_breaker_state.labels().state.assert_called_with("closed")
    
    def test_cache_metrics(self, metrics):
        """測試快取指標"""
        metrics.cache_hits_total = Mock()
        metrics.cache_misses_total = Mock()
        
        # 記錄快取命中
        metrics.record_cache_hit("server", "result_cache")
        metrics.cache_hits_total.labels.assert_called_with(
            server="server",
            cache_type="result_cache"
        )
        
        # 記錄快取未命中
        metrics.record_cache_miss("server", "result_cache")
        metrics.cache_misses_total.labels.assert_called_with(
            server="server",
            cache_type="result_cache"
        )
    
    def test_time_request_context_manager(self, metrics):
        """測試計時請求的上下文管理器"""
        metrics.record_request = Mock()
        
        # 成功的請求
        with metrics.time_request("server", "tool", "http"):
            time.sleep(0.1)
        
        metrics.record_request.assert_called_once()
        args = metrics.record_request.call_args[0]
        assert args[0] == "server"
        assert args[1] == "tool"
        assert args[2] == "http"
        assert args[3] == "success"
        assert args[4] >= 0.1  # 至少 0.1 秒
        
        # 失敗的請求
        metrics.record_request.reset_mock()
        
        with pytest.raises(ValueError):
            with metrics.time_request("server", "tool", "http"):
                raise ValueError("Test error")
        
        metrics.record_request.assert_called_once()
        args = metrics.record_request.call_args[0]
        assert args[3] == "error"
    
    @patch('mcp_common.observability.metrics.generate_latest')
    def test_get_metrics(self, mock_generate, metrics):
        """測試獲取指標"""
        mock_generate.return_value = b"# HELP test\ntest_metric 1.0\n"
        
        result = metrics.get_metrics()
        
        assert "test_metric 1.0" in result
        mock_generate.assert_called_once()
    
    def test_get_metrics_disabled(self):
        """測試停用時獲取指標"""
        metrics = MCPMetrics(enabled=False)
        
        result = metrics.get_metrics()
        assert "not available" in result
    
    @patch('mcp_common.observability.metrics.CONTENT_TYPE_LATEST', 'text/plain; version=0.0.4')
    def test_get_content_type(self, metrics):
        """測試獲取內容類型"""
        content_type = metrics.get_content_type()
        assert content_type == "text/plain; version=0.0.4"
    
    def test_get_content_type_disabled(self):
        """測試停用時獲取內容類型"""
        metrics = MCPMetrics(enabled=False)
        
        content_type = metrics.get_content_type()
        assert content_type == "text/plain"


class TestMetricsDecorator:
    """測試指標裝飾器"""
    
    @pytest.mark.asyncio
    async def test_async_function_decorator(self):
        """測試非同步函數裝飾器"""
        metrics = Mock()
        metrics.time_request = MagicMock()
        
        @with_metrics(metrics, "server", "tool", "http")
        async def async_func():
            await asyncio.sleep(0.01)
            return "result"
        
        result = await async_func()
        
        assert result == "result"
        metrics.time_request.assert_called_with("server", "tool", "http")
    
    def test_sync_function_decorator(self):
        """測試同步函數裝飾器"""
        metrics = Mock()
        metrics.time_request = MagicMock()
        
        @with_metrics(metrics, "server", "tool", "http")
        def sync_func():
            return "result"
        
        result = sync_func()
        
        assert result == "result"
        metrics.time_request.assert_called_with("server", "tool", "http")


class TestGlobalMetrics:
    """測試全域指標"""
    
    def test_get_global_metrics(self):
        """測試獲取全域指標"""
        metrics1 = get_global_metrics()
        metrics2 = get_global_metrics()
        
        assert metrics1 is metrics2  # 單例
        assert isinstance(metrics1, MCPMetrics)
    
    def test_configure_global_metrics(self):
        """測試配置全域指標"""
        # 重設全域變數
        import mcp_common.observability.metrics
        mcp_common.observability.metrics._global_metrics = None
        
        # 配置新的指標
        registry = Mock()
        metrics = configure_global_metrics(registry=registry, enabled=False)
        
        assert metrics.enabled is False
        assert metrics.registry is registry
        
        # 確認是全域指標
        assert get_global_metrics() is metrics


class TestMCPTracing:
    """測試追蹤配置器"""
    
    @pytest.fixture
    def tracing(self):
        """建立測試追蹤配置器"""
        return MCPTracing(
            service_name="test-service",
            enabled=True
        )
    
    def test_create_tracing_without_opentelemetry(self):
        """測試在沒有 OpenTelemetry 的情況下建立追蹤"""
        with patch('mcp_common.observability.tracing.OPENTELEMETRY_AVAILABLE', False):
            tracing = MCPTracing(enabled=True)
            
            # 應該建立 mock tracer
            assert hasattr(tracing, 'tracer')
            
            # 使用 start_span 不應該引發錯誤
            with tracing.start_span("test") as span:
                assert span is not None
    
    @patch('mcp_common.observability.tracing.OPENTELEMETRY_AVAILABLE', True)
    @patch('mcp_common.observability.tracing.trace')
    def test_setup_tracing(self, mock_trace):
        """測試設定追蹤"""
        mock_provider = Mock()
        mock_trace.TracerProvider = Mock(return_value=mock_provider)
        mock_trace.get_tracer = Mock()
        
        tracing = MCPTracing(
            service_name="test-service",
            endpoint="http://localhost:4317"
        )
        
        # 驗證設定
        mock_trace.set_tracer_provider.assert_called_with(mock_provider)
        mock_trace.get_tracer.assert_called()
    
    @pytest.mark.asyncio
    async def test_start_span_success(self, tracing):
        """測試成功的 span"""
        mock_span = Mock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=None)
        
        tracing.tracer = Mock()
        tracing.tracer.start_as_current_span = Mock(return_value=mock_span)
        
        # 使用 span
        with tracing.start_span(
            "test.operation",
            attributes={"user_id": "123"},
            kind="client"
        ) as span:
            assert span is mock_span
        
        # 驗證屬性設定
        mock_span.set_attribute.assert_any_call("service.name", "test-service")
        mock_span.set_attribute.assert_any_call("user_id", "123")
        
        # 驗證成功狀態
        mock_span.set_status.assert_called()
    
    @pytest.mark.asyncio
    async def test_start_span_with_error(self, tracing):
        """測試帶錯誤的 span"""
        mock_span = Mock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=None)
        
        tracing.tracer = Mock()
        tracing.tracer.start_as_current_span = Mock(return_value=mock_span)
        
        # 使用 span 並引發錯誤
        with pytest.raises(ValueError):
            with tracing.start_span("test.operation") as span:
                raise ValueError("Test error")
        
        # 驗證錯誤記錄
        mock_span.record_exception.assert_called()
        mock_span.set_status.assert_called()
    
    def test_span_kind_mapping(self, tracing):
        """測試 span 類型映射"""
        mock_span = Mock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=None)
        
        tracing.tracer = Mock()
        tracing.tracer.start_as_current_span = Mock(return_value=mock_span)
        
        # 測試不同的 span 類型
        for kind in ["client", "server", "internal"]:
            with tracing.start_span("test", kind=kind):
                pass
        
        # 驗證呼叫次數
        assert tracing.tracer.start_as_current_span.call_count == 3


class TestGlobalTracing:
    """測試全域追蹤"""
    
    def test_get_global_tracing(self):
        """測試獲取全域追蹤"""
        tracing1 = get_global_tracing()
        tracing2 = get_global_tracing()
        
        assert tracing1 is tracing2  # 單例
        assert isinstance(tracing1, MCPTracing)


# 整合測試
class TestObservabilityIntegration:
    """測試可觀測性整合"""
    
    @pytest.mark.asyncio
    async def test_metrics_and_tracing_together(self):
        """測試指標和追蹤一起使用"""
        metrics = MCPMetrics(enabled=True)
        tracing = MCPTracing(enabled=True)
        
        # 模擬一個完整的請求
        with tracing.start_span("mcp.call_tool") as span:
            with metrics.time_request("server", "tool", "http"):
                # 模擬一些工作
                await asyncio.sleep(0.01)
        
        # 兩者都應該正常工作，不互相干擾
        assert True  # 如果沒有錯誤就通過