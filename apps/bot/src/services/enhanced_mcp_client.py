"""
增強型 MCP 客戶端

整合 nodecomman 架構的 MCP 客戶端實現，提供：
- 運行時環境檢測和驗證
- 多運行時支援 (Node.js + Python)
- 進程生命週期管理整合
- 向後兼容現有 ProductionMCPClient 介面

設計原則：
- 最小變更：保持現有 API 不變
- 漸進升級：可選擇性啟用新功能
- 錯誤隔離：新功能失敗時回退到原有機制
"""

import time
from typing import Any

import structlog

from ..config.mcp_config import get_mcp_config
from .mcp_connection_pool import get_connection_pool
from .production_mcp_client import ProductionMCPClient, get_production_mcp_client

# 整合 nodecomman 架構
try:
    from ..nodecomman.implementations.process_lifecycle_manager import (
        LifecycleConfig,
        ProcessLifecycleManager,
        RestartPolicy,
    )
    from ..nodecomman.implementations.universal_mcp_factory import (
        UniversalMCPServerFactory,
    )
    from ..nodecomman.interfaces.runtime_interfaces import RuntimeType
    from ..nodecomman.interfaces.server_interfaces import MCPServerConfig, MCPServerType

    NODECOMMAN_AVAILABLE = True
except ImportError as e:
    structlog.get_logger().warning(f"⚠️ nodecomman 架構不可用，使用現有機制: {e}")
    NODECOMMAN_AVAILABLE = False

logger = structlog.get_logger()


