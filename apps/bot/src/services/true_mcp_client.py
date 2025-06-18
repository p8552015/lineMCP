"""
真正的 MCP 客戶端 - 嚴格遵循 MCP 協定
必須透過 MCP Server 進行所有操作，不允許直接資料庫連接
"""

import asyncio
import structlog
from typing import Dict, Any, List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = structlog.get_logger()


class TrueMCPClient:
    """嚴格遵循 MCP 協定的客戶端 - 只能透過 MCP Server 通訊"""
    
    def __init__(self):
        """初始化真正的 MCP 客戶端"""
        self.sessions: Dict[str, ClientSession] = {}
        self.session_contexts: Dict[str, Any] = {}
        
        # MCP Server 配置 - 必須透過 MCP 協定連接
        self.servers = {
            'sqlite': {
                'command': '/usr/bin/python3',
                'args': ['/Users/yen/Desktop/lineMCP/apps/servers/src/sqlite/src/mcp_server_sqlite/server.py', 
                        '/Users/yen/Desktop/lineMCP/apps/servers/src/sqlite/test.db'],
                'cwd': '/Users/yen/Desktop/lineMCP/apps/servers/src/sqlite',
                'protocol': 'stdio',
                'env': {
                    'PYTHONPATH': '/Users/yen/Desktop/lineMCP/apps/servers/src/sqlite/src',
                    'PYTHONUNBUFFERED': '1'
                }
            },
            'postgres': {
                'command': 'node',
                'args': ['/Users/yen/Desktop/lineMCP/apps/servers/src/postgres/dist/index.js', 
                        'postgresql://localhost:5432/mcp_test'],
                'cwd': '/Users/yen/Desktop/lineMCP/apps/servers/src/postgres',
                'protocol': 'stdio'
            }
        }
        
        logger.info("✅ 真正的 MCP 客戶端已初始化 - 嚴格遵循 MCP 協定")
    
    async def _create_mcp_session(self, server_name: str) -> bool:
        """創建真正的 MCP session - 必須透過 MCP 協定"""
        server_config = self.servers.get(server_name)
        if not server_config:
            logger.error(f"❌ 未知的 MCP 伺服器: {server_name}")
            return False
        
        try:
            logger.info(f"🔗 建立 MCP 連接到 {server_name}", 
                       command=server_config['command'],
                       args=server_config['args'])
            
            # 使用 MCP STDIO 協定建立連接
            server_params = StdioServerParameters(
                command=server_config['command'],
                args=server_config['args'],
                cwd=server_config.get('cwd'),
                env=server_config.get('env')
            )
            
            # 使用 async with 正確管理 MCP 客戶端生命週期
            # 我們將 context manager 保存起來，在清理時正確關閉
            session_context = stdio_client(server_params)
            
            # 異步進入上下文
            read, write = await session_context.__aenter__()
            
            try:
                # 建立 MCP 客戶端 session
                session = ClientSession(read, write)
                await session.initialize()
                
                # 保存 session 和 context 供後續使用
                self.sessions[server_name] = session
                self.session_contexts[server_name] = session_context
                
            except Exception as session_error:
                # 如果 session 建立失敗，正確清理 context
                try:
                    await session_context.__aexit__(type(session_error), session_error, session_error.__traceback__)
                except Exception as cleanup_error:
                    logger.warning(f"清理 MCP context 時發生錯誤: {cleanup_error}")
                raise session_error
            
            logger.info(f"✅ 成功建立 MCP 連接: {server_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ MCP 連接失敗 {server_name}: {e}", exc_info=True)
            return False
    
    async def connect_to_server(self, server_name: str) -> bool:
        """連接到 MCP Server - 只允許透過 MCP 協定"""
        if server_name in self.sessions:
            logger.info(f"🔄 重用現有的 MCP session: {server_name}")
            return True
        
        return await self._create_mcp_session(server_name)
    
    async def call_tool(self, server_name: str, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """透過 MCP 協定呼叫工具 - 每次呼叫使用獨立連接避免異步上下文問題"""
        import asyncio
        
        try:
            logger.info(f"🛠️ 開始 MCP 工具呼叫", server=server_name, tool=tool_name)
            
            # 為每次調用創建獨立的 MCP 連接
            if server_name not in self.servers:
                error_msg = f"未知的 MCP 伺服器: {server_name}"
                logger.error(f"❌ {error_msg}")
                return {"success": False, "error": error_msg}
            
            server_config = self.servers[server_name]
            logger.info(f"🔧 MCP 伺服器配置", command=server_config['command'], args=server_config['args'])
            
            server_params = StdioServerParameters(
                command=server_config['command'],
                args=server_config['args'],
                cwd=server_config.get('cwd'),
                env=server_config.get('env')
            )
            
            logger.info(f"📡 嘗試建立 STDIO 連接到 {server_name}")
            
            # 使用 async with 確保連接正確管理
            try:
                async with stdio_client(server_params) as (read_stream, write_stream):
                    logger.info(f"✅ STDIO 連接建立成功")
                    
                    # 建立 session
                    session = ClientSession(read_stream, write_stream)
                    logger.info(f"🔗 初始化 MCP session")
                    await session.initialize()
                    logger.info(f"✅ MCP session 初始化完成")
                    
                    # 列出可用工具
                    logger.info(f"📋 列出可用工具")
                    tools_result = await session.list_tools()
                    available_tools = [tool.name for tool in tools_result.tools]
                    logger.info(f"📋 可用的 MCP 工具: {available_tools}")
                    
                    # 驗證工具是否存在
                    if tool_name not in available_tools:
                        error_msg = f"MCP 工具 '{tool_name}' 不存在。可用工具: {available_tools}"
                        logger.error(f"❌ {error_msg}")
                        return {"success": False, "error": error_msg}
                    
                    # 執行工具調用，添加超時保護
                    logger.info(f"⚡ 執行 MCP 工具呼叫: {tool_name}")
                    try:
                        result = await asyncio.wait_for(
                            session.call_tool(tool_name, parameters),
                            timeout=5.0  # 增加到5秒超時
                        )
                        logger.info(f"✅ MCP 工具呼叫完成")
                    except asyncio.TimeoutError:
                        error_msg = f"MCP 工具呼叫超時 {server_name}.{tool_name}"
                        logger.error(f"⏰ {error_msg}")
                        return {"success": False, "error": error_msg}
                    
                    if hasattr(result, 'content'):
                        logger.info(f"✅ MCP 工具呼叫成功: {server_name}.{tool_name}")
                        return {
                            "success": True,
                            "data": result.content,
                            "is_error": getattr(result, 'isError', False),
                            "mcp_protocol": True  # 標記這是真正的 MCP 呼叫
                        }
                    else:
                        return {
                            "success": True,
                            "data": result,
                            "is_error": False,
                            "mcp_protocol": True
                        }
                    
            except Exception as stdio_error:
                logger.error(f"❌ STDIO 連接失敗: {stdio_error}", exc_info=True)
                return {"success": False, "error": f"STDIO 連接失敗: {stdio_error}"}
                
        except Exception as e:
            error_msg = f"MCP 工具呼叫失敗 - {server_name}.{tool_name}: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def list_tools(self, server_name: str) -> List[str]:
        """透過 MCP 協定列出工具"""
        try:
            if not await self.connect_to_server(server_name):
                logger.error(f"❌ 無法連接到 MCP 伺服器: {server_name}")
                return []
            
            session = self.sessions[server_name]
            tools_result = await session.list_tools()
            tools = [tool.name for tool in tools_result.tools]
            
            logger.info(f"📋 透過 MCP 協定列出工具: {server_name} -> {tools}")
            return tools
            
        except Exception as e:
            logger.error(f"❌ 透過 MCP 列出工具失敗 {server_name}: {e}")
            return []
    
    async def get_server_info(self, server_name: str) -> Dict[str, Any]:
        """透過 MCP 協定獲取伺服器資訊"""
        try:
            if not await self.connect_to_server(server_name):
                return {"error": f"無法連接到 MCP 伺服器: {server_name}"}
            
            session = self.sessions[server_name]
            
            # 透過 MCP 協定獲取工具和資源
            tools_result = await session.list_tools()
            resources_result = await session.list_resources()
            
            return {
                "server_name": server_name,
                "protocol": "MCP",
                "tools": [
                    {
                        "name": tool.name, 
                        "description": tool.description or f"MCP 工具: {tool.name}"
                    } 
                    for tool in tools_result.tools
                ],
                "resources": [
                    {
                        "uri": res.uri, 
                        "name": res.name or "未命名資源"
                    } 
                    for res in (resources_result.resources if resources_result else [])
                ],
                "connection_type": "STDIO MCP",
                "mcp_compliant": True
            }
            
        except Exception as e:
            logger.error(f"❌ 獲取 MCP 伺服器資訊失敗 {server_name}: {e}")
            return {"error": str(e)}
    
    async def close_all_connections(self):
        """關閉所有 MCP 連接"""
        logger.info("🔌 關閉所有 MCP 連接...")
        
        # 關閉所有 MCP sessions
        for server_name, session in self.sessions.items():
            try:
                await session.close()
                logger.info(f"✅ 已關閉 MCP session: {server_name}")
            except Exception as e:
                logger.warning(f"⚠️ 關閉 MCP session 時發生錯誤 {server_name}: {e}")
        
        # 關閉所有 session contexts
        for server_name, context in self.session_contexts.items():
            try:
                await context.__aexit__(None, None, None)
                logger.info(f"✅ 已關閉 MCP context: {server_name}")
            except Exception as e:
                logger.warning(f"⚠️ 關閉 MCP context 時發生錯誤 {server_name}: {e}")
        
        # 清理
        self.sessions.clear()
        self.session_contexts.clear()
        logger.info("✅ 所有 MCP 連接已正確關閉")


# 單例模式 - 確保只有一個真正的 MCP 客戶端實例
_true_mcp_client = None


def get_true_mcp_client() -> TrueMCPClient:
    """獲取真正的 MCP 客戶端實例 - 嚴格遵循 MCP 協定"""
    global _true_mcp_client
    if _true_mcp_client is None:
        _true_mcp_client = TrueMCPClient()
    return _true_mcp_client