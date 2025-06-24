"""
完整系統整合測試
測試整個架構重構後的系統整合
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from linebot.v3.messaging import TextMessage

from src.infrastructure.enhanced_service_factory import EnhancedServiceFactory
from src.application.application_facade import ApplicationFacade
from src.services.message_handler_di import MessageHandlerDI
from src.domain.command_executor import CommandExecutor
from src.application.messaging_service import MessagingApplicationService
from src.application.query_service import QueryApplicationService
from src.application.monitoring_service import MonitoringApplicationService


class TestFullSystemIntegration:
    """完整系統整合測試"""
    
    @pytest.fixture
    def service_factory(self):
        """創建服務工廠"""
        factory = EnhancedServiceFactory()
        return factory
    
    @pytest.fixture
    def application_facade(self, service_factory):
        """創建應用門面"""
        # 每次創建新的工廠實例，避免服務重複註冊
        from src.infrastructure.enhanced_service_factory import EnhancedServiceFactory
        fresh_factory = EnhancedServiceFactory()
        facade = ApplicationFacade(fresh_factory)
        return facade
    
    @pytest.mark.asyncio
    async def test_complete_message_processing_pipeline(self, application_facade):
        """測試完整的訊息處理流水線"""
        # 模擬 MCP 客戶端
        with patch('src.services.unified_mcp_client.get_unified_mcp_client') as mock_mcp:
            mock_client = AsyncMock()
            mock_client.call_tool.return_value = {
                "content": [{"type": "text", "text": "機台 M001 狀態：運行中"}]
            }
            mock_mcp.return_value = mock_client
            
            # 初始化門面
            await application_facade.initialize()
            
            # 測試指令處理
            result = await application_facade.process_message(
                user_id="test_user",
                message_text="/help",
                reply_token="test_token"
            )
            
            assert isinstance(result, TextMessage)
            assert "可用指令" in result.text
    
    @pytest.mark.asyncio
    async def test_natural_language_processing_flow(self, application_facade):
        """測試自然語言處理流程"""
        with patch('src.services.unified_mcp_client.get_unified_mcp_client') as mock_mcp:
            with patch('src.services.openai_client.OpenAIClient') as mock_openai_class:
                # 設置 MCP 模擬
                mock_client = AsyncMock()
                mock_client.call_tool.return_value = {
                    "content": [{"type": "text", "text": "查詢結果"}]
                }
                mock_mcp.return_value = mock_client
                
                # 設置 OpenAI 模擬
                mock_openai = Mock()
                mock_openai.generate_sql_from_natural_language.return_value = {
                    "sql": "SELECT * FROM machines WHERE id = 'M001'",
                    "explanation": "查詢機台M001的資訊"
                }
                mock_openai_class.return_value = mock_openai
                
                # 初始化門面
                await application_facade.initialize()
                
                # 測試自然語言處理
                result = await application_facade.process_message(
                    user_id="test_user",
                    message_text="M001機台狀況如何？",
                    reply_token="test_token"
                )
                
                assert isinstance(result, TextMessage)
    
    @pytest.mark.asyncio
    async def test_sql_query_execution_flow(self, application_facade):
        """測試 SQL 查詢執行流程"""
        with patch('src.services.unified_mcp_client.get_unified_mcp_client') as mock_mcp:
            # 設置模擬
            mock_client = AsyncMock()
            mock_client.call_tool.return_value = {
                "content": [
                    {"type": "text", "text": "機台ID,狀態,溫度\nM001,運行,85°C\nM002,停機,25°C"}
                ]
            }
            mock_mcp.return_value = mock_client
            
            # 初始化門面
            await application_facade.initialize()
            
            # 執行 SQL 查詢
            result = await application_facade.execute_sql_query(
                query="SELECT * FROM machines",
                user_id="test_user"
            )
            
            assert result["success"] is True
            assert "data" in result
            assert result["row_count"] >= 0
    
    @pytest.mark.asyncio
    async def test_monitoring_and_health_checks(self, application_facade):
        """測試監控和健康檢查"""
        # 初始化門面
        await application_facade.initialize()
        
        # 執行健康檢查
        health_result = await application_facade.get_system_health()
        
        assert "overall_status" in health_result
        assert health_result["overall_status"] in ["healthy", "degraded", "unhealthy"]
        assert "components" in health_result
        assert "timestamp" in health_result
        
        # 獲取儀表板數據
        dashboard_data = application_facade.get_dashboard_data()
        
        assert "timestamp" in dashboard_data
        assert "system_uptime" in dashboard_data
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, application_facade):
        """測試錯誤處理和恢復"""
        with patch('src.services.unified_mcp_client.get_unified_mcp_client') as mock_mcp:
            # 設置 MCP 客戶端拋出異常
            mock_client = AsyncMock()
            mock_client.call_tool.side_effect = Exception("MCP connection failed")
            mock_mcp.return_value = mock_client
            
            # 初始化門面
            await application_facade.initialize()
            
            # 測試錯誤處理
            with pytest.raises(Exception):
                await application_facade.execute_sql_query(
                    query="SELECT * FROM machines",
                    user_id="test_user"
                )
            
            # 系統應該仍然可以回應其他請求
            health_result = await application_facade.get_system_health()
            assert health_result is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, application_facade):
        """測試並發請求處理"""
        with patch('src.services.unified_mcp_client.get_unified_mcp_client') as mock_mcp:
            # 設置模擬
            mock_client = AsyncMock()
            mock_client.call_tool.return_value = {
                "content": [{"type": "text", "text": "成功"}]
            }
            mock_mcp.return_value = mock_client
            
            # 初始化門面
            await application_facade.initialize()
            
            # 創建多個並發請求
            tasks = []
            for i in range(5):
                task = application_facade.process_message(
                    user_id=f"user_{i}",
                    message_text="/status",
                    reply_token=f"token_{i}"
                )
                tasks.append(task)
            
            # 等待所有任務完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 驗證所有請求都成功處理
            for result in results:
                assert not isinstance(result, Exception)
                assert isinstance(result, TextMessage)
    
    @pytest.mark.asyncio
    async def test_service_lifecycle_management(self, service_factory):
        """測試服務生命週期管理"""
        # 初始化工廠
        service_factory.initialize()
        
        # 獲取各種服務
        messaging_service = service_factory.get_service(MessagingApplicationService)
        query_service = service_factory.get_service(QueryApplicationService)
        monitoring_service = service_factory.get_service(MonitoringApplicationService)
        
        # 驗證服務已初始化
        assert messaging_service is not None
        assert query_service is not None
        assert monitoring_service is not None
        
        # 驗證單例行為
        messaging_service2 = service_factory.get_service(MessagingApplicationService)
        assert messaging_service is messaging_service2
    
    @pytest.mark.asyncio
    async def test_dependency_injection_chain(self, service_factory):
        """測試依賴注入鏈"""
        service_factory.initialize()
        
        # 獲取訊息處理器
        handler = service_factory.create_message_handler()
        
        # 驗證所有依賴都被正確注入
        assert handler.ai_model_service is not None
        assert handler.nl_service is not None
        assert handler.db_service is not None
        assert handler.formatter is not None
        # flex_builder 已移除，不再測試
        
        # 驗證依賴鏈完整性
        assert handler.nl_service.ai_model_service is not None
        assert handler.nl_service.ai_model_service is handler.ai_model_service  # 單例
    
    def test_service_registry_integration(self, service_factory):
        """測試服務註冊表整合"""
        service_factory.initialize()
        
        # 獲取註冊表資訊
        info = service_factory.get_registry_info()
        
        assert info["total_services"] > 0
        assert len(info["service_types"]) > 0
        assert info["by_scope"]["singleton"] > 0
        assert len(info["by_tag"]) > 0
        
        # 驗證標籤分類
        assert info["by_tag"]["core"] > 0
        assert info["by_tag"]["application"] > 0


class TestPerformanceIntegration:
    """效能整合測試"""
    
    @pytest.fixture
    def application_facade(self):
        """創建應用門面"""
        # 每次創建新的工廠實例
        factory = EnhancedServiceFactory()
        facade = ApplicationFacade(factory)
        return facade
    
    @pytest.mark.asyncio
    async def test_message_processing_performance(self, application_facade):
        """測試訊息處理效能"""
        import time
        
        with patch('src.services.unified_mcp_client.get_unified_mcp_client') as mock_mcp:
            # 設置快速回應的模擬
            mock_client = AsyncMock()
            mock_client.call_tool.return_value = {
                "content": [{"type": "text", "text": "快速回應"}]
            }
            mock_mcp.return_value = mock_client
            
            # 初始化門面
            await application_facade.initialize()
            
            # 測量處理時間
            start_time = time.time()
            
            result = await application_facade.process_message(
                user_id="perf_test_user",
                message_text="/status",
                reply_token="perf_token"
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # 驗證回應時間在合理範圍內（< 1秒）
            assert processing_time < 1.0
            assert isinstance(result, TextMessage)
    
    @pytest.mark.asyncio
    async def test_sql_query_performance(self, application_facade):
        """測試 SQL 查詢效能"""
        import time
        
        with patch('src.services.unified_mcp_client.get_unified_mcp_client') as mock_mcp:
            # 設置模擬
            mock_client = AsyncMock()
            mock_client.call_tool.return_value = {
                "content": [{"type": "text", "text": "查詢結果"}]
            }
            mock_mcp.return_value = mock_client
            
            # 初始化門面
            await application_facade.initialize()
            
            # 測量查詢時間
            start_time = time.time()
            
            result = await application_facade.execute_sql_query(
                query="SELECT * FROM machines LIMIT 100",
                user_id="perf_test_user"
            )
            
            end_time = time.time()
            query_time = end_time - start_time
            
            # 驗證查詢時間在合理範圍內（< 0.5秒）
            assert query_time < 0.5
            assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_concurrent_performance(self, application_facade):
        """測試並發效能"""
        import time
        
        with patch('src.services.unified_mcp_client.get_unified_mcp_client') as mock_mcp:
            # 設置模擬
            mock_client = AsyncMock()
            mock_client.call_tool.return_value = {
                "content": [{"type": "text", "text": "並發回應"}]
            }
            mock_mcp.return_value = mock_client
            
            # 初始化門面
            await application_facade.initialize()
            
            # 測量並發處理時間
            start_time = time.time()
            
            # 創建10個並發請求
            tasks = []
            for i in range(10):
                task = application_facade.process_message(
                    user_id=f"concurrent_user_{i}",
                    message_text="/help",
                    reply_token=f"concurrent_token_{i}"
                )
                tasks.append(task)
            
            # 等待所有任務完成
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # 驗證並發處理效能（10個請求在2秒內完成）
            assert total_time < 2.0
            assert len(results) == 10
            
            # 驗證所有請求都成功
            for result in results:
                assert isinstance(result, TextMessage)
    
    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, application_facade):
        """測試記憶體使用穩定性"""
        import gc
        import psutil
        import os
        
        with patch('src.services.unified_mcp_client.get_unified_mcp_client') as mock_mcp:
            # 設置模擬
            mock_client = AsyncMock()
            mock_client.call_tool.return_value = {
                "content": [{"type": "text", "text": "記憶體測試"}]
            }
            mock_mcp.return_value = mock_client
            
            # 初始化門面
            await application_facade.initialize()
            
            # 獲取初始記憶體使用量
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # 執行多次請求
            for i in range(50):
                await application_facade.process_message(
                    user_id=f"memory_test_user_{i}",
                    message_text=f"/status_{i}",
                    reply_token=f"memory_token_{i}"
                )
                
                # 每10次清理一次垃圾
                if i % 10 == 0:
                    gc.collect()
            
            # 獲取最終記憶體使用量
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            # 驗證記憶體增長在合理範圍內（< 50MB）
            assert memory_increase < 50
    
    def test_service_creation_performance(self):
        """測試服務創建效能"""
        import time
        
        # 測量服務工廠初始化時間
        start_time = time.time()
        
        factory = EnhancedServiceFactory()
        factory.initialize()
        
        end_time = time.time()
        init_time = end_time - start_time
        
        # 驗證初始化時間在合理範圍內（< 2秒）
        assert init_time < 2.0
        
        # 測量服務獲取時間
        start_time = time.time()
        
        # 獲取各種服務
        for _ in range(10):
            factory.get_service(MessagingApplicationService)
            factory.get_service(QueryApplicationService)
            factory.get_service(MonitoringApplicationService)
        
        end_time = time.time()
        service_time = end_time - start_time
        
        # 驗證服務獲取時間在合理範圍內（< 0.1秒）
        assert service_time < 0.1


class TestSystemResilience:
    """系統彈性測試"""
    
    @pytest.fixture
    def application_facade(self):
        """創建應用門面"""
        # 每次創建新的工廠實例
        factory = EnhancedServiceFactory()
        facade = ApplicationFacade(factory)
        return facade
    
    @pytest.mark.asyncio
    async def test_mcp_service_failure_resilience(self, application_facade):
        """測試 MCP 服務故障時的彈性"""
        with patch('src.services.unified_mcp_client.get_unified_mcp_client') as mock_mcp:
            # 初始設置正常工作
            mock_client = AsyncMock()
            mock_client.call_tool.return_value = {
                "content": [{"type": "text", "text": "正常回應"}]
            }
            mock_mcp.return_value = mock_client
            
            # 初始化門面
            await application_facade.initialize()
            
            # 驗證正常操作
            result = await application_facade.process_message(
                user_id="resilience_user",
                message_text="/help",
                reply_token="resilience_token"
            )
            assert isinstance(result, TextMessage)
            
            # 模擬 MCP 服務故障
            mock_client.call_tool.side_effect = Exception("MCP service down")
            
            # 系統應該仍能回應（可能是錯誤訊息，但不應崩潰）
            result = await application_facade.process_message(
                user_id="resilience_user",
                message_text="/status",
                reply_token="resilience_token2"
            )
            assert isinstance(result, TextMessage)
    
    @pytest.mark.asyncio
    async def test_partial_service_failure_isolation(self, application_facade):
        """測試部分服務故障的隔離"""
        # 初始化門面
        await application_facade.initialize()
        
        # 即使某些服務有問題，健康檢查應該仍能運行
        health_result = await application_facade.get_system_health()
        assert health_result is not None
        assert "overall_status" in health_result
        
        # 監控服務應該仍能提供基本數據
        dashboard_data = application_facade.get_dashboard_data()
        assert dashboard_data is not None
    
    @pytest.mark.asyncio
    async def test_high_load_stability(self, application_facade):
        """測試高負載下的穩定性"""
        with patch('src.services.unified_mcp_client.get_unified_mcp_client') as mock_mcp:
            # 設置模擬
            mock_client = AsyncMock()
            mock_client.call_tool.return_value = {
                "content": [{"type": "text", "text": "高負載回應"}]
            }
            mock_mcp.return_value = mock_client
            
            # 初始化門面
            await application_facade.initialize()
            
            # 創建大量並發請求
            tasks = []
            for i in range(20):
                task = application_facade.process_message(
                    user_id=f"load_test_user_{i}",
                    message_text=f"/status_{i}",
                    reply_token=f"load_token_{i}"
                )
                tasks.append(task)
            
            # 所有請求都應該成功完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 驗證沒有異常
            exceptions = [r for r in results if isinstance(r, Exception)]
            assert len(exceptions) == 0
            
            # 驗證所有回應都是有效的
            valid_responses = [r for r in results if isinstance(r, TextMessage)]
            assert len(valid_responses) == 20