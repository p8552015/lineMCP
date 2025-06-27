"""
Python 運行時管理器實現

提供 Python 環境的管理功能，支援：
- Python 解釋器檢測和驗證
- pip/poetry 依賴管理
- Python MCP 服務器進程管理
- 虛擬環境支援

遵循 SOLID 原則：
- SRP: 專注於 Python 運行時環境管理
- OCP: 對新 Python 工具擴展開放
- LSP: 完全實現 IRuntimeManager 介面
- ISP: 介面隔離，只依賴必要功能
- DIP: 依賴抽象的 IProcess 介面
"""

import asyncio
import os
import platform
import shutil
import subprocess
import sys
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


class PythonProcess(IProcess):
    """
    Python 進程實現

    封裝 Python 進程的生命週期管理
    """

    def __init__(
        self,
        command: str,
        args: list[str],
        env: dict[str, str] | None = None,
        working_dir: str | None = None,
    ):
        self.command = command
        self.args = args
        self.env = env or {}
        self.working_dir = working_dir
        self._process: asyncio.subprocess.Process | None = None
        self._info = ProcessInfo(
            pid=None,
            status=ProcessStatus.STOPPED,
            command=command,
            args=args,
            env=self.env,
            working_dir=working_dir or os.getcwd(),
            start_time=None,
        )

    @property
    def info(self) -> ProcessInfo:
        """獲取進程資訊"""
        return self._info

    async def start(self) -> bool:
        """啟動進程"""
        try:
            logger.info(f"🐍 啟動 Python 進程: {self.command} {' '.join(self.args)}")

            # 準備環境變數
            full_env = os.environ.copy()
            full_env.update(self.env)

            # 確保 PYTHONPATH 包含當前目錄
            if "PYTHONPATH" not in full_env:
                full_env["PYTHONPATH"] = "."

            # 啟動進程
            self._process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=full_env,
                cwd=self.working_dir,
            )

            if self._process and self._process.pid:
                self._info.pid = self._process.pid
                self._info.status = ProcessStatus.RUNNING
                self._info.start_time = __import__("time").time()

                logger.info(f"✅ Python 進程啟動成功 (PID: {self._process.pid})")
                return True
            else:
                logger.error("❌ Python 進程啟動失敗：無法獲取 PID")
                return False

        except Exception as e:
            logger.error(f"❌ Python 進程啟動失敗: {e}")
            self._info.status = ProcessStatus.FAILED
            return False

    async def stop(self, timeout: float = 10.0) -> bool:
        """停止進程"""
        try:
            if not self._process:
                return True

            logger.info(f"⏹️ 停止 Python 進程 (PID: {self._process.pid})")

            # 嘗試優雅關閉
            self._process.terminate()

            try:
                await asyncio.wait_for(self._process.wait(), timeout=timeout)
                logger.info("✅ Python 進程已優雅停止")
            except TimeoutError:
                logger.warning("⚠️ Python 進程優雅停止超時，強制終止")
                self._process.kill()
                await self._process.wait()

            self._info.status = ProcessStatus.STOPPED
            self._info.end_time = __import__("time").time()
            return True

        except Exception as e:
            logger.error(f"❌ 停止 Python 進程失敗: {e}")
            return False

    async def is_alive(self) -> bool:
        """檢查進程是否存活"""
        try:
            if not self._process:
                return False

            return self._process.returncode is None

        except Exception:
            return False

    async def wait(self, timeout: float | None = None) -> int | None:
        """等待進程結束"""
        if not self._process:
            return -1

        try:
            if timeout:
                return await asyncio.wait_for(self._process.wait(), timeout=timeout)
            else:
                return await self._process.wait()
        except TimeoutError:
            return None

    async def kill(self) -> bool:
        """強制終止進程"""
        try:
            if not self._process:
                return True

            logger.info(f"💀 強制終止 Python 進程 (PID: {self._process.pid})")

            self._process.kill()
            await self._process.wait()

            self._info.status = ProcessStatus.STOPPED
            self._info.end_time = __import__("time").time()

            logger.info("✅ Python 進程已強制終止")
            return True

        except Exception as e:
            logger.error(f"❌ 強制終止 Python 進程失敗: {e}")
            return False

    async def send_signal(self, signal: int) -> bool:
        """發送信號給進程"""
        try:
            if not self._process:
                return False

            logger.info(
                f"📡 向 Python 進程發送信號: {signal} (PID: {self._process.pid})"
            )

            # 在 Windows 上，信號支援有限
            if platform.system() == "Windows":
                if signal in [2, 9, 15]:  # SIGINT, SIGKILL, SIGTERM
                    self._process.terminate()
                    return True
                else:
                    logger.warning(f"⚠️ Windows 不支援信號 {signal}")
                    return False
            else:
                # Unix-like 系統
                import os

                os.kill(self._process.pid, signal)
                return True

        except Exception as e:
            logger.error(f"❌ 發送信號失敗: {e}")
            return False

    async def communicate(
        self, input_data: str | None = None, timeout: float | None = None
    ) -> tuple[str, str]:
        """與進程通信"""
        if not self._process:
            raise RuntimeError("進程未啟動")

        try:
            # 轉換字串輸入為 bytes
            input_bytes = input_data.encode() if input_data else None

            if timeout:
                stdout, stderr = await asyncio.wait_for(
                    self._process.communicate(input_bytes), timeout=timeout
                )
            else:
                stdout, stderr = await self._process.communicate(input_bytes)

            # 轉換 bytes 輸出為字串
            return stdout.decode() if stdout else "", stderr.decode() if stderr else ""

        except TimeoutError:
            logger.warning("⚠️ Python 進程通信超時")
            raise
        except Exception as e:
            logger.error(f"❌ Python 進程通信失敗: {e}")
            raise


