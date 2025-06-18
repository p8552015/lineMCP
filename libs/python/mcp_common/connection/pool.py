"""
連接池實作

管理和複用 HTTP 連接以提升效能。
"""

import asyncio
import time
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ConnectionPool:
    """
    簡單的連接池實作
    
    管理連接的建立、複用和清理。
    """

    def __init__(
        self,
        min_size: int = 2,
        max_size: int = 20,
        timeout: float = 30.0,
        idle_timeout: float = 300.0,
        **kwargs: Any,
    ):
        """
        初始化連接池
        
        Args:
            min_size: 最小連接數
            max_size: 最大連接數  
            timeout: 連接超時時間
            idle_timeout: 空閒連接超時時間
        """
        self.min_size = min_size
        self.max_size = max_size
        self.timeout = timeout
        self.idle_timeout = idle_timeout
        
        self._connections: Dict[str, Any] = {}
        self._connection_times: Dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._closed = False

    async def get_connection(self, server: str) -> Any:
        """
        獲取連接
        
        Args:
            server: 伺服器識別碼
            
        Returns:
            連接對象
        """
        async with self._lock:
            if self._closed:
                raise RuntimeError("連接池已關閉")
                
            # 檢查是否有現有連接
            if server in self._connections:
                connection = self._connections[server]
                self._connection_times[server] = time.time()
                return connection
            
            # 建立新連接（這裡是簡化實作）
            connection = {
                "server": server,
                "created_at": time.time(),
                "last_used": time.time(),
            }
            
            self._connections[server] = connection
            self._connection_times[server] = time.time()
            
            logger.debug(f"建立新連接: {server}")
            return connection

    async def return_connection(self, server: str, connection: Any) -> None:
        """
        歸還連接到池中
        
        Args:
            server: 伺服器識別碼
            connection: 連接對象
        """
        async with self._lock:
            if not self._closed and server in self._connections:
                self._connection_times[server] = time.time()

    async def remove_connection(self, server: str) -> None:
        """
        移除連接
        
        Args:
            server: 伺服器識別碼
        """
        async with self._lock:
            if server in self._connections:
                del self._connections[server]
                if server in self._connection_times:
                    del self._connection_times[server]
                logger.debug(f"移除連接: {server}")

    async def cleanup_idle_connections(self) -> None:
        """清理空閒連接"""
        async with self._lock:
            current_time = time.time()
            idle_servers = []
            
            for server, last_used in self._connection_times.items():
                if current_time - last_used > self.idle_timeout:
                    idle_servers.append(server)
            
            for server in idle_servers:
                await self.remove_connection(server)
                logger.debug(f"清理空閒連接: {server}")

    def get_stats(self) -> Dict[str, Any]:
        """
        獲取連接池統計資訊
        
        Returns:
            統計資訊字典
        """
        return {
            "total_connections": len(self._connections),
            "min_size": self.min_size,
            "max_size": self.max_size,
            "timeout": self.timeout,
            "idle_timeout": self.idle_timeout,
            "servers": list(self._connections.keys()),
        }

    async def close(self) -> None:
        """關閉連接池"""
        async with self._lock:
            if not self._closed:
                self._closed = True
                self._connections.clear()
                self._connection_times.clear()
                logger.info("連接池已關閉")