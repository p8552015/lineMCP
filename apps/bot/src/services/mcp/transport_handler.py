"""
MCP 傳輸層處理器
支援多種傳輸協議（STDIO、HTTP），提供統一的傳輸接口
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum

import structlog
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client

logger = structlog.get_logger()


class TransportType(Enum):
    """傳輸類型枚舉"""
    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"


class MCPTransport(ABC):
    """MCP 傳輸抽象基類"""
    
    @abstractmethod
    async def connect(self, config: Dict[str, Any]) -> bool:
        """建立連接"""
        pass
    
    @abstractmethod
    async def send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """發送訊息"""
        pass
    
    @abstractmethod
    async def close(self):
        """關閉連接"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """檢查連接狀態"""
        pass


class StdioTransport(MCPTransport):
    """STDIO 傳輸實現"""
    
    def __init__(self):
        self.read_stream = None
        self.write_stream = None
        self.exit_stack = None
        self.connected = False
    
    async def connect(self, config: Dict[str, Any]) -> bool:
        """
        建立 STDIO 連接
        
        Args:
            config: 配置字典，包含 command, args, env
        """
        try:
            from contextlib import AsyncExitStack
            
            self.exit_stack = AsyncExitStack()
            
            server_params = StdioServerParameters(
                command=config.get("command", "python"),
                args=config.get("args", []),
                env=config.get("env")
            )
            
            self.read_stream, self.write_stream = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            
            self.connected = True
            logger.info(f"✅ STDIO 連接已建立: {config.get('command')}")
            return True
            
        except Exception as e:
            logger.error(f"❌ STDIO 連接失敗: {e}")
            self.connected = False
            return False
    
    async def send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """發送 JSON-RPC 訊息"""
        if not self.is_connected():
            return {"success": False, "error": "連接未建立"}
        
        try:
            import json
            
            # 序列化訊息
            message_json = json.dumps(message) + "\n"
            
            # 發送訊息
            self.write_stream.write(message_json.encode())
            await self.write_stream.drain()
            
            # 讀取響應
            response_line = await self.read_stream.readline()
            if not response_line:
                return {"success": False, "error": "無響應"}
            
            response_data = json.loads(response_line.decode().strip())
            return {"success": True, "data": response_data}
            
        except Exception as e:
            logger.error(f"❌ STDIO 訊息發送失敗: {e}")
            return {"success": False, "error": str(e)}
    
    async def close(self):
        """關閉 STDIO 連接"""
        try:
            if self.exit_stack:
                await self.exit_stack.aclose()
            self.connected = False
            logger.info("🔌 STDIO 連接已關閉")
        except Exception as e:
            logger.error(f"❌ STDIO 連接關閉失敗: {e}")
    
    def is_connected(self) -> bool:
        """檢查連接狀態"""
        return self.connected and self.read_stream and self.write_stream


class HttpBridgeTransport(MCPTransport):
    """HTTP 橋接傳輸實現（使用現有的 http_bridge.py）"""
    
    def __init__(self):
        self.base_url = None
        self.session = None
        self.connected = False
    
    async def connect(self, config: Dict[str, Any]) -> bool:
        """
        建立 HTTP 橋接連接
        
        Args:
            config: 配置字典，包含 host, port 等
        """
        try:
            import aiohttp
            
            host = config.get("host", "localhost")
            port = config.get("port", 3003)
            self.base_url = f"http://{host}:{port}"
            
            # 創建 HTTP 會話
            self.session = aiohttp.ClientSession()
            
            # 測試連接
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    self.connected = True
                    logger.info(f"✅ HTTP 橋接連接已建立: {self.base_url}")
                    return True
                else:
                    logger.error(f"❌ HTTP 橋接連接失敗: 狀態碼 {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ HTTP 橋接連接失敗: {e}")
            self.connected = False
            return False
    
    async def send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """發送 HTTP 請求"""
        if not self.is_connected():
            return {"success": False, "error": "連接未建立"}
        
        try:
            method = message.get("method", "")
            
            # 映射 MCP 方法到 HTTP 端點
            if method == "tools/list":
                endpoint = "/tools/list"
            elif method == "tools/call":
                endpoint = "/tools/call"
            else:
                return {"success": False, "error": f"不支援的方法: {method}"}
            
            url = f"{self.base_url}{endpoint}"
            
            async with self.session.post(url, json=message) as response:
                if response.status == 200:
                    data = await response.json()
                    return {"success": True, "data": data}
                else:
                    error_text = await response.text()
                    return {"success": False, "error": f"HTTP {response.status}: {error_text}"}
                    
        except Exception as e:
            logger.error(f"❌ HTTP 請求失敗: {e}")
            return {"success": False, "error": str(e)}
    
    async def close(self):
        """關閉 HTTP 連接"""
        try:
            if self.session:
                await self.session.close()
            self.connected = False
            logger.info("🔌 HTTP 橋接連接已關閉")
        except Exception as e:
            logger.error(f"❌ HTTP 連接關閉失敗: {e}")
    
    def is_connected(self) -> bool:
        """檢查連接狀態"""
        return self.connected and self.session and not self.session.closed


class MCPTransportHandler:
    """MCP 傳輸層處理器"""
    
    def __init__(self):
        self.transports: Dict[str, MCPTransport] = {}
        self.transport_configs: Dict[str, Dict[str, Any]] = {}
        
    def register_transport_config(self, server_name: str, transport_type: TransportType, 
                                config: Dict[str, Any]):
        """
        註冊傳輸配置
        
        Args:
            server_name: 服務器名稱
            transport_type: 傳輸類型
            config: 傳輸配置
        """
        self.transport_configs[server_name] = {
            "type": transport_type,
            "config": config
        }
        logger.info(f"📝 已註冊傳輸配置: {server_name} ({transport_type.value})")
    
    async def get_transport(self, server_name: str) -> Optional[MCPTransport]:
        """
        獲取或創建傳輸實例
        
        Args:
            server_name: 服務器名稱
            
        Returns:
            MCPTransport: 傳輸實例
        """
        # 如果已存在且連接正常，直接返回
        if server_name in self.transports:
            transport = self.transports[server_name]
            if transport.is_connected():
                return transport
            else:
                # 連接已斷開，清理並重建
                await transport.close()
                del self.transports[server_name]
        
        # 創建新的傳輸實例
        transport_info = self.transport_configs.get(server_name)
        if not transport_info:
            # 使用默認 STDIO 配置
            transport_info = {
                "type": TransportType.STDIO,
                "config": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://admin:admin@localhost:5432/mydb"],
                    "env": None
                }
            }
        
        transport_type = transport_info["type"]
        config = transport_info["config"]
        
        # 創建傳輸實例
        if transport_type == TransportType.STDIO:
            transport = StdioTransport()
        elif transport_type == TransportType.HTTP:
            transport = HttpBridgeTransport()
        else:
            logger.error(f"❌ 不支援的傳輸類型: {transport_type}")
            return None
        
        # 建立連接
        if await transport.connect(config):
            self.transports[server_name] = transport
            logger.info(f"✅ 傳輸實例已創建: {server_name} ({transport_type.value})")
            return transport
        else:
            logger.error(f"❌ 傳輸連接失敗: {server_name}")
            return None
    
    async def send_message(self, server_name: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        發送訊息
        
        Args:
            server_name: 服務器名稱
            message: 訊息內容
            
        Returns:
            Dict: 響應結果
        """
        transport = await self.get_transport(server_name)
        if not transport:
            return {"success": False, "error": "無法獲取傳輸實例"}
        
        return await transport.send_message(message)
    
    async def close_transport(self, server_name: str):
        """關閉指定傳輸"""
        if server_name in self.transports:
            transport = self.transports[server_name]
            await transport.close()
            del self.transports[server_name]
            logger.info(f"🔌 傳輸已關閉: {server_name}")
    
    async def close_all_transports(self):
        """關閉所有傳輸"""
        for server_name in list(self.transports.keys()):
            await self.close_transport(server_name)
        logger.info("🧹 所有傳輸已關閉")
    
    def get_transport_status(self) -> Dict[str, Any]:
        """獲取傳輸狀態"""
        status = {}
        for server_name, transport in self.transports.items():
            transport_config = self.transport_configs.get(server_name, {})
            status[server_name] = {
                "type": transport_config.get("type", {}).value if transport_config.get("type") else "unknown",
                "connected": transport.is_connected(),
                "config": transport_config.get("config", {})
            }
        return status


# 單例實例
_transport_handler: Optional[MCPTransportHandler] = None


def get_transport_handler() -> MCPTransportHandler:
    """獲取傳輸處理器實例（單例）"""
    global _transport_handler
    if _transport_handler is None:
        _transport_handler = MCPTransportHandler()
    return _transport_handler