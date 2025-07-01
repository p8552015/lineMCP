"""
增強型 MCP 配置管理

整合 nodecomman 架構的配置檢測和驗證功能，提供：
- 自動運行時環境檢測
- 多運行時配置支援
- 配置驗證和最佳化建議
- 向後兼容現有配置格式

設計原則：
- 無縫升級：不破壞現有配置
- 智能檢測：自動發現最佳配置
- 錯誤容錯：配置失敗時提供建議
"""

import time
from dataclasses import asdict, dataclass, field
from typing import Any

import structlog

from .mcp_config import MCPConfigManager, get_mcp_config

# 整合 nodecomman 架構
try:
    from ..nodecomman.implementations.nodejs_runtime_manager import NodeJSRuntimeManager
    from ..nodecomman.implementations.python_runtime_manager import PythonRuntimeManager
    from ..nodecomman.implementations.universal_mcp_factory import (
        UniversalMCPServerFactory,
    )
    from ..nodecomman.interfaces.runtime_interfaces import RuntimeType
    from ..nodecomman.interfaces.server_interfaces import (
        MCPServerConfig as NodecommanServerConfig,
    )

    NODECOMMAN_AVAILABLE = True
except ImportError:
    NODECOMMAN_AVAILABLE = False

logger = structlog.get_logger()


@dataclass
class RuntimeEnvironmentInfo:
    """運行時環境資訊"""

    runtime_type: str
    available: bool
    version: str
    executable_path: str
    package_manager: str | None = None
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class ServerConfigAnalysis:
    """服務器配置分析結果"""

    server_name: str
    current_config: dict[str, Any]
    is_valid: bool
    runtime_info: RuntimeEnvironmentInfo | None = None
    validation_issues: list[str] = field(default_factory=list)
    optimization_suggestions: list[str] = field(default_factory=list)
    nodecomman_config: dict[str, Any] | None = None


