#!/usr/bin/env python3
"""
生產級 MCP 客戶端 
基於 ultimate-stdio-test.py 的成功模式 1:1 複製而成
"""

import asyncio
import json
import os
import selectors
import sys
import time
from pathlib import Path
from typing import Any

import structlog

# 添加配置路徑
config_path = Path(__file__).parent.parent / "config"
if str(config_path) not in sys.path:
    sys.path.insert(0, str(config_path))

from ..config.mcp_config import (
    get_mcp_config,
    get_server_config,
    validate_server_config,
)
from .mcp_connection_pool import ConnectionStatus, get_connection_pool

logger = structlog.get_logger()
mcp_config = get_mcp_config()


def apply_macos_stdio_fix():
    """應用 macOS STDIO 修復 - 與 ultimate-stdio-test.py 完全一樣"""
    if sys.platform == "darwin":
        try:
            current_loop = asyncio.get_event_loop()
            current_selector = getattr(current_loop, "_selector", None)

            if current_selector and "Kqueue" in str(type(current_selector)):
                logger.info("🔧 檢測到 KqueueSelector，切換到 SelectSelector")

                selector = selectors.SelectSelector()
                new_loop = asyncio.SelectorEventLoop(selector)
                asyncio.set_event_loop(new_loop)

                logger.info("✅ 已切換到 SelectSelector（macOS 修復）")
                return True
        except Exception as e:
            logger.warning(f"⚠️ macOS 修復警告：{e}")
    return False


