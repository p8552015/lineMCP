"""
熔斷器實作

實作基於失敗計數和時間窗口的熔斷器模式。
"""

import asyncio
import time
from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """熔斷器狀態"""
    CLOSED = "closed"      # 正常狀態，允許請求通過
    OPEN = "open"          # 熔斷狀態，拒絕所有請求  
    HALF_OPEN = "half_open"  # 半開狀態，允許少量請求測試


class CircuitBreaker:
    """
    熔斷器實作
    
    基於失敗計數的熔斷器，當失敗次數超過閾值時開啟熔斷，
    經過冷卻時間後進入半開狀態進行恢復測試。
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        timeout: float = 60.0,
        name: str = "circuit_breaker",
    ):
        """
        初始化熔斷器
        
        Args:
            failure_threshold: 失敗次數閾值，超過則開啟熔斷
            success_threshold: 半開狀態下成功次數閾值，達到則關閉熔斷
            timeout: 熔斷超時時間（秒），超過後進入半開狀態
            name: 熔斷器名稱，用於日誌記錄
        """
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.name = name
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """獲取當前狀態"""
        return self._state

    @property
    def failure_count(self) -> int:
        """獲取失敗計數"""
        return self._failure_count

    @property
    def success_count(self) -> int:
        """獲取成功計數"""
        return self._success_count

    @property
    def is_open(self) -> bool:
        """檢查是否處於開啟狀態"""
        return self._state == CircuitState.OPEN

    @property
    def is_closed(self) -> bool:
        """檢查是否處於關閉狀態"""
        return self._state == CircuitState.CLOSED

    @property
    def is_half_open(self) -> bool:
        """檢查是否處於半開狀態"""
        return self._state == CircuitState.HALF_OPEN

    async def _transition_to_state(self, new_state: CircuitState) -> None:
        """轉換到新狀態"""
        old_state = self._state
        self._state = new_state
        
        if old_state != new_state:
            logger.info(
                f"熔斷器 {self.name} 狀態轉換: {old_state.value} -> {new_state.value}"
            )
            
            # 狀態轉換時重置計數器
            if new_state == CircuitState.CLOSED:
                self._failure_count = 0
                self._success_count = 0
            elif new_state == CircuitState.HALF_OPEN:
                self._success_count = 0

    async def _check_timeout(self) -> None:
        """檢查是否應該從開啟狀態轉換到半開狀態"""
        if (
            self._state == CircuitState.OPEN
            and self._last_failure_time is not None
            and time.time() - self._last_failure_time >= self.timeout
        ):
            await self._transition_to_state(CircuitState.HALF_OPEN)

    async def record_success(self) -> None:
        """記錄成功操作"""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                logger.debug(
                    f"熔斷器 {self.name} 記錄成功: {self._success_count}/{self.success_threshold}"
                )
                
                # 成功次數達到閾值，關閉熔斷器
                if self._success_count >= self.success_threshold:
                    await self._transition_to_state(CircuitState.CLOSED)
                    
            elif self._state == CircuitState.CLOSED:
                # 在關閉狀態下，成功操作可以重置失敗計數
                if self._failure_count > 0:
                    self._failure_count = max(0, self._failure_count - 1)

    async def record_failure(self) -> None:
        """記錄失敗操作"""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            logger.debug(
                f"熔斷器 {self.name} 記錄失敗: {self._failure_count}/{self.failure_threshold}"
            )
            
            if self._state == CircuitState.CLOSED:
                # 失敗次數達到閾值，開啟熔斷器
                if self._failure_count >= self.failure_threshold:
                    await self._transition_to_state(CircuitState.OPEN)
                    
            elif self._state == CircuitState.HALF_OPEN:
                # 半開狀態下失敗，直接回到開啟狀態
                await self._transition_to_state(CircuitState.OPEN)

    async def can_execute(self) -> bool:
        """
        檢查是否可以執行請求
        
        Returns:
            True 如果可以執行，False 如果被熔斷器阻止
        """
        async with self._lock:
            await self._check_timeout()
            
            if self._state == CircuitState.CLOSED:
                return True
            elif self._state == CircuitState.HALF_OPEN:
                return True
            else:  # OPEN
                return False

    async def execute(self, func, *args, **kwargs):
        """
        在熔斷器保護下執行函數
        
        Args:
            func: 要執行的函數
            *args: 函數位置參數
            **kwargs: 函數關鍵字參數
            
        Returns:
            函數執行結果
            
        Raises:
            CircuitBreakerError: 熔斷器開啟時拋出
        """
        from ..models.error import CircuitBreakerError
        
        if not await self.can_execute():
            raise CircuitBreakerError(
                message=f"熔斷器 {self.name} 處於開啟狀態",
                details={
                    "state": self._state.value,
                    "failure_count": self._failure_count,
                    "last_failure_time": self._last_failure_time,
                }
            )
        
        try:
            # 執行函數
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # 記錄成功
            await self.record_success()
            return result
            
        except Exception as e:
            # 記錄失敗
            await self.record_failure()
            raise e

    def get_stats(self) -> dict[str, any]:
        """
        獲取熔斷器統計資訊
        
        Returns:
            包含狀態、計數等資訊的字典
        """
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_threshold": self.failure_threshold,
            "success_threshold": self.success_threshold,
            "timeout": self.timeout,
            "last_failure_time": self._last_failure_time,
        }

    async def reset(self) -> None:
        """
        重置熔斷器到初始狀態
        
        Note:
            這是一個管理操作，通常用於手動恢復或測試。
        """
        async with self._lock:
            await self._transition_to_state(CircuitState.CLOSED)
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            
        logger.info(f"熔斷器 {self.name} 已重置")

    def __str__(self) -> str:
        return (
            f"CircuitBreaker(name={self.name}, state={self._state.value}, "
            f"failures={self._failure_count}, successes={self._success_count})"
        )