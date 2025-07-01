"""
Node.js 運行時管理器實現

實現 IRuntimeManager 介面，提供 Node.js 環境的檢查、依賴安裝和進程管理功能。
遵循 SOLID 原則：
- SRP: 專注於 Node.js 運行時環境管理
- LSP: 完全符合 IRuntimeManager 契約
- DIP: 依賴抽象介面而非具體實現
"""

import asyncio
import os
import shutil
from typing import Any

import structlog

from ..interfaces.runtime_interfaces import (
    IProcess,
    IRuntimeManager,
    ProcessInfo,
    ProcessStatus,
    RuntimeInfo,
    RuntimeType,
)

logger = structlog.get_logger()


class NodeJSProcess(IProcess):
    """
    Node.js 進程實現

    遵循 SRP 原則：專注於單一 Node.js 進程的管理
    """

    def __init__(
        self,
        command: str,
        args: list[str],
        env: dict[str, str] | None = None,
        working_dir: str | None = None,
    ):
        self._command = command
        self._args = args
        self._env = env or {}
        self._working_dir = working_dir
        self._process: asyncio.subprocess.Process | None = None
        self._start_time: float | None = None
        self._end_time: float | None = None

        # 初始化進程資訊
        self._info = ProcessInfo(
            pid=None,
            status=ProcessStatus.STOPPED,
            command=command,
            args=args,
            env=self._env,
            working_dir=working_dir or os.getcwd(),
        )

    @property
    def info(self) -> ProcessInfo:
        """獲取進程資訊"""
        if self._process:
            self._info.pid = self._process.pid
            self._info.return_code = self._process.returncode

        self._info.start_time = self._start_time
        self._info.end_time = self._end_time

        return self._info

    async def start(self) -> bool:
        """啟動 Node.js 進程"""
        try:
            if self._process and await self.is_alive():
                logger.warning(f"進程已在運行: {self._command}")
                return True

            logger.info(f"啟動 Node.js 進程: {self._command} {' '.join(self._args)}")

            # 準備環境變數
            full_env = {**os.environ, **self._env}

            # 啟動進程
            self._info.status = ProcessStatus.STARTING
            self._start_time = __import__("time").time()

            self._process = await asyncio.create_subprocess_exec(
                self._command,
                *self._args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE,
                env=full_env,
                cwd=self._working_dir,
            )

            self._info.pid = self._process.pid
            self._info.status = ProcessStatus.RUNNING
            self._info.start_time = self._start_time

            logger.info(f"✅ Node.js 進程已啟動: PID={self._process.pid}")
            return True

        except FileNotFoundError:
            logger.error(f"❌ 找不到命令: {self._command}")
            self._info.status = ProcessStatus.FAILED
            return False
        except Exception as e:
            logger.error(f"❌ 啟動進程失敗: {e}")
            self._info.status = ProcessStatus.FAILED
            return False

    async def stop(self, timeout: float = 10.0) -> bool:
        """停止進程"""
        if not self._process:
            return True

        try:
            logger.info(f"停止 Node.js 進程: PID={self._process.pid}")

            self._info.status = ProcessStatus.STOPPING

            # 優雅停止
            self._process.terminate()

            try:
                await asyncio.wait_for(self._process.wait(), timeout=timeout)
                logger.info("✅ 進程已優雅停止")
            except TimeoutError:
                logger.warning("⚠️ 優雅停止超時，強制終止")
                await self.kill()

            self._end_time = __import__("time").time()
            self._info.status = ProcessStatus.STOPPED
            self._info.end_time = self._end_time
            self._info.return_code = self._process.returncode

            return True

        except Exception as e:
            logger.error(f"❌ 停止進程失敗: {e}")
            return False

    async def kill(self) -> bool:
        """強制終止進程"""
        if not self._process:
            return True

        try:
            logger.info(f"強制終止進程: PID={self._process.pid}")
            self._process.kill()
            await self._process.wait()

            self._end_time = __import__("time").time()
            self._info.status = ProcessStatus.STOPPED
            self._info.end_time = self._end_time
            self._info.return_code = self._process.returncode

            logger.info("✅ 進程已強制終止")
            return True

        except Exception as e:
            logger.error(f"❌ 強制終止失敗: {e}")
            return False

    async def wait(self, timeout: float | None = None) -> int | None:
        """等待進程結束"""
        if not self._process:
            return None

        try:
            if timeout:
                await asyncio.wait_for(self._process.wait(), timeout=timeout)
            else:
                await self._process.wait()

            return self._process.returncode

        except TimeoutError:
            return None
        except Exception as e:
            logger.error(f"❌ 等待進程失敗: {e}")
            return None

    async def is_alive(self) -> bool:
        """檢查進程是否存活"""
        if not self._process:
            return False

        return self._process.returncode is None

    async def send_signal(self, signal: int) -> bool:
        """發送信號給進程"""
        if not self._process:
            return False

        try:
            self._process.send_signal(signal)
            return True
        except Exception as e:
            logger.error(f"❌ 發送信號失敗: {e}")
            return False

    async def communicate(
        self, input_data: str | None = None, timeout: float | None = None
    ) -> tuple[str, str]:
        """與進程通信"""
        if not self._process:
            return "", "進程未啟動"

        try:
            input_bytes = input_data.encode("utf-8") if input_data else None

            if timeout:
                stdout, stderr = await asyncio.wait_for(
                    self._process.communicate(input_bytes), timeout=timeout
                )
            else:
                stdout, stderr = await self._process.communicate(input_bytes)

            return stdout.decode("utf-8"), stderr.decode("utf-8")

        except TimeoutError:
            return "", "通信超時"
        except Exception as e:
            logger.error(f"❌ 進程通信失敗: {e}")
            return "", str(e)


