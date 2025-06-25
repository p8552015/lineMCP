"""
新一代 MCP (Model Context Protocol) 客戶端模組
基於官方 Python SDK 重新打造，解決並發安全性和生產環境可靠性問題

主要組件：
- MCPClientManager: 統一客戶端管理器
- MCPSessionPool: 會話池管理  
- MCPTransportHandler: 傳輸層處理
- MCPSecurityValidator: 安全驗證器
- MCPMessageSerializer: 訊息序列化器
"""

from .client_manager import MCPClientManager, get_mcp_client_manager
from .session_pool import MCPSessionPool
from .security_validator import MCPSecurityValidator

__all__ = [
    "MCPClientManager",
    "MCPSessionPool", 
    "MCPSecurityValidator",
    "get_mcp_client_manager",
]