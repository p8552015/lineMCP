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

                # 並行處理所有事件，設定 9 秒總超時
                if event_tasks:
                    try:
                        await asyncio.wait_for(
                            asyncio.gather(*event_tasks, return_exceptions=True),
                            timeout=9.0,
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
        raise HTTPException(status_code=500, detail="Internal server error")


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
            # 設定 8 秒超時（LINE Platform 通常要求 10 秒內回應）
            reply_message = await asyncio.wait_for(
                message_handler.process_message(
                    user_id=user_id, message_text=message_text, reply_token=reply_token
                ),
                timeout=8.0,
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
