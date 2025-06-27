"""
MCP 服務器介面模組

定義符合 SOLID 原則的 MCP 服務器相關抽象介面：
- IMCPServerFactory: MCP 服務器工廠介面
- IMCPServer: MCP 服務器介面
- IMCPConnection: MCP 連接介面

遵循設計原則：
- SRP: 每個介面專注單一職責
- OCP: 對擴展開放，對修改封閉
- ISP: 介面隔離，細粒度設計
- DIP: 依賴抽象而非具體實現
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .runtime_interfaces import IProcess, RuntimeType


class MCPServerType(Enum):
    """MCP 服務器類型"""

    POSTGRES = "postgres"
    SQLITE = "sqlite"
    DATABASE = "database"  # 通用資料庫類型
    FILESYSTEM = "filesystem"
    HTTP_API = "http_api"
    CUSTOM = "custom"


class ConnectionStatus(Enum):
    """連接狀態"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"
    TIMEOUT = "timeout"


class MCPProtocol(Enum):
    """MCP 協議類型"""

    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"
    TCP = "tcp"


class MCPServerStatus(Enum):
    """MCP 服務器狀態"""

    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    RESTARTING = "restarting"


@dataclass
class MCPConnectionInfo:
    """MCP 連接資訊"""

    transport: str  # "stdio", "http", "websocket", "tcp"
    address: str
    port: int | None = None
    url: str | None = None
    protocol_version: str = "1.0"
    connection_id: str | None = None

    @property
    def endpoint(self) -> str:
        """獲取連接端點"""
        if self.url:
            return self.url
        elif self.port:
            return f"{self.address}:{self.port}"
        else:
            return self.address


@dataclass
class MCPServerInfo:
    """MCP 服務器資訊"""

    config: "MCPServerConfig"
    process_id: int | None = None
    status: MCPServerStatus = MCPServerStatus.CREATED
    connection_info: MCPConnectionInfo | None = None
    runtime_info: Any | None = None

    # 時間戳
    created_at: float | None = None
    started_at: float | None = None
    stopped_at: float | None = None
    last_health_check: float | None = None

    # 統計資訊
    restart_count: int = 0
    total_uptime: float = 0.0

    # 錯誤資訊
    last_error: str | None = None
    error_count: int = 0

    @property
    def uptime(self) -> float:
        """計算當前運行時間"""
        if self.started_at and self.status == MCPServerStatus.RUNNING:
            import time

            return time.time() - self.started_at
        return 0.0

    @property
    def is_healthy(self) -> bool:
        """檢查服務器是否健康"""
        return (
            self.status == MCPServerStatus.RUNNING
            and self.process_id is not None
            and (
                self.last_health_check is None
                or __import__("time").time() - self.last_health_check < 60
            )
        )


@dataclass
class MCPServerConfig:
    """MCP 服務器配置"""

    name: str
    server_type: MCPServerType
    runtime_type: RuntimeType
    protocol: MCPProtocol = MCPProtocol.STDIO

    # 執行配置
    command: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    working_directory: str | None = None  # 修改為一致的名稱
    description: str = ""  # 添加缺少的 description 欄位

    # 連接配置
    host: str | None = None
    port: int | None = None
    url: str | None = None

    # 超時和重試配置
    timeout: float = 30.0
    connect_timeout: float = 10.0
    retry_attempts: int = 3
    retry_delay: float = 1.0

    # 健康檢查配置
    health_check_interval: float = 30.0
    health_check_timeout: float = 5.0

    # 額外配置
    auto_restart: bool = True
    max_restart_attempts: int = 5
    restart_delay: float = 2.0

    def validate(self) -> list[str]:
        """
        驗證配置有效性

        Returns:
            List[str]: 驗證錯誤列表，空列表表示配置有效
        """
        errors = []

        if not self.name:
            errors.append("服務器名稱不能為空")

        if self.protocol == MCPProtocol.STDIO and not self.command:
            errors.append("STDIO 協議需要指定命令")

        if (
            self.protocol in [MCPProtocol.HTTP, MCPProtocol.WEBSOCKET]
            and not self.url
            and not (self.host and self.port)
        ):
            errors.append("網路協議需要指定 URL 或 host/port")

        if self.timeout <= 0:
            errors.append("超時時間必須大於 0")

        if self.retry_attempts < 0:
            errors.append("重試次數不能為負數")

        return errors

    @property
    def is_valid(self) -> bool:
        """檢查配置是否有效"""
        return len(self.validate()) == 0


