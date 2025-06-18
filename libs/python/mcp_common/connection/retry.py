"""
重試策略實作

提供各種重試策略的實作。
"""

import asyncio
import random
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, Type
import logging

logger = logging.getLogger(__name__)


class RetryStrategy(ABC):
    """重試策略抽象基類"""
    
    @abstractmethod
    async def should_retry(
        self,
        attempt: int,
        exception: Exception,
    ) -> bool:
        """
        判斷是否應該重試
        
        Args:
            attempt: 當前嘗試次數（從 1 開始）
            exception: 發生的異常
            
        Returns:
            True 如果應該重試，False 否則
        """
        pass
    
    @abstractmethod
    async def get_delay(self, attempt: int) -> float:
        """
        獲取重試延遲時間
        
        Args:
            attempt: 當前嘗試次數（從 1 開始）
            
        Returns:
            延遲時間（秒）
        """
        pass


class ExponentialBackoff(RetryStrategy):
    """指數退避重試策略"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: tuple[Type[Exception], ...] = (Exception,),
    ):
        """
        初始化指數退避策略
        
        Args:
            max_attempts: 最大嘗試次數
            base_delay: 基礎延遲時間
            max_delay: 最大延遲時間
            multiplier: 延遲倍數
            jitter: 是否加入隨機抖動
            retryable_exceptions: 可重試的異常類型
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions

    async def should_retry(
        self,
        attempt: int,
        exception: Exception,
    ) -> bool:
        """判斷是否應該重試"""
        if attempt >= self.max_attempts:
            return False
        
        return isinstance(exception, self.retryable_exceptions)

    async def get_delay(self, attempt: int) -> float:
        """計算指數退避延遲"""
        delay = self.base_delay * (self.multiplier ** (attempt - 1))
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            # 加入 ±25% 的隨機抖動
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)


class LinearBackoff(RetryStrategy):
    """線性退避重試策略"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        delay_increment: float = 1.0,
        max_delay: float = 30.0,
        retryable_exceptions: tuple[Type[Exception], ...] = (Exception,),
    ):
        """
        初始化線性退避策略
        
        Args:
            max_attempts: 最大嘗試次數
            delay_increment: 延遲增量
            max_delay: 最大延遲時間
            retryable_exceptions: 可重試的異常類型
        """
        self.max_attempts = max_attempts
        self.delay_increment = delay_increment
        self.max_delay = max_delay
        self.retryable_exceptions = retryable_exceptions

    async def should_retry(
        self,
        attempt: int,
        exception: Exception,
    ) -> bool:
        """判斷是否應該重試"""
        if attempt >= self.max_attempts:
            return False
        
        return isinstance(exception, self.retryable_exceptions)

    async def get_delay(self, attempt: int) -> float:
        """計算線性延遲"""
        delay = self.delay_increment * attempt
        return min(delay, self.max_delay)


class FixedDelay(RetryStrategy):
    """固定延遲重試策略"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        retryable_exceptions: tuple[Type[Exception], ...] = (Exception,),
    ):
        """
        初始化固定延遲策略
        
        Args:
            max_attempts: 最大嘗試次數
            delay: 固定延遲時間
            retryable_exceptions: 可重試的異常類型
        """
        self.max_attempts = max_attempts
        self.delay = delay
        self.retryable_exceptions = retryable_exceptions

    async def should_retry(
        self,
        attempt: int,
        exception: Exception,
    ) -> bool:
        """判斷是否應該重試"""
        if attempt >= self.max_attempts:
            return False
        
        return isinstance(exception, self.retryable_exceptions)

    async def get_delay(self, attempt: int) -> float:
        """返回固定延遲"""
        return self.delay


async def retry_with_strategy(
    func: Callable,
    strategy: RetryStrategy,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """
    使用指定策略執行重試
    
    Args:
        func: 要執行的函數
        strategy: 重試策略
        *args: 函數位置參數
        **kwargs: 函數關鍵字參數
        
    Returns:
        函數執行結果
        
    Raises:
        最後一次嘗試的異常
    """
    last_exception = None
    attempt = 0
    
    while True:
        attempt += 1
        
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
                
        except Exception as e:
            last_exception = e
            
            logger.debug(
                f"第 {attempt} 次嘗試失敗: {type(e).__name__}: {e}"
            )
            
            # 檢查是否應該重試
            if not await strategy.should_retry(attempt, e):
                logger.debug(f"不再重試，已達到最大嘗試次數或異常不可重試")
                raise e
            
            # 等待重試延遲
            delay = await strategy.get_delay(attempt)
            if delay > 0:
                logger.debug(f"等待 {delay:.2f} 秒後重試")
                await asyncio.sleep(delay)
    
    # 理論上不會執行到這裡
    if last_exception:
        raise last_exception