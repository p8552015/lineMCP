"""
連接管理模組

提供連接池、熔斷器、重試策略等連接相關功能。
"""

from .circuit import CircuitBreaker, CircuitState
from .pool import ConnectionPool
from .retry import RetryStrategy, ExponentialBackoff

__all__ = [
    "CircuitBreaker",
    "CircuitState", 
    "ConnectionPool",
    "RetryStrategy",
    "ExponentialBackoff",
]