class EnhancedMCPConfig:
    """
    增強型 MCP 配置管理器

    在現有 MCPConfig 基礎上添加 nodecomman 架構的智能檢測和驗證功能。
    """

    def __init__(self, enable_nodecomman: bool = True):
        """
        初始化增強型配置管理器

        Args:
            enable_nodecomman: 是否啟用 nodecomman 功能
        """
        self.enable_nodecomman = enable_nodecomman and NODECOMMAN_AVAILABLE
        self.base_config = get_mcp_config()

        # nodecomman 組件
        self._mcp_factory: UniversalMCPServerFactory | None = None
        self._nodejs_runtime: NodeJSRuntimeManager | None = None
        self._python_runtime: PythonRuntimeManager | None = None

        # 分析結果緩存
        self._environment_analysis: dict[str, RuntimeEnvironmentInfo] = {}
        self._config_analysis: dict[str, ServerConfigAnalysis] = {}

        # 初始化
        if self.enable_nodecomman:
            self._initialize_nodecomman()

        logger.info(
            f"🔧 增強型 MCP 配置管理器初始化完成 (nodecomman: {self.enable_nodecomman})"
        )

    def _initialize_nodecomman(self):
        """初始化 nodecomman 組件"""
        try:
            self._mcp_factory = UniversalMCPServerFactory()
            self._nodejs_runtime = NodeJSRuntimeManager()
            self._python_runtime = PythonRuntimeManager()
            logger.info("✅ nodecomman 配置組件初始化成功")
        except Exception as e:
            logger.error(f"❌ nodecomman 配置組件初始化失敗: {e}")
            self.enable_nodecomman = False

    async def analyze_runtime_environments(self) -> dict[str, RuntimeEnvironmentInfo]:
        """分析所有運行時環境"""
        if not self.enable_nodecomman:
            return {}

        try:
            environments = {}

            # 分析 Node.js 環境
            nodejs_info = await self._analyze_nodejs_environment()
            if nodejs_info:
                environments["nodejs"] = nodejs_info

            # 分析 Python 環境
            python_info = await self._analyze_python_environment()
            if python_info:
                environments["python"] = python_info

            self._environment_analysis = environments
            return environments

        except Exception as e:
            logger.error(f"❌ 運行時環境分析失敗: {e}")
            return {}

    async def _analyze_nodejs_environment(self) -> RuntimeEnvironmentInfo | None:
        """分析 Node.js 環境"""
        try:
            if not self._nodejs_runtime:
                return None

            is_available = await self._nodejs_runtime.check_availability()
            runtime_info = await self._nodejs_runtime.get_runtime_info()

            issues: list[Any] = []
            recommendations: list[Any] = []

            if not is_available:
                issues.append("Node.js 運行時不可用")
                recommendations.append("請安裝 Node.js v16 或更高版本")
            else:
                # 檢查版本
                version = runtime_info.version
                if "v14" in version or "v12" in version:
                    issues.append(f"Node.js 版本過舊: {version}")
                    recommendations.append("建議升級到 Node.js v18 LTS")

                # 檢查 npm
                npm_info = runtime_info.env_variables.get("npm_version", "")
                if not npm_info:
                    issues.append("npm 不可用")
                    recommendations.append("請確保 npm 已正確安裝")

            return RuntimeEnvironmentInfo(
                runtime_type="nodejs",
                available=is_available,
                version=runtime_info.version,
                executable_path=runtime_info.executable_path,
                package_manager=(
                    "npm" if "npm" in runtime_info.env_variables else None
                ),
                issues=issues,
                recommendations=recommendations,
            )

        except Exception as e:
            logger.error(f"❌ Node.js 環境分析失敗: {e}")
            return RuntimeEnvironmentInfo(
                runtime_type="nodejs",
                available=False,
                version="unknown",
                executable_path="unknown",
                issues=[f"分析失敗: {e}"],
                recommendations=["檢查 Node.js 安裝"],
            )

    async def _analyze_python_environment(self) -> RuntimeEnvironmentInfo | None:
        """分析 Python 環境"""
        try:
            if not self._python_runtime:
                return None

            is_available = await self._python_runtime.check_availability()
            runtime_info = await self._python_runtime.get_runtime_info()

            issues: list[Any] = []
            recommendations: list[Any] = []

            if not is_available:
                issues.append("Python 運行時不可用")
                recommendations.append("請安裝 Python 3.8 或更高版本")
            else:
                # 檢查版本
                version = runtime_info.version
                if "3.7" in version or "3.6" in version:
                    issues.append(f"Python 版本過舊: {version}")
                    recommendations.append("建議升級到 Python 3.11+")

                # 檢查包管理器
                if not runtime_info.package_manager:
                    issues.append("pip 不可用")
                    recommendations.append("請確保 pip 已正確安裝")

            return RuntimeEnvironmentInfo(
                runtime_type="python",
                available=is_available,
                version=runtime_info.version,
                executable_path=runtime_info.executable_path,
                package_manager=runtime_info.package_manager,
                issues=issues,
                recommendations=recommendations,
            )

        except Exception as e:
            logger.error(f"❌ Python 環境分析失敗: {e}")
            return RuntimeEnvironmentInfo(
                runtime_type="python",
                available=False,
                version="unknown",
                executable_path="unknown",
                issues=[f"分析失敗: {e}"],
                recommendations=["檢查 Python 安裝"],
            )

    async def analyze_server_config(
        self, server_name: str
    ) -> ServerConfigAnalysis | None:
        """分析特定服務器配置"""
        try:
            # 獲取當前配置
            current_config = self.base_config.get_server_config(server_name)
            if not current_config:
                return ServerConfigAnalysis(
                    server_name=server_name,
                    current_config={},
                    is_valid=False,
                    validation_issues=[f"服務器 {server_name} 配置不存在"],
                )

            # 基本分析
            analysis = ServerConfigAnalysis(
                server_name=server_name,
                current_config=asdict(current_config),
                is_valid=True,
            )

            if not self.enable_nodecomman:
                return analysis

            # 使用 nodecomman 進行深度分析
            await self._enhance_config_analysis(analysis)

            self._config_analysis[server_name] = analysis
            return analysis

        except Exception as e:
            logger.error(f"❌ 服務器配置分析失敗: {e}")
            return ServerConfigAnalysis(
                server_name=server_name,
                current_config={},
                is_valid=False,
                validation_issues=[f"分析失敗: {e}"],
            )

    async def _enhance_config_analysis(self, analysis: ServerConfigAnalysis):
        """使用 nodecomman 增強配置分析"""
        try:
            server_name = analysis.server_name

            # 檢查是否有對應的 nodecomman 配置
            if self._mcp_factory is None:
                return

            nodecomman_config = await self._mcp_factory.get_predefined_config(
                server_name
            )
            if nodecomman_config:
                analysis.nodecomman_config = {
                    "name": nodecomman_config.name,
                    "runtime_type": nodecomman_config.runtime_type.value,
                    "command": nodecomman_config.command,
                    "args": nodecomman_config.args,
                    "description": nodecomman_config.description,
                }

                # 驗證配置
                validation_issues = await self._mcp_factory.validate_config(
                    nodecomman_config
                )
                analysis.validation_issues.extend(validation_issues)

                # 檢查運行時環境
                runtime_type = nodecomman_config.runtime_type
                if runtime_type == RuntimeType.NODEJS:
                    analysis.runtime_info = self._environment_analysis.get("nodejs")
                elif runtime_type == RuntimeType.PYTHON:
                    analysis.runtime_info = self._environment_analysis.get("python")

                # 生成優化建議
                await self._generate_optimization_suggestions(
                    analysis, nodecomman_config
                )
            else:
                analysis.validation_issues.append(
                    f"nodecomman 中無 {server_name} 預定義配置"
                )
                analysis.optimization_suggestions.append(
                    "考慮為此服務器添加 nodecomman 配置"
                )

            # 最終有效性檢查
            analysis.is_valid = len(analysis.validation_issues) == 0

        except Exception as e:
            logger.error(f"❌ 增強配置分析失敗: {e}")
            analysis.validation_issues.append(f"增強分析失敗: {e}")

    async def _generate_optimization_suggestions(
        self, analysis: ServerConfigAnalysis, nodecomman_config: NodecommanServerConfig
    ):
        """生成優化建議"""
        try:
            current = analysis.current_config
            nodecomman = analysis.nodecomman_config

            # 檢查 nodecomman 是否可用
            if nodecomman is None:
                return

            # 比較命令和參數
            if current.get("command") != nodecomman.get("command"):
                analysis.optimization_suggestions.append(
                    f"建議更新命令: {current.get('command')} → "
                    f"{nodecomman.get('command')}"
                )

            if current.get("args") != nodecomman.get("args"):
                analysis.optimization_suggestions.append(
                    f"建議更新參數: {current.get('args')} → {nodecomman.get('args')}"
                )

            # 檢查運行時特定建議
            if analysis.runtime_info and not analysis.runtime_info.available:
                analysis.optimization_suggestions.append(
                    f"需要安裝 {analysis.runtime_info.runtime_type} 運行時環境"
                )

            # 檢查是否可以創建
            if self._mcp_factory is not None:
                can_create = await self._mcp_factory.can_create(nodecomman_config)
            if not can_create:
                analysis.optimization_suggestions.append(
                    "當前環境無法創建此服務器，請檢查依賴"
                )

        except Exception as e:
            logger.error(f"❌ 生成優化建議失敗: {e}")

    async def get_comprehensive_report(self) -> dict[str, Any]:
        """獲取綜合分析報告"""
        try:
            # 分析運行時環境
            environments = await self.analyze_runtime_environments()

            # 分析所有服務器配置
            servers_analysis = {}
            for server_name in self.base_config.list_servers():
                analysis = await self.analyze_server_config(server_name)
                if analysis:
                    servers_analysis[server_name] = asdict(analysis)

            # 系統整體評估
            system_health = self._evaluate_system_health(environments, servers_analysis)

            return {
                "timestamp": int(time.time()),
                "nodecomman_enabled": self.enable_nodecomman,
                "system_health": system_health,
                "runtime_environments": {k: asdict(v) for k, v in environments.items()},
                "servers_analysis": servers_analysis,
                "recommendations": self._generate_system_recommendations(
                    environments, servers_analysis
                ),
            }

        except Exception as e:
            logger.error(f"❌ 生成綜合報告失敗: {e}")
            return {"error": str(e)}

    def _evaluate_system_health(
        self,
        environments: dict[str, RuntimeEnvironmentInfo],
        servers: dict[str, dict[str, Any]],
    ) -> str:
        """評估系統整體健康狀況"""
        total_issues = 0

        # 統計運行時問題
        for env in environments.values():
            total_issues += len(env.issues)

        # 統計服務器配置問題
        valid_servers = 0
        for server_data in servers.values():
            if server_data.get("is_valid", False):
                valid_servers += 1
            total_issues += len(server_data.get("validation_issues", []))

        if total_issues == 0:
            return "excellent"
        elif total_issues <= 2:
            return "good"
        elif total_issues <= 5:
            return "fair"
        else:
            return "poor"

    def _generate_system_recommendations(
        self,
        environments: dict[str, RuntimeEnvironmentInfo],
        servers: dict[str, dict[str, Any]],
    ) -> list[str]:
        """生成系統級建議"""
        recommendations: list[str] = []

        # 運行時建議
        for env in environments.values():
            recommendations.extend(env.recommendations)

        # 服務器配置建議
        for server_data in servers.values():
            recommendations.extend(server_data.get("optimization_suggestions", []))

        # 去重並排序
        unique_recommendations = list(set(recommendations))
        unique_recommendations.sort()

        return unique_recommendations

    def get_base_config(self) -> MCPConfigManager:
        """獲取基礎配置對象"""
        return self.base_config

    async def get_optimal_config_for_server(
        self, server_name: str
    ) -> dict[str, Any] | None:
        """獲取服務器的最佳配置建議"""
        try:
            analysis = await self.analyze_server_config(server_name)
            if not analysis or not analysis.nodecomman_config:
                return None

            # 基於分析結果生成最佳配置
            optimal_config = analysis.nodecomman_config.copy()

            # 添加運行時特定優化
            if analysis.runtime_info and analysis.runtime_info.available:
                optimal_config["runtime_verified"] = True
                optimal_config["runtime_path"] = analysis.runtime_info.executable_path

            return optimal_config

        except Exception as e:
            logger.error(f"❌ 獲取最佳配置失敗: {e}")
            return None


# 單例管理
_enhanced_mcp_config: EnhancedMCPConfig | None = None


def get_enhanced_mcp_config(enable_nodecomman: bool = True) -> EnhancedMCPConfig:
    """
    獲取增強型 MCP 配置管理器單例

    Args:
        enable_nodecomman: 是否啟用 nodecomman 功能

    Returns:
        EnhancedMCPConfig: 增強型配置管理器實例
    """
    global _enhanced_mcp_config

    if _enhanced_mcp_config is None:
        _enhanced_mcp_config = EnhancedMCPConfig(enable_nodecomman)

    return _enhanced_mcp_config