@dataclass
class MCPTool:
    """MCP 工具定義"""

    name: str
    description: str
    input_schema: dict[str, Any]
    parameters: dict[str, Any] = field(default_factory=dict)

    def validate_input(self, input_data: dict[str, Any]) -> bool:
        """
        驗證輸入資料是否符合 schema

        Args:
            input_data: 輸入資料

        Returns:
            bool: 驗證是否通過
        """
        # 簡單驗證實現，實際應該使用 jsonschema
        required_fields = self.input_schema.get("required", [])
        return all(field in input_data for field in required_fields)


@dataclass
class MCPResource:
    """MCP 資源定義"""

    uri: str
    name: str
    description: str
    mime_type: str | None = None

    @property
    def is_readable(self) -> bool:
        """檢查資源是否可讀"""
        return self.mime_type is not None


@dataclass
class MCPToolCall:
    """MCP 工具調用"""

    tool_name: str
    parameters: dict[str, Any]
    call_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """轉換為字典格式"""
        return {
            "tool": self.tool_name,
            "parameters": self.parameters,
            "call_id": self.call_id,
        }


@dataclass
class MCPToolResult:
    """MCP 工具執行結果"""

    success: bool
    result: Any = None
    error: str | None = None
    call_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """轉換為字典格式"""
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "call_id": self.call_id,
            "metadata": self.metadata,
        }


class IMCPConnection(ABC):
    """
    MCP 連接介面

    遵循 SRP 原則：專注於單一 MCP 連接的管理
    """

    @property
    @abstractmethod
    def status(self) -> ConnectionStatus:
        """獲取連接狀態"""
        pass

    @property
    @abstractmethod
    def config(self) -> MCPServerConfig:
        """獲取連接配置"""
        pass

    @abstractmethod
    async def connect(self) -> bool:
        """
        建立連接

        Returns:
            bool: 連接是否成功
        """
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """
        斷開連接

        Returns:
            bool: 斷開是否成功
        """
        pass

    @abstractmethod
    async def is_alive(self) -> bool:
        """
        檢查連接是否存活

        Returns:
            bool: 連接是否存活
        """
        pass

    @abstractmethod
    async def ping(self, timeout: float | None = None) -> bool:
        """
        ping 測試連接

        Args:
            timeout: 超時時間

        Returns:
            bool: ping 是否成功
        """
        pass

    @abstractmethod
    async def call_tool(self, tool_call: MCPToolCall) -> MCPToolResult:
        """
        調用 MCP 工具

        Args:
            tool_call: 工具調用請求

        Returns:
            MCPToolResult: 工具執行結果
        """
        pass

    @abstractmethod
    async def list_tools(self) -> list[MCPTool]:
        """
        列出可用工具

        Returns:
            List[MCPTool]: 可用工具列表
        """
        pass

    @abstractmethod
    async def list_resources(self) -> list[MCPResource]:
        """
        列出可用資源

        Returns:
            List[MCPResource]: 可用資源列表
        """
        pass


class IMCPServer(ABC):
    """
    MCP 服務器介面

    遵循 SRP 原則：專注於 MCP 服務器的管理
    遵循 ISP 原則：只定義服務器管理相關的方法
    """

    @property
    @abstractmethod
    def config(self) -> MCPServerConfig:
        """獲取服務器配置"""
        pass

    @property
    @abstractmethod
    def process(self) -> IProcess | None:
        """獲取服務器進程（如果適用）"""
        pass

    @abstractmethod
    async def start(self) -> bool:
        """
        啟動服務器

        Returns:
            bool: 啟動是否成功
        """
        pass

    @abstractmethod
    async def stop(self, timeout: float | None = None) -> bool:
        """
        停止服務器

        Args:
            timeout: 停止超時時間

        Returns:
            bool: 停止是否成功
        """
        pass

    @abstractmethod
    async def restart(self, timeout: float | None = None) -> bool:
        """
        重啟服務器

        Args:
            timeout: 重啟超時時間

        Returns:
            bool: 重啟是否成功
        """
        pass

    @abstractmethod
    async def is_running(self) -> bool:
        """
        檢查服務器是否正在運行

        Returns:
            bool: 服務器是否正在運行
        """
        pass

    @abstractmethod
    async def get_connection(self) -> IMCPConnection:
        """
        獲取 MCP 連接

        Returns:
            IMCPConnection: MCP 連接實例
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        健康檢查

        Returns:
            bool: 服務器是否健康
        """
        pass


