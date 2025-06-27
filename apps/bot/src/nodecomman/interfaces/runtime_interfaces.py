"""
運行時管理介面模組

定義符合 SOLID 原則的運行時環境管理抽象介面：
- IRuntimeManager: 運行時環境管理介面
- IProcessLifecycleManager: 進程生命週期管理介面

遵循設計原則：
- SRP: 每個介面專注單一職責
- ISP: 介面隔離，客戶端只依賴需要的方法
- DIP: 依賴抽象而非具體實現
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from enum import Enum


class RuntimeType(Enum):
    """支援的運行時類型"""

    NODEJS = "nodejs"
    PYTHON = "python"
    DENO = "deno"
    BUN = "bun"
    UNKNOWN = "unknown"


class ProcessStatus(Enum):
    """進程狀態枚舉"""

    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class RuntimeInfo:
    """運行時環境資訊"""

    type: RuntimeType
    version: str
    executable_path: str
    is_available: bool
    capabilities: list[str]
    env_variables: dict[str, str]
    package_manager: str | None = None

    @property
    def is_usable(self) -> bool:
        """檢查運行時是否可用"""
        return self.is_available and bool(self.executable_path)


@dataclass
class ProcessInfo:
    """進程資訊"""

    pid: int | None
    status: ProcessStatus
    command: str
    args: list[str]
    env: dict[str, str]
    working_dir: str
    start_time: float | None = None
    end_time: float | None = None
    return_code: int | None = None

    @property
    def is_alive(self) -> bool:
        """檢查進程是否存活"""
        return self.status in [ProcessStatus.STARTING, ProcessStatus.RUNNING]

    @property
    def runtime_seconds(self) -> float | None:
        """計算執行時間（秒）"""
        if self.start_time is None:
            return None
        end = self.end_time or __import__("time").time()
        return end - self.start_time


class IRuntimeManager(ABC):
    """
    運行時環境管理介面

    遵循 SRP 原則：專注於運行時環境的檢查、安裝和管理
    遵循 ISP 原則：只定義運行時管理相關的方法
    """

    @abstractmethod
    async def check_availability(self) -> bool:
        """
        檢查運行時環境是否可用

        Returns:
            bool: 運行時環境是否可用
        """
        pass

    @abstractmethod
    async def get_runtime_info(self) -> RuntimeInfo:
        """
        獲取運行時環境詳細資訊

        Returns:
            RuntimeInfo: 運行時環境資訊
        """
        pass

    @abstractmethod
    async def install_dependencies(self, dependencies: list[str]) -> bool:
        """
        安裝指定依賴套件

        Args:
            dependencies: 要安裝的依賴套件列表

        Returns:
            bool: 安裝是否成功
        """
        pass

    @abstractmethod
    async def create_process(
        self,
        command: str,
        args: list[str],
        env: dict[str, str] | None = None,
        working_dir: str | None = None,
    ) -> "IProcess":
        """
        創建運行時進程

        Args:
            command: 要執行的命令
            args: 命令參數
            env: 環境變數
            working_dir: 工作目錄

        Returns:
            IProcess: 進程介面實例
        """
        pass

    @abstractmethod
    async def validate_command(self, command: str, args: list[str]) -> bool:
        """
        驗證命令是否有效

        Args:
            command: 要驗證的命令
            args: 命令參數

        Returns:
            bool: 命令是否有效
        """
        pass

    @abstractmethod
    async def get_supported_packages(self) -> list[str]:
        """
        獲取支援的套件列表

        Returns:
            List[str]: 支援的套件名稱列表
        """
        pass


class IProcess(ABC):
    """
    進程介面

    遵循 SRP 原則：專注於單一進程的管理
    """

    @property
    @abstractmethod
    def info(self) -> ProcessInfo:
        """獲取進程資訊"""
        pass

    @abstractmethod
    async def start(self) -> bool:
        """
        啟動進程

        Returns:
            bool: 啟動是否成功
        """
        pass

    @abstractmethod
    async def stop(self, timeout: float = 10.0) -> bool:
        """
        停止進程

        Args:
            timeout: 停止超時時間（秒）

        Returns:
            bool: 停止是否成功
        """
        pass

    @abstractmethod
    async def kill(self) -> bool:
        """
        強制終止進程

        Returns:
            bool: 終止是否成功
        """
        pass

    @abstractmethod
    async def wait(self, timeout: float | None = None) -> int | None:
        """
        等待進程結束

        Args:
            timeout: 等待超時時間（秒）

        Returns:
            Optional[int]: 進程退出碼，超時返回 None
        """
        pass

    @abstractmethod
    async def is_alive(self) -> bool:
        """
        檢查進程是否存活

        Returns:
            bool: 進程是否存活
        """
        pass

    @abstractmethod
    async def send_signal(self, signal: int) -> bool:
        """
        發送信號給進程

        Args:
            signal: 信號編號

        Returns:
            bool: 發送是否成功
        """
        pass

    @abstractmethod
    async def communicate(
        self, input_data: str | None = None, timeout: float | None = None
    ) -> tuple[str, str]:
        """
        與進程通信

        Args:
            input_data: 輸入資料
            timeout: 通信超時時間

        Returns:
            tuple[str, str]: (stdout, stderr)
        """
        pass


class IProcessLifecycleManager(ABC):
    """
    進程生命週期管理介面

    遵循 SRP 原則：專注於多進程的生命週期管理
    遵循 ISP 原則：只定義生命週期管理相關的方法
    """

    @abstractmethod
    async def register_process(self, process: IProcess, name: str) -> bool:
        """
        註冊進程到管理器

        Args:
            process: 進程實例
            name: 進程名稱

        Returns:
            bool: 註冊是否成功
        """
        pass

    @abstractmethod
    async def unregister_process(self, name: str) -> bool:
        """
        取消註冊進程

        Args:
            name: 進程名稱

        Returns:
            bool: 取消註冊是否成功
        """
        pass

    @abstractmethod
    async def get_process(self, name: str) -> IProcess | None:
        """
        獲取指定名稱的進程

        Args:
            name: 進程名稱

        Returns:
            Optional[IProcess]: 進程實例，不存在返回 None
        """
        pass

    @abstractmethod
    async def list_processes(self) -> dict[str, IProcess]:
        """
        列出所有管理的進程

        Returns:
            Dict[str, IProcess]: 進程名稱到進程實例的映射
        """
        pass

    @abstractmethod
    async def start_all(self) -> dict[str, bool]:
        """
        啟動所有進程

        Returns:
            Dict[str, bool]: 進程名稱到啟動結果的映射
        """
        pass

    @abstractmethod
    async def stop_all(self, timeout: float = 10.0) -> dict[str, bool]:
        """
        停止所有進程

        Args:
            timeout: 停止超時時間（秒）

        Returns:
            Dict[str, bool]: 進程名稱到停止結果的映射
        """
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, bool]:
        """
        檢查所有進程健康狀態

        Returns:
            Dict[str, bool]: 進程名稱到健康狀態的映射
        """
        pass

    @abstractmethod
    async def restart_process(self, name: str, timeout: float = 10.0) -> bool:
        """
        重啟指定進程

        Args:
            name: 進程名稱
            timeout: 重啟超時時間（秒）

        Returns:
            bool: 重啟是否成功
        """
        pass

    @abstractmethod
    async def get_process_logs(
        self, name: str, lines: int = 100
    ) -> AsyncGenerator[str, None]:
        """
        獲取進程日誌

        Args:
            name: 進程名稱
            lines: 要獲取的行數

        Yields:
            str: 日誌行
        """
        pass
        # AsyncGenerator 需要 yield，這裡是抽象方法的聲明
        yield ""  # 讓 Python 知道這是 generator 函數，提供預設值
