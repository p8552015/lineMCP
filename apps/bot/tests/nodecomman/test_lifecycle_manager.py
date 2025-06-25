"""
Process Lifecycle Manager 測試套件

測試進程生命週期管理的核心功能：
- 進程註冊和管理
- 健康檢查機制
- 自動重啟策略
- 優雅關機處理
- 進程監控和指標
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# 測試導入
from src.nodecomman.implementations.process_lifecycle_manager import (
    ProcessLifecycleManager, 
    LifecycleConfig, 
    RestartPolicy,
    ManagedProcess,
    ProcessMetrics
)
from src.nodecomman.interfaces.runtime_interfaces import ProcessStatus
from src.nodecomman.interfaces.runtime_interfaces import IProcess, ProcessInfo
from src.nodecomman.interfaces.server_interfaces import MCPServerConfig


class MockProcess:
    """模擬進程類別"""
    
    def __init__(self, pid: int = 12345, is_alive: bool = True):
        self.pid = pid
        self._is_alive = is_alive
        self._return_code = None if is_alive else 1
        self.start_time = time.time()
        
    def is_running(self) -> bool:
        return self._is_alive
    
    async def wait(self) -> int:
        if self._is_alive:
            await asyncio.sleep(0.1)  # 模擬等待
            return 0
        return self._return_code
    
    async def terminate(self):
        self._is_alive = False
        self._return_code = 0
    
    async def kill(self):
        self._is_alive = False
        self._return_code = -9
        
    async def send_signal(self, signal: int):
        if signal == 15:  # SIGTERM
            await self.terminate()
        elif signal == 9:  # SIGKILL
            await self.kill()
    
    def get_info(self) -> ProcessInfo:
        return ProcessInfo(
            pid=self.pid,
            command="test_command",
            args=["--test"],
            status="running" if self._is_alive else "stopped",
            start_time=self.start_time,
            memory_usage=1024 * 1024,  # 1MB
            cpu_percent=5.0
        )


class TestProcessLifecycleManager:
    """進程生命週期管理器測試"""
    
    @pytest.fixture
    def lifecycle_manager(self):
        """創建生命週期管理器實例"""
        return ProcessLifecycleManager()
    
    @pytest.fixture
    def mock_process(self):
        """創建模擬進程"""
        return MockProcess()
    
    @pytest.fixture
    def lifecycle_config(self):
        """創建生命週期配置"""
        return LifecycleConfig(
            health_check_interval=1.0,
            restart_policy=RestartPolicy.ON_FAILURE,
            max_restart_attempts=3,
            restart_delay=0.1
        )
    
    @pytest.fixture
    def server_config(self):
        """創建服務器配置"""
        from src.nodecomman.interfaces.runtime_interfaces import RuntimeType
        return MCPServerConfig(
            name="test_server",
            runtime_type=RuntimeType.PYTHON,
            command="python",
            args=["-c", "import time; time.sleep(10)"],
            description="測試服務器"
        )
    
    @pytest.mark.asyncio
    async def test_register_process(self, lifecycle_manager, mock_process, lifecycle_config, server_config):
        """測試進程註冊"""
        process_id = "test_process"
        
        result = await lifecycle_manager.register_process(
            process_id, mock_process, lifecycle_config, server_config
        )
        
        assert result is True
        assert process_id in lifecycle_manager._managed_processes
        
        managed_process = lifecycle_manager._managed_processes[process_id]
        assert managed_process.process == mock_process
        assert managed_process.config == lifecycle_config
        assert managed_process.server_config == server_config
    
    @pytest.mark.asyncio
    async def test_start_process(self, lifecycle_manager, mock_process, lifecycle_config, server_config):
        """測試進程啟動"""
        process_id = "test_process"
        
        # 先註冊進程
        await lifecycle_manager.register_process(
            process_id, mock_process, lifecycle_config, server_config
        )
        
        # 啟動進程
        result = await lifecycle_manager.start_process(process_id)
        assert result is True
        
        # 檢查狀態
        status = await lifecycle_manager.get_process_status(process_id)
        assert status["status"] == ProcessStatus.RUNNING
        assert status["pid"] == mock_process.pid
    
    @pytest.mark.asyncio
    async def test_stop_process(self, lifecycle_manager, mock_process, lifecycle_config, server_config):
        """測試進程停止"""
        process_id = "test_process"
        
        # 註冊並啟動進程
        await lifecycle_manager.register_process(
            process_id, mock_process, lifecycle_config, server_config
        )
        await lifecycle_manager.start_process(process_id)
        
        # 停止進程
        result = await lifecycle_manager.stop_process(process_id)
        assert result is True
        
        # 檢查狀態
        status = await lifecycle_manager.get_process_status(process_id)
        assert status["status"] == ProcessStatus.STOPPED
    
    @pytest.mark.asyncio
    async def test_health_check_monitoring(self, lifecycle_manager, mock_process, lifecycle_config, server_config):
        """測試健康檢查監控"""
        process_id = "test_process"
        
        # 啟用監控
        lifecycle_config.enable_monitoring = True
        lifecycle_config.health_check_interval = 0.1  # 快速檢查
        
        await lifecycle_manager.register_process(
            process_id, mock_process, lifecycle_config, server_config
        )
        await lifecycle_manager.start_process(process_id)
        
        # 啟動監控
        await lifecycle_manager.start_monitoring()
        
        # 等待一些健康檢查週期
        await asyncio.sleep(0.3)
        
        # 獲取指標
        metrics = await lifecycle_manager.get_process_metrics(process_id)
        assert metrics is not None
        assert metrics["health_check_count"] >= 1
        
        # 停止監控
        await lifecycle_manager.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_restart_on_failure(self, lifecycle_manager, lifecycle_config, server_config):
        """測試失敗時自動重啟"""
        process_id = "test_process"
        
        # 創建會失敗的進程
        failing_process = MockProcess(is_alive=False)
        
        lifecycle_config.restart_policy = RestartPolicy.ON_FAILURE
        lifecycle_config.max_restart_attempts = 2
        lifecycle_config.restart_delay = 0.1
        
        await lifecycle_manager.register_process(
            process_id, failing_process, lifecycle_config, server_config
        )
        
        # 模擬進程創建工廠
        restart_count = 0
        
        async def mock_restart_process():
            nonlocal restart_count
            restart_count += 1
            if restart_count <= 2:
                return MockProcess(is_alive=True)  # 重啟成功
            return None
        
        with patch.object(lifecycle_manager, '_create_new_process', side_effect=mock_restart_process):
            await lifecycle_manager.start_process(process_id)
            
            # 觸發失敗檢測
            await lifecycle_manager._check_process_health(process_id)
            
            # 等待重啟完成
            await asyncio.sleep(0.5)
            
            # 檢查重啟指標
            metrics = await lifecycle_manager.get_process_metrics(process_id)
            assert metrics["restart_count"] >= 1
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, lifecycle_manager, mock_process, lifecycle_config, server_config):
        """測試優雅關機"""
        process_id = "test_process"
        
        await lifecycle_manager.register_process(
            process_id, mock_process, lifecycle_config, server_config
        )
        await lifecycle_manager.start_process(process_id)
        
        # 執行優雅關機
        result = await lifecycle_manager.shutdown_all(timeout=5.0)
        assert result is True
        
        # 檢查所有進程都已停止
        status = await lifecycle_manager.get_process_status(process_id)
        assert status["status"] == ProcessStatus.STOPPED
    
    @pytest.mark.asyncio
    async def test_process_metrics_collection(self, lifecycle_manager, mock_process, lifecycle_config, server_config):
        """測試進程指標收集"""
        process_id = "test_process"
        
        await lifecycle_manager.register_process(
            process_id, mock_process, lifecycle_config, server_config
        )
        await lifecycle_manager.start_process(process_id)
        
        # 等待指標收集
        await asyncio.sleep(0.1)
        
        metrics = await lifecycle_manager.get_process_metrics(process_id)
        
        assert metrics is not None
        assert "start_time" in metrics
        assert "uptime" in metrics
        assert "memory_usage" in metrics
        assert "cpu_percent" in metrics
        assert "restart_count" in metrics
        assert "health_check_count" in metrics
    
    def test_lifecycle_config_validation(self):
        """測試生命週期配置驗證"""
        # 有效配置
        valid_config = LifecycleConfig(
            health_check_interval=5.0,
            restart_policy=RestartPolicy.ALWAYS,
            max_restart_attempts=3
        )
        assert valid_config.health_check_interval == 5.0
        assert valid_config.restart_policy == RestartPolicy.ALWAYS
        
        # 無效間隔（應該被調整）
        invalid_config = LifecycleConfig(health_check_interval=0.5)
        assert invalid_config.health_check_interval >= 1.0  # 最小值限制


class TestRestartPolicies:
    """重啟策略測試"""
    
    @pytest.fixture
    def lifecycle_manager(self):
        return ProcessLifecycleManager()
    
    @pytest.mark.asyncio
    async def test_never_restart_policy(self, lifecycle_manager):
        """測試永不重啟策略"""
        config = LifecycleConfig(restart_policy=RestartPolicy.NEVER)
        failing_process = MockProcess(is_alive=False)
        
        await lifecycle_manager.register_process(
            "test", failing_process, config, None
        )
        
        # 失敗的進程不應該重啟
        should_restart = await lifecycle_manager._should_restart_process("test")
        assert should_restart is False
    
    @pytest.mark.asyncio
    async def test_always_restart_policy(self, lifecycle_manager):
        """測試總是重啟策略"""
        config = LifecycleConfig(restart_policy=RestartPolicy.ALWAYS)
        
        await lifecycle_manager.register_process(
            "test", MockProcess(is_alive=False), config, None
        )
        
        # 進程應該總是重啟
        should_restart = await lifecycle_manager._should_restart_process("test")
        assert should_restart is True
    
    @pytest.mark.asyncio
    async def test_restart_attempts_limit(self, lifecycle_manager):
        """測試重啟次數限制"""
        config = LifecycleConfig(
            restart_policy=RestartPolicy.ON_FAILURE,
            max_restart_attempts=2
        )
        
        await lifecycle_manager.register_process(
            "test", MockProcess(is_alive=False), config, None
        )
        
        managed_process = lifecycle_manager._managed_processes["test"]
        
        # 第一次和第二次應該重啟
        managed_process.metrics.restart_count = 0
        assert await lifecycle_manager._should_restart_process("test") is True
        
        managed_process.metrics.restart_count = 1
        assert await lifecycle_manager._should_restart_process("test") is True
        
        # 第三次不應該重啟（超過限制）
        managed_process.metrics.restart_count = 2
        assert await lifecycle_manager._should_restart_process("test") is False


class TestErrorHandling:
    """錯誤處理測試"""
    
    @pytest.fixture
    def lifecycle_manager(self):
        return ProcessLifecycleManager()
    
    @pytest.mark.asyncio
    async def test_unregistered_process_operations(self, lifecycle_manager):
        """測試對未註冊進程的操作"""
        # 嘗試啟動未註冊的進程
        result = await lifecycle_manager.start_process("nonexistent")
        assert result is False
        
        # 嘗試停止未註冊的進程
        result = await lifecycle_manager.stop_process("nonexistent")
        assert result is False
        
        # 嘗試獲取未註冊進程的狀態
        status = await lifecycle_manager.get_process_status("nonexistent")
        assert status is None
    
    @pytest.mark.asyncio
    async def test_process_startup_failure(self, lifecycle_manager):
        """測試進程啟動失敗"""
        # 創建啟動會失敗的進程
        failing_process = Mock()
        failing_process.is_running.return_value = False
        failing_process.get_info.side_effect = Exception("啟動失敗")
        
        config = LifecycleConfig()
        
        await lifecycle_manager.register_process(
            "failing", failing_process, config, None
        )
        
        result = await lifecycle_manager.start_process("failing")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_monitoring_exception_handling(self, lifecycle_manager):
        """測試監控過程中的異常處理"""
        # 創建會拋出異常的進程
        exception_process = Mock()
        exception_process.is_running.side_effect = Exception("進程檢查失敗")
        
        config = LifecycleConfig(enable_monitoring=True)
        
        await lifecycle_manager.register_process(
            "exception", exception_process, config, None
        )
        
        # 監控不應該因為單個進程異常而崩潰
        try:
            await lifecycle_manager._check_process_health("exception")
        except Exception:
            pytest.fail("監控不應該因為進程異常而崩潰")


class TestPerformance:
    """性能測試"""
    
    @pytest.mark.asyncio
    async def test_multiple_processes_management(self):
        """測試多進程管理性能"""
        lifecycle_manager = ProcessLifecycleManager()
        
        # 註冊多個進程
        num_processes = 10
        for i in range(num_processes):
            process = MockProcess(pid=1000 + i)
            config = LifecycleConfig()
            
            await lifecycle_manager.register_process(
                f"process_{i}", process, config, None
            )
        
        # 批量啟動
        start_time = time.time()
        tasks = []
        for i in range(num_processes):
            task = lifecycle_manager.start_process(f"process_{i}")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # 所有進程都應該成功啟動
        assert all(results)
        
        # 啟動時間應該合理（< 1秒）
        assert (end_time - start_time) < 1.0
        
        # 清理
        await lifecycle_manager.shutdown_all()


if __name__ == "__main__":
    # 運行測試
    pytest.main([__file__, "-v"])