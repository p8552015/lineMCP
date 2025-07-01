"""
Prometheus 指標收集器
提供應用層面的業務指標
"""

import time
from functools import wraps

import psutil
from fastapi import APIRouter, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)

# ==============================================================================
# 指標定義
# ==============================================================================

# 應用信息
app_info = Info("app_info", "Application information")
app_info.info({"version": "0.1.0", "name": "line-mcp-bot", "environment": "production"})

# HTTP 請求指標
http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

# LINE Bot 業務指標
line_message_processing_total = Counter(
    "line_message_processing_total",
    "Total number of LINE messages processed",
    ["message_type", "user_type"],
)

line_message_processing_failures_total = Counter(
    "line_message_processing_failures_total",
    "Total number of LINE message processing failures",
    ["error_type", "message_type"],
)

line_message_processing_duration_seconds = Histogram(
    "line_message_processing_duration_seconds",
    "LINE message processing duration in seconds",
    ["message_type"],
)

# AI 模型指標
ai_model_requests_total = Counter(
    "ai_model_requests_total",
    "Total number of AI model requests",
    ["provider", "model", "operation"],
)

ai_model_request_failures_total = Counter(
    "ai_model_request_failures_total",
    "Total number of AI model request failures",
    ["provider", "model", "error_type"],
)

ai_model_request_duration_seconds = Histogram(
    "ai_model_request_duration_seconds",
    "AI model request duration in seconds",
    ["provider", "model"],
)

ai_model_tokens_total = Counter(
    "ai_model_tokens_total",
    "Total number of tokens processed",
    ["provider", "model", "type"],  # 類型: input/output
)

# MCP 指標
mcp_queries_total = Counter(
    "mcp_queries_total", "Total number of MCP queries", ["query_type", "database"]
)

mcp_query_failures_total = Counter(
    "mcp_query_failures_total",
    "Total number of MCP query failures",
    ["error_type", "database"],
)

mcp_query_duration_seconds = Histogram(
    "mcp_query_duration_seconds", "MCP query duration in seconds", ["query_type"]
)

mcp_connection_failures_total = Counter(
    "mcp_connection_failures_total",
    "Total number of MCP connection failures",
    ["server", "error_type"],
)

# 系統指標
system_memory_usage_bytes = Gauge(
    "system_memory_usage_bytes", "System memory usage in bytes"
)

system_cpu_usage_percent = Gauge(
    "system_cpu_usage_percent", "System CPU usage percentage"
)

system_disk_usage_percent = Gauge(
    "system_disk_usage_percent", "System disk usage percentage"
)

# 應用指標
app_uptime_seconds = Gauge("app_uptime_seconds", "Application uptime in seconds")

app_active_connections = Gauge("app_active_connections", "Number of active connections")

app_cache_hits_total = Counter(
    "app_cache_hits_total", "Total number of cache hits", ["cache_type"]
)

app_cache_misses_total = Counter(
    "app_cache_misses_total", "Total number of cache misses", ["cache_type"]
)

# 資料庫指標
database_connections_active = Gauge(
    "database_connections_active", "Number of active database connections", ["database"]
)

database_query_duration_seconds = Histogram(
    "database_query_duration_seconds",
    "Database query duration in seconds",
    ["database", "operation"],
)


# ==============================================================================
# 指標收集器
# ==============================================================================


class MetricsCollector:
    """指標收集器"""

    def __init__(self):
        self.start_time = time.time()

    def update_system_metrics(self):
        """更新系統指標"""
        try:
            # 記憶體使用
            memory = psutil.virtual_memory()
            system_memory_usage_bytes.set(memory.used)

            # CPU 使用率
            cpu_percent = psutil.cpu_percent()
            system_cpu_usage_percent.set(cpu_percent)

            # 磁碟使用率
            disk = psutil.disk_usage("/")
            disk_percent = (disk.used / disk.total) * 100
            system_disk_usage_percent.set(disk_percent)

            # 應用運行時間
            uptime = time.time() - self.start_time
            app_uptime_seconds.set(uptime)

        except Exception as e:
            print(f"Error updating system metrics: {e}")

    def record_http_request(
        self, method: str, endpoint: str, status_code: int, duration: float
    ):
        """記錄 HTTP 請求指標"""
        http_requests_total.labels(
            method=method, endpoint=endpoint, status=str(status_code)
        ).inc()
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(
            duration
        )

    def record_line_message(
        self,
        message_type: str,
        user_type: str,
        duration: float,
        success: bool = True,
        error_type: str | None = None,
    ):
        """記錄 LINE 訊息處理指標"""
        if success:
            line_message_processing_total.labels(
                message_type=message_type, user_type=user_type
            ).inc()
        else:
            line_message_processing_failures_total.labels(
                error_type=error_type or "unknown", message_type=message_type
            ).inc()

        line_message_processing_duration_seconds.labels(
            message_type=message_type
        ).observe(duration)

    def record_ai_request(
        self,
        provider: str,
        model: str,
        operation: str,
        duration: float,
        success: bool = True,
        error_type: str | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ):
        """記錄 AI 模型請求指標"""
        if success:
            ai_model_requests_total.labels(
                provider=provider, model=model, operation=operation
            ).inc()

            # 記錄 token 使用量
            if input_tokens > 0:
                ai_model_tokens_total.labels(
                    provider=provider, model=model, type="input"
                ).inc(input_tokens)
            if output_tokens > 0:
                ai_model_tokens_total.labels(
                    provider=provider, model=model, type="output"
                ).inc(output_tokens)
        else:
            ai_model_request_failures_total.labels(
                provider=provider, model=model, error_type=error_type or "unknown"
            ).inc()

        ai_model_request_duration_seconds.labels(
            provider=provider, model=model
        ).observe(duration)

    def record_mcp_query(
        self,
        query_type: str,
        database: str,
        duration: float,
        success: bool = True,
        error_type: str | None = None,
    ):
        """記錄 MCP 查詢指標"""
        if success:
            mcp_queries_total.labels(query_type=query_type, database=database).inc()
        else:
            mcp_query_failures_total.labels(
                error_type=error_type or "unknown", database=database
            ).inc()

        mcp_query_duration_seconds.labels(query_type=query_type).observe(duration)

    def record_mcp_connection_failure(self, server: str, error_type: str):
        """記錄 MCP 連接失敗"""
        mcp_connection_failures_total.labels(server=server, error_type=error_type).inc()

    def record_cache_operation(self, cache_type: str, hit: bool):
        """記錄快取操作"""
        if hit:
            app_cache_hits_total.labels(cache_type=cache_type).inc()
        else:
            app_cache_misses_total.labels(cache_type=cache_type).inc()


