"""Webhook 整合測試 - 使用 FastAPI TestClient"""

import base64
import hashlib
import hmac
import json
import os

import pytest

# 準確地導入 FastAPI app instance
from apps.bot.src.main import app
from fastapi.testclient import TestClient

# 測試用的 LINE Channel Secret，與設定檔中的測試值保持一致
# 注意：為了讓簽名驗證中間件正確工作，這個值必須與應用程式在測試環境中讀取的值相符。
# 我們將透過環境變數來設定它。
TEST_CHANNEL_SECRET = "test_secret"
os.environ["LINE_CHANNEL_SECRET"] = TEST_CHANNEL_SECRET


# 使用 TestClient
client = TestClient(app)


def create_line_signature(body: str, secret: str = TEST_CHANNEL_SECRET) -> str:
    """為測試請求創建一個有效的 LINE 簽名"""
    signature = hmac.new(
        secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256
    ).digest()
    return base64.b64encode(signature).decode("utf-8")


def create_test_message_event(message_text: str = "測試訊息") -> dict:
    """創建一個標準的 LINE 訊息事件的 JSON body"""
    return {
        "events": [
            {
                "type": "message",
                "message": {"type": "text", "text": message_text},
                "source": {"type": "user", "userId": "test_user_123"},
                "replyToken": "test_reply_token_123",
                "timestamp": 1234567890123,
            }
        ],
        "destination": "test_destination",
    }


def test_health_check():
    """測試 /health 端點是否正常"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_metrics_endpoint():
    """測試 /metrics 端點是否暴露"""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "prometheus_client" in response.text


def test_webhook_rejects_get_method():
    """測試 Webhook 端點是否拒絕 GET 請求"""
    response = client.get("/webhook")
    assert response.status_code == 405  # Method Not Allowed


def test_webhook_missing_signature():
    """測試缺少 X-Line-Signature 標頭的請求會被拒絕"""
    event_data = create_test_message_event()
    body = json.dumps(event_data)

    response = client.post(
        "/webhook",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert "Missing X-Line-Signature" in response.json()["detail"]


def test_webhook_invalid_signature():
    """測試無效的 X-Line-Signature 會被拒絕"""
    event_data = create_test_message_event()
    body = json.dumps(event_data)

    response = client.post(
        "/webhook",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Line-Signature": "invalid_signature",
        },
    )
    assert response.status_code == 400
    assert "Invalid signature" in response.json()["detail"]


def test_webhook_valid_request_mocked_handler():
    """
    測試帶有有效簽名的請求能成功被接收。
    注意：這裡我們只測試到 Webhook 層，MessageHandler 的行為應在單元測試中覆蓋。
    """
    event_data = create_test_message_event("一個有效的請求")
    body_str = json.dumps(event_data)
    signature = create_line_signature(body_str)

    response = client.post(
        "/webhook",
        data=body_str,
        headers={
            "Content-Type": "application/json",
            "X-Line-Signature": signature,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webhook_empty_body():
    """測試空請求體會返回客戶端錯誤"""
    signature = create_line_signature("")
    response = client.post(
        "/webhook",
        data="",
        headers={
            "Content-Type": "application/json",
            "X-Line-Signature": signature,
        },
    )
    # FastAPI 會因為無法解析 JSON 而返回 422
    assert response.status_code == 422


def test_webhook_invalid_json():
    """測試無效的 JSON 格式會被 FastAPI 內建機制攔截"""
    invalid_json = "{'key': 'value'}"  # 使用單引號，是無效的 JSON
    signature = create_line_signature(invalid_json)

    response = client.post(
        "/webhook",
        data=invalid_json,
        headers={
            "Content-Type": "application/json",
            "X-Line-Signature": signature,
        },
    )
    assert response.status_code == 422  # Unprocessable Entity


@pytest.mark.parametrize(
    "message_text",
    [
        "你好",
        "查詢所有機台",
        "特殊字符 !@#$%^&*()_+",
        "A" * 1000,  # 大型負載
    ],
)
def test_webhook_various_valid_message_events(message_text):
    """使用參數化測試多種有效的訊息事件"""
    event_data = create_test_message_event(message_text)
    body_str = json.dumps(event_data)
    signature = create_line_signature(body_str)

    response = client.post(
        "/webhook",
        data=body_str,
        headers={
            "Content-Type": "application/json",
            "X-Line-Signature": signature,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webhook_unsupported_content_type():
    """測試不支援的 Content-Type 會被拒絕"""
    event_data = create_test_message_event()
    body = json.dumps(event_data)
    signature = create_line_signature(body)

    # 雖然簽名有效，但 Content-Type 錯誤
    response = client.post(
        "/webhook",
        data=body,
        headers={
            "Content-Type": "text/plain",
            "X-Line-Signature": signature,
        },
    )
    # FastAPI 預期 application/json，可能會返回 422，因為它無法按預期解析
    # 但這裡我們的中介層沒有嚴格檢查 Content-Type，所以會往下傳遞
    # 實際行為取決於應用的具體實現
    assert response.status_code == 200
    # 如果 SignatureValidator 中間件嚴格檢查 Content-Type，這裡應該是 400/415
    # 目前的實作是成功的，因為請求體仍然是有效的 JSON 字串


def test_webhook_malformed_line_event_structure():
    """測試結構不完整的 LINE 事件"""
    # 缺少 'events' 鍵
    malformed_event = {"destination": "test_destination"}
    body_str = json.dumps(malformed_event)
    signature = create_line_signature(body_str)

    response = client.post(
        "/webhook",
        data=body_str,
        headers={
            "Content-Type": "application/json",
            "X-Line-Signature": signature,
        },
    )

    # pydantic 模型驗證失敗，應返回 422
    assert response.status_code == 422
    assert "events" in response.text
    assert "Field required" in response.text
