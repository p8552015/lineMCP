import asyncio
import concurrent.futures
import hashlib
import json
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from prometheus_client import Counter

from src.config import get_settings
from src.infrastructure.enhanced_service_factory import get_enhanced_service_factory
from src.services.message_handler_di import MessageHandlerDI
from src.utils.signature_validator import SignatureValidator

logger = structlog.get_logger()
settings = get_settings()
router = APIRouter()

webhook_handler = WebhookHandler(settings.line_channel_secret)
configuration = Configuration(access_token=settings.line_channel_access_token)
signature_validator = SignatureValidator(settings.line_channel_secret, settings.app_env)

# 初始化LINE API客戶端和訊息處理器
# 使用新架構的增強版服務工廠
enhanced_factory = get_enhanced_service_factory()
enhanced_factory.initialize()
message_handler: MessageHandlerDI = enhanced_factory.create_message_handler()

webhook_requests_total = Counter(
    "webhook_requests_total",
    "Total webhook requests",
    ["event_type", "status"],
)


@router.post("/Webhook")
async def handle_webhook(
    request: Request,
    x_line_signature: str = Header(None, alias="X-Line-Signature"),
    x_line_request_id: str = Header(None, alias="X-Line-Request-Id"),
):
    try:
        logger.info(
            "Received webhook request",
            signature_present=bool(x_line_signature),
            request_id=x_line_request_id,
        )

        body = await request.body()
        body_str = body.decode("utf-8")

        logger.info(
            "Processing webhook body",
            body_length=len(body_str),
            body_preview=body_str[:200],
        )

        # 使用安全的簽章驗證器
        if not x_line_signature:
            logger.error("Missing X-Line-Signature header")
            webhook_requests_total.labels(
                event_type="unknown", status="missing_signature"
            ).inc()
            raise HTTPException(status_code=400, detail="Missing signature")

        # 驗證簽章
        is_valid, validation_method = signature_validator.validate(
            body, x_line_signature
        )

        if not is_valid:
            logger.error(
                "Invalid LINE signature",
                request_id=x_line_request_id,
                validation_method=validation_method,
                body_preview=body_str[:100],
            )
            webhook_requests_total.labels(event_type="unknown", status="invalid").inc()
            raise HTTPException(status_code=400, detail="Invalid signature")

        logger.info(
            "Signature validation successful", validation_method=validation_method
        )

        # 直接處理 LINE webhook 事件，繞過同步事件處理器
        try:
            webhook_data = json.loads(body_str)
            events = webhook_data.get("events", [])

            logger.info(f"Processing {len(events)} webhook events")

            # 使用 asyncio.gather 並行處理所有事件，設定總超時時間
            if events:
                # 創建所有事件的處理任務
                event_tasks = []
                for event in events:
                    if (
                        event.get("type") == "message"
                        and event.get("message", {}).get("type") == "text"
                    ):
                        event_tasks.append(handle_text_message_async(event))
                    else:
                        logger.info(f"Skipping event type: {event.get('type')}")
                        webhook_requests_total.labels(
                            event_type=event.get("type", "unknown"), status="skipped"
                        ).inc()

                # 並行處理所有事件，設定 30 秒總超時（與消息處理超時一致）
                if event_tasks:
                    try:
                        await asyncio.wait_for(
                            asyncio.gather(*event_tasks, return_exceptions=True),
                            timeout=30.0,
                        )
                        webhook_requests_total.labels(
                            event_type="message", status="success"
                        ).inc()
                    except TimeoutError:
                        logger.warning(
                            f"Webhook processing timeout for {len(event_tasks)} events"
                        )
                        webhook_requests_total.labels(
                            event_type="message", status="timeout"
                        ).inc()
                        # 繼續返回成功，讓 LINE Platform 知道我們收到了請求

            logger.info("Webhook events processed successfully")
        except Exception as e:
            logger.error("Webhook processing error", error=str(e), exc_info=e)
            webhook_requests_total.labels(
                event_type="unknown", status="processing_error"
            ).inc()
            # 不拋出異常，返回成功響應避免 LINE Platform 重試
            logger.warning(
                "Returning success despite processing error to prevent retries"
            )

        logger.info("Webhook processed successfully")
        return JSONResponse(content={"status": "ok"})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected webhook error",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=e,
        )
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/test")
async def test_endpoint():
    """Simple test endpoint to verify service is running"""
    return JSONResponse(
        content={
            "status": "ok",
            "message": "LINE webhook service is running",
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )

@router.post("/test-llm")
async def test_llm_guidance(request: Request):
    """測試 LLM 指導功能的端點"""
    try:
        body = await request.json()
        user_input = body.get("text", "機台")
        
        # 獲取服務工廠
        factory = get_enhanced_service_factory()
        message_handler = factory.create_message_handler()
        
        # 模擬處理用戶訊息（使用正確的方法名稱）
        result = await message_handler.process_message(
            user_id="test_user", 
            message_text=user_input, 
            reply_token="test_token"
        )
        
        return JSONResponse(
            content={
                "status": "success", 
                "input": user_input,
                "response": result.text if hasattr(result, 'text') else str(result),
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
        
    except Exception as e:
        logger.error("測試端點錯誤", error=str(e))
        return JSONResponse(
            content={
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            },
            status_code=500
        )


@router.get("/health")
async def health_check():
    """
    健康檢查端點 - T-08 實施
    提供詳細的服務狀態、進程存活檢查和依賴服務監控
    """
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "service": "LINE MCP Bot",
            "version": "v2.2",
            "checks": {},
        }

        # 1. 基本進程檢查
        health_status["checks"]["process"] = {
            "status": "ok",
            "message": "Process is running",
        }

        # 2. 服務工廠健康檢查
        try:
            factory_health = enhanced_factory.get_health_status()
            health_status["checks"]["service_factory"] = {
                "status": "ok" if factory_health.get("healthy", False) else "warning",
                "services_count": factory_health.get("services_count", 0),
                "message": (
                    f"Service factory operational with "
                    f"{factory_health.get('services_count', 0)} services"
                ),
            }
        except Exception as e:
            health_status["checks"]["service_factory"] = {
                "status": "error",
                "message": f"Service factory check failed: {str(e)}",
            }
            health_status["status"] = "degraded"

        # 3. 訊息處理器健康檢查
        try:
            # 測試訊息處理器是否可用
            if message_handler:
                health_status["checks"]["message_handler"] = {
                    "status": "ok",
                    "message": "Message handler is available",
                }
            else:
                health_status["checks"]["message_handler"] = {
                    "status": "error",
                    "message": "Message handler not initialized",
                }
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["checks"]["message_handler"] = {
                "status": "error",
                "message": f"Message handler check failed: {str(e)}",
            }
            health_status["status"] = "degraded"

        # 4. LINE API 配置檢查
        try:
            if settings.line_channel_access_token and settings.line_channel_secret:
                health_status["checks"]["line_config"] = {
                    "status": "ok",
                    "message": "LINE API configuration is present",
                }
            else:
                health_status["checks"]["line_config"] = {
                    "status": "error",
                    "message": "LINE API configuration missing",
                }
                health_status["status"] = "unhealthy"
        except Exception as e:
            health_status["checks"]["line_config"] = {
                "status": "error",
                "message": f"LINE config check failed: {str(e)}",
            }
            health_status["status"] = "degraded"

        # 5. AI 服務健康檢查
        try:
            ai_service = enhanced_factory.get_ai_service()
            if ai_service:
                health_status["checks"]["ai_service"] = {
                    "status": "ok",
                    "message": "AI service is available",
                }
            else:
                health_status["checks"]["ai_service"] = {
                    "status": "warning",
                    "message": "AI service not available",
                }
                health_status["status"] = (
                    "degraded"
                    if health_status["status"] == "healthy"
                    else health_status["status"]
                )
        except Exception as e:
            health_status["checks"]["ai_service"] = {
                "status": "warning",
                "message": f"AI service check failed: {str(e)}",
            }
            health_status["status"] = (
                "degraded"
                if health_status["status"] == "healthy"
                else health_status["status"]
            )

        # 6. NL-to-SQL 服務健康檢查
        try:
            nl_service = enhanced_factory.get_nl_service()
            if nl_service:
                health_status["checks"]["nl_to_sql"] = {
                    "status": "ok",
                    "message": "NL-to-SQL service is available",
                }
            else:
                health_status["checks"]["nl_to_sql"] = {
                    "status": "warning",
                    "message": "NL-to-SQL service not available",
                }
                health_status["status"] = (
                    "degraded"
                    if health_status["status"] == "healthy"
                    else health_status["status"]
                )
        except Exception as e:
            health_status["checks"]["nl_to_sql"] = {
                "status": "warning",
                "message": f"NL-to-SQL service check failed: {str(e)}",
            }
            health_status["status"] = (
                "degraded"
                if health_status["status"] == "healthy"
                else health_status["status"]
            )

        # 設置 HTTP 狀態碼
        status_code = 200
        if health_status["status"] == "degraded":
            status_code = 200  # 仍可服務，但有警告
        elif health_status["status"] == "unhealthy":
            status_code = 503  # 服務不可用

        return JSONResponse(content=health_status, status_code=status_code)

    except Exception as e:
        logger.error("Health check failed", error=str(e), exc_info=e)
        return JSONResponse(
            content={
                "status": "unhealthy",
                "timestamp": datetime.now(UTC).isoformat(),
                "error": "Health check system failure",
                "message": str(e),
            },
            status_code=503,
        )


async def handle_text_message_async(event: dict):
    """非同步處理 LINE 文字訊息事件 - 快速回應版本"""
    try:
        user_id = event.get("source", {}).get("userId", "")
        message_text = event.get("message", {}).get("text", "")
        reply_token = event.get("replyToken", "")

        if not user_id or not message_text or not reply_token:
            logger.warning("Missing required event data", event=event)
            return

        user_id_hash = hashlib.sha256(
            (user_id + settings.jwt_secret_key).encode()
        ).hexdigest()[:8]

        logger.info(
            "Processing text message async",
            user_id_hash=user_id_hash,
            message_text=message_text[:50],
        )

        # 使用 asyncio.wait_for 設定超時限制，確保不會超過 LINE 的要求
        try:
            # 設定 25 秒超時，足夠處理複雜查詢但避免無限等待
            reply_message = await asyncio.wait_for(
                message_handler.process_message(
                    user_id=user_id, message_text=message_text, reply_token=reply_token
                ),
                timeout=25.0,
            )

            # 發送回覆訊息
            if reply_message and reply_token:
                await send_reply_message_async(reply_token, reply_message)

        except TimeoutError:
            logger.warning(
                "Message processing timeout, sending quick response",
                user_id_hash=user_id_hash,
                message_text=message_text[:50],
            )

            # 發送快速回應
            quick_response = TextMessage(text="⏳ 正在處理您的請求，請稍候...")
            await send_reply_message_async(reply_token, quick_response)

            # 超時情況下無法進行進一步處理，直接返回

    except Exception as e:
        logger.error("Error processing text message", error=str(e), exc_info=e)

        # 發送錯誤回應
        try:
            error_response = TextMessage(text="❌ 處理訊息時發生錯誤，請稍後再試")
            await send_reply_message_async(reply_token, error_response)
        except Exception as send_error:
            logger.error("Failed to send error response", error=str(send_error))


async def send_reply_message_async(reply_token: str, message):
    """非同步發送回覆訊息"""
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)

            # 在執行緒池中執行同步 API 呼叫
            def send_sync():
                line_bot_api.reply_message(
                    ReplyMessageRequest(reply_token=reply_token, messages=[message])
                )

            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                await loop.run_in_executor(executor, send_sync)

        logger.info("Reply message sent successfully", reply_token=reply_token)

    except Exception as e:
        logger.error(
            "Failed to send reply message", error=str(e), reply_token=reply_token
        )


# 優化完成：移除了損壞的 replay attack 檢查和未使用的背景處理功能
