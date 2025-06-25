"""
MCP 會話池管理器
解決並發安全性問題，實現請求隊列和響應匹配機制
"""

import asyncio
import uuid
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Dict, Optional, Any, Set
from enum import Enum

import structlog
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from .asyncio_fix import suppress_mcp_errors

from .security_validator import MCPSecurityValidator

logger = structlog.get_logger()


class SessionStatus(Enum):
    """會話狀態枚舉"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    ERROR = "error"
    CLOSED = "closed"


@dataclass
class MCPSession:
    """MCP 會話包裝器"""
    session_id: str
    server_name: str
    client_session: ClientSession
    exit_stack: AsyncExitStack
    status: SessionStatus
    created_at: float
    last_used_at: float
    request_count: int = 0
    error_count: int = 0


@dataclass 
class PendingRequest:
    """待處理的請求"""
    request_id: str
    method: str
    params: Dict[str, Any]
    future: asyncio.Future
    created_at: float
    timeout: float = 30.0


class MCPSessionPool:
    """MCP 會話池管理器 - 解決並發安全性問題"""
    
    def __init__(self, security_validator: MCPSecurityValidator, 
                 max_sessions_per_server: int = 3,
                 session_timeout: float = 300.0,
                 request_timeout: float = 30.0):
        """
        初始化會話池
        
        Args:
            security_validator: 安全驗證器
            max_sessions_per_server: 每個服務器的最大會話數
            session_timeout: 會話超時時間（秒）
            request_timeout: 請求超時時間（秒）
        """
        self.security_validator = security_validator
        self.max_sessions_per_server = max_sessions_per_server
        self.session_timeout = session_timeout
        self.request_timeout = request_timeout
        
        # 會話管理
        self._sessions: Dict[str, MCPSession] = {}
        self._server_sessions: Dict[str, Set[str]] = {}
        self._session_locks: Dict[str, asyncio.Lock] = {}
        
        # 請求隊列管理 - 解決 STDIO 並發問題
        self._request_queues: Dict[str, asyncio.Queue] = {}
        self._pending_requests: Dict[str, PendingRequest] = {}
        self._session_cleanup_queues: Dict[str, asyncio.Queue] = {}  # 新增：會話清理隊列
        self._queue_processors: Dict[str, asyncio.Task] = {}
        
        # 全局鎖
        self._global_lock = asyncio.Lock()
        
        # 健康檢查任務
        self._health_check_task: Optional[asyncio.Task] = None
        self._start_health_check()
        
        logger.info("🏊 MCP 會話池已初始化", 
                   max_sessions=max_sessions_per_server,
                   session_timeout=session_timeout)
    
    async def get_session(self, server_name: str) -> Optional[MCPSession]:
        """
        獲取或創建 MCP 會話
        
        Args:
            server_name: 服務器名稱
            
        Returns:
            MCPSession: 會話實例，失敗返回 None
        """
        async with self._global_lock:
            try:
                # 檢查是否有可用的會話
                available_session = await self._find_available_session(server_name)
                if available_session:
                    available_session.last_used_at = asyncio.get_event_loop().time()
                    logger.info(f"♻️ 復用會話: {server_name}")
                    return available_session
                
                # 檢查會話數量限制
                server_session_count = len(self._server_sessions.get(server_name, set()))
                if server_session_count >= self.max_sessions_per_server:
                    # 清理最舊的會話
                    await self._cleanup_oldest_session(server_name)
                
                # 創建新會話
                return await self._create_new_session(server_name)
                
            except Exception as e:
                logger.error(f"❌ 獲取會話失敗: {server_name}, 錯誤: {e}")
                return None
    
    async def execute_request(self, server_name: str, method: str, 
                            params: Dict[str, Any]) -> Dict[str, Any]:
        """
        執行 MCP 請求（並發安全）
        
        Args:
            server_name: 服務器名稱
            method: MCP 方法
            params: 請求參數
            
        Returns:
            Dict: 響應結果
        """
        request_id = str(uuid.uuid4())
        
        try:
            # 確保請求隊列存在
            await self._ensure_request_queue(server_name)
            
            # 創建待處理請求
            future = asyncio.Future()
            pending_request = PendingRequest(
                request_id=request_id,
                method=method,
                params=params,
                future=future,
                created_at=asyncio.get_event_loop().time(),
                timeout=self.request_timeout
            )
            
            # 加入請求隊列
            self._pending_requests[request_id] = pending_request
            await self._request_queues[server_name].put(pending_request)
            
            logger.info(f"📤 請求已加入隊列: {server_name}.{method}", request_id=request_id)
            
            # 等待響應
            try:
                result = await asyncio.wait_for(future, timeout=self.request_timeout)
                logger.info(f"✅ 請求執行成功: {server_name}.{method}", request_id=request_id)
                return result
            except asyncio.TimeoutError:
                logger.error(f"⏰ 請求超時: {server_name}.{method}", request_id=request_id)
                return {"success": False, "error": "請求超時"}
            
        except Exception as e:
            logger.error(f"❌ 請求執行失敗: {server_name}.{method}, 錯誤: {e}")
            return {"success": False, "error": str(e)}
        finally:
            # 清理待處理請求
            self._pending_requests.pop(request_id, None)
    
    async def _ensure_request_queue(self, server_name: str):
        """確保請求隊列存在"""
        if server_name not in self._request_queues:
            self._request_queues[server_name] = asyncio.Queue()
            self._session_cleanup_queues[server_name] = asyncio.Queue()  # 為每個服務器創建清理隊列
            # 啟動隊列處理器
            processor = asyncio.create_task(self._process_request_queue(server_name))
            self._queue_processors[server_name] = processor
            logger.info(f"🔄 已創建請求隊列處理器: {server_name}")
    
    async def _process_request_queue(self, server_name: str):
        """處理請求隊列（解決 STDIO 並發問題）"""
        logger.info(f"🚀 啟動請求隊列處理器: {server_name}")
        
        while True:
            try:
                # 優先處理清理請求
                try:
                    session_id_to_close = self._session_cleanup_queues[server_name].get_nowait()
                    await self._do_close_session_in_owner_task(session_id_to_close)
                    self._session_cleanup_queues[server_name].task_done()
                    continue  # 處理完清理請求後繼續循環，優先處理下一個清理請求
                except asyncio.QueueEmpty:
                    pass  # 沒有清理請求，繼續處理正常請求
                
                # 從隊列獲取請求
                pending_request = await self._request_queues[server_name].get()
                
                # 檢查請求是否已超時
                current_time = asyncio.get_event_loop().time()
                if current_time - pending_request.created_at > pending_request.timeout:
                    pending_request.future.set_result({
                        "success": False, 
                        "error": "請求在隊列中超時"
                    })
                    continue
                
                # 獲取會話並執行請求
                session = await self.get_session(server_name)
                if not session:
                    pending_request.future.set_result({
                        "success": False,
                        "error": "無法獲取會話"
                    })
                    continue
                
                # 執行實際的 MCP 請求
                try:
                    result = await self._execute_mcp_request(
                        session, pending_request.method, pending_request.params
                    )
                    pending_request.future.set_result(result)
                    session.request_count += 1
                    
                except Exception as e:
                    logger.error(f"❌ MCP 請求執行錯誤: {e}")
                    pending_request.future.set_result({
                        "success": False,
                        "error": str(e)
                    })
                    session.error_count += 1
                
            except asyncio.CancelledError:
                logger.info(f"🛑 請求隊列處理器已取消: {server_name}")
                break
            except Exception as e:
                logger.error(f"❌ 請求隊列處理器錯誤: {server_name}, {e}")
                await asyncio.sleep(1)  # 避免瘋狂重試
    
    async def _do_close_session_in_owner_task(self, session_id: str):
        """內部方法：在會話擁有者任務中執行實際的會話關閉操作"""
        session = self._sessions.get(session_id)
        if not session:
            return
        
        async with suppress_mcp_errors():
            try:
                # 這是關鍵行，必須在創建該會話的任務上下文中執行
                await session.exit_stack.aclose() 
                
                # 從註冊表中移除（這些操作可以在任何任務中執行，但為原子性在此處完成）
                self._sessions.pop(session_id, None)
                self._session_locks.pop(session_id, None)
                if session.server_name in self._server_sessions:
                    self._server_sessions[session.server_name].discard(session_id)
                
                logger.info(f"🗑️ 會話已關閉 (由擁有者任務): {session.server_name}", session_id=session_id)
                
            except Exception as e:
                logger.error(f"❌ 關閉會話失敗 (由擁有者任務): {session_id}, 錯誤: {e}")
    
    async def _execute_mcp_request(self, session: MCPSession, method: str, 
                                 params: Dict[str, Any]) -> Dict[str, Any]:
        """執行實際的 MCP 請求"""
        try:
            if method == "tools/list":
                result = await session.client_session.list_tools()
                return {
                    "success": True,
                    "tools": [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.inputSchema
                        }
                        for tool in result.tools
                    ]
                }
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                result = await session.client_session.call_tool(tool_name, arguments)
                return {
                    "success": True,
                    "content": result.content
                }
            
            else:
                return {"success": False, "error": f"不支援的方法: {method}"}
                
        except Exception as e:
            logger.error(f"❌ MCP 請求執行失敗: {method}, 錯誤: {e}")
            return {"success": False, "error": str(e)}
    
    async def _find_available_session(self, server_name: str) -> Optional[MCPSession]:
        """查找可用的會話"""
        server_sessions = self._server_sessions.get(server_name, set())
        
        for session_id in server_sessions:
            session = self._sessions.get(session_id)
            if session and session.status == SessionStatus.ACTIVE:
                return session
        
        return None
    
    async def _create_new_session(self, server_name: str) -> Optional[MCPSession]:
        """創建新的 MCP 會話"""
        try:
            # 安全驗證
            secure_config = self.security_validator.get_secure_config(server_name)
            if not secure_config:
                logger.error(f"❌ 服務器 '{server_name}' 未通過安全驗證")
                return None
            
            # 創建會話 ID 和退出堆疊
            session_id = str(uuid.uuid4())
            exit_stack = AsyncExitStack()
            
            # 配置服務器參數
            server_args = secure_config.args.copy()
            # 為不同服務器添加特定參數
            if server_name == "postgres":
                # PostgreSQL 連接字符串
                connection_string = "postgresql://admin:admin@localhost:5432/mydb"
                server_args.append(connection_string)
            
            server_params = StdioServerParameters(
                command=secure_config.command,
                args=server_args,
                env=secure_config.environment_vars
            )
            
            # 建立 STDIO 連接
            read_stream, write_stream = await exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            
            # 創建客戶端會話
            client_session = await exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            
            # 初始化會話
            await client_session.initialize()
            
            # 創建會話實例
            current_time = asyncio.get_event_loop().time()
            session = MCPSession(
                session_id=session_id,
                server_name=server_name,
                client_session=client_session,
                exit_stack=exit_stack,
                status=SessionStatus.ACTIVE,
                created_at=current_time,
                last_used_at=current_time
            )
            
            # 註冊會話
            self._sessions[session_id] = session
            self._session_locks[session_id] = asyncio.Lock()
            
            if server_name not in self._server_sessions:
                self._server_sessions[server_name] = set()
            self._server_sessions[server_name].add(session_id)
            
            logger.info(f"✅ 新會話已創建: {server_name}", session_id=session_id)
            return session
            
        except Exception as e:
            logger.error(f"❌ 創建會話失敗: {server_name}, 錯誤: {e}")
            # 清理資源
            try:
                await exit_stack.aclose()
            except:
                pass
            return None
    
    async def _cleanup_oldest_session(self, server_name: str):
        """清理最舊的會話"""
        server_sessions = self._server_sessions.get(server_name, set())
        if not server_sessions:
            return
        
        # 找到最舊的會話
        oldest_session = None
        oldest_time = float('inf')
        
        for session_id in server_sessions:
            session = self._sessions.get(session_id)
            if session and session.last_used_at < oldest_time:
                oldest_time = session.last_used_at
                oldest_session = session
        
        if oldest_session:
            await self.close_session(oldest_session.session_id)
    
    async def close_session(self, session_id: str):
        """關閉指定會話"""
        # 獲取會話實例
        session = self._sessions.get(session_id)
        if not session:
            return
        
        try:
            # 將會話狀態設置為關閉中，防止新請求使用
            session.status = SessionStatus.CLOSED

            # 將關閉請求委託給創建該會話的處理器任務
            server_name = session.server_name
            if server_name in self._session_cleanup_queues:
                await self._session_cleanup_queues[server_name].put(session_id)
                logger.info(f"📤 會話關閉請求已加入清理隊列: {server_name}", session_id=session_id)
            else:
                # 如果沒有對應的處理器隊列（例如，處理器已終止），則直接嘗試關閉
                logger.warning(f"⚠️ 無法找到清理隊列，直接嘗試關閉會話 (可能導致錯誤): {session_id}")
                await self._do_close_session_in_owner_task(session_id)  # 嘗試直接關閉

        except Exception as e:
            logger.error(f"❌ 關閉會話失敗: {session_id}, 錯誤: {e}")
    
    async def close_all_sessions(self):
        """關閉所有會話"""
        session_ids = list(self._sessions.keys())
        for session_id in session_ids:
            await self.close_session(session_id)  # 委託給擁有者任務
        
        # 等待所有清理隊列處理完成，確保所有會話都已嘗試關閉
        for q in self._session_cleanup_queues.values():
            try:
                await asyncio.wait_for(q.join(), timeout=5.0)  # 5秒超時
            except asyncio.TimeoutError:
                logger.warning("⚠️ 清理隊列等待超時，強制繼續")
        
        # 取消隊列處理器
        for processor in self._queue_processors.values():
            processor.cancel()
        
        # 取消健康檢查
        if self._health_check_task:
            self._health_check_task.cancel()
        
        logger.info("🧹 所有會話已關閉")
    
    def _start_health_check(self):
        """啟動健康檢查任務"""
        async def health_check_loop():
            while True:
                try:
                    await asyncio.sleep(60)  # 每分鐘檢查一次
                    await self._perform_health_check()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"❌ 健康檢查錯誤: {e}")
        
        self._health_check_task = asyncio.create_task(health_check_loop())
    
    async def _perform_health_check(self):
        """執行健康檢查"""
        current_time = asyncio.get_event_loop().time()
        expired_sessions = []
        
        for session_id, session in self._sessions.items():
            # 檢查會話是否超時
            if current_time - session.last_used_at > self.session_timeout:
                expired_sessions.append(session_id)
            
            # 檢查錯誤率
            if session.request_count > 0:
                error_rate = session.error_count / session.request_count
                if error_rate > 0.5:  # 錯誤率超過 50%
                    logger.warning(f"⚠️ 會話錯誤率過高: {session.server_name}", 
                                 error_rate=error_rate, session_id=session_id)
        
        # 清理過期會話
        for session_id in expired_sessions:
            await self.close_session(session_id)
            logger.info(f"🕐 過期會話已清理: {session_id}")
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """獲取池統計信息"""
        return {
            "total_sessions": len(self._sessions),
            "active_sessions": len([s for s in self._sessions.values() 
                                  if s.status == SessionStatus.ACTIVE]),
            "servers": {
                server: len(sessions) 
                for server, sessions in self._server_sessions.items()
            },
            "pending_requests": len(self._pending_requests),
            "queue_processors": len(self._queue_processors)
        }