class ProductionMCPClient:
    """
    生產級 MCP 客戶端
    基於 ultimate-stdio-test.py 成功邏輯的完全複製
    """

    def __init__(self):
        """初始化生產級 MCP 客戶端"""
        self.processes: dict[str, asyncio.subprocess.Process] = {}
        self.connections: dict[str, bool] = {}

        # 🏊 初始化連接池
        self.connection_pool = get_connection_pool()
        self._pool_started = False

        # 應用 macOS 修復
        apply_macos_stdio_fix()

        logger.info("✅ 生產級 MCP 客戶端初始化完成（含連接池）")

    async def _ensure_pool_started(self):
        """確保連接池已啟動"""
        if not self._pool_started:
            await self.connection_pool.start()
            self._pool_started = True

    async def connect_to_server(self, server_name: str = "sqlite") -> bool:
        """連接到 MCP 服務器 - 使用連接池管理"""
        await self._ensure_pool_started()

        # 先檢查現有進程健康狀態
        if await self._verify_process_health(server_name):
            logger.info(f"✅ 現有連接健康：{server_name}")
            return True

        # 🏊 檢查連接池中的連接
        connection_info = await self.connection_pool.get_connection(server_name)
        if connection_info and connection_info.status == ConnectionStatus.CONNECTED:
            # 同步到舊有的狀態管理
            if connection_info.process:
                self.processes[server_name] = connection_info.process
                self.connections[server_name] = True
                logger.info(f"🔄 重用連接池連接：{server_name}")
                return True
            else:
                # 連接池狀態不一致，標記為斷開並繼續建立新連接
                logger.warning(
                    f"⚠️ 連接池返回 CONNECTED 但無進程，重建連接：{server_name}"
                )
                connection_info.status = ConnectionStatus.DISCONNECTED
                # 繼續執行下面的連接邏輯

        # 獲取服務器配置
        server_config = get_server_config(server_name)
        if not server_config:
            logger.error(f"❌ 找不到服務器配置：{server_name}")
            return False

        # 驗證配置
        is_valid, error_msg = validate_server_config(server_name)
        if not is_valid:
            logger.error(f"❌ 服務器配置無效：{error_msg}")
            return False

        try:
            logger.info(f"🚀 建立 MCP 連接：{server_name} ({server_config.protocol})")

            if server_config.protocol != "stdio":
                logger.error(
                    f"❌ 目前只支援 STDIO 協議，不支援：{server_config.protocol}"
                )
                return False

            # 檢查服務器腳本文件
            server_script = server_config.args[0] if server_config.args else None
            if not server_script or not os.path.exists(server_script):
                logger.error(f"❌ 服務器腳本不存在：{server_script}")
                return False

            # 準備環境變數
            env = os.environ.copy()
            env.update(server_config.env)

            # 創建子進程
            process = await asyncio.create_subprocess_exec(
                server_config.command,
                *server_config.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=server_config.cwd,
                env=env,
            )

            logger.info("✅ 子進程創建成功")

            # 測試通信 - 使用與 ultimate-stdio-test.py 相同的邏輯
            if await self._test_communication(process, server_name):
                self.processes[server_name] = process
                self.connections[server_name] = True

                # 🏊 同步到連接池
                if connection_info:
                    connection_info.process = process
                    connection_info.status = ConnectionStatus.CONNECTED
                    connection_info.metrics.connection_count += 1

                logger.info(f"✅ MCP 連接成功：{server_name}")
                return True
            else:
                # 🏊 標記連接池失敗
                if connection_info:
                    connection_info.status = ConnectionStatus.FAILED
                await self._cleanup_process(process)
                return False

        except Exception as e:
            logger.error(f"❌ MCP 連接失敗 {server_name}：{e}")
            return False

    async def _test_communication(
        self, process: asyncio.subprocess.Process, server_name: str
    ) -> bool:
        """測試通信 - 使用配置管理的超時設定"""
        server_config = get_server_config(server_name)
        timeout = server_config.timeout if server_config else 10

        try:
            logger.info(f"🧪 測試 {server_name} 通信")

            # 等待服務器啟動
            await asyncio.sleep(0.5)

            # 檢查進程是否退出
            if process.returncode is not None:
                logger.error(f"❌ 服務器進程退出，返回碼：{process.returncode}")
                stderr_output = await process.stderr.read()
                if stderr_output:
                    logger.error(f"❌ 服務器錯誤：{stderr_output.decode()}")
                return False

            # 先發送初始化請求
            init_request = {
                "jsonrpc": "2.0",
                "id": "init",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "production-mcp-client", "version": "1.0.0"},
                },
            }

            init_json = json.dumps(init_request) + "\n"
            process.stdin.write(init_json.encode())
            await process.stdin.drain()

            # 等待初始化響應
            init_response = await asyncio.wait_for(
                process.stdout.readline(), timeout=timeout
            )

            if init_response:
                init_text = init_response.decode().strip()
                init_data = json.loads(init_text)
                if "error" in init_data:
                    logger.error(f"❌ 初始化錯誤：{init_data['error']}")
                    return False

            # 發送 initialized 通知
            initialized_notif = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            }

            notif_json = json.dumps(initialized_notif) + "\n"
            process.stdin.write(notif_json.encode())
            await process.stdin.drain()

            # 發送工具列表請求
            request = {
                "jsonrpc": "2.0",
                "id": "ultimate-test",
                "method": "tools/list",
                "params": {},
            }

            request_json = json.dumps(request) + "\n"
            logger.info(f"📤 發送請求：{request}")

            process.stdin.write(request_json.encode())
            await process.stdin.drain()

            # 等待響應 - 與 ultimate-stdio-test.py 完全相同
            logger.info("⏳ 等待響應...")
            try:
                response_line = await asyncio.wait_for(
                    process.stdout.readline(), timeout=timeout
                )

                if response_line:
                    response_text = response_line.decode().strip()
                    logger.info(f"📥 收到響應：{response_text}")

                    response = json.loads(response_text)

                    if "result" in response and "tools" in response["result"]:
                        tools = response["result"]["tools"]
                        logger.info(f"✅ 通信成功，發現 {len(tools)} 個工具")
                        return True
                    elif "error" in response:
                        logger.error(f"❌ 服務器錯誤：{response['error']}")
                        return False
                    else:
                        logger.error(f"❌ 未知響應：{response}")
                        return False
                else:
                    logger.error("❌ 無響應數據")
                    return False

            except TimeoutError:
                logger.error("❌ 響應超時")
                return False

        except Exception as e:
            logger.error(f"❌ 通信測試失敗：{e}")
            return False

    async def call_tool(
        self, server_name: str, tool_name: str, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """調用工具 - 增強錯誤處理和重試機制 + 連接池監控"""
        await self._ensure_pool_started()

        server_config = get_server_config(server_name)
        timeout = server_config.timeout if server_config else 10
        max_retries = 2  # 最多重試2次
        start_time = time.time()

        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(
                        f"🔄 重試工具調用 (第{attempt}次)：{server_name}.{tool_name}"
                    )
                else:
                    logger.info(f"🛠️ 調用工具：{server_name}.{tool_name}")

                # 確保連接
                if not await self.connect_to_server(server_name):
                    error_msg = f"無法連接到服務器：{server_name}"
                    if attempt < max_retries:
                        logger.warning(f"⚠️ {error_msg}，準備重試...")
                        await asyncio.sleep(1)  # 等待1秒後重試
                        continue
                    return {"success": False, "error": error_msg}

                # 檢查進程是否存在於字典中
                if server_name not in self.processes:
                    logger.warning(f"⚠️ 進程不存在於字典中：{server_name}，強制重新連接")
                    self.connections[server_name] = False
                    # 清理連接池狀態
                    connection_info = await self.connection_pool.get_connection(
                        server_name
                    )
                    if connection_info:
                        connection_info.status = ConnectionStatus.DISCONNECTED
                    if attempt < max_retries:
                        await asyncio.sleep(1)  # 等待1秒後重試
                        continue
                    return {"success": False, "error": f"進程未找到：{server_name}"}

                process = self.processes[server_name]

                # 檢查進程狀態
                if process.returncode is not None:
                    logger.error(f"❌ 服務器進程已退出，返回碼：{process.returncode}")
                    # 重置連接狀態，強制重新連接
                    self.connections[server_name] = False
                    if attempt < max_retries:
                        continue
                    return {
                        "success": False,
                        "error": f"服務器進程已退出 (code: {process.returncode})",
                    }

                # 檢查連接狀態
                if not self.connections.get(server_name):
                    error_msg = "連接狀態異常"
                    if attempt < max_retries:
                        logger.warning(f"⚠️ {error_msg}，準備重新連接...")
                        self.connections[server_name] = False
                        continue
                    return {"success": False, "error": error_msg}

                # 構建請求
                request = {
                    "jsonrpc": "2.0",
                    "id": f"tool-call-{attempt}",
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": parameters},
                }

                # 發送請求
                try:
                    request_json = json.dumps(request) + "\n"
                    process.stdin.write(request_json.encode())
                    await process.stdin.drain()
                except (BrokenPipeError, ConnectionError) as e:
                    logger.error(f"❌ 寫入失敗：{e}")
                    self.connections[server_name] = False
                    if attempt < max_retries:
                        continue
                    return {"success": False, "error": f"通信失敗：{str(e)}"}

                # 等待響應
                try:
                    response_line = await asyncio.wait_for(
                        process.stdout.readline(), timeout=timeout
                    )

                    if response_line:
                        response_text = response_line.decode().strip()
                        if not response_text:
                            logger.warning("⚠️ 收到空響應")
                            if attempt < max_retries:
                                continue
                            return {"success": False, "error": "空響應"}

                        try:
                            response = json.loads(response_text)
                        except json.JSONDecodeError as e:
                            logger.error(
                                f"❌ JSON 解析失敗：{e}, 響應：{response_text[:100]}..."
                            )
                            if attempt < max_retries:
                                continue
                            return {
                                "success": False,
                                "error": f"響應格式錯誤：{str(e)}",
                            }

                        if "result" in response:
                            # 🏊 記錄成功操作到連接池
                            response_time = time.time() - start_time
                            await self.connection_pool.record_success(
                                server_name, response_time
                            )

                            logger.info(f"✅ 工具調用成功：{server_name}.{tool_name}")
                            return {"success": True, "data": response["result"]}
                        elif "error" in response:
                            error_info = response["error"]
                            error_msg = error_info.get("message", "未知錯誤")
                            error_code = error_info.get("code", 0)
                            logger.error(
                                f"❌ 工具調用錯誤 (code: {error_code})：{error_msg}"
                            )
                            # 對於某些錯誤不重試
                            if error_code in [
                                -32600,
                                -32601,
                                -32602,
                            ]:  # 無效請求、方法不存在、參數錯誤
                                return {"success": False, "error": error_msg}
                            elif attempt < max_retries:
                                continue
                            return {"success": False, "error": error_msg}
                        else:
                            logger.warning(f"⚠️ 意外的響應格式：{response}")
                            if attempt < max_retries:
                                continue
                            return {"success": False, "error": "意外的響應格式"}
                    else:
                        logger.warning("⚠️ 無響應數據")
                        if attempt < max_retries:
                            continue
                        return {"success": False, "error": "無響應數據"}

                except TimeoutError:
                    logger.warning(f"⚠️ 響應超時 ({timeout}s)")
                    if attempt < max_retries:
                        continue
                    return {"success": False, "error": f"響應超時 ({timeout}s)"}

            except Exception as e:
                # 🏊 記錄失敗操作到連接池
                await self.connection_pool.record_failure(server_name, str(e))

                logger.error(
                    f"❌ 工具調用異常 {server_name}.{tool_name} (嘗試 {attempt + 1})：{e}"
                )
                if attempt < max_retries:
                    await asyncio.sleep(1)  # 等待後重試
                    continue
                return {"success": False, "error": f"工具調用失敗：{str(e)}"}

    async def list_tools(self, server_name: str = "sqlite") -> dict[str, Any]:
        """列出服務器工具"""
        server_config = get_server_config(server_name)
        timeout = server_config.timeout if server_config else 10

        try:
            if not await self.connect_to_server(server_name):
                return {"success": False, "error": f"無法連接到服務器：{server_name}"}

            process = self.processes[server_name]

            request = {
                "jsonrpc": "2.0",
                "id": "list-tools",
                "method": "tools/list",
                "params": {},
            }

            request_json = json.dumps(request) + "\n"
            process.stdin.write(request_json.encode())
            await process.stdin.drain()

            response_line = await asyncio.wait_for(
                process.stdout.readline(), timeout=timeout
            )

            if response_line:
                response = json.loads(response_line.decode().strip())

                if "result" in response and "tools" in response["result"]:
                    tools = response["result"]["tools"]
                    logger.info(
                        f"📋 列出工具成功：{server_name} -> {len(tools)} 個工具"
                    )
                    return {"success": True, "tools": tools}
                elif "error" in response:
                    return {"success": False, "error": response["error"]["message"]}

            return {"success": False, "error": "無效響應"}

        except Exception as e:
            logger.error(f"❌ 列出工具失敗 {server_name}：{e}")
            return {"success": False, "error": str(e)}

    async def _verify_process_health(self, server_name: str) -> bool:
        """驗證進程健康狀態"""
        if server_name not in self.processes:
            logger.debug(f"🔍 進程不存在於字典中：{server_name}")
            return False

        process = self.processes[server_name]
        if process.returncode is not None:
            # 進程已退出
            logger.warning(f"⚠️ 進程已退出：{server_name}，返回碼：{process.returncode}")
            del self.processes[server_name]
            self.connections[server_name] = False
            # 同步更新連接池狀態
            connection_info = await self.connection_pool.get_connection(server_name)
            if connection_info:
                connection_info.status = ConnectionStatus.FAILED
                connection_info.process = None
            return False

        logger.debug(f"✅ 進程健康：{server_name}")
        return True

    async def _cleanup_process(self, process: asyncio.subprocess.Process):
        """清理進程 - 與 ultimate-stdio-test.py 相同的邏輯"""
        try:
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except TimeoutError:
                    process.kill()
                    await process.wait()
            logger.info("✅ 進程清理完成")
        except Exception as e:
            logger.warning(f"⚠️ 清理警告：{e}")

    async def close_connection(self, server_name: str):
        """關閉指定服務器連接"""
        if server_name in self.processes:
            process = self.processes[server_name]
            await self._cleanup_process(process)
            del self.processes[server_name]

        if server_name in self.connections:
            del self.connections[server_name]

        logger.info(f"✅ 已關閉連接：{server_name}")

    async def close_all_connections(self):
        """關閉所有連接 - 與 ultimate-stdio-test.py 相同的邏輯 + 連接池清理"""
        logger.info("🔌 關閉所有 MCP 連接...")

        for server_name in list(self.processes.keys()):
            await self.close_connection(server_name)

        self.processes.clear()
        self.connections.clear()

        # 🏊 停止連接池
        if self._pool_started:
            await self.connection_pool.stop()
            self._pool_started = False

        logger.info("✅ 所有 MCP 連接已關閉（生產級清理完成 + 連接池清理）")

    async def get_connection_pool_status(self) -> dict[str, Any]:
        """獲取連接池狀態"""
        await self._ensure_pool_started()
        return await self.connection_pool.get_pool_status()


# 單例模式
_production_mcp_client = None


def get_production_mcp_client() -> ProductionMCPClient:
    """獲取生產級 MCP 客戶端單例"""
    global _production_mcp_client
    if _production_mcp_client is None:
        _production_mcp_client = ProductionMCPClient()
    return _production_mcp_client


# 兼容性包裝函數
async def get_unified_mcp_client():
    """兼容性函數 - 返回生產級客戶端"""
    return get_production_mcp_client()
