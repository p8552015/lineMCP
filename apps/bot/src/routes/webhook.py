from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import JSONResponse
import structlog
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import hashlib
from datetime import datetime, timezone
from prometheus_client import Counter

from src.config import get_settings
from src.services.message_handler import MessageHandler
from src.utils.signature_validator import SignatureValidator
# from src.utils.redis_client import get_cached_value, set_cached_value
# from src.utils.observability import get_tracer

logger = structlog.get_logger()
settings = get_settings()
router = APIRouter()
# tracer = get_tracer(__name__)

webhook_handler = WebhookHandler(settings.line_channel_secret)
configuration = Configuration(access_token=settings.line_channel_access_token)
signature_validator = SignatureValidator(settings.line_channel_secret, settings.app_env)

# 初始化LINE API客戶端和訊息處理器
from src.services.message_handler import MessageHandler
message_handler = MessageHandler()


webhook_requests_total = Counter(
    "webhook_requests_total",
    "Total webhook requests",
    ["event_type", "status"],
)

replay_attacks_blocked = Counter(
    "replay_attacks_blocked_total",
    "Total replay attacks blocked",
)


@router.post("/Webhook")
async def handle_webhook(
    request: Request,
    x_line_signature: str = Header(None, alias="X-Line-Signature"),
    x_line_request_id: str = Header(None, alias="X-Line-Request-Id"),
):
    try:
        # with tracer.start_as_current_span("webhook_handler") as span:
        #     span.set_attribute("line.request_id", x_line_request_id or "")
        
        logger.info("Received webhook request", 
                   signature_present=bool(x_line_signature),
                   request_id=x_line_request_id)
        
        body = await request.body()
        body_str = body.decode("utf-8")
        
        logger.info("Processing webhook body", body_length=len(body_str), body_preview=body_str[:200])

        # 使用安全的簽章驗證器
        if not x_line_signature:
            logger.error("Missing X-Line-Signature header")
            webhook_requests_total.labels(event_type="unknown", status="missing_signature").inc()
            raise HTTPException(status_code=400, detail="Missing signature")

        # 驗證簽章
        is_valid, validation_method = signature_validator.validate(body, x_line_signature)
        
        if not is_valid:
            logger.error("Invalid LINE signature", 
                       request_id=x_line_request_id,
                       validation_method=validation_method,
                       body_preview=body_str[:100])
            webhook_requests_total.labels(event_type="unknown", status="invalid").inc()
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        logger.info("Signature validation successful", validation_method=validation_method)

        # 直接處理 LINE webhook 事件，繞過同步事件處理器
        try:
            import json
            webhook_data = json.loads(body_str)
            events = webhook_data.get('events', [])
            
            logger.info(f"Processing {len(events)} webhook events")
            
            # 使用 asyncio.gather 並行處理所有事件，設定總超時時間
            import asyncio
            
            if events:
                # 創建所有事件的處理任務
                event_tasks = []
                for event in events:
                    if event.get('type') == 'message' and event.get('message', {}).get('type') == 'text':
                        event_tasks.append(handle_text_message_async(event))
                    else:
                        logger.info(f"Skipping event type: {event.get('type')}")
                        webhook_requests_total.labels(event_type=event.get('type', 'unknown'), status="skipped").inc()
                
                # 並行處理所有事件，設定 9 秒總超時
                if event_tasks:
                    try:
                        await asyncio.wait_for(
                            asyncio.gather(*event_tasks, return_exceptions=True),
                            timeout=9.0
                        )
                        webhook_requests_total.labels(event_type="message", status="success").inc()
                    except asyncio.TimeoutError:
                        logger.warning(f"Webhook processing timeout for {len(event_tasks)} events")
                        webhook_requests_total.labels(event_type="message", status="timeout").inc()
                        # 繼續返回成功，讓 LINE Platform 知道我們收到了請求
            
            logger.info("Webhook events processed successfully")
        except Exception as e:
            logger.error("Webhook processing error", error=str(e), exc_info=e)
            webhook_requests_total.labels(event_type="unknown", status="processing_error").inc()
            # 不拋出異常，返回成功響應避免 LINE Platform 重試
            logger.warning("Returning success despite processing error to prevent retries")

        # Skip replay attack check for now to debug
        # try:
        #     if await check_replay_attack(body_str, x_line_request_id):
        #         logger.warning("Replay attack detected", request_id=x_line_request_id)
        #         replay_attacks_blocked.inc()
        #         raise HTTPException(status_code=400, detail="Duplicate request")
        # except Exception as e:
        #     logger.warning("Replay check failed, skipping", error=str(e))

        logger.info("Webhook processed successfully")
        return JSONResponse(content={"status": "ok"})
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected webhook error", 
                   error=str(e),
                   error_type=type(e).__name__,
                   exc_info=e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/test")
