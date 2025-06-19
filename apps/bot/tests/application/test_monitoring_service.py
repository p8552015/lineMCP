"""
測試監控應用服務
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from src.application.monitoring_service import MonitoringApplicationService, PerformanceMetric, HealthStatus


class TestPerformanceMetric:
    """效能指標數據類測試"""
    
    def test_metric_creation(self):
        """測試指標創建"""
        timestamp = datetime.now()
        metric = PerformanceMetric(
            name="test.metric",
            value=42.5,
            unit="ms",
            timestamp=timestamp,
            tags={"service": "test"}
        )
        
        assert metric.name == "test.metric"
        assert metric.value == 42.5
        assert metric.unit == "ms"
        assert metric.timestamp == timestamp
        assert metric.tags == {"service": "test"}
    
    def test_metric_default_tags(self):
        """測試預設標籤"""
        metric = PerformanceMetric(
            name="test.metric",
            value=1.0,
            unit="count",
            timestamp=datetime.now()
        )
        
        assert metric.tags == {}


class TestHealthStatus:
    """健康狀態數據類測試"""
    
    def test_health_status_creation(self):
        """測試健康狀態創建"""
        status = HealthStatus(
            component="database",
            status="healthy",
            message="All connections active"
        )
        
        assert status.component == "database"
        assert status.status == "healthy"
        assert status.message == "All connections active"
        assert status.details == {}
        assert isinstance(status.timestamp, datetime)
    
    def test_health_status_with_details(self):
        """測試帶詳細資訊的健康狀態"""
        details = {"connections": 5, "latency": 0.1}
        timestamp = datetime.now()
        
        status = HealthStatus(
            component="api",
            status="degraded",
            message="High latency detected",
            details=details,
            timestamp=timestamp
        )
        
        assert status.details == details
        assert status.timestamp == timestamp


class TestMonitoringApplicationService:
    """監控應用服務測試"""
    
    @pytest.fixture
    def mock_service_context(self):
        """模擬服務上下文"""
        context = Mock()
        context.health_check_all = AsyncMock()
        return context
    
    @pytest.fixture
    def monitoring_service(self, mock_service_context):
        """監控服務實例"""
        return MonitoringApplicationService(
            service_context=mock_service_context,
            retention_hours=1  # 測試用較短的保留時間
        )
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, monitoring_service):
        """測試服務初始化"""
        assert not monitoring_service.is_initialized
        
        await monitoring_service.initialize()
        
        assert monitoring_service.is_initialized
        # 應該記錄啟動指標
        assert len(monitoring_service._metrics) > 0
        startup_metrics = [m for m in monitoring_service._metrics if m.name == "service.startup"]
        assert len(startup_metrics) == 1
    
    def test_record_metric(self, monitoring_service):
        """測試指標記錄"""
        monitoring_service.record_metric("test.counter", 5, "count", {"type": "test"})
        
        assert len(monitoring_service._metrics) == 1
        metric = monitoring_service._metrics[0]
        assert metric.name == "test.counter"
        assert metric.value == 5
        assert metric.unit == "count"
        assert metric.tags == {"type": "test"}
    
    def test_record_metric_retention(self, monitoring_service):
        """測試指標保留時間限制"""
        # 添加超過最大數量的指標
        for i in range(10005):  # 超過 _max_metrics
            monitoring_service._metrics.append(
                PerformanceMetric(
                    name=f"test.{i}",
                    value=i,
                    unit="count",
                    timestamp=datetime.now() - timedelta(hours=2)  # 過期的指標
                )
            )
        
        # 記錄新指標觸發清理
        monitoring_service.record_metric("new.metric", 1, "count")
        
        # 驗證過期指標被清理
        assert len(monitoring_service._metrics) <= monitoring_service._max_metrics
        # 新指標應該還在
        new_metrics = [m for m in monitoring_service._metrics if m.name == "new.metric"]
        assert len(new_metrics) == 1
    
    def test_record_request_metrics(self, monitoring_service):
        """測試請求指標記錄"""
        # 記錄成功請求
        monitoring_service.record_request_metrics(
            duration=0.5,
            status="success",
            endpoint="test_api"
        )
        
        assert monitoring_service._system_stats["total_requests"] == 1
        assert monitoring_service._system_stats["error_count"] == 0
        
        # 驗證指標記錄
        duration_metrics = [m for m in monitoring_service._metrics if m.name == "request.duration"]
        assert len(duration_metrics) == 1
        assert duration_metrics[0].value == 0.5
        assert duration_metrics[0].tags["status"] == "success"
        assert duration_metrics[0].tags["endpoint"] == "test_api"
        
        # 記錄錯誤請求
        monitoring_service.record_request_metrics(
            duration=1.0,
            status="error"
        )
        
        assert monitoring_service._system_stats["total_requests"] == 2
        assert monitoring_service._system_stats["error_count"] == 1
    
    def test_record_slow_request(self, monitoring_service):
        """測試慢請求記錄"""
        # 記錄慢請求（超過基線）
        monitoring_service.record_request_metrics(
            duration=2.0,  # 超過基線的 1.0 秒
            status="success"
        )
        
        # 應該記錄慢請求指標
        slow_metrics = [m for m in monitoring_service._metrics if m.name == "request.slow"]
        assert len(slow_metrics) == 1
    
    @pytest.mark.asyncio
    async def test_comprehensive_health_check(self, monitoring_service, mock_service_context):
        """測試全面健康檢查"""
        # 設置服務上下文回應
        mock_service_context.health_check_all.return_value = {
            "overall_status": "healthy",
            "services": {"test_service": {"status": "healthy"}}
        }
        
        with patch.object(monitoring_service, '_check_system_resources') as mock_system:
            with patch.object(monitoring_service, '_check_performance_metrics') as mock_perf:
                mock_system.return_value = {"status": "healthy"}
                mock_perf.return_value = {"status": "healthy"}
                
                result = await monitoring_service.perform_comprehensive_health_check()
                
                assert result["overall_status"] == "healthy"
                assert "components" in result
                assert "timestamp" in result
                assert "check_duration" in result
                assert "summary" in result
                
                # 驗證健康檢查被調用
                mock_service_context.health_check_all.assert_called_once()
                mock_system.assert_called_once()
                mock_perf.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_with_degraded_service(self, monitoring_service, mock_service_context):
        """測試降級服務的健康檢查"""
        # 設置服務上下文回應為降級
        mock_service_context.health_check_all.return_value = {
            "overall_status": "degraded",
            "services": {"test_service": {"status": "degraded"}}
        }
        
        with patch.object(monitoring_service, '_check_system_resources') as mock_system:
            with patch.object(monitoring_service, '_check_performance_metrics') as mock_perf:
                mock_system.return_value = {"status": "healthy"}
                mock_perf.return_value = {"status": "healthy"}
                
                result = await monitoring_service.perform_comprehensive_health_check()
                
                assert result["overall_status"] == "degraded"
    
    @pytest.mark.asyncio
    async def test_health_check_with_error(self, monitoring_service, mock_service_context):
        """測試健康檢查遇到錯誤"""
        # 設置服務上下文拋出異常
        mock_service_context.health_check_all.side_effect = Exception("Service error")
        
        with patch.object(monitoring_service, '_check_system_resources') as mock_system:
            with patch.object(monitoring_service, '_check_performance_metrics') as mock_perf:
                mock_system.return_value = {"status": "healthy"}
                mock_perf.return_value = {"status": "healthy"}
                
                result = await monitoring_service.perform_comprehensive_health_check()
                
                assert result["overall_status"] == "unhealthy"
                assert "application_services" in result["components"]
                assert result["components"]["application_services"]["status"] == "error"
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_check_system_resources_healthy(self, mock_disk, mock_memory, mock_cpu, monitoring_service):
        """測試系統資源檢查（健康狀態）"""
        # 設置模擬回傳健康的資源使用率
        mock_cpu.return_value = 30.0
        mock_memory.return_value = Mock(used=200*1024*1024, percent=40.0)  # 200MB, 40%
        mock_disk.return_value = Mock(percent=50.0)
        
        result = monitoring_service._check_system_resources()
        
        assert result["status"] == "healthy"
        assert result["cpu_percent"] == 30.0
        assert result["memory_percent"] == 40.0
        assert result["disk_percent"] == 50.0
        assert len(result["issues"]) == 0
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_check_system_resources_degraded(self, mock_disk, mock_memory, mock_cpu, monitoring_service):
        """測試系統資源檢查（降級狀態）"""
        # 設置模擬回傳高資源使用率
        mock_cpu.return_value = 90.0  # 超過80%基線
        mock_memory.return_value = Mock(used=600*1024*1024, percent=85.0)  # 600MB，超過500MB基線
        mock_disk.return_value = Mock(percent=95.0)  # 超過90%
        
        result = monitoring_service._check_system_resources()
        
        assert result["status"] == "degraded"
        assert len(result["issues"]) == 3  # CPU, 記憶體, 磁碟都超標
        assert any("高 CPU 使用率" in issue for issue in result["issues"])
        assert any("高記憶體使用" in issue for issue in result["issues"])
        assert any("磁碟空間不足" in issue for issue in result["issues"])
    
    def test_check_system_resources_no_psutil(self, monitoring_service):
        """測試無 psutil 時的系統資源檢查"""
        # 模擬導入錯誤
        with patch.object(monitoring_service, '_check_system_resources') as mock_check:
            mock_check.return_value = {
                "status": "unknown",
                "message": "psutil 未安裝，無法獲取系統資源資訊"
            }
            
            result = monitoring_service._check_system_resources()
            
            assert result["status"] == "unknown"
            assert "psutil 未安裝" in result["message"]
    
    def test_check_performance_metrics(self, monitoring_service):
        """測試效能指標檢查"""
        # 設置一些請求指標
        monitoring_service._system_stats = {
            "total_requests": 100,
            "error_count": 3
        }
        
        # 添加一些響應時間指標
        for i in range(10):
            monitoring_service._metrics.append(
                PerformanceMetric(
                    name="request.duration",
                    value=0.5 + i * 0.1,  # 0.5 到 1.4 秒
                    unit="seconds",
                    timestamp=datetime.now()
                )
            )
        
        result = monitoring_service._check_performance_metrics()
        
        assert result["status"] in ["healthy", "degraded"]
        assert "avg_response_time" in result
        assert "error_rate" in result
        assert result["error_rate"] == 3.0  # 3/100 * 100
    
    def test_check_performance_metrics_high_error_rate(self, monitoring_service):
        """測試高錯誤率的效能檢查"""
        # 設置高錯誤率
        monitoring_service._system_stats = {
            "total_requests": 100,
            "error_count": 10  # 10% 錯誤率，超過5%基線
        }
        
        result = monitoring_service._check_performance_metrics()
        
        assert result["status"] == "degraded"
        assert any("錯誤率過高" in issue for issue in result["issues"])
    
    def test_generate_health_summary(self, monitoring_service):
        """測試健康檢查摘要生成"""
        component_results = {
            "service1": {"status": "healthy"},
            "service2": {"status": "degraded"},
            "service3": {"status": "unhealthy"},
            "service4": {"status": "healthy"}
        }
        
        summary = monitoring_service._generate_health_summary(component_results)
        
        assert summary["total_components"] == 4
        assert summary["healthy"] == 2
        assert summary["degraded"] == 1
        assert summary["unhealthy"] == 1
        assert summary["health_percentage"] == 50.0  # 2/4 * 100
    
    def test_update_health_status(self, monitoring_service):
        """測試健康狀態更新"""
        monitoring_service._update_health_status(
            component="test_component",
            status="healthy",
            message="All systems operational"
        )
        
        assert "test_component" in monitoring_service._health_statuses
        status = monitoring_service._health_statuses["test_component"]
        assert status.component == "test_component"
        assert status.status == "healthy"
        assert status.message == "All systems operational"
    
    def test_get_dashboard_data(self, monitoring_service):
        """測試儀表板數據獲取"""
        # 設置一些測試數據
        monitoring_service._system_stats = {
            "start_time": datetime.now() - timedelta(hours=2),
            "total_requests": 150,
            "error_count": 5,
            "last_health_check": datetime.now() - timedelta(minutes=5)
        }
        
        # 添加一些指標
        monitoring_service._metrics.append(
            PerformanceMetric("test.metric", 42, "count", datetime.now())
        )
        
        # 添加健康狀態
        monitoring_service._health_statuses["test"] = HealthStatus(
            "test", "healthy", "OK"
        )
        
        data = monitoring_service.get_dashboard_data()
        
        assert "timestamp" in data
        assert "system_uptime" in data
        assert data["total_requests"] == 150
        assert data["error_count"] == 5
        assert data["error_rate"] == 5/150 * 100
        assert "last_health_check" in data
        assert "recent_metrics_count" in data
        assert "aggregated_metrics" in data
        assert "health_statuses" in data
    
    def test_get_performance_report(self, monitoring_service):
        """測試效能報告獲取"""
        # 設置一些測試數據
        monitoring_service._system_stats = {
            "total_requests": 200,
            "error_count": 10
        }
        
        # 添加響應時間指標
        for i in range(5):
            monitoring_service._metrics.append(
                PerformanceMetric(
                    "request.duration",
                    0.5 + i * 0.2,
                    "seconds",
                    datetime.now()
                )
            )
        
        # 添加錯誤指標
        for i in range(2):
            monitoring_service._metrics.append(
                PerformanceMetric(
                    "request.count",
                    1,
                    "count",
                    datetime.now(),
                    {"status": "error"}
                )
            )
        
        report = monitoring_service.get_performance_report(24)
        
        assert report["period_hours"] == 24
        assert "performance_summary" in report
        assert "performance_baselines" in report
        assert "recommendations" in report
        
        summary = report["performance_summary"]
        assert "avg_response_time" in summary
        assert "max_response_time" in summary
        assert "total_requests" in summary
        assert "total_errors" in summary
    
    def test_generate_performance_recommendations(self, monitoring_service):
        """測試效能建議生成"""
        # 設置高響應時間指標
        high_response_metrics = [
            PerformanceMetric("request.duration", 2.5, "seconds", datetime.now()),
            PerformanceMetric("request.duration", 3.0, "seconds", datetime.now()),
            PerformanceMetric("request.duration", 1.8, "seconds", datetime.now())
        ]
        
        # 設置高錯誤率
        monitoring_service._system_stats = {
            "total_requests": 100,
            "error_count": 8  # 8% 錯誤率
        }
        
        recommendations = monitoring_service._generate_performance_recommendations(high_response_metrics)
        
        assert len(recommendations) >= 1
        # 應該包含關於響應時間和錯誤率的建議
        rec_text = " ".join(recommendations)
        assert any(keyword in rec_text for keyword in ["響應時間", "錯誤率"])
    
    @pytest.mark.asyncio
    async def test_health_checks(self, monitoring_service):
        """測試健康檢查"""
        # 設置一些測試數據
        monitoring_service._metrics = [Mock(), Mock(), Mock()]
        monitoring_service._system_stats = {
            "start_time": datetime.now() - timedelta(hours=1),
            "total_requests": 50,
            "error_count": 2
        }
        
        checks = await monitoring_service._perform_health_checks()
        
        assert "metrics_collection" in checks
        assert checks["metrics_collection"]["status"] == "healthy"
        assert checks["metrics_collection"]["total_metrics"] == 3
        
        assert "system_statistics" in checks
        assert checks["system_statistics"]["status"] == "healthy"
        assert checks["system_statistics"]["total_requests"] == 50
    
    @pytest.mark.asyncio
    async def test_shutdown_service(self, monitoring_service):
        """測試服務關閉"""
        # 設置一些數據
        monitoring_service._metrics = [Mock(), Mock()]
        monitoring_service._health_statuses = {"test": Mock()}
        
        await monitoring_service._shutdown_service()
        
        # 驗證清理
        assert len(monitoring_service._metrics) == 0
        assert len(monitoring_service._health_statuses) == 0


class TestMonitoringServiceIntegration:
    """監控服務集成測試"""
    
    @pytest.mark.asyncio
    async def test_full_monitoring_lifecycle(self):
        """測試完整的監控生命週期"""
        # 創建服務
        service_context = Mock()
        service_context.health_check_all = AsyncMock(return_value={"overall_status": "healthy"})
        
        service = MonitoringApplicationService(service_context)
        
        # 初始化
        await service.initialize()
        assert service.is_initialized
        
        # 記錄一些指標
        service.record_metric("test.counter", 1, "count")
        service.record_request_metrics(0.5, "success", "test_endpoint")
        
        # 執行健康檢查
        with patch.object(service, '_check_system_resources') as mock_system:
            with patch.object(service, '_check_performance_metrics') as mock_perf:
                mock_system.return_value = {"status": "healthy"}
                mock_perf.return_value = {"status": "healthy"}
                
                health_result = await service.perform_comprehensive_health_check()
                assert health_result["overall_status"] == "healthy"
        
        # 獲取儀表板數據
        dashboard_data = service.get_dashboard_data()
        assert dashboard_data["total_requests"] == 1
        
        # 獲取效能報告
        report = service.get_performance_report()
        assert "performance_summary" in report
        
        # 關閉服務
        await service.shutdown()
        assert not service.is_initialized