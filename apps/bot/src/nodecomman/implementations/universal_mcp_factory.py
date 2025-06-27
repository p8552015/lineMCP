"""
通用 MCP 服務器工廠實現

提供跨運行時環境的 MCP 服務器創建和管理功能，支援：
- Node.js MCP 服務器（npx、node 命令）
- Python MCP 服務器（python、uvicorn 命令）
- 自動運行時檢測和選擇
- 統一的配置介面

遵循 SOLID 原則：
- SRP: 專注於 MCP 服務器的創建和管理
- OCP: 對新運行時環境擴展開放
- LSP: 實現 IMCPServerFactory 介面契約
- ISP: 介面隔離，避免客戶端依賴不需要的功能
- DIP: 依賴抽象的運行時管理器介面
"""

import asyncio
import os

import structlog

from ..interfaces.runtime_interfaces import IProcess, IRuntimeManager, RuntimeType
from ..interfaces.server_interfaces import (
    IMCPServer,
    IMCPServerFactory,
    MCPConnectionInfo,
    MCPProtocol,
    MCPServerConfig,
    MCPServerInfo,
    MCPServerStatus,
    MCPServerType,
)
from .mcp_server_impl import MCPServerImpl
from .nodejs_runtime_manager import NodeJSRuntimeManager
from .python_runtime_manager import PythonRuntimeManager

logger = structlog.get_logger()


