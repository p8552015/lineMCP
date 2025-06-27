"""
健康檢查模組測試
測試系統健康監控功能
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException

from src.monitoring.health import HealthChecker, HealthStatus, liveness_check, ping


class TestHealthStatus:
    """測試健康狀態模型"""

    def test_health_status_creation(self):
        """測試健康狀態模型創建"""
        checks = {"system": {"healthy": True}}
        metrics = {"cpu": 30.0}

        status = HealthStatus(
            status="healthy",
            timestamp=datetime.now(UTC),
            version="1.0.0",
            uptime=3600.0,
            checks=checks,
            metrics=metrics,
        )

        assert status.status == "healthy"
        assert status.version == "1.0.0"
        assert status.uptime == 3600.0
        assert status.checks == checks
        assert status.metrics == metrics


class TestHealthChecker:
    """測試健康檢查器"""

    @pytest.fixture
    def mock_service_factory(self):
        """模擬服務工廠"""
        factory = Mock()
        factory.get_unified_mcp_client = Mock()
        factory.get_ai_service = Mock()
        return factory

    @pytest.fixture
    def health_checker(self, mock_service_factory):
        """健康檢查器實例"""
        with patch("time.time", return_value=1000.0):
            return HealthChecker(mock_service_factory)

    async def test_health_checker_initialization(self, health_checker):
        """測試健康檢查器初始化"""
        assert health_checker.service_factory is not None
        assert health_checker.start_time == 1000.0

    @patch("src.monitoring.health.psutil.cpu_percent")
    @patch("src.monitoring.health.psutil.virtual_memory")
    @patch("src.monitoring.health.psutil.disk_usage")
    async def test_check_system_healthy(
        self, mock_disk, mock_memory, mock_cpu, health_checker
    ):
        """測試系統檢查 - 健康狀態"""
        # 設置健康的系統狀態
        mock_cpu.return_value = 30.0
        mock_memory.return_value = Mock(percent=40.0)
        mock_disk.return_value = Mock(percent=50.0)

        with patch(
            "src.monitoring.health.psutil.getloadavg", return_value=(0.5, 0.6, 0.7)
        ):
            result = await health_checker._check_system()

        assert result["healthy"] is True
        assert result["cpu_percent"] == 30.0
        assert result["memory_percent"] == 40.0
        assert result["disk_percent"] == 50.0
        assert result["load_average"] == (0.5, 0.6, 0.7)

    @patch("src.monitoring.health.psutil.cpu_percent")
    @patch("src.monitoring.health.psutil.virtual_memory")
    @patch("src.monitoring.health.psutil.disk_usage")
    async def test_check_system_unhealthy(
        self, mock_disk, mock_memory, mock_cpu, health_checker
    ):
        """測試系統檢查 - 不健康狀態"""
        # 設置不健康的系統狀態
        mock_cpu.return_value = 90.0  # 高 CPU
        mock_memory.return_value = Mock(percent=85.0)  # 高記憶體
        mock_disk.return_value = Mock(percent=95.0)  # 高磁碟使用率

        result = await health_checker._check_system()

        assert result["healthy"] is False
        assert result["cpu_percent"] == 90.0
        assert result["memory_percent"] == 85.0
        assert result["disk_percent"] == 95.0

    @patch("src.monitoring.health.psutil.cpu_percent")
    async def test_check_system_exception(self, mock_cpu, health_checker):
        """測試系統檢查異常處理"""
        mock_cpu.side_effect = Exception("System error")

        result = await health_checker._check_system()

        assert result["healthy"] is False
        assert "error" in result
        assert result["error"] == "System error"

    async def test_check_database_healthy(self, health_checker):
        """測試資料庫檢查 - 健康狀態"""
        result = await health_checker._check_database()

        assert result["healthy"] is True
        assert "connection_count" in result
        assert "response_time_ms" in result

    async def test_check_redis_healthy(self, health_checker):
        """測試 Redis 檢查 - 健康狀態"""
        result = await health_checker._check_redis()

        assert result["healthy"] is True
        assert "memory_usage_mb" in result
        assert "connected_clients" in result
        assert "response_time_ms" in result

    async def test_check_mcp_healthy(self, health_checker):
        """測試 MCP 服務檢查 - 健康狀態"""
        with patch("time.time", side_effect=[1000.0, 1000.1]):  # 模擬 100ms 響應時間
            result = await health_checker._check_mcp()

        assert result["healthy"] is True
        assert result["connection_status"] == "connected"
        assert "response_time_ms" in result
        assert result["server_count"] == 1

    async def test_check_mcp_unhealthy(self, health_checker):
        """測試 MCP 服務檢查 - 不健康狀態"""
        health_checker.service_factory.get_unified_mcp_client.side_effect = Exception(
            "MCP connection failed"
        )

        result = await health_checker._check_mcp()

        assert result["healthy"] is False
        assert result["error"] == "MCP connection failed"

    async def test_check_ai_models_healthy(self, health_checker):
        """測試 AI 模型服務檢查 - 健康狀態"""
        with patch("time.time", side_effect=[1000.0, 1000.05]):  # 模擬 50ms 響應時間
            result = await health_checker._check_ai_models()

        assert result["healthy"] is True
        assert result["primary_model"] == "google-gemini-1.5-flash"
        assert result["backup_model"] == "openai-gpt-4o-mini"
        assert "response_time_ms" in result

    async def test_check_ai_models_unhealthy(self, health_checker):
        """測試 AI 模型服務檢查 - 不健康狀態"""
        health_checker.service_factory.get_ai_service.side_effect = Exception(
            "AI service error"
        )

        result = await health_checker._check_ai_models()

        assert result["healthy"] is False
        assert result["error"] == "AI service error"

    @patch("src.monitoring.health.httpx.AsyncClient")
    async def test_check_external_apis_healthy(self, mock_client, health_checker):
        """測試外部 API 檢查 - 健康狀態"""
        # 模擬成功的 HTTP 響應
        mock_response = Mock()
        mock_response.status_code = 401  # 預期的認證錯誤

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("time.time", side_effect=[1000.0, 1000.1, 1000.2, 1000.3]):
            result = await health_checker._check_external_apis()

        assert result["healthy"] is True
        assert "checks" in result
        assert "line_api" in result["checks"]
        assert "google_api" in result["checks"]
        assert result["checks"]["line_api"]["healthy"] is True
        assert result["checks"]["line_api"]["status_code"] == 401

    @patch("src.monitoring.health.httpx.AsyncClient")
    async def test_check_external_apis_unhealthy(self, mock_client, health_checker):
        """測試外部 API 檢查 - 不健康狀態"""
        # 模擬連接失敗
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(
            side_effect=Exception("Connection timeout")
        )
        mock_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await health_checker._check_external_apis()

        assert result["healthy"] is False
        assert "checks" in result
        assert result["checks"]["line_api"]["healthy"] is False
        assert result["checks"]["line_api"]["error"] == "Connection timeout"

    @patch("src.monitoring.health.psutil.Process")
    async def test_collect_metrics(self, mock_process_class, health_checker):
        """測試指標收集"""
        # 模擬進程信息
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.memory_info.return_value = Mock(
            rss=100 * 1024 * 1024, vms=200 * 1024 * 1024
        )
        mock_process.cpu_percent.return_value = 25.5
        mock_process.num_threads.return_value = 10
        mock_process.open_files.return_value = []
        mock_process.connections.return_value = []

        mock_process_class.return_value = mock_process

        with patch("src.monitoring.health.psutil.cpu_count", return_value=8), patch(
            "src.monitoring.health.psutil.virtual_memory"
        ) as mock_vm, patch(
            "src.monitoring.health.psutil.disk_usage"
        ) as mock_disk, patch(
            "src.monitoring.health.psutil.boot_time", return_value=900000.0
        ):

            mock_vm.return_value = Mock(total=16 * 1024 * 1024 * 1024)
            mock_disk.return_value = Mock(total=500 * 1024 * 1024 * 1024)

            result = await health_checker._collect_metrics()

        assert "process" in result
        assert "system" in result
        assert result["process"]["pid"] == 12345
        assert result["process"]["memory_rss_mb"] == 100.0
        assert result["process"]["cpu_percent"] == 25.5
        assert result["system"]["cpu_count"] == 8

    @patch("src.monitoring.health.psutil.Process")
    async def test_collect_metrics_exception(self, mock_process_class, health_checker):
        """測試指標收集異常處理"""
        mock_process_class.side_effect = Exception("Process access denied")

        result = await health_checker._collect_metrics()

        assert "error" in result
        assert result["error"] == "Process access denied"

    async def test_check_health_all_healthy(self, health_checker):
        """測試完整健康檢查 - 全部健康"""
        with patch.object(
            health_checker, "_check_system", return_value={"healthy": True}
        ), patch.object(
            health_checker, "_check_database", return_value={"healthy": True}
        ), patch.object(
            health_checker, "_check_redis", return_value={"healthy": True}
        ), patch.object(
            health_checker, "_check_mcp", return_value={"healthy": True}
        ), patch.object(
            health_checker, "_check_ai_models", return_value={"healthy": True}
        ), patch.object(
            health_checker, "_check_external_apis", return_value={"healthy": True}
        ), patch.object(
            health_checker, "_collect_metrics", return_value={"test": "metrics"}
        ), patch(
            "time.time", return_value=2000.0
        ):

            result = await health_checker.check_health()

        assert result.status == "healthy"
        assert result.version == "0.1.0"
        assert result.uptime == 1000.0  # 2000.0 - 1000.0
        assert "system" in result.checks
        assert "database" in result.checks
        assert "mcp" in result.checks
        assert result.metrics == {"test": "metrics"}

    async def test_check_health_degraded(self, health_checker):
        """測試完整健康檢查 - 降級狀態"""
        with patch.object(
            health_checker, "_check_system", return_value={"healthy": True}
        ), patch.object(
            health_checker, "_check_database", return_value={"healthy": False}
        ), patch.object(
            health_checker, "_check_redis", return_value={"healthy": True}
        ), patch.object(
            health_checker, "_check_mcp", return_value={"healthy": True}
        ), patch.object(
            health_checker, "_check_ai_models", return_value={"healthy": True}
        ), patch.object(
            health_checker, "_check_external_apis", return_value={"healthy": True}
        ), patch.object(
            health_checker, "_collect_metrics", return_value={}
        ):

            result = await health_checker.check_health()

        assert result.status == "degraded"

    async def test_check_health_unhealthy(self, health_checker):
        """測試完整健康檢查 - 不健康狀態"""
        with patch.object(
            health_checker, "_check_system", return_value={"healthy": False}
        ), patch.object(
            health_checker, "_check_database", return_value={"healthy": False}
        ), patch.object(
            health_checker, "_check_redis", return_value={"healthy": True}
        ), patch.object(
            health_checker, "_check_mcp", return_value={"healthy": True}
        ), patch.object(
            health_checker, "_check_ai_models", return_value={"healthy": True}
        ), patch.object(
            health_checker, "_check_external_apis", return_value={"healthy": True}
        ), patch.object(
            health_checker, "_collect_metrics", return_value={}
        ):

            result = await health_checker.check_health()

        assert result.status == "unhealthy"


class TestHealthEndpoints:
    """測試健康檢查端點"""

    async def test_ping_endpoint(self):
        """測試 ping 端點"""
        result = await ping()

        assert result["status"] == "ok"
        assert "timestamp" in result
        assert isinstance(result["timestamp"], datetime)

    @patch("src.monitoring.health.psutil.Process")
    async def test_liveness_check_endpoint(self, mock_process_class):
        """測試存活檢查端點"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process_class.return_value = mock_process

        result = await liveness_check()

        assert result["alive"] is True
        assert result["pid"] == 12345
        assert "timestamp" in result

    async def test_health_check_endpoint_healthy(self):
        """測試健康檢查端點 - 健康狀態"""
        from src.monitoring.health import health_check

        mock_checker = Mock()
        mock_health_status = Mock()
        mock_health_status.status = "healthy"
        mock_health_status.dict.return_value = {"status": "healthy"}
        mock_checker.check_health = AsyncMock(return_value=mock_health_status)

        result = await health_check(mock_checker)

        assert result == mock_health_status

    async def test_health_check_endpoint_degraded(self):
        """測試健康檢查端點 - 降級狀態"""
        from src.monitoring.health import health_check

        mock_checker = Mock()
        mock_health_status = Mock()
        mock_health_status.status = "degraded"
        mock_health_status.dict.return_value = {"status": "degraded"}
        mock_checker.check_health = AsyncMock(return_value=mock_health_status)

        # 降級狀態應該拋出 HTTPException，但狀態碼是 200
        with pytest.raises(HTTPException) as exc_info:
            await health_check(mock_checker)

        assert exc_info.value.status_code == 200

    async def test_health_check_endpoint_unhealthy(self):
        """測試健康檢查端點 - 不健康狀態"""
        from src.monitoring.health import health_check

        mock_checker = Mock()
        mock_health_status = Mock()
        mock_health_status.status = "unhealthy"
        mock_health_status.dict.return_value = {"status": "unhealthy"}
        mock_checker.check_health = AsyncMock(return_value=mock_health_status)

        # 不健康狀態應該拋出 503 HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await health_check(mock_checker)

        assert exc_info.value.status_code == 503

    async def test_health_check_endpoint_exception(self):
        """測試健康檢查端點異常處理"""
        from src.monitoring.health import health_check

        mock_checker = Mock()
        mock_checker.check_health = AsyncMock(side_effect=Exception("System error"))

        # 系統異常應該拋出 500 HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await health_check(mock_checker)

        assert exc_info.value.status_code == 500

    async def test_readiness_check_ready(self):
        """測試就緒檢查 - 準備就緒"""
        from src.monitoring.health import readiness_check

        mock_checker = Mock()
        mock_health_status = Mock()
        mock_health_status.checks = {
            "system": {"healthy": True},
            "mcp": {"healthy": True},
            "ai_models": {"healthy": True},
            "database": {"healthy": False},  # 非關鍵服務
        }
        mock_checker.check_health = AsyncMock(return_value=mock_health_status)

        result = await readiness_check(mock_checker)

        assert result["ready"] is True
        assert "timestamp" in result

    async def test_readiness_check_not_ready(self):
        """測試就緒檢查 - 未準備就緒"""
        from src.monitoring.health import readiness_check

        mock_checker = Mock()
        mock_health_status = Mock()
        mock_health_status.checks = {
            "system": {"healthy": True},
            "mcp": {"healthy": False},  # 關鍵服務失敗
            "ai_models": {"healthy": True},
        }
        mock_checker.check_health = AsyncMock(return_value=mock_health_status)

        # 關鍵服務失敗應該拋出 503 HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await readiness_check(mock_checker)

        assert exc_info.value.status_code == 503
        assert "failed_checks" in exc_info.value.detail
        assert "mcp" in exc_info.value.detail["failed_checks"]

    async def test_readiness_check_exception(self):
        """測試就緒檢查異常處理"""
        from src.monitoring.health import readiness_check

        mock_checker = Mock()
        mock_checker.check_health = AsyncMock(side_effect=Exception("Check failed"))

        # 檢查異常應該拋出 500 HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await readiness_check(mock_checker)

        assert exc_info.value.status_code == 500