# 全域指標收集器實例
metrics_collector = MetricsCollector()


# ==============================================================================
# 裝飾器
# ==============================================================================


def monitor_http_requests(endpoint: str | None = None):
    """HTTP 請求監控裝飾器"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            method = kwargs.get("request", args[0] if args else None)
            method_name = getattr(method, "method", "UNKNOWN") if method else "UNKNOWN"
            endpoint_name = endpoint or func.__name__

            try:
                result = await func(*args, **kwargs)
                status_code = getattr(result, "status_code", 200)
                metrics_collector.record_http_request(
                    method_name, endpoint_name, status_code, time.time() - start_time
                )
                return result
            except Exception:
                metrics_collector.record_http_request(
                    method_name, endpoint_name, 500, time.time() - start_time
                )
                raise

        return wrapper

    return decorator


def monitor_line_message_processing(
    message_type: str = "unknown", user_type: str = "unknown"
):
    """LINE 訊息處理監控裝飾器"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                metrics_collector.record_line_message(
                    message_type, user_type, time.time() - start_time, True
                )
                return result
            except Exception as e:
                error_type = type(e).__name__
                metrics_collector.record_line_message(
                    message_type, user_type, time.time() - start_time, False, error_type
                )
                raise

        return wrapper

    return decorator


def monitor_ai_requests(provider: str, model: str, operation: str = "generate"):
    """AI 請求監控裝飾器"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                # 嘗試提取 token 使用量
                input_tokens = getattr(result, "input_tokens", 0)
                output_tokens = getattr(result, "output_tokens", 0)
                metrics_collector.record_ai_request(
                    provider,
                    model,
                    operation,
                    time.time() - start_time,
                    True,
                    None,
                    input_tokens,
                    output_tokens,
                )
                return result
            except Exception as e:
                error_type = type(e).__name__
                metrics_collector.record_ai_request(
                    provider,
                    model,
                    operation,
                    time.time() - start_time,
                    False,
                    error_type,
                )
                raise

        return wrapper

    return decorator


def monitor_mcp_queries(query_type: str = "select", database: str = "default"):
    """MCP 查詢監控裝飾器"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                metrics_collector.record_mcp_query(
                    query_type, database, time.time() - start_time, True
                )
                return result
            except Exception as e:
                error_type = type(e).__name__
                metrics_collector.record_mcp_query(
                    query_type, database, time.time() - start_time, False, error_type
                )
                raise

        return wrapper

    return decorator


# ==============================================================================
# 路由器
# ==============================================================================

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def get_metrics():
    """
    Prometheus 指標端點
    返回所有收集的指標數據
    """
    # 更新系統指標
    metrics_collector.update_system_metrics()

    # 生成 Prometheus 格式的指標
    metrics_data = generate_latest()

    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)


@router.get("/metrics/summary")
async def get_metrics_summary():
    """
    指標摘要端點
    返回人類可讀的指標摘要
    """
    # 更新系統指標
    metrics_collector.update_system_metrics()

    # 收集關鍵指標
    try:
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent()
        disk = psutil.disk_usage("/")

        return {
            "system": {
                "cpu_usage_percent": cpu_percent,
                "memory_usage_percent": memory.percent,
                "disk_usage_percent": (disk.used / disk.total) * 100,
                "uptime_seconds": time.time() - metrics_collector.start_time,
            },
            "application": {
                "version": "0.1.0",
                "environment": "production",
                "start_time": metrics_collector.start_time,
            },
            "note": "For detailed metrics, use /metrics endpoint",
        }
    except Exception as e:
        return {"error": str(e)}