async def test_endpoint():
    """Simple test endpoint to verify service is running"""
    return JSONResponse(content={
        "status": "ok", 
        "message": "LINE webhook service is running",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


async def handle_text_message_async(event: dict):
    """非同步處理 LINE 文字訊息事件 - 快速回應版本"""
    try:
        user_id = event.get('source', {}).get('userId', '')
        message_text = event.get('message', {}).get('text', '')
        reply_token = event.get('replyToken', '')
        
        if not user_id or not message_text or not reply_token:
            logger.warning("Missing required event data", event=event)
            return
        
        user_id_hash = hashlib.sha256(
            (user_id + settings.jwt_secret_key).encode()
        ).hexdigest()[:8]
        
        logger.info("Processing text message async", 
                   user_id_hash=user_id_hash,
                   message_text=message_text[:50])
        
        # 使用 asyncio.wait_for 設定超時限制，確保不會超過 LINE 的要求
        import asyncio
        
        try:
            # 設定 8 秒超時（LINE Platform 通常要求 10 秒內回應）
            reply_message = await asyncio.wait_for(
                message_handler.process_message(
                    user_id=user_id,
                    message_text=message_text,
                    reply_token=reply_token
                ),
                timeout=8.0
            )
            
            # 發送回覆訊息
            if reply_message and reply_token:
                await send_reply_message_async(reply_token, reply_message)
                
        except asyncio.TimeoutError:
            logger.warning("Message processing timeout, sending quick response", 
                         user_id_hash=user_id_hash,
                         message_text=message_text[:50])
            
            # 發送快速回應
            quick_response = TextMessage(text="⏳ 正在處理您的請求，請稍候...")
            await send_reply_message_async(reply_token, quick_response)
            
            # 在背景繼續處理（不等待結果）
            # 註：背景任務可能會引起異步上下文問題，暫時禁用
            # asyncio.create_task(process_message_background(user_id, message_text))
            logger.info("背景處理已暫時禁用以避免異步上下文問題")
            
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
            import asyncio
            import concurrent.futures
            
            def send_sync():
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[message]
                    )
                )
            
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                await loop.run_in_executor(executor, send_sync)
                
        logger.info("Reply message sent successfully", reply_token=reply_token)
        
    except Exception as e:
        logger.error("Failed to send reply message", 
                   error=str(e), 
                   reply_token=reply_token)


async def process_message_background(user_id: str, message_text: str):
    """背景處理訊息（用於超時後的處理）"""
    try:
        logger.info("Processing message in background", 
                   user_id_hash=hashlib.sha256((user_id + settings.jwt_secret_key).encode()).hexdigest()[:8],
                   message_text=message_text[:50])
        
        # 在背景處理訊息，不需要 reply_token
        result = await message_handler.process_message(
            user_id=user_id,
            message_text=message_text,
            reply_token=""  # 背景處理不需要 reply token
        )
        
        logger.info("Background message processing completed")
        
    except Exception as e:
        logger.error("Background message processing failed", error=str(e), exc_info=e)


async def check_replay_attack(body: str, request_id: str) -> bool:
    if not request_id:
        return False
    
    cache_key = f"line_request:{request_id}"
    if await get_cached_value(cache_key):
        return True
    
    body_hash = hashlib.sha256(body.encode()).hexdigest()
    await set_cached_value(cache_key, body_hash, expire_seconds=300)
    return False


# 舊的同步事件處理器已移除，現在使用完全非同步的架構