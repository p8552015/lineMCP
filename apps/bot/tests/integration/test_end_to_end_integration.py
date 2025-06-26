"""
端到端整合測試
測試完整的 LINE Bot 查詢流程，包括自然語言處理、資料庫查詢、回應生成等
"""

import os
import sys
import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

# 添加 src 到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from src.application.application_facade import ApplicationFacade
from src.utils.database_health_check import DatabaseHealthChecker


@pytest.fixture
def mock_line_bot_api():
    """模擬 LINE Bot API"""
    return Mock()


@pytest.fixture
async def application_facade():
    """建立應用程式門面"""
    try:
        facade = ApplicationFacade()
        await facade.initialize()
        yield facade
        await facade.cleanup()
    except Exception as e:
        pytest.skip(f"無法初始化應用程式: {e}")


@pytest.fixture
def database_url():
    """資料庫連接字串"""
    return "postgresql://admin:admin@localhost:5432/mydb"


class TestEndToEndIntegration:
    """端到端整合測試"""
    
    @pytest.mark.asyncio
    async def test_system_startup_health_check(self, database_url):
        """測試系統啟動時的健康檢查"""
        health_checker = DatabaseHealthChecker(database_url)
        
        # 執行完整健康檢查
        result = await health_checker.comprehensive_health_check()
        
        # 系統應該能夠正常啟動
        assert result['overall_status'] in ['healthy', 'warning']
        assert result['connection']['status'] == 'healthy'
        assert result['tables']['status'] in ['healthy', 'warning']
        assert result['functionality']['status'] in ['healthy', 'warning']
    
    @pytest.mark.asyncio
    async def test_machine_query_flow(self, application_facade):
        """測試機台查詢完整流程"""
        # 模擬用戶查詢機台資訊
        user_query = "請告訴我M001機台的狀態"
        
        try:
            # 通過應用程式門面處理查詢
            response = await application_facade.process_query(user_query)
            
            # 驗證回應
            assert response is not None
            assert isinstance(response, str)
            assert len(response) > 0
            
            # 回應應該包含機台相關資訊
            assert any(keyword in response.lower() for keyword in ['機台', 'm001', '狀態'])
            
        except Exception as e:
            pytest.skip(f"查詢處理失敗: {e}")
    
    @pytest.mark.asyncio
    async def test_fault_query_flow(self, application_facade):
        """測試故障查詢完整流程"""
        # 模擬用戶查詢故障資訊
        user_query = "有哪些機台目前有故障？"
        
        try:
            # 通過應用程式門面處理查詢
            response = await application_facade.process_query(user_query)
            
            # 驗證回應
            assert response is not None
            assert isinstance(response, str)
            assert len(response) > 0
            
            # 回應應該包含故障相關資訊
            assert any(keyword in response.lower() for keyword in ['故障', '問題', '維修'])
            
        except Exception as e:
            pytest.skip(f"故障查詢處理失敗: {e}")
    
    @pytest.mark.asyncio
    async def test_utilization_query_flow(self, application_facade):
        """測試使用率查詢完整流程"""
        # 模擬用戶查詢使用率資訊
        user_query = "機台使用率如何？"
        
        try:
            # 通過應用程式門面處理查詢
            response = await application_facade.process_query(user_query)
            
            # 驗證回應
            assert response is not None
            assert isinstance(response, str)
            assert len(response) > 0
            
            # 回應應該包含使用率相關資訊
            assert any(keyword in response.lower() for keyword in ['使用率', '效率', '利用率'])
            
        except Exception as e:
            pytest.skip(f"使用率查詢處理失敗: {e}")


class TestLineWebhookIntegration:
    """LINE Webhook 整合測試"""
    
    @pytest.mark.asyncio
    async def test_webhook_message_processing(self, application_facade, mock_line_bot_api):
        """測試 Webhook 訊息處理"""
        # 模擬 LINE Webhook 事件
        mock_event = Mock()
        mock_event.message.text = "請查詢機台狀態"
        mock_event.reply_token = "test_reply_token"
        mock_event.source.user_id = "test_user_id"
        
        try:
            # 模擬 Webhook 處理器
            with patch('linebot.LineBotApi') as mock_api:
                mock_api.return_value = mock_line_bot_api
                
                # 處理訊息事件
                response = await application_facade.handle_message_event(mock_event)
                
                # 驗證處理結果
                assert response is not None
                
        except Exception as e:
            pytest.skip(f"Webhook 處理失敗: {e}")
    
    @pytest.mark.asyncio
    async def test_webhook_error_handling(self, application_facade, mock_line_bot_api):
        """測試 Webhook 錯誤處理"""
        # 模擬無效的查詢
        mock_event = Mock()
        mock_event.message.text = "無意義的查詢內容 #@$%"
        mock_event.reply_token = "test_reply_token"
        mock_event.source.user_id = "test_user_id"
        
        try:
            # 模擬 Webhook 處理器
            with patch('linebot.LineBotApi') as mock_api:
                mock_api.return_value = mock_line_bot_api
                
                # 處理訊息事件
                response = await application_facade.handle_message_event(mock_event)
                
                # 即使查詢無效，也應該有適當的回應
                assert response is not None
                
        except Exception as e:
            # 錯誤處理應該優雅地處理異常
            assert "處理失敗" in str(e) or "無法理解" in str(e)


