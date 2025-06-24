from contextlib import asynccontextmanager
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import make_asgi_app

from src.config import get_settings
from src.middleware import setup_middleware
from src.routes import webhook
from src.utils.observability import setup_observability
from src.utils.redis_client import get_redis_client

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        setup_observability()
        logger.info("Observability setup complete")
    except Exception as e:
        logger.warning("Observability setup failed", error=str(e))

    try:
        redis_client = get_redis_client()
        await redis_client.ping()
        logger.info("Redis connection successful")
    except Exception as e:
        logger.warning("Redis connection failed", error=str(e))

    logger.info("Application started", environment=settings.app_env)
    yield

    try:
        redis_client = get_redis_client()
        await redis_client.close()
    except Exception as e:
        logger.warning("Redis cleanup failed", error=str(e))
    logger.info("Application shutdown")


app = FastAPI(
    title="LINE MCP Webhook",
    description="LINE OA integration with Remote MCP via OpenAI",
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.app_debug,
)

setup_middleware(app)
FastAPIInstrumentor.instrument_app(app)

app.include_router(webhook.router, tags=["webhook"])

# 測試路由已移除，聚焦核心功能

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/health")
async def health_check():
    try:
        redis_client = get_redis_client()
        await redis_client.ping()
        return {
            "status": "healthy",
            "service": settings.otel_service_name,
            "version": "1.0.0",
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=503, content={"status": "unhealthy", "error": str(e)}
        )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    trace_id = (
        request.state.trace_id if hasattr(request.state, "trace_id") else str(uuid4())
    )
    logger.error(
        "Unhandled exception",
        trace_id=trace_id,
        path=request.url.path,
        error=str(exc),
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "trace_id": trace_id,
        },
    )