class NodeJSRuntimeManager(IRuntimeManager):
    """
    Node.js 運行時管理器

    遵循 SOLID 原則：
    - SRP: 專注於 Node.js 環境管理
    - LSP: 完全實現 IRuntimeManager 介面契約
    - DIP: 依賴抽象介面
    """

    def __init__(self):
        self._runtime_info: RuntimeInfo | None = None
        self._supported_packages = [
            "@modelcontextprotocol/server-postgres",
            "@modelcontextprotocol/server-sqlite",
            "@modelcontextprotocol/server-filesystem",
            "typescript",
            "ts-node",
            "nodemon",
        ]

    async def check_availability(self) -> bool:
        """檢查 Node.js 運行時環境是否可用"""
        try:
            # 檢查 node 命令
            node_result = await self._run_command(["node", "--version"])
            if not node_result["success"]:
                logger.warning("❌ Node.js 未安裝或不在 PATH 中")
                return False

            # 檢查 npm 命令
            npm_result = await self._run_command(["npm", "--version"])
            if not npm_result["success"]:
                logger.warning("❌ npm 未安裝或不在 PATH 中")
                return False

            logger.info("✅ Node.js 和 npm 都可用")
            return True

        except Exception as e:
            logger.error(f"❌ 檢查 Node.js 可用性失敗: {e}")
            return False

    async def get_runtime_info(self) -> RuntimeInfo:
        """獲取 Node.js 運行時環境詳細資訊"""
        if self._runtime_info:
            return self._runtime_info

        try:
            is_available = await self.check_availability()

            if not is_available:
                self._runtime_info = RuntimeInfo(
                    type=RuntimeType.NODEJS,
                    version="未安裝",
                    executable_path="",
                    is_available=False,
                    capabilities=[],
                    env_variables={},
                )
                return self._runtime_info

            # 獲取版本資訊
            node_version_result = await self._run_command(["node", "--version"])
            node_version = (
                node_version_result["stdout"].strip()
                if node_version_result["success"]
                else "未知"
            )

            npm_version_result = await self._run_command(["npm", "--version"])
            npm_version = (
                npm_version_result["stdout"].strip()
                if npm_version_result["success"]
                else "未知"
            )

            # 獲取執行路徑
            node_path = shutil.which("node") or ""
            npm_path = shutil.which("npm") or ""

            # 獲取 Node.js 能力
            capabilities = ["javascript", "typescript", "npm", "package-management"]

            # 檢查 npx 是否可用
            npx_result = await self._run_command(["npx", "--version"])
            if npx_result["success"]:
                capabilities.append("npx")

            # 環境變數
            env_variables = {
                "NODE_VERSION": node_version,
                "NPM_VERSION": npm_version,
                "NODE_PATH": node_path,
                "NPM_PATH": npm_path,
            }

            self._runtime_info = RuntimeInfo(
                type=RuntimeType.NODEJS,
                version=node_version,
                executable_path=node_path,
                is_available=True,
                capabilities=capabilities,
                env_variables=env_variables,
                package_manager="npm",
            )

            logger.info(f"📊 Node.js 運行時資訊: {node_version}, npm: {npm_version}")
            return self._runtime_info

        except Exception as e:
            logger.error(f"❌ 獲取 Node.js 運行時資訊失敗: {e}")

            self._runtime_info = RuntimeInfo(
                type=RuntimeType.NODEJS,
                version="錯誤",
                executable_path="",
                is_available=False,
                capabilities=[],
                env_variables={},
            )
            return self._runtime_info

    async def install_dependencies(self, dependencies: list[str]) -> bool:
        """使用 npm 安裝指定依賴套件"""
        if not await self.check_availability():
            logger.error("❌ Node.js 環境不可用，無法安裝依賴")
            return False

        try:
            logger.info(f"📦 開始安裝 Node.js 依賴: {dependencies}")

            # 使用 npm install 安裝全域套件
            for dependency in dependencies:
                logger.info(f"安裝套件: {dependency}")

                # 使用 npm install -g 進行全域安裝
                result = await self._run_command(
                    ["npm", "install", "-g", dependency], timeout=300
                )  # 5分鐘超時

                if not result["success"]:
                    logger.error(f"❌ 安裝 {dependency} 失敗: {result['stderr']}")
                    return False

                logger.info(f"✅ 成功安裝 {dependency}")

            logger.info("🎉 所有 Node.js 依賴安裝完成")
            return True

        except Exception as e:
            logger.error(f"❌ 安裝 Node.js 依賴失敗: {e}")
            return False

    async def create_process(
        self,
        command: str,
        args: list[str],
        env: dict[str, str] | None = None,
        working_dir: str | None = None,
    ) -> IProcess:
        """創建 Node.js 進程"""
        return NodeJSProcess(command, args, env, working_dir)

    async def validate_command(self, command: str, args: list[str]) -> bool:
        """驗證 Node.js 命令是否有效"""
        try:
            # 檢查命令是否存在
            if not shutil.which(command):
                logger.warning(f"⚠️ 命令不存在: {command}")
                return False

            # 對於 npx 命令，檢查套件是否可用
            if command == "npx" and args:
                package_name = (
                    args[0] if args[0] != "-y" else (args[1] if len(args) > 1 else "")
                )
                if package_name:
                    # 檢查套件是否已安裝或可安裝
                    check_result = await self._run_command(
                        ["npm", "list", "-g", package_name.split("@")[0]]
                    )

                    if not check_result["success"]:
                        logger.info(
                            f"📦 套件 {package_name} 未安裝，但可通過 npx 自動安裝"
                        )

            logger.info(f"✅ 命令驗證成功: {command}")
            return True

        except Exception as e:
            logger.error(f"❌ 驗證命令失敗: {e}")
            return False

    async def get_supported_packages(self) -> list[str]:
        """獲取支援的 Node.js 套件列表"""
        return self._supported_packages.copy()

    async def _run_command(
        self, cmd: list[str], timeout: float = 30.0, cwd: str | None = None
    ) -> dict[str, Any]:
        """執行命令並返回結果"""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode("utf-8"),
                "stderr": stderr.decode("utf-8"),
                "returncode": process.returncode,
            }

        except TimeoutError:
            logger.error(f"⏰ 命令執行超時: {' '.join(cmd)}")
            return {
                "success": False,
                "stdout": "",
                "stderr": "命令執行超時",
                "returncode": -1,
            }
        except Exception as e:
            logger.error(f"❌ 執行命令失敗: {e}")
            return {"success": False, "stdout": "", "stderr": str(e), "returncode": -1}
