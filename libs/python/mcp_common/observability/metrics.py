"""
MCP 客戶端 Prometheus 指標

提供 MCP 客戶端的監控指標收集功能。
"""

import time
from typing import Any, Dict, Optional, Set
from functools import wraps
from contextlib import contextmanager

try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        Enum,
        CollectorRegistry,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    
    # Mock 類別，當 prometheus_client 不可用時
    class MockMetric:
        def inc(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
        def set(self, *args, **kwargs): pass
        def state(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self


class MCPMetrics:
    """
    MCP 客戶端指標收集器
    
    收集並暴露 MCP 客戶端的各種效能和狀態指標。
    """

    def __init__(self, registry: Optional[CollectorRegistry] = None, enabled: bool = True):
        """
        初始化指標收集器
        
        Args:
            registry: Prometheus 註冊表，None 表示使用預設註冊表
            enabled: 是否啟用指標收集
        """
        self.enabled = enabled and PROMETHEUS_AVAILABLE
        self.registry = registry
        
        if not self.enabled:
            # 建立 mock 指標
            self._create_mock_metrics()
            return
        
        # 建立真實指標
        self._create_prometheus_metrics()

    def _create_prometheus_metrics(self):
        """建立 Prometheus 指標"""
        # 請求計數器
        self.requests_total = Counter(
            'mcp_client_requests_total',
            'Total number of MCP client requests',
            ['server', 'tool', 'status', 'protocol'],
            registry=self.registry
        )
        
        # 請求延遲直方圖
        self.request_duration = Histogram(
            'mcp_client_request_duration_seconds',
            'MCP client request duration in seconds',
            ['server', 'tool', 'protocol'],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry
        )
        
        # 連線狀態計量器
        self.connections_active = Gauge(
            'mcp_client_connections_active',
            'Number of active MCP client connections',
            ['server', 'protocol'],
            registry=self.registry
        )
        
        # 連線池使用率
        self.pool_utilization = Gauge(
            'mcp_client_pool_utilization_ratio',
            'MCP client connection pool utilization ratio',
            ['server'],
            registry=self.registry
        )
        
        # 熔斷器狀態
        self.circuit_breaker_state = Enum(
            'mcp_client_circuit_breaker_state',
            'MCP client circuit breaker state',
            ['server'],
            states=['closed', 'open', 'half_open'],
            registry=self.registry
        )
        
        # 批次大小
        self.batch_size = Histogram(
            'mcp_client_batch_size',
            'MCP client batch request size',
            ['server'],
            buckets=(1, 2, 5, 10, 20, 50, 100),
            registry=self.registry
        )
        
        # 重試次數
        self.retries_total = Counter(
            'mcp_client_retries_total',
            'Total number of MCP client retries',
            ['server', 'tool', 'reason'],
            registry=self.registry
        )
        
        # 快取命中率
        self.cache_hits_total = Counter(
            'mcp_client_cache_hits_total',
            'Total number of MCP client cache hits',
            ['server', 'cache_type'],
            registry=self.registry
        )
        
        self.cache_misses_total = Counter(
            'mcp_client_cache_misses_total',
            'Total number of MCP client cache misses',
            ['server', 'cache_type'],
            registry=self.registry
        )

    def _create_mock_metrics(self):
        """建立 mock 指標（當 Prometheus 不可用時）"""
        self.requests_total = MockMetric()
        self.request_duration = MockMetric()
        self.connections_active = MockMetric()
        self.pool_utilization = MockMetric()
        self.circuit_breaker_state = MockMetric()
        self.batch_size = MockMetric()
        self.retries_total = MockMetric()
        self.cache_hits_total = MockMetric()
        self.cache_misses_total = MockMetric()

    def record_request(
        self,
        server: str,
        tool: str,
        protocol: str,
        status: str,
        duration: float,
    ):
        """
        記錄請求指標
        
        Args:
            server: 伺服器名稱
            tool: 工具名稱
            protocol: 協議類型
            status: 請求狀態 (success/error/timeout)
            duration: 請求持續時間（秒）
        """
        if not self.enabled:
            return
        
        self.requests_total.labels(
            server=server,
            tool=tool,
            status=status,
            protocol=protocol
        ).inc()
        
        self.request_duration.labels(
            server=server,
            tool=tool,
            protocol=protocol
        ).observe(duration)

    def record_batch(self, server: str, size: int):
        """
        記錄批次請求指標
        
        Args:
            server: 伺服器名稱
            size: 批次大小
        """
        if not self.enabled:
            return
        
        self.batch_size.labels(server=server).observe(size)

    def record_retry(self, server: str, tool: str, reason: str):
        """
        記錄重試指標
        
        Args:
            server: 伺服器名稱
            tool: 工具名稱
            reason: 重試原因
        """
        if not self.enabled:
            return
        
        self.retries_total.labels(
            server=server,
            tool=tool,
            reason=reason
        ).inc()

    def set_connections_active(self, server: str, protocol: str, count: int):
        """
        設定活躍連線數
        
        Args:
            server: 伺服器名稱
            protocol: 協議類型
            count: 連線數量
        """
        if not self.enabled:
            return
        
        self.connections_active.labels(
            server=server,
            protocol=protocol
        ).set(count)

    def set_pool_utilization(self, server: str, ratio: float):
        """
        設定連線池使用率
        
        Args:
            server: 伺服器名稱
            ratio: 使用率（0.0-1.0）
        """
        if not self.enabled:
            return
        
        self.pool_utilization.labels(server=server).set(ratio)

    def set_circuit_breaker_state(self, server: str, state: str):
        """
        設定熔斷器狀態
        
        Args:
            server: 伺服器名稱
            state: 狀態 (closed/open/half_open)
        """
        if not self.enabled:
            return
        
        valid_states = {'closed', 'open', 'half_open'}
        if state not in valid_states:
            state = 'closed'  # 預設狀態
        
        self.circuit_breaker_state.labels(server=server).state(state)

    def record_cache_hit(self, server: str, cache_type: str = "default"):
        """
        記錄快取命中
        
        Args:
            server: 伺服器名稱
            cache_type: 快取類型
        """
        if not self.enabled:
            return
        
        self.cache_hits_total.labels(
            server=server,
            cache_type=cache_type
        ).inc()

    def record_cache_miss(self, server: str, cache_type: str = "default"):
        """
        記錄快取未命中
        
        Args:
            server: 伺服器名稱
            cache_type: 快取類型
        """
        if not self.enabled:
            return
        
        self.cache_misses_total.labels(
            server=server,
            cache_type=cache_type
        ).inc()

    @contextmanager
    def time_request(self, server: str, tool: str, protocol: str):
        """
        計時請求執行時間的上下文管理器
        
        Args:
            server: 伺服器名稱
            tool: 工具名稱
            protocol: 協議類型
            
        Usage:
            with metrics.time_request("sqlite", "query", "http"):
                # 執行請求
                result = await client.call_tool(...)
        """
        start_time = time.time()
        status = "success"
        
        try:
            yield
        except Exception:
            status = "error"
            raise
        finally:
            duration = time.time() - start_time
            self.record_request(server, tool, protocol, status, duration)

    def get_metrics(self) -> str:
        """
        取得 Prometheus 格式的指標資料
        
        Returns:
            Prometheus 格式的指標字串
        """
        if not self.enabled or not PROMETHEUS_AVAILABLE:
            return "# Prometheus metrics not available\n"
        
        return generate_latest(self.registry).decode('utf-8')

    def get_content_type(self) -> str:
        """
        取得 Prometheus 指標的 Content-Type
        
        Returns:
            Content-Type 字串
        """
        if not self.enabled or not PROMETHEUS_AVAILABLE:
            return "text/plain"
        
        return CONTENT_TYPE_LATEST


def with_metrics(
    metrics: MCPMetrics,
    server: str,
    tool: str,
    protocol: str = "http"
):
    """
    為函數添加指標記錄的裝飾器
    
    Args:
        metrics: 指標收集器實例
        server: 伺服器名稱
        tool: 工具名稱
        protocol: 協議類型
        
    Usage:
        @with_metrics(metrics, "sqlite", "query")
        async def call_sqlite_query():
            # 函數實作
            pass
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with metrics.time_request(server, tool, protocol):
                return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with metrics.time_request(server, tool, protocol):
                return func(*args, **kwargs)
        
        # 根據函數類型選擇包裝器
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# 全域指標實例
_global_metrics: Optional[MCPMetrics] = None


def get_global_metrics() -> MCPMetrics:
    """
    取得全域指標實例
    
    Returns:
        全域指標收集器
    """
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = MCPMetrics()
    return _global_metrics


def configure_global_metrics(
    registry: Optional[CollectorRegistry] = None,
    enabled: bool = True
) -> MCPMetrics:
    """
    配置全域指標實例
    
    Args:
        registry: Prometheus 註冊表
        enabled: 是否啟用指標收集
        
    Returns:
        配置後的指標收集器
    """
    global _global_metrics
    _global_metrics = MCPMetrics(registry=registry, enabled=enabled)
    return _global_metrics 