class UniversalMCPServerFactory(IMCPServerFactory):
    """
    通用 MCP 服務器工廠

    提供統一的 MCP 服務器創建介面，支援多種運行時環境。
    這是解決原始 Node.js MCP 配置問題的核心組件。

    遵循 SOLID 原則：
    - SRP: 專注於 MCP 服務器工廠功能
    - LSP: 完全實現 IMCPServerFactory 介面
    - DIP: 依賴 IRuntimeManager 抽象介面
    """

    def __init__(self):
        self._runtime_managers: dict[RuntimeType, IRuntimeManager] = {}
        self._server_registry: dict[str, MCPServerInfo] = {}
        self._active_servers: dict[str, IProcess] = {}

        # 初始化支援的運行時管理器
        self._initialize_runtime_managers()

        # 預定義的 MCP 服務器配置
        self._predefined_configs = self._load_predefined_configs()

    def _initialize_runtime_managers(self):
        """初始化運行時管理器"""
        try:
            # 初始化 Node.js 運行時管理器
            self._runtime_managers[RuntimeType.NODEJS] = NodeJSRuntimeManager()
            logger.info("✅ Node.js 運行時管理器已初始化")

            # 初始化 Python 運行時管理器
            self._runtime_managers[RuntimeType.PYTHON] = PythonRuntimeManager()
            logger.info("✅ Python 運行時管理器已初始化")

        except Exception as e:
            logger.error(f"❌ 初始化運行時管理器失敗: {e}")

    def _load_predefined_configs(self) -> dict[str, MCPServerConfig]:
        """載入預定義的 MCP 服務器配置"""
        return {
            "postgres": MCPServerConfig(
                name="postgres",
                server_type=MCPServerType.DATABASE,
                runtime_type=RuntimeType.NODEJS,
                command="npx",
                args=[
                    "-y",
                    "@modelcontextprotocol/server-postgres",
                    "postgresql://admin:admin@localhost:5432/mydb",
                ],
                env={},
                working_directory=None,
                auto_restart=True,
                description="PostgreSQL MCP 服務器 - 支援資料庫查詢和操作",
            ),
            "sqlite": MCPServerConfig(
                name="sqlite",
                server_type=MCPServerType.DATABASE,
                runtime_type=RuntimeType.NODEJS,
                command="npx",
                args=[
                    "-y",
                    "@modelcontextprotocol/server-sqlite",
                    "--db-path",
                    "./data/sqlite/test.db",
                ],
                env={},
                working_directory=None,
                auto_restart=True,
                description="SQLite MCP 服務器 - 支援輕量級資料庫操作",
            ),
            "filesystem": MCPServerConfig(
                name="filesystem",
                server_type=MCPServerType.FILESYSTEM,
                runtime_type=RuntimeType.NODEJS,
                command="npx",
                args=[
                    "-y",
                    "@modelcontextprotocol/server-filesystem",
                    "--base-path",
                    "/Users/yen/Desktop/lineMCP",
                ],
                env={},
                working_directory=None,
                auto_restart=False,
                description="檔案系統 MCP 服務器 - 支援檔案操作",
            ),
        }

    async def create_server(self, config: MCPServerConfig) -> IMCPServer:
        """創建 MCP 服務器"""
        try:
            logger.info(
                f"🚀 創建 MCP 服務器: {config.name} ({config.runtime_type.value})"
            )

            # 檢查運行時環境是否可用
            runtime_manager = self._runtime_managers.get(config.runtime_type)
            if not runtime_manager:
                raise ValueError(f"不支援的運行時類型: {config.runtime_type}")

            # 驗證運行時環境
            if not await runtime_manager.check_availability():
                raise RuntimeError(f"{config.runtime_type.value} 運行時環境不可用")

            # 驗證命令
            if not await runtime_manager.validate_command(config.command, config.args):
                # 如果是 Node.js 且命令無效，嘗試安裝依賴
                if (
                    config.runtime_type == RuntimeType.NODEJS
                    and config.command == "npx"
                ):
                    package_name = self._extract_package_name(config.args)
                    if package_name:
                        logger.info(f"📦 嘗試安裝 Node.js 套件: {package_name}")
                        if not await runtime_manager.install_dependencies(
                            [package_name]
                        ):
                            logger.warning("⚠️ 套件安裝失敗，但將繼續嘗試執行")

            # 創建進程
            process = await runtime_manager.create_process(
                command=config.command,
                args=config.args,
                env=config.env,
                working_dir=config.working_directory,
            )

            # 創建 MCP 服務器實例
            server = MCPServerImpl(config, runtime_manager, process)

            # 生成服務器資訊用於內部跟蹤
            server_info = MCPServerInfo(
                config=config,
                process_id=None,  # 將在啟動後設置
                status=MCPServerStatus.CREATED,
                connection_info=MCPConnectionInfo(
                    transport="stdio", address="local", port=None
                ),
                runtime_info=await runtime_manager.get_runtime_info(),
                created_at=__import__("time").time(),
                last_health_check=None,
            )

            # 註冊服務器
            self._server_registry[config.name] = server_info
            self._active_servers[config.name] = process

            logger.info(f"✅ MCP 服務器 {config.name} 創建成功")
            return server

        except Exception as e:
            logger.error(f"❌ 創建 MCP 服務器失敗: {e}")
            raise

    async def start_server(self, server_name: str) -> bool:
        """啟動 MCP 服務器"""
        try:
            if server_name not in self._server_registry:
                raise ValueError(f"服務器 {server_name} 不存在")

            process = self._active_servers.get(server_name)
            server_info = self._server_registry[server_name]

            if not process:
                raise RuntimeError(f"服務器 {server_name} 進程不存在")

            logger.info(f"▶️ 啟動 MCP 服務器: {server_name}")

            # 啟動進程
            if await process.start():
                server_info.process_id = process.info.pid
                server_info.status = MCPServerStatus.RUNNING
                server_info.started_at = __import__("time").time()

                logger.info(
                    f"✅ MCP 服務器 {server_name} 啟動成功 (PID: {server_info.process_id})"
                )
                return True
            else:
                server_info.status = MCPServerStatus.FAILED
                logger.error(f"❌ MCP 服務器 {server_name} 啟動失敗")
                return False

        except Exception as e:
            logger.error(f"❌ 啟動 MCP 服務器失敗: {e}")
            if server_name in self._server_registry:
                self._server_registry[server_name].status = MCPServerStatus.FAILED
            return False

    async def stop_server(self, server_name: str) -> bool:
        """停止 MCP 服務器"""
        try:
            if server_name not in self._server_registry:
                return True  # 服務器不存在，視為已停止

            process = self._active_servers.get(server_name)
            server_info = self._server_registry[server_name]

            if not process:
                server_info.status = MCPServerStatus.STOPPED
                return True

            logger.info(f"⏹️ 停止 MCP 服務器: {server_name}")

            # 停止進程
            if await process.stop(timeout=10.0):
                server_info.status = MCPServerStatus.STOPPED
                server_info.stopped_at = __import__("time").time()
                logger.info(f"✅ MCP 服務器 {server_name} 已停止")
                return True
            else:
                logger.warning(f"⚠️ MCP 服務器 {server_name} 停止時出現問題")
                return False

        except Exception as e:
            logger.error(f"❌ 停止 MCP 服務器失敗: {e}")
            return False

    async def restart_server(self, server_name: str) -> bool:
        """重啟 MCP 服務器"""
        try:
            logger.info(f"🔄 重啟 MCP 服務器: {server_name}")

            # 先停止服務器
            await self.stop_server(server_name)

            # 等待一秒確保完全停止
            await asyncio.sleep(1)

            # 重新啟動
            return await self.start_server(server_name)

        except Exception as e:
            logger.error(f"❌ 重啟 MCP 服務器失敗: {e}")
            return False

    async def get_server_info(self, server_name: str) -> MCPServerInfo | None:
        """獲取服務器資訊"""
        return self._server_registry.get(server_name)

    async def list_servers(self) -> list[MCPServerInfo]:
        """列出所有服務器"""
        return list(self._server_registry.values())

    async def health_check(self, server_name: str) -> bool:
        """健康檢查"""
        try:
            if server_name not in self._server_registry:
                return False

            process = self._active_servers.get(server_name)
            server_info = self._server_registry[server_name]

            if not process:
                server_info.status = MCPServerStatus.STOPPED
                return False

            # 檢查進程是否存活
            is_alive = await process.is_alive()

            if is_alive:
                server_info.status = MCPServerStatus.RUNNING
                server_info.last_health_check = __import__("time").time()
                return True
            else:
                server_info.status = MCPServerStatus.STOPPED
                return False

        except Exception as e:
            logger.error(f"❌ 健康檢查失敗: {e}")
            return False

    async def get_predefined_config(self, config_name: str) -> MCPServerConfig | None:
        """獲取預定義配置"""
        return self._predefined_configs.get(config_name)

    async def list_predefined_configs(self) -> list[str]:
        """列出所有預定義配置名稱"""
        return list(self._predefined_configs.keys())

    async def create_from_predefined(
        self, config_name: str, **overrides
    ) -> MCPServerInfo:
        """從預定義配置創建服務器"""
        base_config = self._predefined_configs.get(config_name)
        if not base_config:
            raise ValueError(f"預定義配置 {config_name} 不存在")

        # 應用覆蓋設置
        config_dict = base_config.__dict__.copy()
        config_dict.update(overrides)

        # 創建新配置
        modified_config = MCPServerConfig(**config_dict)

        return await self.create_server(modified_config)

    async def cleanup_all_servers(self) -> dict[str, bool]:
        """清理所有服務器"""
        results = {}

        for server_name in list(self._server_registry.keys()):
            try:
                result = await self.stop_server(server_name)
                results[server_name] = result
            except Exception as e:
                logger.error(f"❌ 清理服務器 {server_name} 失敗: {e}")
                results[server_name] = False

        # 清理註冊表
        self._server_registry.clear()
        self._active_servers.clear()

        logger.info("🧹 所有 MCP 服務器已清理")
        return results

    def _extract_package_name(self, args: list[str]) -> str | None:
        """從 npx 參數中提取套件名稱"""
        try:
            # 跳過 -y 等選項
            for arg in args:
                if not arg.startswith("-") and arg != "npx":
                    return arg
            return None
        except Exception:
            return None

    async def get_supported_runtimes(self) -> list[RuntimeType]:
        """獲取支援的運行時類型"""
        available_runtimes = []

        for runtime_type, manager in self._runtime_managers.items():
            try:
                if await manager.check_availability():
                    available_runtimes.append(runtime_type)
            except Exception as e:
                logger.warning(f"⚠️ 檢查運行時 {runtime_type} 失敗: {e}")

        return available_runtimes

    async def validate_config(self, config: MCPServerConfig) -> list[str]:
        """驗證配置"""
        issues = []

        try:
            # 檢查運行時支援
            if config.runtime_type not in self._runtime_managers:
                issues.append(f"不支援的運行時類型: {config.runtime_type}")
                return issues

            # 檢查運行時可用性
            runtime_manager = self._runtime_managers[config.runtime_type]
            if not await runtime_manager.check_availability():
                issues.append(f"{config.runtime_type.value} 運行時環境不可用")

            # 檢查命令有效性
            if not await runtime_manager.validate_command(config.command, config.args):
                issues.append(f"命令無效: {config.command} {' '.join(config.args)}")

            # 檢查工作目錄
            if config.working_directory and not os.path.exists(
                config.working_directory
            ):
                issues.append(f"工作目錄不存在: {config.working_directory}")

        except Exception as e:
            issues.append(f"配置驗證失敗: {e}")

        return issues

    async def get_supported_protocols(self) -> list[MCPProtocol]:
        """獲取支援的協議類型"""
        return [MCPProtocol.STDIO]  # 目前只支援 STDIO

    async def get_supported_server_types(self) -> list[MCPServerType]:
        """獲取支援的服務器類型"""
        return [
            MCPServerType.DATABASE,
            MCPServerType.FILESYSTEM,
            MCPServerType.POSTGRES,
            MCPServerType.SQLITE,
        ]

    async def get_default_config(
        self, server_type: MCPServerType, runtime_type: RuntimeType
    ) -> MCPServerConfig:
        """獲取預設配置"""
        if server_type == MCPServerType.POSTGRES and runtime_type == RuntimeType.NODEJS:
            return self._predefined_configs["postgres"]
        elif server_type == MCPServerType.SQLITE and runtime_type == RuntimeType.NODEJS:
            return self._predefined_configs["sqlite"]
        elif (
            server_type == MCPServerType.FILESYSTEM
            and runtime_type == RuntimeType.NODEJS
        ):
            return self._predefined_configs["filesystem"]
        else:
            # 返回基本配置
            return MCPServerConfig(
                name=f"default_{server_type.value}",
                server_type=server_type,
                runtime_type=runtime_type,
                command="node" if runtime_type == RuntimeType.NODEJS else "python",
                args=["--version"],
                description=f"預設 {server_type.value} 配置",
            )

    async def can_create(self, config: MCPServerConfig) -> bool:
        """檢查是否可以創建指定配置的服務器"""
        try:
            # 檢查運行時支援
            if config.runtime_type not in self._runtime_managers:
                return False

            # 檢查運行時可用性
            runtime_manager = self._runtime_managers[config.runtime_type]
            if not await runtime_manager.check_availability():
                return False

            # 檢查配置有效性
            validation_issues = await self.validate_config(config)
            return len(validation_issues) == 0

        except Exception:
            return False