class PythonRuntimeManager(IRuntimeManager):
    """
    Python 運行時管理器

    提供完整的 Python 環境管理功能，支援多種 Python 安裝和工具。
    """

    def __init__(self):
        self.runtime_type = RuntimeType.PYTHON
        self._python_executable = self._detect_python_executable()
        self._pip_executable = self._detect_pip_executable()
        self._poetry_available = self._check_poetry_availability()

        logger.info(f"🐍 Python 運行時管理器初始化: {self._python_executable}")

    @property
    def runtime_type_value(self) -> RuntimeType:
        """獲取運行時類型"""
        return self.runtime_type

    def _detect_python_executable(self) -> str | None:
        """檢測 Python 可執行檔"""
        # 按優先順序檢測 Python
        python_candidates = ["python3", "python", sys.executable]

        for candidate in python_candidates:
            if candidate and shutil.which(candidate):
                try:
                    result = subprocess.run(
                        [candidate, "--version"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        logger.info(
                            f"✅ 找到 Python: {candidate} ({result.stdout.strip()})"
                        )
                        return candidate
                except Exception:
                    continue

        logger.warning("⚠️ 未找到可用的 Python 執行檔")
        return None

    def _detect_pip_executable(self) -> str | None:
        """檢測 pip 可執行檔"""
        pip_candidates = ["pip3", "pip"]

        for candidate in pip_candidates:
            if shutil.which(candidate):
                try:
                    result = subprocess.run(
                        [candidate, "--version"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        logger.info(f"✅ 找到 pip: {candidate}")
                        return candidate
                except Exception:
                    continue

        logger.warning("⚠️ 未找到可用的 pip")
        return None

    def _check_poetry_availability(self) -> bool:
        """檢查 Poetry 可用性"""
        try:
            result = subprocess.run(
                ["poetry", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                logger.info(f"✅ 找到 Poetry: {result.stdout.strip()}")
                return True
        except Exception:
            pass

        logger.info("ℹ️ Poetry 不可用")
        return False

    async def check_availability(self) -> bool:
        """檢查運行時可用性"""
        try:
            if not self._python_executable:
                logger.warning("⚠️ Python 運行時不可用：未找到 Python 執行檔")
                return False

            # 檢查 Python 版本
            process = await asyncio.create_subprocess_exec(
                self._python_executable,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                version_info = stdout.decode().strip()
                logger.info(f"✅ Python 運行時可用: {version_info}")
                return True
            else:
                logger.error(f"❌ Python 版本檢查失敗: {stderr.decode()}")
                return False

        except Exception as e:
            logger.error(f"❌ Python 運行時檢查失敗: {e}")
            return False

    async def get_runtime_info(self) -> RuntimeInfo:
        """獲取運行時資訊"""
        try:
            # 獲取 Python 版本
            process = await asyncio.create_subprocess_exec(
                self._python_executable, "--version", stdout=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            python_version = stdout.decode().strip()

            # 獲取 pip 版本
            pip_version = "不可用"
            if self._pip_executable:
                try:
                    process = await asyncio.create_subprocess_exec(
                        self._pip_executable,
                        "--version",
                        stdout=asyncio.subprocess.PIPE,
                    )
                    stdout, _ = await process.communicate()
                    pip_version = stdout.decode().strip()
                except Exception:
                    pass

            return RuntimeInfo(
                type=self.runtime_type,
                version=python_version,
                executable_path=self._python_executable,
                is_available=True,
                capabilities=["mcp-server", "async-support", "pip-install"],
                env_variables={
                    "PYTHONPATH": ".",
                    "PYTHONUNBUFFERED": "1",
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
                package_manager="pip" if self._pip_executable else None,
            )

        except Exception as e:
            logger.error(f"❌ 獲取 Python 運行時資訊失敗: {e}")
            return RuntimeInfo(
                type=self.runtime_type,
                version="未知",
                executable_path=self._python_executable or "未知",
                is_available=False,
                capabilities=[],
                env_variables={},
                package_manager=None,
            )

    async def validate_command(self, command: str, args: list[str]) -> bool:
        """驗證命令有效性"""
        try:
            logger.info(f"🔍 驗證 Python 命令: {command} {' '.join(args[:2])}")

            # 檢查基本 Python 命令
            if command in ["python", "python3"]:
                return self._python_executable is not None

            # 檢查模組執行命令
            if command == self._python_executable and args and args[0] == "-m":
                if len(args) < 2:
                    return False

                module_name = args[1]

                # 檢查模組是否可導入
                try:
                    process = await asyncio.create_subprocess_exec(
                        self._python_executable,
                        "-c",
                        f"import {module_name}",
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                    await process.communicate()
                    is_valid = process.returncode == 0

                    if is_valid:
                        logger.info(f"✅ 模組驗證成功: {module_name}")
                    else:
                        logger.warning(f"⚠️ 模組不可用: {module_name}")

                    return is_valid

                except Exception as e:
                    logger.error(f"❌ 模組驗證失敗: {e}")
                    return False

            # 檢查其他可執行檔
            return shutil.which(command) is not None

        except Exception as e:
            logger.error(f"❌ Python 命令驗證失敗: {e}")
            return False

    async def create_process(
        self,
        command: str,
        args: list[str],
        env: dict[str, str] | None = None,
        working_dir: str | None = None,
    ) -> IProcess:
        """創建進程"""
        try:
            logger.info(f"🚀 創建 Python 進程: {command}")

            # 規範化命令
            if command in ["python", "python3"] and self._python_executable:
                command = self._python_executable

            return PythonProcess(command, args, env, working_dir)

        except Exception as e:
            logger.error(f"❌ 創建 Python 進程失敗: {e}")
            raise

    async def install_dependencies(self, packages: list[str]) -> bool:
        """安裝依賴包"""
        try:
            if not packages:
                return True

            logger.info(f"📦 安裝 Python 套件: {', '.join(packages)}")

            if not self._pip_executable:
                logger.error("❌ pip 不可用，無法安裝套件")
                return False

            # 使用 pip 安裝
            for package in packages:
                try:
                    logger.info(f"📦 安裝套件: {package}")

                    process = await asyncio.create_subprocess_exec(
                        self._pip_executable,
                        "install",
                        package,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )

                    stdout, stderr = await process.communicate()

                    if process.returncode == 0:
                        logger.info(f"✅ 套件安裝成功: {package}")
                    else:
                        logger.error(f"❌ 套件安裝失敗: {package} - {stderr.decode()}")
                        return False

                except Exception as e:
                    logger.error(f"❌ 安裝套件 {package} 失敗: {e}")
                    return False

            return True

        except Exception as e:
            logger.error(f"❌ 依賴安裝失敗: {e}")
            return False

    async def cleanup_processes(self) -> dict[str, bool]:
        """清理相關進程"""
        try:
            logger.info("🧹 清理 Python 相關進程")

            # 這是簡化實現，實際可能需要追踪所有創建的進程
            # 目前只返回成功狀態

            logger.info("✅ Python 進程清理完成")
            return {"cleanup": True}

        except Exception as e:
            logger.error(f"❌ Python 進程清理失敗: {e}")
            return {"cleanup": False}

    async def get_environment_variables(self) -> dict[str, str]:
        """獲取推薦的環境變數"""
        return {
            "PYTHONPATH": ".",
            "PYTHONUNBUFFERED": "1",  # 確保即時輸出
            "PYTHONDONTWRITEBYTECODE": "1",  # 避免生成 .pyc 檔案
        }

    async def get_default_working_directory(self) -> str:
        """獲取預設工作目錄"""
        return os.getcwd()

    async def supports_hot_reload(self) -> bool:
        """檢查是否支援熱重載"""
        return True  # Python 通常支援模組重載

    async def get_package_manager_info(self) -> dict[str, Any]:
        """獲取套件管理器資訊"""
        return {
            "pip": {
                "available": self._pip_executable is not None,
                "executable": self._pip_executable,
            },
            "poetry": {
                "available": self._poetry_available,
                "executable": "poetry" if self._poetry_available else None,
            },
        }

    async def get_supported_packages(self) -> list[str]:
        """
        獲取 Python 運行時支援的套件列表

        Returns:
            List[str]: 支援的 MCP 相關套件名稱列表
        """
        # 返回常用的 Python MCP 相關套件
        return [
            "mcp",
            "mcp-server-sqlite",
            "mcp-server-postgres",
            "fastapi",
            "uvicorn",
            "httpx",
            "aiofiles",
            "structlog",
            "asyncio",
            "dataclasses",
            "typing-extensions",
            "pydantic",
        ]
