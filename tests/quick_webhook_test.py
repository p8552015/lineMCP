#!/usr/bin/env python3
"""
Quick webhook test with timeout handling
快速測試 webhook 超時處理
"""

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
import asyncio
import json
import structlog

app = FastAPI(title="Quick Webhook Test")
logger = structlog.get_logger()

@app.post("/Webhook")
async def quick_webhook(
    request: Request,
    x_line_signature: str = Header(None, alias="X-Line-Signature")
):
    """快速 webhook 測試端點"""
    try:
        # 立即記錄收到請求
        start_time = asyncio.get_event_loop().time()
        logger.info("Webhook request received", signature_present=bool(x_line_signature))
        
        # 讀取 body
        body = await request.body()
        body_str = body.decode("utf-8")
        
        logger.info("Body received", body_length=len(body_str))
        
        # 解析 webhook 資料
        try:
            webhook_data = json.loads(body_str)
            events = webhook_data.get('events', [])
            
            logger.info(f"Processing {len(events)} events")
            
            # 快速處理每個事件
            for event in events:
                if event.get('type') == 'message':
                    user_id = event.get('source', {}).get('userId', '')
                    message_text = event.get('message', {}).get('text', '')
                    reply_token = event.get('replyToken', '')
                    
                    logger.info("Message event", 
                              user_id=user_id[:8] + "...",
                              message=message_text[:50],
                              has_reply_token=bool(reply_token))
                    
                    # 這裡可以添加實際的訊息處理邏輯
                    # 目前只記錄
                
        except json.JSONDecodeError as e:
            logger.error("JSON decode error", error=str(e))
            raise HTTPException(status_code=400, detail="Invalid JSON")
        
        # 計算處理時間
        end_time = asyncio.get_event_loop().time()
        processing_time = (end_time - start_time) * 1000  # ms
        
        logger.info(f"Webhook processed successfully in {processing_time:.2f}ms")
        
        return JSONResponse(content={
            "status": "ok",
            "processing_time_ms": round(processing_time, 2),
            "events_processed": len(events)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Webhook error", error=str(e), exc_info=e)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/test")
async def test_endpoint():
    """測試端點"""
    return {
        "status": "ok",
        "message": "Quick webhook test is running",
        "timestamp": asyncio.get_event_loop().time()
    }


@app.get("/health")
async def health_check():
    """健康檢查"""
    return {"status": "healthy", "service": "quick_webhook_test"}


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting quick webhook test server...")
    print("📝 Webhook endpoint: http://localhost:8000/Webhook")
    print("🧪 Test endpoint: http://localhost:8000/test")
    
    uvicorn.run(
        "quick_webhook_test:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )