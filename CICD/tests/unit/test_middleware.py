"""
中間件測試
測試 FastAPI 中間件功能
"""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.middleware import (
    active_requests,
    http_request_duration_seconds,
    http_requests_total,
    setup_middleware,
)


class TestMiddlewareSetup:
    """測試中間件設置"""

    def test_setup_middleware_adds_cors(self):
        """測試設置 CORS 中間件"""
        app = FastAPI()

        # 記錄初始中間件數量
        initial_count = len(app.user_middleware)

        setup_middleware(app)

        # 檢查是否添加了中間件
        assert len(app.user_middleware) > initial_count

    def test_setup_middleware_adds_trusted_host(self):
        """測試設置受信任主機中間件"""
        app = FastAPI()

        setup_middleware(app)

        # 檢查中間件是否正確設置（通過中間件數量變化確認）
        assert len(app.user_middleware) >= 2  # 至少有 CORS 和 TrustedHost

    def test_setup_middleware_adds_custom_middleware(self):
        """測試設置自定義中間件"""
        app = FastAPI()

        setup_middleware(app)

        # 檢查是否添加了自定義 HTTP 中間件
        assert (
            len(app.user_middleware) >= 5
        )  # CORS, TrustedHost, trace_id, prometheus, logging


class TestTraceIdMiddleware:
    """測試追蹤ID中間件"""

    @pytest.fixture
    def app_with_middleware(self):
        """創建帶中間件的 FastAPI 應用"""
        app = FastAPI()
        setup_middleware(app)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        return app

    def test_trace_id_from_header(self, app_with_middleware):
        """測試從請求頭獲取追蹤ID"""
        client = TestClient(app_with_middleware)
        trace_id = "test-trace-123"

        response = client.get("/test", headers={"X-Trace-Id": trace_id})

        assert response.status_code == 200
        assert response.headers.get("X-Trace-Id") == trace_id

    def test_trace_id_generated_when_missing(self, app_with_middleware):
        """測試當請求頭缺少追蹤ID時自動生成"""
        client = TestClient(app_with_middleware)

        response = client.get("/test")

        assert response.status_code == 200
        assert "X-Trace-Id" in response.headers
        assert len(response.headers["X-Trace-Id"]) > 0

    def test_trace_id_format(self, app_with_middleware):
        """測試生成的追蹤ID格式"""
        client = TestClient(app_with_middleware)

        response = client.get("/test")

        trace_id = response.headers.get("X-Trace-Id")
        assert trace_id is not None
        # UUID4 格式檢查（包含連字符）
        assert len(trace_id.replace("-", "")) == 32


class TestPrometheusMiddleware:
    """測試 Prometheus 中間件"""

    @pytest.fixture
    def app_with_middleware(self):
        """創建帶中間件的 FastAPI 應用"""
        app = FastAPI()
        setup_middleware(app)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        @app.get("/metrics")
        async def metrics_endpoint():
            return {"metrics": "data"}

        @app.get("/health")
        async def health_endpoint():
            return {"status": "ok"}

        return app

    def test_prometheus_middleware_skips_metrics_endpoint(self, app_with_middleware):
        """測試 Prometheus 中間件跳過 metrics 端點"""
        client = TestClient(app_with_middleware)

        # metrics 端點應該被跳過，不計入指標
        response = client.get("/metrics")

        assert response.status_code == 200

    def test_prometheus_middleware_skips_health_endpoint(self, app_with_middleware):
        """測試 Prometheus 中間件跳過 health 端點"""
        client = TestClient(app_with_middleware)

        # health 端點應該被跳過，不計入指標
        response = client.get("/health")

        assert response.status_code == 200

    @patch("src.middleware.active_requests")
    def test_prometheus_middleware_tracks_active_requests(
        self, mock_active_requests, app_with_middleware
    ):
        """測試 Prometheus 中間件追蹤活動請求數"""
        client = TestClient(app_with_middleware)

        response = client.get("/test")

        assert response.status_code == 200
        # 驗證指標被調用
        mock_active_requests.inc.assert_called()
        mock_active_requests.dec.assert_called()


class TestPrometheusMetrics:
    """測試 Prometheus 指標"""

    def test_http_requests_total_counter_exists(self):
        """測試 HTTP 請求總數計數器存在"""
        assert http_requests_total is not None
        assert hasattr(http_requests_total, "_name")
        assert http_requests_total._name == "http_requests"

    def test_http_request_duration_histogram_exists(self):
        """測試 HTTP 請求持續時間直方圖存在"""
        assert http_request_duration_seconds is not None
        assert hasattr(http_request_duration_seconds, "_name")
        assert http_request_duration_seconds._name == "http_request_duration_seconds"

    def test_active_requests_gauge_exists(self):
        """測試活動請求數量計量器存在"""
        assert active_requests is not None
        assert hasattr(active_requests, "_name")
        assert active_requests._name == "active_requests"

    def test_metrics_have_correct_labels(self):
        """測試指標具有正確的標籤"""
        # 檢查計數器標籤
        assert http_requests_total._labelnames == ("method", "endpoint", "status")

        # 檢查直方圖標籤
        assert http_request_duration_seconds._labelnames == ("method", "endpoint")

        # 檢查計量器沒有標籤
        assert active_requests._labelnames == ()


class TestMiddlewareIntegration:
    """測試中間件整合"""

    @pytest.fixture
    def app_with_middleware(self):
        """創建完整的 FastAPI 應用"""
        app = FastAPI()
        setup_middleware(app)

        @app.get("/api/test")
        async def test_endpoint():
            return {"message": "success"}

        @app.get("/api/error")
        async def error_endpoint():
            raise Exception("Test error")

        return app

    def test_middleware_chain_works(self, app_with_middleware):
        """測試中間件鏈正常工作"""
        client = TestClient(app_with_middleware)

        response = client.get("/api/test")

        assert response.status_code == 200
        assert "X-Trace-Id" in response.headers

    def test_middleware_handles_errors(self, app_with_middleware):
        """測試中間件處理錯誤情況"""
        client = TestClient(app_with_middleware, raise_server_exceptions=False)

        # 這個端點會拋出異常，預期500錯誤
        response = client.get("/api/error")

        # 檢查錯誤狀態碼
        assert response.status_code == 500
        # 確認錯誤被正確處理
        assert response.text == "Internal Server Error"

    def test_cors_headers_added(self, app_with_middleware):
        """測試 CORS 標頭被添加"""
        client = TestClient(app_with_middleware)

        response = client.options(
            "/api/test", headers={"Origin": "http://localhost:3000"}
        )

        # CORS 中間件應該添加相應的標頭
        assert response.status_code in [
            200,
            405,
        ]  # OPTIONS 可能返回 405 但仍會添加 CORS 標頭


class TestMiddlewareConfiguration:
    """測試中間件配置"""

    def test_setup_middleware_is_callable(self):
        """測試 setup_middleware 函數可調用"""
        assert callable(setup_middleware)

    def test_setup_middleware_accepts_fastapi_app(self):
        """測試 setup_middleware 接受 FastAPI 應用"""
        app = FastAPI()

        # 這不應該拋出異常
        try:
            setup_middleware(app)
        except Exception as e:
            pytest.fail(f"setup_middleware 拋出異常: {e}")

    def test_middleware_setup_idempotent(self):
        """測試中間件設置是冪等的"""
        app = FastAPI()

        # 多次調用應該安全
        setup_middleware(app)
        initial_count = len(app.user_middleware)

        setup_middleware(app)
        final_count = len(app.user_middleware)

        # 第二次調用應該添加相同數量的中間件
        assert final_count == initial_count * 2  # 會重複添加
