"""API 端點整合測試"""
import pytest
import httpx
import asyncio
import os
import sys

# 添加 src 到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))


class TestAPIEndpoints:
    """API 端點測試類別"""
    
    BASE_URL = "http://localhost:8000"
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """測試健康檢查端點"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.BASE_URL}/health")
                assert response.status_code == 200
                
                data = response.json()
                assert "status" in data
                assert data["status"] == "healthy"
                assert "timestamp" in data
                assert "version" in data
                
            except httpx.ConnectError:
                # 如果應用程式未運行，跳過測試
                pytest.skip("應用程式未運行，跳過 API 測試")
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint(self):
        """測試指標端點"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.BASE_URL}/metrics")
                # Prometheus 指標端點應該返回文本格式
                assert response.status_code == 200
                assert "text/plain" in response.headers.get("content-type", "")
                
                content = response.text
                # 檢查基本的 Prometheus 指標
                assert "python_info" in content or "http_requests_total" in content
                
            except httpx.ConnectError:
                pytest.skip("應用程式未運行，跳過指標測試")
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """測試根端點"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.BASE_URL}/")
                assert response.status_code == 200
                
                data = response.json()
                assert "message" in data or "service" in data
                
            except httpx.ConnectError:
                pytest.skip("應用程式未運行，跳過根端點測試")
    
    @pytest.mark.asyncio
    async def test_webhook_endpoint_structure(self):
        """測試 Webhook 端點結構（不發送實際 LINE 請求）"""
        webhook_url = f"{self.BASE_URL}/webhook"
        
        # 測試 GET 請求（應該不被允許）
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(webhook_url)
                # Webhook 通常只接受 POST 請求
                assert response.status_code in [405, 404]  # Method Not Allowed 或 Not Found
                
            except httpx.ConnectError:
                pytest.skip("應用程式未運行，跳過 Webhook 結構測試")
    
    @pytest.mark.asyncio
    async def test_cors_headers(self):
        """測試 CORS 標頭"""
        async with httpx.AsyncClient() as client:
            try:
                # 發送 OPTIONS 請求
                response = await client.options(f"{self.BASE_URL}/health")
                
                # 檢查 CORS 相關標頭
                headers = response.headers
                
                # 基本的 CORS 檢查（如果有配置的話）
                if "access-control-allow-origin" in headers:
                    assert headers["access-control-allow-origin"] is not None
                
            except httpx.ConnectError:
                pytest.skip("應用程式未運行，跳過 CORS 測試")
    
    @pytest.mark.asyncio
    async def test_response_time(self):
        """測試回應時間"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                import time
                start_time = time.time()
                
                response = await client.get(f"{self.BASE_URL}/health")
                
                end_time = time.time()
                response_time = end_time - start_time
                
                # 健康檢查應該在 5 秒內回應
                assert response_time < 5.0, f"回應時間過長: {response_time}s"
                assert response.status_code == 200
                
            except httpx.ConnectError:
                pytest.skip("應用程式未運行，跳過回應時間測試")
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """測試錯誤處理"""
        async with httpx.AsyncClient() as client:
            try:
                # 測試不存在的端點
                response = await client.get(f"{self.BASE_URL}/nonexistent")
                assert response.status_code == 404
                
                # 測試錯誤回應格式
                if response.headers.get("content-type", "").startswith("application/json"):
                    data = response.json()
                    # 檢查是否有錯誤訊息
                    assert "detail" in data or "error" in data or "message" in data
                
            except httpx.ConnectError:
                pytest.skip("應用程式未運行，跳過錯誤處理測試")
    
    @pytest.mark.asyncio 
    async def test_content_type_headers(self):
        """測試內容類型標頭"""
        endpoints = [
            ("/health", "application/json"),
            ("/metrics", "text/plain"),
        ]
        
        async with httpx.AsyncClient() as client:
            try:
                for endpoint, expected_content_type in endpoints:
                    response = await client.get(f"{self.BASE_URL}{endpoint}")
                    
                    if response.status_code == 200:
                        content_type = response.headers.get("content-type", "")
                        assert expected_content_type in content_type, \
                            f"端點 {endpoint} 的內容類型錯誤: 期望 {expected_content_type}, 實際 {content_type}"
                    
            except httpx.ConnectError:
                pytest.skip("應用程式未運行，跳過內容類型測試")
    
    @pytest.mark.asyncio
    async def test_security_headers(self):
        """測試安全標頭"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.BASE_URL}/health")
                
                if response.status_code == 200:
                    headers = response.headers
                    
                    # 檢查常見的安全標頭（如果有配置）
                    security_headers = [
                        "x-content-type-options",
                        "x-frame-options", 
                        "x-xss-protection"
                    ]
                    
                    # 記錄哪些安全標頭存在（不強制要求）
                    present_headers = []
                    for header in security_headers:
                        if header in headers:
                            present_headers.append(header)
                    
                    # 至少記錄結果，不強制通過
                    print(f"存在的安全標頭: {present_headers}")
                    
            except httpx.ConnectError:
                pytest.skip("應用程式未運行，跳過安全標頭測試")
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """測試併發請求處理"""
        async with httpx.AsyncClient() as client:
            try:
                # 發送多個併發請求
                tasks = []
                for i in range(5):
                    task = client.get(f"{self.BASE_URL}/health")
                    tasks.append(task)
                
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 檢查所有請求都成功
                successful_responses = 0
                for response in responses:
                    if isinstance(response, httpx.Response) and response.status_code == 200:
                        successful_responses += 1
                
                # 至少 80% 的請求應該成功
                success_rate = successful_responses / len(tasks)
                assert success_rate >= 0.8, f"併發請求成功率過低: {success_rate}"
                
            except httpx.ConnectError:
                pytest.skip("應用程式未運行，跳過併發測試")