class TestHealthCheckerIntegration:
    """健康檢查器整合測試"""

    @pytest.fixture
    def real_service_factory(self):
        """真實的服務工廠（用於整合測試）"""
        factory = Mock()
        factory.get_unified_mcp_client = Mock(return_value=Mock())
        factory.get_ai_service = Mock(return_value=Mock())
        return factory

    async def test_health_checker_full_cycle(self, real_service_factory):
        """測試健康檢查器完整週期"""
        checker = HealthChecker(real_service_factory)

        # 模擬所有檢查方法
        with patch.object(
            checker, "_check_system", return_value={"healthy": True, "cpu_percent": 30}
        ), patch.object(
            checker, "_check_database", return_value={"healthy": True}
        ), patch.object(
            checker, "_check_redis", return_value={"healthy": True}
        ), patch.object(
            checker, "_check_mcp", return_value={"healthy": True}
        ), patch.object(
            checker, "_check_ai_models", return_value={"healthy": True}
        ), patch.object(
            checker, "_check_external_apis", return_value={"healthy": True}
        ), patch.object(
            checker, "_collect_metrics", return_value={"process": {"pid": 123}}
        ):

            health_status = await checker.check_health()

            assert isinstance(health_status, HealthStatus)
            assert health_status.status == "healthy"
            assert isinstance(health_status.timestamp, datetime)
            assert health_status.uptime > 0
            assert len(health_status.checks) == 6
            assert "process" in health_status.metrics

    async def test_health_checker_partial_failure(self, real_service_factory):
        """測試健康檢查器部分失敗情況"""
        checker = HealthChecker(real_service_factory)

        # 模擬部分服務失敗
        with patch.object(
            checker, "_check_system", return_value={"healthy": True}
        ), patch.object(
            checker,
            "_check_database",
            return_value={"healthy": False, "error": "Connection failed"},
        ), patch.object(
            checker,
            "_check_redis",
            return_value={"healthy": False, "error": "Redis down"},
        ), patch.object(
            checker, "_check_mcp", return_value={"healthy": True}
        ), patch.object(
            checker, "_check_ai_models", return_value={"healthy": True}
        ), patch.object(
            checker, "_check_external_apis", return_value={"healthy": True}
        ), patch.object(
            checker, "_collect_metrics", return_value={}
        ):

            health_status = await checker.check_health()

            # 2個非關鍵服務失敗，但系統服務正常，應該是降級狀態
            assert health_status.status == "degraded"
            assert not health_status.checks["database"]["healthy"]
            assert not health_status.checks["redis"]["healthy"]
