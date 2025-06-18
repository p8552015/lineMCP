"""
協議適配器基礎類別

定義所有協議適配器的共用介面和基礎功能。
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional

from ..models.base import (
    MCPResponse,
    MCPCall,
    CallOptions,
    HealthStatus,
)


class BaseProtocolAdapter(ABC):
    """
    協議適配器基礎類別
    
    定義所有協議適配器必須實作的方法。
    """

    def __init__(self, config: Dict[str, Any] | None = None):
        """
        初始化適配器
        
        Args:
            config: 適配器配置
        """
        self.config = config or {}
        self.protocol = "unknown"
        self._closed = False

    @abstractmethod
    async def call_tool(
        self,
        server_url: str,
        tool: str,
        params: Dict[str, Any],
        *,
        options: CallOptions | None = None,
    ) -> MCPResponse:
        """
        呼叫 MCP 工具
        
        Args:
            server_url: 伺服器 URL 或識別碼
            tool: 工具名稱
            params: 工具參數
            options: 呼叫選項
            
        Returns:
            MCP 回應結果
        """
        pass

    @abstractmethod
    async def batch_call(
        self,
        server_url: str,
        calls: List[MCPCall],
    ) -> List[MCPResponse]:
        """
        批次呼叫多個 MCP 工具
        
        Args:
            server_url: 伺服器 URL 或識別碼
            calls: 批次呼叫清單
            
        Returns:
            對應的回應結果清單
        """
        pass

    @abstractmethod
    async def stream_call(
        self,
        server_url: str,
        tool: str,
        params: Dict[str, Any],
        *,
        options: CallOptions | None = None,
    ) -> AsyncIterator[MCPResponse]:
        """
        串流呼叫 MCP 工具
        
        Args:
            server_url: 伺服器 URL 或識別碼
            tool: 工具名稱
            params: 工具參數
            options: 呼叫選項
            
        Yields:
            串流回應結果
        """
        pass

    @abstractmethod
    async def health_check(self, server_url: str) -> HealthStatus:
        """
        檢查伺服器健康狀態
        
        Args:
            server_url: 伺服器 URL 或識別碼
            
        Returns:
            健康狀態資訊
        """
        pass

    @abstractmethod
    async def list_tools(self, server_url: str) -> List[Dict[str, Any]]:
        """
        列出伺服器可用工具
        
        Args:
            server_url: 伺服器 URL 或識別碼
            
        Returns:
            工具清單
        """
        pass

    async def close(self) -> None:
        """
        關閉適配器並清理資源
        
        子類別應該覆寫此方法以進行特定的清理工作。
        """
        self._closed = True

    def __repr__(self) -> str:
        """返回適配器的字串表示"""
        return f"{self.__class__.__name__}(protocol={self.protocol})" 