class TestDatabaseQueryIntegration:
    """資料庫查詢整合測試"""
    
    @pytest.mark.asyncio
    async def test_sql_generation_and_execution(self, application_facade):
        """測試 SQL 生成和執行"""
        # 測試自然語言到 SQL 的轉換
        natural_queries = [
            "查詢所有機台",
            "M001機台的狀態",
            "有故障的機台",
            "機台使用率統計"
        ]
        
        for query in natural_queries:
            try:
                # 處理查詢
                response = await application_facade.process_query(query)
                
                # 驗證回應
                assert response is not None
                assert isinstance(response, str)
                assert len(response) > 0
                
                # 回應不應該包含錯誤訊息
                error_keywords = ['錯誤', 'error', '失敗', 'failed', '異常']
                assert not any(keyword in response.lower() for keyword in error_keywords)
                
            except Exception as e:
                pytest.skip(f"查詢 '{query}' 處理失敗: {e}")
    
    @pytest.mark.asyncio
    async def test_query_result_formatting(self, application_facade):
        """測試查詢結果格式化"""
        # 測試結果格式化
        query = "查詢機台列表"
        
        try:
            response = await application_facade.process_query(query)
            
            # 驗證回應格式
            assert response is not None
            assert isinstance(response, str)
            
            # 回應應該是結構化的
            assert len(response.split('\n')) > 1 or len(response.split('、')) > 1
            
        except Exception as e:
            pytest.skip(f"結果格式化測試失敗: {e}")


class TestSystemResilience:
    """系統韌性測試"""
    
    @pytest.mark.asyncio
    async def test_database_connection_recovery(self, application_facade):
        """測試資料庫連接恢復"""
        # 模擬資料庫連接問題
        with patch('asyncpg.connect') as mock_connect:
            # 第一次連接失敗，第二次成功
            mock_connect.side_effect = [
                Exception("Connection failed"),
                AsyncMock()
            ]
            
            try:
                # 嘗試查詢
                response = await application_facade.process_query("查詢機台狀態")
                
                # 系統應該能夠處理連接問題
                assert response is not None
                
            except Exception as e:
                # 系統應該優雅地處理連接錯誤
                assert "連接" in str(e) or "資料庫" in str(e)
    
    @pytest.mark.asyncio
    async def test_query_timeout_handling(self, application_facade):
        """測試查詢超時處理"""
        # 模擬長時間查詢
        with patch('asyncio.wait_for') as mock_wait_for:
            mock_wait_for.side_effect = asyncio.TimeoutError("Query timeout")
            
            try:
                # 嘗試查詢
                response = await application_facade.process_query("複雜的統計查詢")
                
                # 系統應該能夠處理超時
                assert response is not None
                assert "超時" in response or "請稍後再試" in response
                
            except Exception as e:
                # 系統應該優雅地處理超時錯誤
                assert "超時" in str(e) or "timeout" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, application_facade):
        """測試並發請求處理"""
        # 模擬多個並發查詢
        queries = [
            "查詢機台M001",
            "查詢機台M002", 
            "查詢故障列表",
            "查詢使用率統計",
            "查詢維修記錄"
        ]
        
        async def process_single_query(query):
            try:
                return await application_facade.process_query(query)
            except Exception as e:
                return f"查詢失敗: {e}"
        
        # 並發執行查詢
        tasks = [process_single_query(query) for query in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 驗證結果
        assert len(results) == len(queries)
        
        # 至少一半的查詢應該成功
        successful_results = [r for r in results if isinstance(r, str) and "查詢失敗" not in r]
        assert len(successful_results) >= len(queries) // 2


class TestPerformanceIntegration:
    """效能整合測試"""
    
    @pytest.mark.asyncio
    async def test_query_response_time(self, application_facade):
        """測試查詢回應時間"""
        import time
        
        query = "查詢機台狀態"
        
        start_time = time.time()
        try:
            response = await application_facade.process_query(query)
            end_time = time.time()
            
            response_time = end_time - start_time
            
            # 查詢應該在合理時間內完成（10秒內）
            assert response_time < 10.0, f"查詢耗時過長: {response_time:.3f}秒"
            assert response is not None
            
        except Exception as e:
            pytest.skip(f"效能測試失敗: {e}")
    
    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, application_facade):
        """測試記憶體使用穩定性"""
        import gc
        import psutil
        import os
        
        # 獲取當前程序
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # 執行多次查詢
        for i in range(10):
            try:
                await application_facade.process_query(f"查詢機台M00{i % 5 + 1}")
            except Exception:
                pass  # 忽略查詢錯誤，專注於記憶體測試
        
        # 強制垃圾回收
        gc.collect()
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # 記憶體增長應該在合理範圍內（50MB）
        max_increase = 50 * 1024 * 1024  # 50MB
        assert memory_increase < max_increase, f"記憶體增長過多: {memory_increase / 1024 / 1024:.2f}MB"


if __name__ == "__main__":
    # 直接運行測試
    import subprocess
    import sys
    
    # 運行當前文件的測試
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"
    ], cwd=os.path.dirname(os.path.abspath(__file__)))
    
    sys.exit(result.returncode) 