#!/usr/bin/env python3
"""
MCP 相關介面定義
遵循 SOLID 原則的抽象介面
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol
from dataclasses import dataclass


@dataclass
class ResourceState:
    """資源狀態"""
    memory_mb: float
    file_descriptors: int
    child_processes: int
    has_leaks: bool


@dataclass
class MCPConnectionConfig:
    """MCP 連接配置"""
    server_name: str
    command: str
    args: List[str]
    env: Dict[str, str]
    cwd: Optional[str] = None
    timeout: int = 30


class IResourceTracker(ABC):
    """資源追蹤器介面"""
    
    @abstractmethod
    def capture_baseline(self) -> None:
        """捕獲基線資源狀態"""
        pass
    
    @abstractmethod
    def check_current_state(self) -> ResourceState:
        """檢查當前資源狀態"""
        pass
    
    @abstractmethod
    def has_leaks(self) -> bool:
        """檢查是否有洩漏"""
        pass


class ICommandResolver(ABC):
    """命令解析器介面"""
    
    @abstractmethod
    def resolve_command(self, command: str) -> str:
        """解析命令的完整路徑"""
        pass
    
    @abstractmethod
    def supports_command(self, command: str) -> bool:
        """檢查是否支援此命令"""
        pass


class IProcessManager(ABC):
    """進程管理器介面"""
    
    @abstractmethod
    async def start_process(self, config: MCPConnectionConfig) -> Any:
        """啟動進程"""
        pass
    
    @abstractmethod
    async def stop_process(self, process: Any) -> None:
        """停止進程"""
        pass
    
    @abstractmethod
    async def force_cleanup(self, process: Any) -> None:
        """強制清理進程"""
        pass


class ISecurityValidator(ABC):
    """安全驗證器介面"""
    
    @abstractmethod
    def validate_config(self, config: MCPConnectionConfig) -> bool:
        """驗證配置安全性"""
        pass
    
    @abstractmethod
    def is_command_allowed(self, command: str, args: List[str]) -> bool:
        """檢查命令是否被允許"""
        pass


class IMCPClient(ABC):
    """MCP 客戶端介面"""
    
    @abstractmethod
    async def connect(self) -> None:
        """建立連接"""
        pass
    
    @abstractmethod
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """調用工具"""
        pass
    
    @abstractmethod
    async def list_tools(self) -> Dict[str, Any]:
        """列出工具"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """關閉連接"""
        pass


class IMCPClientManager(ABC):
    """MCP 客戶端管理器介面"""
    
    @abstractmethod
    async def get_client(self, server_name: str) -> IMCPClient:
        """獲取客戶端"""
        pass
    
    @abstractmethod
    async def close_client(self, server_name: str) -> None:
        """關閉指定客戶端"""
        pass
    
    @abstractmethod
    async def close_all(self) -> None:
        """關閉所有客戶端"""
        pass


class IConfigurationProvider(Protocol):
    """配置提供者協議"""
    
    def get_server_config(self, server_name: str) -> Optional[MCPConnectionConfig]:
        """獲取服務器配置"""
        ...


class IMCPClientFactory(ABC):
    """MCP 客戶端工廠介面"""
    
    @abstractmethod
    def create_client(
        self, 
        config: MCPConnectionConfig,
        resource_tracker: IResourceTracker,
        process_manager: IProcessManager,
        security_validator: ISecurityValidator
    ) -> IMCPClient:
        """創建 MCP 客戶端"""
        pass