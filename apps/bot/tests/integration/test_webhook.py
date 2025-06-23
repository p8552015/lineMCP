"""Webhook 整合測試"""
import pytest
import httpx
import json
import hashlib
import hmac
import base64
import os
import sys

# 添加 src 到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))


class TestWebhook:
    """Webhook 測試類別"""
    
    BASE_URL = "http://localhost:8000"
    WEBHOOK_URL = f"{BASE_URL}/webhook"
    
    # 測試用的 LINE Channel Secret
    TEST_CHANNEL_SECRET = "test_channel_secret"
    
    def create_line_signature(self, body: str, secret: str) -> str:
        """創建 LINE 簽名"""
        signature = hmac.new(
            secret.encode('utf-8'),
            body.encode('utf-8'),
            hashlib.sha256
        ).digest()
        return base64.b64encode(signature).decode('utf-8')
    
    def create_test_message_event(self, message_text: str = "測試訊息") -> dict:
        """創建測試訊息事件"""
        return {
            "events": [
                {
                    "type": "message",
                    "message": {
                        "type": "text",
                        "text": message_text
                    },
                    "source": {
                        "type": "user",
                        "userId": "test_user_123"
                    },
                    "replyToken": "test_reply_token_123",
                    "timestamp": 1234567890123
                }
            ],
            "destination": "test_destination"
        }
    
    @pytest.mark.asyncio
    async def test_webhook_post_method_only(self):
        """測試 Webhook 只接受 POST 方法"""
        async with httpx.AsyncClient() as client:
            try:
                # 測試 GET 請求
                response = await client.get(self.WEBHOOK_URL)
                assert response.status_code == 405  # Method Not Allowed
                
            except httpx.ConnectError:
                pytest.skip("應用程式未運行，跳過 Webhook 方法測試")
    
    @pytest.mark.asyncio
    async def test_webhook_missing_signature(self):
        """測試缺少簽名的請求"""
        async with httpx.AsyncClient() as client:
            try:
                event_data = self.create_test_message_event()
                body = json.dumps(event_data)
                
                # 不包含 X-Line-Signature 標頭
                response = await client.post(
                    self.WEBHOOK_URL,
                    content=body,
                    headers={"Content-Type": "application/json"}
                )
                
                # 應該返回 400 或 401（未授權）
                assert response.status_code in [400, 401, 403]
                
            except httpx.ConnectError:
                pytest.skip("應用程式未運行，跳過簽名測試")
    
    @pytest.mark.asyncio
    async def test_webhook_invalid_signature(self):
        """測試無效簽名的請求"""
        async with httpx.AsyncClient() as client:
            try:
                event_data = self.create_test_message_event()
                body = json.dumps(event_data)
                
                # 使用無效的簽名
                response = await client.post(
                    self.WEBHOOK_URL,
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Line-Signature": "invalid_signature"
                    }
                )
                
                # 應該返回 400 或 401（簽名驗證失敗）
                assert response.status_code in [400, 401, 403]
                
            except httpx.ConnectError:
                pytest.skip("應用程式未運行，跳過無效簽名測試")
    
    @pytest.mark.asyncio
    async def test_webhook_valid_signature_structure(self):
        """測試有效簽名結構（不進行實際驗證）"""
        event_data = self.create_test_message_event()
        body = json.dumps(event_data)
        
        # 創建測試簽名
        signature = self.create_line_signature(body, self.TEST_CHANNEL_SECRET)
        
        # 驗證簽名格式
        assert len(signature) > 0
        assert isinstance(signature, str)
        
        # Base64 格式檢查
        try:
            decoded = base64.b64decode(signature)
            assert len(decoded) == 32  # SHA256 哈希長度
        except Exception:
            pytest.fail("簽名不是有效的 Base64 格式")
    
    @pytest.mark.asyncio
    async def test_webhook_empty_body(self):
        """測試空請求體"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.WEBHOOK_URL,
                    content="",
                    headers={"Content-Type": "application/json"}
                )
                
                # 空請求體應該返回錯誤
                assert response.status_code in [400, 422]
                
            except httpx.ConnectError:
                pytest.skip("應用程式未運行，跳過空請求體測試")
    
    @pytest.mark.asyncio
    async def test_webhook_invalid_json(self):
        """測試無效 JSON 格式"""
        async with httpx.AsyncClient() as client:
            try:
                invalid_json = "{ invalid json format"
                
                response = await client.post(
                    self.WEBHOOK_URL,
                    content=invalid_json,
                    headers={"Content-Type": "application/json"}
                )
                
                # 無效 JSON 應該返回錯誤
                assert response.status_code in [400, 422]
                
            except httpx.ConnectError:
                pytest.skip("應用程式未運行，跳過無效 JSON 測試")
    
    @pytest.mark.asyncio
    async def test_webhook_message_event_structure(self):
        """測試訊息事件結構"""
        # 測試不同類型的訊息事件
        message_events = [
            {
                "description": "文字訊息",
                "event": self.create_test_message_event("你好")
            },
            {
                "description": "查詢指令",
                "event": self.create_test_message_event("查看所有機台")
            },
            {
                "description": "特殊字符",
                "event": self.create_test_message_event("測試@#$%^&*()")
            }
        ]
        
        for test_case in message_events:
            event_data = test_case["event"]
            
            # 驗證事件結構
            assert "events" in event_data
            assert len(event_data["events"]) > 0
            
            event = event_data["events"][0]
            assert event["type"] == "message"
            assert "message" in event
            assert "source" in event
            assert "replyToken" in event
            
            message = event["message"]
            assert message["type"] == "text"
            assert "text" in message
            assert len(message["text"]) > 0
    
    @pytest.mark.asyncio
    async def test_webhook_content_type_validation(self):
        """測試內容類型驗證"""
        async with httpx.AsyncClient() as client:
            try:
                event_data = self.create_test_message_event()
                body = json.dumps(event_data)
                
                # 測試錯誤的 Content-Type
                response = await client.post(
                    self.WEBHOOK_URL,
                    content=body,
                    headers={"Content-Type": "text/plain"}
                )
                
                # 應該要求 application/json
                assert response.status_code in [400, 415, 422]
                
            except httpx.ConnectError:
                pytest.skip("應用程式未運行，跳過內容類型測試")
    
    @pytest.mark.asyncio
    async def test_webhook_large_payload(self):
        """測試大型請求負載"""
        async with httpx.AsyncClient() as client:
            try:
                # 創建大型訊息（但不超過合理限制）
                large_message = "A" * 1000  # 1KB 訊息
                event_data = self.create_test_message_event(large_message)
                body = json.dumps(event_data)
                
                response = await client.post(
                    self.WEBHOOK_URL,
                    content=body,
                    headers={"Content-Type": "application/json"}
                )
                
                # 大型但合理的請求應該被處理（可能因簽名失敗而返回 401）
                assert response.status_code != 413  # 不應該是 Payload Too Large
                
            except httpx.ConnectError:
                pytest.skip("應用程式未運行，跳過大型負載測試")
    
    @pytest.mark.asyncio
    async def test_webhook_concurrent_requests(self):
        """測試併發 Webhook 請求"""
        import asyncio
        
        async with httpx.AsyncClient() as client:
            try:
                # 創建多個併發請求
                tasks = []
                for i in range(3):
                    event_data = self.create_test_message_event(f"訊息 {i}")
                    body = json.dumps(event_data)
                    
                    task = client.post(
                        self.WEBHOOK_URL,
                        content=body,
                        headers={"Content-Type": "application/json"}
                    )
                    tasks.append(task)
                
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 檢查所有請求都得到回應（不管是成功還是失敗）
                for response in responses:
                    if isinstance(response, httpx.Response):
                        assert response.status_code is not None
                        # 由於沒有有效簽名，期望 400/401/403
                        assert response.status_code in [400, 401, 403]
                
            except httpx.ConnectError:
                pytest.skip("應用程式未運行，跳過併發請求測試")
    
    @pytest.mark.asyncio
    async def test_webhook_response_time(self):
        """測試 Webhook 回應時間"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                import time
                
                event_data = self.create_test_message_event("快速測試")
                body = json.dumps(event_data)
                
                start_time = time.time()
                
                response = await client.post(
                    self.WEBHOOK_URL,
                    content=body,
                    headers={"Content-Type": "application/json"}
                )
                
                end_time = time.time()
                response_time = end_time - start_time
                
                # Webhook 應該快速回應（即使是錯誤回應）
                assert response_time < 10.0, f"Webhook 回應時間過長: {response_time}s"
                
            except httpx.ConnectError:
                pytest.skip("應用程式未運行，跳過回應時間測試")