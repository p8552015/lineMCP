#!/usr/bin/env python3
"""
生產級 MCP 客戶端 
基於 ultimate-stdio-test.py 的成功模式 1:1 複製而成
"""

import asyncio
import sys
import os
import selectors
import json
import structlog
from typing import Dict, Any, Optional
from dataclasses import dataclass
import sys
from pathlib import Path

# 添加配置路徑
config_path = Path(__file__).parent.parent / 'config'
if str(config_path) not in sys.path:
    sys.path.insert(0, str(config_path))

from ..config.mcp_config import get_mcp_config, get_server_config, validate_server_config

logger = structlog.get_logger()
mcp_config = get_mcp_config()


def apply_macos_stdio_fix():
    """應用 macOS STDIO 修復 - 與 ultimate-stdio-test.py 完全一樣"""
    if sys.platform == 'darwin':
        try:
            current_loop = asyncio.get_event_loop()
            current_selector = getattr(current_loop, '_selector', None)
            
            if current_selector and 'Kqueue' in str(type(current_selector)):
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
        self.processes: Dict[str, asyncio.subprocess.Process] = {}
        self.connections: Dict[str, bool] = {}
        
        # 應用 macOS 修復
        apply_macos_stdio_fix()
        
        logger.info("✅ 生產級 MCP 客戶端初始化完成")
    
    async def connect_to_server(self, server_name: str = 'sqlite') -> bool:
        """連接到 MCP 服務器 - 使用配置管理"""
        if server_name in self.connections and self.connections[server_name]:
            logger.info(f"🔄 重用現有連接：{server_name}")
            return True
        
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
            
            if server_config.protocol != 'stdio':
                logger.error(f"❌ 目前只支援 STDIO 協議，不支援：{server_config.protocol}")
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
                env=env
            )
            
            logger.info("✅ 子進程創建成功")
            
            # 測試通信 - 使用與 ultimate-stdio-test.py 相同的邏輯
            if await self._test_communication(process, server_name):
                self.processes[server_name] = process
                self.connections[server_name] = True
                logger.info(f"✅ MCP 連接成功：{server_name}")
                return True
            else:
                await self._cleanup_process(process)
                return False
                
        except Exception as e:
            logger.error(f"❌ MCP 連接失敗 {server_name}：{e}")
            return False
    
    async def _test_communication(self, process: asyncio.subprocess.Process, server_name: str) -> bool:
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
                    "clientInfo": {
                        "name": "production-mcp-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            init_json = json.dumps(init_request) + '\n'
            process.stdin.write(init_json.encode())
            await process.stdin.drain()
            
            # 等待初始化響應
            init_response = await asyncio.wait_for(
                process.stdout.readline(),
                timeout=timeout
            )
            
            if init_response:
                init_text = init_response.decode().strip()
                init_data = json.loads(init_text)
                if 'error' in init_data:
                    logger.error(f"❌ 初始化錯誤：{init_data['error']}")
                    return False
            
            # 發送 initialized 通知
            initialized_notif = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            
            notif_json = json.dumps(initialized_notif) + '\n'
            process.stdin.write(notif_json.encode())
            await process.stdin.drain()
            
            # 發送工具列表請求
            request = {
                "jsonrpc": "2.0",
                "id": "ultimate-test",
                "method": "tools/list",
                "params": {}
            }
            
            request_json = json.dumps(request) + '\n'
            logger.info(f"📤 發送請求：{request}")
            
            process.stdin.write(request_json.encode())
            await process.stdin.drain()
            
            # 等待響應 - 與 ultimate-stdio-test.py 完全相同
            logger.info("⏳ 等待響應...")
            try:
                response_line = await asyncio.wait_for(
                    process.stdout.readline(),
                    timeout=timeout
                )
                
                if response_line:
                    response_text = response_line.decode().strip()
                    logger.info(f"📥 收到響應：{response_text}")
                    
                    response = json.loads(response_text)
                    
                    if 'result' in response and 'tools' in response['result']:
                        tools = response['result']['tools']
                        logger.info(f"✅ 通信成功，發現 {len(tools)} 個工具")
                        return True
                    elif 'error' in response:
                        logger.error(f"❌ 服務器錯誤：{response['error']}")
                        return False
                    else:
                        logger.error(f"❌ 未知響應：{response}")
                        return False
                else:
                    logger.error("❌ 無響應數據")
                    return False
                    
            except asyncio.TimeoutError:
                logger.error("❌ 響應超時")
                return False
                
        except Exception as e:
            logger.error(f"❌ 通信測試失敗：{e}")
            return False
    
    async def call_tool(self, server_name: str, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """調用工具 - 使用配置管理的超時設定"""
        server_config = get_server_config(server_name)
        timeout = server_config.timeout if server_config else 10
        
        try:
            logger.info(f"🛠️ 調用工具：{server_name}.{tool_name}")
            
            # 確保連接
            if not await self.connect_to_server(server_name):
                return {"success": False, "error": f"無法連接到服務器：{server_name}"}
            
            process = self.processes[server_name]
            
            # 檢查連接狀態
            if not self.connections.get(server_name):
                return {"success": False, "error": "未連接"}
            
            # 與 ultimate-stdio-test.py 相同的請求格式
            request = {
                "jsonrpc": "2.0",
                "id": "tool-call",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": parameters
                }
            }
            
            request_json = json.dumps(request) + '\n'
            process.stdin.write(request_json.encode())
            await process.stdin.drain()
            
            response_line = await asyncio.wait_for(
                process.stdout.readline(),
                timeout=timeout
            )
            
            if response_line:
                response = json.loads(response_line.decode().strip())
                if 'result' in response:
                    logger.info(f"✅ 工具調用成功：{server_name}.{tool_name}")
                    return {"success": True, "data": response['result']}
                elif 'error' in response:
                    logger.error(f"❌ 工具調用錯誤：{response['error']['message']}")
                    return {"success": False, "error": response['error']['message']}
            
            return {"success": False, "error": "無響應"}
            
        except Exception as e:
            logger.error(f"❌ 工具調用失敗 {server_name}.{tool_name}：{e}")
            return {"success": False, "error": str(e)}
    
    async def list_tools(self, server_name: str = 'sqlite') -> Dict[str, Any]:
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
                "params": {}
            }
            
            request_json = json.dumps(request) + '\n'
            process.stdin.write(request_json.encode())
            await process.stdin.drain()
            
            response_line = await asyncio.wait_for(
                process.stdout.readline(),
                timeout=timeout
            )
            
            if response_line:
                response = json.loads(response_line.decode().strip())
                
                if 'result' in response and 'tools' in response['result']:
                    tools = response['result']['tools']
                    logger.info(f"📋 列出工具成功：{server_name} -> {len(tools)} 個工具")
                    return {"success": True, "tools": tools}
                elif 'error' in response:
                    return {"success": False, "error": response['error']['message']}
            
            return {"success": False, "error": "無效響應"}
            
        except Exception as e:
            logger.error(f"❌ 列出工具失敗 {server_name}：{e}")
            return {"success": False, "error": str(e)}
    
    async def _cleanup_process(self, process: asyncio.subprocess.Process):
        """清理進程 - 與 ultimate-stdio-test.py 相同的邏輯"""
        try:
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
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
        """關閉所有連接 - 與 ultimate-stdio-test.py 相同的邏輯"""
        logger.info("🔌 關閉所有 MCP 連接...")
        
        for server_name in list(self.processes.keys()):
            await self.close_connection(server_name)
        
        self.processes.clear()
        self.connections.clear()
        
        logger.info("✅ 所有 MCP 連接已關閉（生產級清理完成）")


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