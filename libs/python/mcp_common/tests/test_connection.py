"""
測試連接管理元件
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from mcp_common.connection.pool import ConnectionPool, PooledConnection
from mcp_common.connection.circuit import CircuitBreaker, CircuitState
from mcp_common.connection.health import HealthChecker, HealthStatus
from mcp_common.connection.retry import RetryPolicy, exponential_backoff, retry_with_backoff


class TestConnectionPool:
    """測試連接池"""
    
    @pytest.fixture
    def pool(self):
        """建立測試連接池"""
        return ConnectionPool(
            min_size=2,
            max_size=5,
            timeout=1.0,
            idle_timeout=60.0
        )
    
    @pytest.mark.asyncio
    async def test_acquire_connection(self, pool):
        """測試獲取連接"""
        # 建立模擬連接
        mock_conn = Mock()
        await pool._create_connection = AsyncMock(return_value=mock_conn)
        
        # 獲取連接
        async with pool.acquire() as conn:
            assert isinstance(conn, PooledConnection)
            assert conn.raw_connection == mock_conn
            assert pool.active_connections == 1
        
        # 連接應該被釋放
        assert pool.active_connections == 0
    
    @pytest.mark.asyncio
    async def test_connection_reuse(self, pool):
        """測試連接重用"""
        mock_conn = Mock()
        pool._create_connection = AsyncMock(return_value=mock_conn)
        
        # 第一次獲取
        async with pool.acquire() as conn1:
            first_conn = conn1.raw_connection
        
        # 第二次獲取應該重用同一連接
        async with pool.acquire() as conn2:
            assert conn2.raw_connection is first_conn
        
        # 只應該建立一次連接
        pool._create_connection.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_max_connections(self, pool):
        """測試最大連接數限制"""
        pool._create_connection = AsyncMock(return_value=Mock())
        
        # 同時獲取最大數量的連接
        connections = []
        for _ in range(pool.max_size):
            conn = await pool.acquire()
            connections.append(conn)
        
        assert pool.active_connections == pool.max_size
        
        # 嘗試獲取更多連接應該超時
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(pool.acquire(), timeout=0.1)
        
        # 釋放一個連接
        await connections[0].release()
        
        # 現在應該可以獲取連接
        conn = await pool.acquire()
        assert conn is not None
    
    @pytest.mark.asyncio
    async def test_idle_timeout(self, pool):
        """測試空閒超時"""
        mock_conn = Mock()
        mock_conn.is_closed = Mock(return_value=False)
        pool._create_connection = AsyncMock(return_value=mock_conn)
        pool.idle_timeout = 0.1  # 設定短超時
        
        # 獲取並釋放連接
        async with pool.acquire() as conn:
            pass
        
        # 等待超過空閒超時
        await asyncio.sleep(0.2)
        
        # 清理空閒連接
        await pool._cleanup_idle_connections()
        
        # 連接應該被關閉
        mock_conn.close.assert_called()
    
    @pytest.mark.asyncio
    async def test_close_pool(self, pool):
        """測試關閉連接池"""
        mock_conn = Mock()
        pool._create_connection = AsyncMock(return_value=mock_conn)
        
        # 建立一些連接
        async with pool.acquire() as conn:
            pass
        
        # 關閉池
        await pool.close()
        
        # 所有連接應該被關閉
        mock_conn.close.assert_called()
        assert pool.closed is True


class TestCircuitBreaker:
    """測試斷路器"""
    
    @pytest.fixture
    def breaker(self):
        """建立測試斷路器"""
        return CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1.0,
            half_open_max_calls=1
        )
    
    def test_initial_state(self, breaker):
        """測試初始狀態"""
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed is True
        assert breaker.is_open is False
        assert breaker.is_half_open is False
    
    def test_record_success(self, breaker):
        """測試記錄成功"""
        breaker.record_success()
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
    
    def test_record_failures_opens_circuit(self, breaker):
        """測試失敗導致斷路器開啟"""
        # 記錄失敗直到達到閾值
        for _ in range(breaker.failure_threshold):
            breaker.record_failure()
        
        assert breaker.state == CircuitState.OPEN
        assert breaker.is_open is True
    
    def test_half_open_after_timeout(self, breaker):
        """測試超時後進入半開狀態"""
        # 開啟斷路器
        for _ in range(breaker.failure_threshold):
            breaker.record_failure()
        
        assert breaker.state == CircuitState.OPEN
        
        # 模擬超時
        breaker._last_failure_time = datetime.now() - timedelta(seconds=2)
        
        # 檢查是否可以嘗試
        assert breaker.can_execute is True
        assert breaker.state == CircuitState.HALF_OPEN
    
    def test_half_open_to_closed(self, breaker):
        """測試半開狀態成功後關閉"""
        # 設定為半開狀態
        breaker._state = CircuitState.HALF_OPEN
        
        # 記錄成功
        breaker.record_success()
        
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
    
    def test_half_open_to_open(self, breaker):
        """測試半開狀態失敗後重新開啟"""
        # 設定為半開狀態
        breaker._state = CircuitState.HALF_OPEN
        
        # 記錄失敗
        breaker.record_failure()
        
        assert breaker.state == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_call_with_circuit(self, breaker):
        """測試使用斷路器呼叫函數"""
        # 成功的函數
        async def success_func():
            return "success"
        
        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
        
        # 失敗的函數
        async def failure_func():
            raise Exception("Test error")
        
        # 記錄失敗直到開啟
        for _ in range(breaker.failure_threshold):
            with pytest.raises(Exception):
                await breaker.call(failure_func)
        
        assert breaker.state == CircuitState.OPEN
        
        # 在開啟狀態下呼叫應該直接失敗
        with pytest.raises(Exception) as exc_info:
            await breaker.call(success_func)
        assert "Circuit breaker is OPEN" in str(exc_info.value)


class TestHealthChecker:
    """測試健康檢查器"""
    
    @pytest.fixture
    def checker(self):
        """建立測試健康檢查器"""
        return HealthChecker(
            check_interval=1.0,
            timeout=0.5,
            healthy_threshold=2,
            unhealthy_threshold=2
        )
    
    @pytest.mark.asyncio
    async def test_add_check(self, checker):
        """測試添加健康檢查"""
        async def check_func():
            return True
        
        checker.add_check("test_service", check_func)
        assert "test_service" in checker._checks
    
    @pytest.mark.asyncio
    async def test_perform_check_success(self, checker):
        """測試執行成功的健康檢查"""
        async def healthy_check():
            return True
        
        checker.add_check("service1", healthy_check)
        
        result = await checker.check_health("service1")
        assert result.status == HealthStatus.HEALTHY
        assert result.latency_ms > 0
    
    @pytest.mark.asyncio
    async def test_perform_check_failure(self, checker):
        """測試執行失敗的健康檢查"""
        async def unhealthy_check():
            raise Exception("Service unavailable")
        
        checker.add_check("service2", unhealthy_check)
        
        result = await checker.check_health("service2")
        assert result.status == HealthStatus.UNHEALTHY
        assert "Service unavailable" in result.error
    
    @pytest.mark.asyncio
    async def test_check_all_services(self, checker):
        """測試檢查所有服務"""
        async def healthy_check():
            return True
        
        async def unhealthy_check():
            return False
        
        checker.add_check("healthy_service", healthy_check)
        checker.add_check("unhealthy_service", unhealthy_check)
        
        results = await checker.check_all()
        
        assert len(results) == 2
        assert results["healthy_service"].status == HealthStatus.HEALTHY
        assert results["unhealthy_service"].status == HealthStatus.UNHEALTHY
    
    @pytest.mark.asyncio
    async def test_threshold_tracking(self, checker):
        """測試閾值追蹤"""
        call_count = 0
        
        async def flaky_check():
            nonlocal call_count
            call_count += 1
            return call_count % 3 != 0  # 每三次失敗一次
        
        checker.add_check("flaky_service", flaky_check)
        
        # 執行多次檢查
        for _ in range(5):
            await checker.check_health("flaky_service")
        
        # 檢查狀態歷史
        status = checker.get_status("flaky_service")
        assert status is not None


class TestRetryPolicy:
    """測試重試策略"""
    
    def test_default_policy(self):
        """測試預設策略"""
        policy = RetryPolicy()
        
        assert policy.max_attempts == 3
        assert policy.initial_delay == 1.0
        assert policy.max_delay == 60.0
        assert policy.exponential_base == 2.0
        assert policy.jitter is True
    
    def test_should_retry(self):
        """測試是否應該重試"""
        policy = RetryPolicy(max_attempts=3)
        
        # 一般異常應該重試
        assert policy.should_retry(Exception("Test"), 1) is True
        assert policy.should_retry(Exception("Test"), 2) is True
        assert policy.should_retry(Exception("Test"), 3) is False  # 超過最大次數
        
        # 特定異常不重試
        policy = RetryPolicy(
            max_attempts=3,
            retryable_exceptions=[ConnectionError, TimeoutError]
        )
        assert policy.should_retry(ConnectionError(), 1) is True
        assert policy.should_retry(ValueError(), 1) is False
    
    def test_exponential_backoff(self):
        """測試指數退避"""
        delays = []
        for attempt in range(5):
            delay = exponential_backoff(
                attempt=attempt,
                initial_delay=1.0,
                max_delay=30.0,
                exponential_base=2.0,
                jitter=False
            )
            delays.append(delay)
        
        # 驗證指數增長
        assert delays[0] == 1.0
        assert delays[1] == 2.0
        assert delays[2] == 4.0
        assert delays[3] == 8.0
        assert delays[4] == 16.0
    
    def test_exponential_backoff_with_jitter(self):
        """測試帶抖動的指數退避"""
        delay = exponential_backoff(
            attempt=2,
            initial_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter=True
        )
        
        # 帶抖動的延遲應該在 0 到基本延遲之間
        base_delay = 4.0  # 1.0 * 2^2
        assert 0 < delay <= base_delay
    
    @pytest.mark.asyncio
    async def test_retry_decorator(self):
        """測試重試裝飾器"""
        call_count = 0
        
        @retry_with_backoff(max_attempts=3, initial_delay=0.01)
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"
        
        result = await flaky_function()
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_decorator_max_attempts_exceeded(self):
        """測試重試裝飾器超過最大次數"""
        @retry_with_backoff(max_attempts=2, initial_delay=0.01)
        async def always_fails():
            raise ConnectionError("Always fails")
        
        with pytest.raises(ConnectionError):
            await always_fails()