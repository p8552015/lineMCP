"""
MCP 客戶端管理器
統一管理所有 MCP 連接，提供高級 API 和向下兼容性
"""

import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

import structlog

from .security_validator import MCPSecurityValidator
from .session_pool import MCPSessionPool

logger = structlog.get_logger()


@dataclass
class MCPServerInfo:
    """MCP 服務器信息"""
    name: str
    protocol: str
    status: str
    tools: List[Dict[str, Any]]
    connection_count: int
    request_count: int
    error_count: int


class MCPClientManager:
    """
    MCP 客戶端管理器
    
    提供統一的 MCP 服務接口，解決原有系統的並發安全性和安全漏洞問題
    """
    
    def __init__(self, max_sessions_per_server: int = 3,
                 session_timeout: float = 300.0,
                 request_timeout: float = 30.0):
        """
        初始化 MCP 客戶端管理器
        
        Args:
            max_sessions_per_server: 每個服務器的最大會話數
            session_timeout: 會話超時時間（秒）
            request_timeout: 請求超時時間（秒）
        """
        self.security_validator = MCPSecurityValidator()
        self.session_pool = MCPSessionPool(
            security_validator=self.security_validator,
            max_sessions_per_server=max_sessions_per_server,
            session_timeout=session_timeout,
            request_timeout=request_timeout
        )
        
        # 統計信息
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
        
        logger.info("🎯 MCP 客戶端管理器已初始化")
    
    async def call_tool(self, server: str, tool: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        調用 MCP 工具（向下兼容接口）
        
        Args:
            server: 服務器名稱
            tool: 工具名稱  
            params: 參數字典
            
        Returns:
            Dict: 標準化響應格式
        """
        self._total_requests += 1
        
        try:
            # 安全驗證
            if not self._validate_request(server, tool, params):
                self._failed_requests += 1
                return {"success": False, "error": "請求未通過安全驗證"}
            
            # 執行請求
            result = await self.session_pool.execute_request(
                server_name=server,
                method="tools/call",
                params={"name": tool, "arguments": params}
            )
            
            if result.get("success"):
                self._successful_requests += 1
                logger.info(f"✅ 工具調用成功: {server}.{tool}")
            else:
                self._failed_requests += 1
                logger.error(f"❌ 工具調用失敗: {server}.{tool}, 錯誤: {result.get('error')}")
            
            return result
            
        except Exception as e:
            self._failed_requests += 1
            logger.error(f"❌ 工具調用異常: {server}.{tool}, 錯誤: {e}")
            return {"success": False, "error": str(e)}
    
    async def list_tools(self, server: str = "postgres") -> Dict[str, Any]:
        """
        列出服務器可用工具
        
        Args:
            server: 服務器名稱
            
        Returns:
            Dict: 工具列表響應
        """
        try:
            # 安全驗證
            if not self.security_validator.validate_server_config(server, "", []):
                return {"success": False, "error": "服務器未通過安全驗證"}
            
            result = await self.session_pool.execute_request(
                server_name=server,
                method="tools/list",
                params={}
            )
            
            logger.info(f"📋 工具列表獲取: {server}, 成功: {result.get('success')}")
            return result
            
        except Exception as e:
            logger.error(f"❌ 獲取工具列表失敗: {server}, 錯誤: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_server_info(self, server: str = "postgres") -> Dict[str, Any]:
        """
        獲取服務器信息
        
        Args:
            server: 服務器名稱
            
        Returns:
            Dict: 服務器信息
        """
        try:
            # 獲取工具列表
            tools_result = await self.list_tools(server)
            
            if tools_result.get("success"):
                # 獲取統計信息
                pool_stats = self.session_pool.get_pool_stats()
                server_sessions = pool_stats.get("servers", {}).get(server, 0)
                
                return {
                    "success": True,
                    "server_name": server,
                    "protocol": "STDIO (官方 MCP SDK)",
                    "status": "active" if server_sessions > 0 else "inactive",
                    "tools": tools_result.get("tools", []),
                    "connection_count": server_sessions,
                    "mcp_compliant": True,
                    "security_validated": True
                }
            else:
                return tools_result
                
        except Exception as e:
            logger.error(f"❌ 獲取服務器信息失敗: {server}, 錯誤: {e}")
            return {"success": False, "error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """
        系統健康檢查
        
        Returns:
            Dict: 健康狀態報告
        """
        try:
            pool_stats = self.session_pool.get_pool_stats()
            success_rate = (
                self._successful_requests / max(self._total_requests, 1) * 100
            )
            
            # 檢查關鍵服務器
            postgres_info = await self.get_server_info("postgres")
            
            overall_status = "healthy"
            if success_rate < 90:
                overall_status = "degraded"
            if not postgres_info.get("success"):
                overall_status = "unhealthy"
            
            return {
                "success": True,
                "overall_status": overall_status,
                "timestamp": asyncio.get_event_loop().time(),
                "statistics": {
                    "total_requests": self._total_requests,
                    "successful_requests": self._successful_requests,
                    "failed_requests": self._failed_requests,
                    "success_rate": f"{success_rate:.2f}%"
                },
                "pool_status": pool_stats,
                "servers": {
                    "postgres": postgres_info.get("status", "unknown")
                },
                "security": {
                    "validator_active": True,
                    "whitelist_enabled": True,
                    "request_validation": True
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 健康檢查失敗: {e}")
            return {
                "success": False,
                "overall_status": "error",
                "error": str(e)
            }
    
    async def close_all_connections(self):
        """關閉所有連接"""
        try:
            await self.session_pool.close_all_sessions()
            logger.info("🔌 所有 MCP 連接已關閉")
        except Exception as e:
            logger.error(f"❌ 關閉連接失敗: {e}")
    
    def _validate_request(self, server: str, tool: str, params: Dict[str, Any]) -> bool:
        """驗證請求的安全性"""
        try:
            # 檢查服務器名稱
            if not server or not isinstance(server, str):
                logger.error("❌ 無效的服務器名稱")
                return False
            
            # 檢查工具名稱
            if not tool or not isinstance(tool, str):
                logger.error("❌ 無效的工具名稱")
                return False
            
            # 檢查參數
            if not isinstance(params, dict):
                logger.error("❌ 無效的參數格式")
                return False
            
            # 安全驗證
            secure_config = self.security_validator.get_secure_config(server)
            if not secure_config:
                logger.error(f"❌ 服務器 '{server}' 未通過安全驗證")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 請求驗證失敗: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """獲取統計信息"""
        pool_stats = self.session_pool.get_pool_stats()
        success_rate = (
            self._successful_requests / max(self._total_requests, 1) * 100
        )
        
        return {
            "client_stats": {
                "total_requests": self._total_requests,
                "successful_requests": self._successful_requests,
                "failed_requests": self._failed_requests,
                "success_rate": f"{success_rate:.2f}%"
            },
            "pool_stats": pool_stats,
            "security_stats": {
                "cache_size": len(self.security_validator.validation_cache),
                "allowed_servers": len(self.security_validator.ALLOWED_MCP_SERVERS)
            }
        }


# 單例模式
_mcp_client_manager: Optional[MCPClientManager] = None


async def get_mcp_client_manager() -> MCPClientManager:
    """獲取 MCP 客戶端管理器實例（單例）"""
    global _mcp_client_manager
    
    if _mcp_client_manager is None:
        _mcp_client_manager = MCPClientManager()
        logger.info("🏗️ MCP 客戶端管理器實例已創建")
    
    return _mcp_client_manager


# 向下兼容的函數接口
async def call_mcp_tool(server: str, tool: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """向下兼容的工具調用函數"""
    manager = await get_mcp_client_manager()
    return await manager.call_tool(server, tool, params)


async def list_mcp_tools(server: str = "postgres") -> Dict[str, Any]:
    """向下兼容的工具列表函數"""
    manager = await get_mcp_client_manager()
    return await manager.list_tools(server)


async def get_mcp_server_info(server: str = "postgres") -> Dict[str, Any]:
    """向下兼容的服務器信息函數"""
    manager = await get_mcp_client_manager()
    return await manager.get_server_info(server)