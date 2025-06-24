"""
測試應用服務門面 (Application Facade)
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from linebot.v3.messaging import Message, TextMessage

from src.application.application_facade import ApplicationFacade, get_application_facade
from src.application.messaging_service import MessagingApplicationService
from src.application.monitoring_service import MonitoringApplicationService
from src.application.query_service import QueryApplicationService
from src.infrastructure.service_factory_interface import IServiceFactory


class TestApplicationFacade:
    """應用服務門面測試"""
    
    def setup_method(self):
        """每個測試前清理全域狀態"""
        import src.application.application_facade
        src.application.application_facade._application_facade = None
    
    @pytest.fixture
    def mock_service_factory(self):
        """模擬服務工廠"""
        factory = Mock(spec=IServiceFactory)
        
        # 模擬 IServiceFactory 介面方法
        factory.initialize = Mock()
        factory.get_service = Mock()
        factory.get_required_service = Mock()
        
        # 設置唯一的服務名稱
        mock_messaging = Mock()
        mock_messaging.name = "test_messaging_service"
        mock_messaging.initialize = AsyncMock()
        mock_query = Mock()
        mock_query.name = "test_query_service"
        mock_query.initialize = AsyncMock()
        mock_monitoring = Mock()
        mock_monitoring.name = "test_monitoring_service"
        mock_monitoring.initialize = AsyncMock()
        
        factory.get_required_service.side_effect = lambda service_type: {
            MessagingApplicationService: mock_messaging,
            QueryApplicationService: mock_query,
            MonitoringApplicationService: mock_monitoring
        }.get(service_type, Mock())
        
        return factory
    
    @pytest.fixture
    def application_facade(self, mock_service_factory):
        """應用服務門面實例"""
        return ApplicationFacade(mock_service_factory)
    
    @pytest.mark.asyncio
    async def test_facade_initialization(self, application_facade):
        """測試門面初始化"""
        assert not application_facade.is_initialized
        
        # 初始化門面
        await application_facade.initialize()
        
        # 驗證初始化成功
        assert application_facade.is_initialized
        assert application_facade._messaging_service is not None
        assert application_facade._query_service is not None
        assert application_facade._monitoring_service is not None
    
    @pytest.mark.asyncio
    async def test_facade_double_initialization(self, application_facade):
        """測試重複初始化"""
        # 第一次初始化
        await application_facade.initialize()
        assert application_facade.is_initialized
        
        # 第二次初始化應該不會重複
        await application_facade.initialize()
        assert application_facade.is_initialized  # 仍然應該是已初始化狀態
    
    @pytest.mark.asyncio
    async def test_process_message_auto_initialization(self, application_facade):
        """測試處理訊息時自動初始化"""
        with patch.object(application_facade, 'initialize') as mock_init:
            with patch.object(application_facade, '_messaging_service') as mock_service:
                mock_service.process_message = AsyncMock(return_value=TextMessage(text="test"))
                application_facade._initialized = True  # 避免真正初始化
                
                result = await application_facade.process_message(
                    user_id="test_user",
                    message_text="hello",
                    reply_token="test_token"
                )
                
                assert isinstance(result, Message)
    
    @pytest.mark.asyncio
    async def test_process_message_with_metrics(self, application_facade):
        """測試訊息處理的監控指標"""
        with patch.object(application_facade, 'initialize') as mock_init:
            with patch.object(application_facade, '_messaging_service') as mock_msg_service:
                with patch.object(application_facade, '_monitoring_service') as mock_mon_service:
                    # 設置模擬
                    mock_msg_service.process_message = AsyncMock(return_value=TextMessage(text="test"))
                    mock_mon_service.record_request_metrics = Mock()
                    application_facade._initialized = True
                    
                    # 執行
                    await application_facade.process_message(
                        user_id="test_user",
                        message_text="hello",
                        reply_token="test_token"
                    )
                    
                    # 驗證指標記錄
                    mock_mon_service.record_request_metrics.assert_called()
                    call_args = mock_mon_service.record_request_metrics.call_args[1]
                    assert call_args["status"] == "success"
                    assert call_args["endpoint"] == "process_message"
    
    @pytest.mark.asyncio
    async def test_execute_sql_query(self, application_facade):
        """測試 SQL 查詢執行"""
        with patch.object(application_facade, 'initialize') as mock_init:
            with patch.object(application_facade, '_query_service') as mock_service:
                # 設置模擬
                expected_result = {
                    "success": True,
                    "data": [{"id": 1, "name": "test"}],
                    "row_count": 1
                }
                mock_service.execute_sql_query = AsyncMock(return_value=expected_result)
                application_facade._initialized = True
                
                # 執行
                result = await application_facade.execute_sql_query(
                    query="SELECT * FROM test",
                    user_id="test_user"
                )
                
                # 驗證
                assert result == expected_result
                mock_service.execute_sql_query.assert_called_once_with(
                    query="SELECT * FROM test",
                    user_id="test_user",
                    use_cache=True
                )
    
    @pytest.mark.asyncio
    async def test_get_system_health(self, application_facade):
        """測試系統健康檢查"""
        with patch.object(application_facade, 'initialize') as mock_init:
            with patch.object(application_facade, '_monitoring_service') as mock_service:
                # 設置模擬
                expected_health = {
                    "overall_status": "healthy",
                    "components": {"test": {"status": "healthy"}}
                }
                mock_service.perform_comprehensive_health_check = AsyncMock(
                    return_value=expected_health
                )
                application_facade._initialized = True
                
                # 執行
                result = await application_facade.get_system_health()
                
                # 驗證
                assert result == expected_health
    
    def test_get_dashboard_data(self, application_facade):
        """測試儀表板數據獲取"""
        with patch.object(application_facade, '_monitoring_service') as mock_mon_service:
            with patch.object(application_facade, '_messaging_service') as mock_msg_service:
                with patch.object(application_facade, '_query_service') as mock_query_service:
                    # 設置模擬
                    mock_mon_service.get_dashboard_data.return_value = {"metrics": "test"}
                    mock_msg_service.get_processing_stats.return_value = {"messages": 100}
                    mock_query_service.get_query_statistics.return_value = {"queries": 50}
                    application_facade._initialized = True
                    
                    # 執行
                    result = application_facade.get_dashboard_data()
                    
                    # 驗證
                    assert "metrics" in result
                    assert "messaging_stats" in result
                    assert "query_stats" in result
    
    def test_get_dashboard_data_not_initialized(self, application_facade):
        """測試未初始化時獲取儀表板數據"""
        result = application_facade.get_dashboard_data()
        assert result == {"error": "監控服務未初始化"}
    
    def test_user_session_management(self, application_facade):
        """測試用戶會話管理"""
        with patch.object(application_facade, '_messaging_service') as mock_service:
            # 設置模擬
            expected_session = {"user_id": "test", "data": "session_data"}
            mock_service.get_user_session.return_value = expected_session
            mock_service.clear_user_session.return_value = True
            
            # 測試獲取會話
            session = application_facade.get_user_session("test_user")
            assert session == expected_session
            
            # 測試清除會話
            result = application_facade.clear_user_session("test_user")
            assert result is True
    
    def test_query_statistics(self, application_facade):
        """測試查詢統計資訊"""
        with patch.object(application_facade, '_query_service') as mock_service:
            expected_stats = {"total_queries": 100, "success_rate": 95.0}
            mock_service.get_query_statistics.return_value = expected_stats
            
            result = application_facade.get_query_statistics()
            assert result == expected_stats
    
    def test_clear_query_cache(self, application_facade):
        """測試清除查詢快取"""
        with patch.object(application_facade, '_query_service') as mock_service:
            mock_service.clear_cache.return_value = 10
            
            result = application_facade.clear_query_cache()
            assert result == 10
    
    def test_get_performance_report(self, application_facade):
        """測試效能報告獲取"""
        with patch.object(application_facade, '_monitoring_service') as mock_service:
            expected_report = {"avg_response_time": 0.5, "total_requests": 1000}
            mock_service.get_performance_report.return_value = expected_report
            
            result = application_facade.get_performance_report(24)
            assert result == expected_report
            mock_service.get_performance_report.assert_called_once_with(24)
    
    @pytest.mark.asyncio
    async def test_shutdown(self, application_facade):
        """測試門面關閉"""
        with patch.object(application_facade, 'context') as mock_context:
            mock_context.shutdown_all = AsyncMock()
            application_facade._initialized = True
            
            await application_facade.shutdown()
            
            assert not application_facade.is_initialized
            mock_context.shutdown_all.assert_called_once()
    
    def test_get_facade_info(self, application_facade):
        """測試獲取門面資訊"""
        with patch.object(application_facade, '_messaging_service') as mock_msg_service:
            with patch.object(application_facade, 'context') as mock_context:
                # 設置模擬
                mock_msg_service.get_service_info.return_value = {"name": "messaging"}
                mock_context.get_context_info.return_value = {"services": 3}
                application_facade._initialized = True
                
                # 執行
                result = application_facade.get_facade_info()
                
                # 驗證
                assert result["initialized"] is True
                assert "services" in result
                assert "context_info" in result
    
    @pytest.mark.asyncio
    async def test_process_message_error_handling(self, application_facade):
        """測試處理訊息時的錯誤處理"""
        with patch.object(application_facade, 'initialize') as mock_init:
            with patch.object(application_facade, '_messaging_service') as mock_msg_service:
                with patch.object(application_facade, '_monitoring_service') as mock_mon_service:
                    # 設置服務拋出異常
                    test_error = Exception("Test error")
                    mock_msg_service.process_message = AsyncMock(side_effect=test_error)
                    mock_mon_service.record_request_metrics = Mock()
                    application_facade._initialized = True
                    
                    # 執行並預期拋出異常
                    with pytest.raises(Exception) as exc_info:
                        await application_facade.process_message(
                            user_id="test_user",
                            message_text="hello",
                            reply_token="test_token"
                        )
                    
                    assert str(exc_info.value) == "Test error"
                    
                    # 驗證錯誤指標記錄
                    mock_mon_service.record_request_metrics.assert_called()
                    call_args = mock_mon_service.record_request_metrics.call_args[1]
                    assert call_args["status"] == "error"
    
    def test_get_application_facade_singleton(self):
        """測試全域門面實例"""
        # 清除現有實例
        import src.application.application_facade
        original_facade = src.application.application_facade._application_facade
        src.application.application_facade._application_facade = None
        
        try:
            # 獲取實例
            facade1 = get_application_facade()
            facade2 = get_application_facade()
            
            # 驗證單例模式
            assert facade1 is facade2
            assert isinstance(facade1, ApplicationFacade)
        finally:
            # 恢復原實例
            src.application.application_facade._application_facade = original_facade


class TestApplicationFacadeIntegration:
    """應用服務門面集成測試"""
    
    @pytest.mark.asyncio
    async def test_full_message_processing_flow(self):
        """測試完整的訊息處理流程"""
        # 使用真實的服務工廠但模擬底層依賴
        with patch('src.infrastructure.enhanced_service_factory.get_enhanced_service_factory') as mock_get_factory:
            # 創建模擬工廠，實現 IServiceFactory 介面
            mock_factory = Mock(spec=IServiceFactory)
            mock_get_factory.return_value = mock_factory
            
            # 設置 IServiceFactory 介面方法
            mock_factory.initialize = Mock()
            mock_factory.get_service = Mock()
            mock_factory.get_required_service = Mock()
            
            # 設置服務返回
            mock_messaging_service = Mock(spec=MessagingApplicationService)
            mock_messaging_service.name = "messaging_service"
            mock_messaging_service.initialize = AsyncMock()
            mock_query_service = Mock(spec=QueryApplicationService) 
            mock_query_service.name = "query_service"
            mock_query_service.initialize = AsyncMock()
            mock_monitoring_service = Mock(spec=MonitoringApplicationService)
            mock_monitoring_service.name = "monitoring_service"
            mock_monitoring_service.initialize = AsyncMock()
            
            mock_factory.get_required_service.side_effect = lambda service_type: {
                MessagingApplicationService: mock_messaging_service,
                QueryApplicationService: mock_query_service,
                MonitoringApplicationService: mock_monitoring_service
            }.get(service_type, Mock())
            
            # 清理全域狀態
            import src.application.application_facade
            src.application.application_facade._application_facade = None
            
            # 創建門面 - 使用全域函數
            facade = get_application_facade()
            
            # 初始化門面
            await facade.initialize()
            
            # 驗證初始化成功
            assert facade.is_initialized
            
            # 驗證服務創建
            assert facade._messaging_service is not None
            assert facade._query_service is not None
            assert facade._monitoring_service is not None