class IMCPServerFactory(ABC):
    """
    MCP 服務器工廠介面

    遵循 OCP 原則：對擴展開放，對修改封閉
    遵循 DIP 原則：依賴抽象而非具體實現
    """

    @abstractmethod
    async def create_server(self, config: MCPServerConfig) -> IMCPServer:
        """
        創建 MCP 服務器實例

        Args:
            config: 服務器配置

        Returns:
            IMCPServer: MCP 服務器實例

        Raises:
            ValueError: 配置無效
            RuntimeError: 創建失敗
        """
        pass

    @abstractmethod
    async def get_supported_runtimes(self) -> list[RuntimeType]:
        """
        獲取支援的運行時類型

        Returns:
            List[RuntimeType]: 支援的運行時類型列表
        """
        pass

    @abstractmethod
    async def get_supported_protocols(self) -> list[MCPProtocol]:
        """
        獲取支援的協議類型

        Returns:
            List[MCPProtocol]: 支援的協議類型列表
        """
        pass

    @abstractmethod
    async def get_supported_server_types(self) -> list[MCPServerType]:
        """
        獲取支援的服務器類型

        Returns:
            List[MCPServerType]: 支援的服務器類型列表
        """
        pass

    @abstractmethod
    async def validate_config(self, config: MCPServerConfig) -> list[str]:
        """
        驗證服務器配置

        Args:
            config: 要驗證的配置

        Returns:
            List[str]: 驗證錯誤列表，空列表表示配置有效
        """
        pass

    @abstractmethod
    async def get_default_config(
        self, server_type: MCPServerType, runtime_type: RuntimeType
    ) -> MCPServerConfig:
        """
        獲取預設配置

        Args:
            server_type: 服務器類型
            runtime_type: 運行時類型

        Returns:
            MCPServerConfig: 預設配置
        """
        pass

    @abstractmethod
    async def can_create(self, config: MCPServerConfig) -> bool:
        """
        檢查是否可以創建指定配置的服務器

        Args:
            config: 服務器配置

        Returns:
            bool: 是否可以創建
        """
        pass


class IMCPServerManager(ABC):
    """
    MCP 服務器管理器介面

    遵循 SRP 原則：專注於多服務器的統一管理
    """

    @abstractmethod
    async def register_server(self, server: IMCPServer, name: str) -> bool:
        """
        註冊服務器

        Args:
            server: 服務器實例
            name: 服務器名稱

        Returns:
            bool: 註冊是否成功
        """
        pass

    @abstractmethod
    async def unregister_server(self, name: str) -> bool:
        """
        取消註冊服務器

        Args:
            name: 服務器名稱

        Returns:
            bool: 取消註冊是否成功
        """
        pass

    @abstractmethod
    async def get_server(self, name: str) -> IMCPServer | None:
        """
        獲取指定名稱的服務器

        Args:
            name: 服務器名稱

        Returns:
            Optional[IMCPServer]: 服務器實例，不存在返回 None
        """
        pass

    @abstractmethod
    async def list_servers(self) -> dict[str, IMCPServer]:
        """
        列出所有管理的服務器

        Returns:
            Dict[str, IMCPServer]: 服務器名稱到服務器實例的映射
        """
        pass

    @abstractmethod
    async def start_all(self) -> dict[str, bool]:
        """
        啟動所有服務器

        Returns:
            Dict[str, bool]: 服務器名稱到啟動結果的映射
        """
        pass

    @abstractmethod
    async def stop_all(self, timeout: float | None = None) -> dict[str, bool]:
        """
        停止所有服務器

        Args:
            timeout: 停止超時時間

        Returns:
            Dict[str, bool]: 服務器名稱到停止結果的映射
        """
        pass

    @abstractmethod
    async def health_check_all(self) -> dict[str, bool]:
        """
        檢查所有服務器健康狀態

        Returns:
            Dict[str, bool]: 服務器名稱到健康狀態的映射
        """
        pass
