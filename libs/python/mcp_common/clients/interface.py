"""
MCP 客戶端統一介面定義

定義所有 MCP 客戶端必須實作的標準介面。
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Protocol, runtime_checkable

from ..models.base import MCPResponse, MCPCall, CallOptions, HealthStatus


@runtime_checkable
class MCPClientInterface(Protocol):
    """
    MCP 客戶端統一介面協議
    
    所有 MCP 客戶端實作都必須符合此介面規範。
    """

    async def call_tool(
        self,
        server: str,
        tool: str,
        params: dict[str, Any],
        *,
        options: CallOptions | None = None,
    ) -> MCPResponse:
        """
        呼叫 MCP 伺服器工具
        
        Args:
            server: 伺服器名稱或 URL
            tool: 工具名稱
            params: 工具參數
            options: 呼叫選項 (超時、重試等)
            
        Returns:
            MCP 回應結果
            
        Raises:
            MCPError: MCP 相關錯誤
            TimeoutError: 請求超時
            ConnectionError: 連線錯誤
        """
        ...

    async def batch_call(self, calls: list[MCPCall]) -> list[MCPResponse]:
        """
        批次呼叫多個 MCP 工具
        
        Args:
            calls: 批次呼叫清單
            
        Returns:
            對應的回應結果清單
            
        Note:
            即使部分呼叫失敗，仍會回傳所有結果。
            失敗的呼叫會在回應中包含錯誤資訊。
        """
        ...

    async def stream_call(
        self,
        server: str,
        tool: str,
        params: dict[str, Any],
        *,
        options: CallOptions | None = None,
    ) -> AsyncIterator[MCPResponse]:
        """
        串流呼叫 MCP 工具
        
        Args:
            server: 伺服器名稱或 URL
            tool: 工具名稱
            params: 工具參數
            options: 呼叫選項
            
        Yields:
            串流回應結果
            
        Note:
            適用於長時間執行或大量資料回傳的工具。
        """
        ...

    async def health_check(self, server: str | None = None) -> HealthStatus:
        """
        檢查伺服器健康狀態
        
        Args:
            server: 特定伺服器名稱，None 表示檢查所有伺服器
            
        Returns:
            健康狀態資訊
        """
        ...

    async def list_tools(self, server: str) -> list[dict[str, Any]]:
        """
        列出伺服器可用工具
        
        Args:
            server: 伺服器名稱或 URL
            
        Returns:
            工具清單，包含名稱、描述、參數等資訊
        """
        ...

    async def close(self) -> None:
        """
        關閉客戶端並清理資源
        
        Note:
            應確保所有連線、執行緒池等資源被正確釋放。
        """
        ...


class BaseMCPClient(ABC):
    """
    MCP 客戶端抽象基類
    
    提供公共功能的預設實作。
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        初始化客戶端
        
        Args:
            config: 客戶端配置
        """
        self.config = config or {}
        self._closed = False

    async def __aenter__(self):
        """非同步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同步上下文管理器出口"""
        await self.close()

    def __del__(self):
        """析構函數，確保資源清理"""
        if not self._closed:
            import asyncio
            try:
                # 嘗試在事件迴圈中清理
                loop = asyncio.get_event_loop()
                if not loop.is_closed():
                    loop.create_task(self.close())
            except RuntimeError:
                pass  # 事件迴圈已關閉，無法清理

    @abstractmethod
    async def call_tool(
        self,
        server: str,
        tool: str,
        params: dict[str, Any],
        *,
        options: CallOptions | None = None,
    ) -> MCPResponse:
        """抽象方法：呼叫工具"""
        pass

    @abstractmethod
    async def batch_call(self, calls: list[MCPCall]) -> list[MCPResponse]:
        """抽象方法：批次呼叫"""
        pass

    @abstractmethod
    async def stream_call(
        self,
        server: str,
        tool: str,
        params: dict[str, Any],
        *,
        options: CallOptions | None = None,
    ) -> AsyncIterator[MCPResponse]:
        """抽象方法：串流呼叫"""
        pass

    @abstractmethod
    async def health_check(self, server: str | None = None) -> HealthStatus:
        """抽象方法：健康檢查"""
        pass

    @abstractmethod
    async def list_tools(self, server: str) -> list[dict[str, Any]]:
        """抽象方法：列出工具"""
        pass

    async def close(self) -> None:
        """關閉客戶端基礎實作"""
        self._closed = True