class EnhancedMCPClient:
    """
    增強型 MCP 客戶端

    整合 nodecomman 架構的優勢，同時保持與現有系統的兼容性。
    """

    def __init__(self, use_nodecomman: bool = True, fallback_enabled: bool = True):
        """
        初始化增強型 MCP 客戶端

        Args:
            use_nodecomman: 是否使用 nodecomman 架構
            fallback_enabled: 當 nodecomman 失敗時是否回退到原有機制
        """
        self.use_nodecomman = use_nodecomman and NODECOMMAN_AVAILABLE
        self.fallback_enabled = fallback_enabled
        self.config = get_mcp_config()
        self.connection_pool = get_connection_pool()

        # 原有客戶端（作為回退機制）
        self._production_client: ProductionMCPClient | None = None

        # nodecomman 組件
        self._mcp_factory: UniversalMCPServerFactory | None = None
        self._lifecycle_manager: ProcessLifecycleManager | None = None
        self._managed_servers: dict[str, Any] = {}

        # 初始化
        self._initialize_components()

        logger.info(
            f"🚀 增強型 MCP 客戶端初始化完成 (nodecomman: {self.use_nodecomman})"
        )

    def _initialize_components(self):
        """初始化各組件"""
        try:
            if self.use_nodecomman:
                self._mcp_factory = UniversalMCPServerFactory()
                self._lifecycle_manager = ProcessLifecycleManager()
                logger.info("✅ nodecomman 組件初始化成功")

            # 始終初始化原有客戶端作為備用
            if self.fallback_enabled:
                self._production_client = get_production_mcp_client()
                logger.info("✅ 原有 ProductionMCPClient 已備用")

        except Exception as e:
            logger.error(f"❌ 組件初始化失敗: {e}")
            if self.fallback_enabled:
                self.use_nodecomman = False
                logger.info("🔄 已回退到原有機制")

    async def connect_to_server(self, server_name: str = "postgres") -> bool:
        """
        連接到 MCP 服務器

        Args:
            server_name: 服務器名稱

        Returns:
            bool: 連接是否成功
        """
        try:
            if self.use_nodecomman:
                return await self._connect_with_nodecomman(server_name)
            else:
                return await self._connect_with_fallback(server_name)

        except Exception as e:
            logger.error(f"❌ 連接服務器失敗: {e}")

            # 嘗試回退機制
            if self.use_nodecomman and self.fallback_enabled:
                logger.info("🔄 嘗試回退到原有連接機制")
                return await self._connect_with_fallback(server_name)

            return False

    async def _connect_with_nodecomman(self, server_name: str) -> bool:
        """使用 nodecomman 架構連接"""
        try:
            logger.info(f"🔗 使用 nodecomman 架構連接: {server_name}")

            # 檢查預定義配置
            config = await self._mcp_factory.get_predefined_config(server_name)
            if not config:
                logger.error(f"❌ 未找到 {server_name} 的配置")
                return False

            # 驗證運行時環境
            validation_issues = await self._mcp_factory.validate_config(config)
            if validation_issues:
                logger.warning(f"⚠️ 配置驗證問題: {validation_issues}")
                # 非致命問題，繼續嘗試

            # 檢查是否可以創建服務器
            if not await self._mcp_factory.can_create(config):
                logger.error(f"❌ 無法創建 {server_name} 服務器")
                return False

            # 創建服務器
            server = await self._mcp_factory.create_server(config)

            # 註冊到生命週期管理器
            lifecycle_config = LifecycleConfig(
                health_check_interval=30.0,
                restart_policy=RestartPolicy.ON_FAILURE,
                max_restart_attempts=3,
            )

            process = server.process
            if process and await self._lifecycle_manager.register_process(
                server_name, process, lifecycle_config, config
            ):
                # 啟動服務器
                if await self._lifecycle_manager.start_process(server_name):
                    self._managed_servers[server_name] = server
                    logger.info(f"✅ nodecomman 服務器 {server_name} 連接成功")
                    return True

            logger.error(f"❌ nodecomman 服務器 {server_name} 連接失敗")
            return False

        except Exception as e:
            logger.error(f"❌ nodecomman 連接過程失敗: {e}")
            return False

    async def _connect_with_fallback(self, server_name: str) -> bool:
        """使用原有機制連接"""
        try:
            logger.info(f"🔄 使用原有機制連接: {server_name}")

            if not self._production_client:
                self._production_client = get_production_mcp_client()

            return await self._production_client.connect_to_server(server_name)

        except Exception as e:
            logger.error(f"❌ 原有機制連接失敗: {e}")
            return False

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        parameters: dict[str, Any],
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """
        調用 MCP 工具

        Args:
            server_name: 服務器名稱
            tool_name: 工具名稱
            parameters: 工具參數
            timeout: 超時時間

        Returns:
            Dict[str, Any]: 工具執行結果
        """
        try:
            if self.use_nodecomman and server_name in self._managed_servers:
                return await self._call_tool_nodecomman(
                    server_name, tool_name, parameters, timeout
                )
            else:
                return await self._call_tool_fallback(
                    server_name, tool_name, parameters, timeout
                )

        except Exception as e:
            logger.error(f"❌ 工具調用失敗: {e}")

            # 嘗試回退機制
            if (
                self.use_nodecomman
                and server_name in self._managed_servers
                and self.fallback_enabled
            ):
                logger.info("🔄 嘗試回退到原有工具調用機制")
                return await self._call_tool_fallback(
                    server_name, tool_name, parameters, timeout
                )

            return {"success": False, "error": str(e)}

    async def _call_tool_nodecomman(
        self,
        server_name: str,
        tool_name: str,
        parameters: dict[str, Any],
        timeout: float | None,
    ) -> dict[str, Any]:
        """使用 nodecomman 架構調用工具"""
        try:
            server = self._managed_servers[server_name]
            connection = await server.get_connection()

            from ..nodecomman.interfaces.server_interfaces import MCPToolCall

            tool_call = MCPToolCall(
                tool_name=tool_name,
                parameters=parameters,
                call_id=f"enhanced_{int(time.time()*1000)}",
            )

            result = await connection.call_tool(tool_call)

            if result.success:
                logger.info(f"✅ nodecomman 工具調用成功: {tool_name}")
                return {"success": True, "data": result.result}
            else:
                logger.error(f"❌ nodecomman 工具調用失敗: {result.error}")
                return {"success": False, "error": result.error}

        except Exception as e:
            logger.error(f"❌ nodecomman 工具調用過程失敗: {e}")
            return {"success": False, "error": str(e)}

    async def _call_tool_fallback(
        self,
        server_name: str,
        tool_name: str,
        parameters: dict[str, Any],
        timeout: float | None,
    ) -> dict[str, Any]:
        """使用原有機制調用工具"""
        try:
            if not self._production_client:
                self._production_client = get_production_mcp_client()

            return await self._production_client.call_tool(
                server_name, tool_name, parameters, timeout
            )

        except Exception as e:
            logger.error(f"❌ 原有機制工具調用失敗: {e}")
            return {"success": False, "error": str(e)}

    async def list_tools(self, server_name: str) -> list[dict[str, Any]]:
        """列出可用工具"""
        try:
            if self.use_nodecomman and server_name in self._managed_servers:
                server = self._managed_servers[server_name]
                connection = await server.get_connection()
                tools = await connection.list_tools()

                return [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.input_schema,
                    }
                    for tool in tools
                ]
            else:
                # 使用原有機制的簡化實現
                return [{"name": "query", "description": "執行資料庫查詢"}]

        except Exception as e:
            logger.error(f"❌ 列出工具失敗: {e}")
            return []

    async def get_server_status(self, server_name: str) -> dict[str, Any]:
        """獲取服務器狀態"""
        try:
            if self.use_nodecomman and self._lifecycle_manager:
                status = await self._lifecycle_manager.get_process_status(server_name)
                if status:
                    return {
                        "server_name": server_name,
                        "using_nodecomman": True,
                        "status": status,
                    }

            # 使用原有機制檢查
            if self._production_client:
                # 簡化的狀態檢查
                return {
                    "server_name": server_name,
                    "using_nodecomman": False,
                    "status": "unknown",  # 原有機制沒有詳細狀態
                }

            return {"server_name": server_name, "status": "not_connected"}

        except Exception as e:
            logger.error(f"❌ 獲取服務器狀態失敗: {e}")
            return {"server_name": server_name, "status": "error", "error": str(e)}

    async def get_system_info(self) -> dict[str, Any]:
        """獲取系統資訊"""
        try:
            info = {
                "enhanced_client": True,
                "nodecomman_available": NODECOMMAN_AVAILABLE,
                "using_nodecomman": self.use_nodecomman,
                "fallback_enabled": self.fallback_enabled,
                "managed_servers": list(self._managed_servers.keys()),
                "supported_runtimes": [],
            }

            if self.use_nodecomman and self._mcp_factory:
                try:
                    runtimes = await self._mcp_factory.get_supported_runtimes()
                    info["supported_runtimes"] = [rt.value for rt in runtimes]
                except Exception:
                    pass

            return info

        except Exception as e:
            logger.error(f"❌ 獲取系統資訊失敗: {e}")
            return {"error": str(e)}

    @property
    def server_configs(self) -> dict[str, Any]:
        """獲取服務器配置字典 - 提供 API 一致性"""
        if self._production_client:
            return self._production_client.server_configs
        else:
            # 直接從配置管理器獲取
            config_summary = self.config.get_config_summary()
            return config_summary.get("servers", {})

    def list_servers(self) -> list[str]:
        """列出所有可用的服務器名稱 - 提供 API 一致性"""
        return self.config.list_servers()

    async def close_all_connections(self) -> bool:
        """關閉所有連接"""
        try:
            success = True

            # 關閉 nodecomman 管理的服務器
            if self._lifecycle_manager:
                try:
                    await self._lifecycle_manager.shutdown_all(timeout=30.0)
                    logger.info("✅ nodecomman 服務器已關閉")
                except Exception as e:
                    logger.error(f"❌ 關閉 nodecomman 服務器失敗: {e}")
                    success = False

            # 關閉原有客戶端
            if self._production_client:
                try:
                    await self._production_client.close_all_connections()
                    logger.info("✅ 原有客戶端已關閉")
                except Exception as e:
                    logger.error(f"❌ 關閉原有客戶端失敗: {e}")
                    success = False

            # 清理工廠
            if self._mcp_factory:
                try:
                    await self._mcp_factory.cleanup_all_servers()
                    logger.info("✅ MCP 工廠已清理")
                except Exception as e:
                    logger.error(f"❌ 清理 MCP 工廠失敗: {e}")
                    success = False

            self._managed_servers.clear()

            logger.info("🧹 增強型 MCP 客戶端已關閉")
            return success

        except Exception as e:
            logger.error(f"❌ 關閉增強型 MCP 客戶端失敗: {e}")
            return False


# 單例管理
_enhanced_mcp_client: EnhancedMCPClient | None = None


def get_enhanced_mcp_client(
    use_nodecomman: bool = True, fallback_enabled: bool = True
) -> EnhancedMCPClient:
    """
    獲取增強型 MCP 客戶端單例

    Args:
        use_nodecomman: 是否使用 nodecomman 架構
        fallback_enabled: 是否啟用回退機制

    Returns:
        EnhancedMCPClient: 增強型 MCP 客戶端實例
    """
    global _enhanced_mcp_client

    if _enhanced_mcp_client is None:
        _enhanced_mcp_client = EnhancedMCPClient(use_nodecomman, fallback_enabled)

    return _enhanced_mcp_client
