import json
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.services.message_handler import MessageHandler

logger = structlog.get_logger()
settings = get_settings()
router = APIRouter()
message_handler = MessageHandler()


@router.post("/test-webhook")
async def handle_test_webhook(request: Request):
    """
    測試用的 webhook 端點 - 僅在開發環境使用
    不進行簽章驗證，用於本機測試和除錯
    """
    if settings.app_env.lower() not in ["development", "dev", "test"]:
        raise HTTPException(
            status_code=404, detail="Test endpoint not available in production"
        )

    try:
        logger.info("Received test webhook request")

        body = await request.body()
        body_str = body.decode("utf-8")

        logger.info(
            "Processing test webhook body",
            body_length=len(body_str),
            body_preview=body_str[:200],
        )

        # 解析測試請求
        try:
            webhook_data = json.loads(body_str)
            events = webhook_data.get("events", [])

            for event in events:
                if (
                    event.get("type") == "message"
                    and event.get("message", {}).get("type") == "text"
                ):
                    message_text = event["message"]["text"]
                    user_id = event["source"]["userId"]
                    reply_token = event["replyToken"]

                    logger.info(
                        "Processing test message",
                        user_id=user_id,
                        message_text=message_text,
                    )

                    # 處理訊息（但不真正回覆，因為沒有有效的 reply_token）
                    response_message = await message_handler.process_message(
                        user_id=user_id,
                        message_text=message_text,
                        reply_token=reply_token,
                    )

                    logger.info(
                        "Test message processed successfully",
                        response_type=type(response_message).__name__,
                        response_text=getattr(response_message, "text", "N/A")[:100],
                    )

        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in test request", error=str(e))
            raise HTTPException(status_code=400, detail="Invalid JSON")
        except Exception as e:
            logger.error("Failed to process test message", error=str(e), exc_info=e)
            raise HTTPException(status_code=500, detail="Message processing failed")

        logger.info("Test webhook processed successfully")
        return JSONResponse(
            content={
                "status": "ok",
                "message": "Test webhook processed successfully",
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected test webhook error",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=e,
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/test-status")
async def test_status():
    """測試狀態檢查端點"""
    if settings.app_env.lower() not in ["development", "dev", "test"]:
        raise HTTPException(
            status_code=404, detail="Test endpoint not available in production"
        )

    return JSONResponse(
        content={
            "status": "ok",
            "environment": settings.app_env,
            "message": "Test webhook service is running",
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )
