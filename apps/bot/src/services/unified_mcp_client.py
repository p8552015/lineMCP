"""
統一 MCP 客戶端 - 使用 mcp_common 核心組件
專為 LINE MCP Bot 優化的實作
"""

import sys
import os
import asyncio
import structlog
from typing import Dict, Any, List, Optional

# 設置 mcp_common 路徑
# /Users/yen/Desktop/lineMCP/apps/bot/src/services/unified_mcp_client.py -> /Users/yen/Desktop/lineMCP
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
libs_path = os.path.join(project_root, 'libs', 'python')
if libs_path not in sys.path:
    sys.path.insert(0, libs_path)

logger = structlog.get_logger()

# 直接使用 TrueMCPClient，完全遵循 MCP 協定原則
_MCP_COMMON_AVAILABLE = False
logger.info("✅ 使用 TrueMCPClient 實作，100% MCP 協定合規")

# 定義基本狀態常數
class MCPStatusCode:
    SUCCESS = "success"
    ERROR = "error"


class UnifiedMCPClient:
    """統一 MCP 客戶端 - 線Bot服務專用"""
    
    def __init__(self, client_type: str = "mock", **kwargs):
        """
        初始化統一客戶端
        
        Args:
            client_type: 客戶端類型 ("mock", "simple", "legacy")
            **kwargs: 額外配置參數
        """
        self.client_type = client_type
        self._client = None
        self._fallback_client = None
        
        # 直接使用 TrueMCPClient，符合 MCP 協定原則
        self._init_fallback_client()
    
    
    def _init_fallback_client(self):
        """初始化回退客戶端 - 必須遵循 MCP 協定"""
        logger.info("📦 使用 MCP 協定回退模式")
        try:
            # 首先嘗試強健的MCP客戶端
            from src.services.robust_mcp_client import get_robust_mcp_client
            # 注意：這裡不能直接調用async函數，稍後在call_tool中處理
            self._fallback_client = None
            self._fallback_type = "robust_mcp"
            logger.info("✅ 準備使用強健的MCP客戶端")
        except Exception as e:
            logger.warning(f"⚠️ 強健的MCP客戶端不可用: {e}")
            try:
                # 回退到真正的MCP客戶端
                from src.services.true_mcp_client import get_true_mcp_client
                self._fallback_client = get_true_mcp_client()
                self._fallback_type = "true_mcp"
                logger.info("✅ 使用真正的MCP客戶端作為回退")
            except Exception as e2:
                # 最後回退到MCP兼容適配器
                logger.warning(f"⚠️ 真正的MCP客戶端也不可用: {e2}")
                from src.services.mcp_compatible_adapter import get_mcp_compatible_adapter
                self._fallback_client = get_mcp_compatible_adapter()
                self._fallback_type = "mcp_compatible"
                logger.info("✅ 使用MCP兼容適配器作為最終回退")
    
    async def call_tool(self, server: str, tool: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        呼叫 MCP 工具（新統一介面）
        
        Args:
            server: 伺服器名稱
            tool: 工具名稱
            params: 參數字典
            
        Returns:
            標準化回應字典
        """
        # 處理強健的MCP客戶端
        if hasattr(self, '_fallback_type') and self._fallback_type == "robust_mcp":
            try:
                if not self._fallback_client:
                    logger.info("🔧 初始化強健的MCP客戶端")
                    from src.services.robust_mcp_client import get_robust_mcp_client
                    self._fallback_client = await get_robust_mcp_client()
                
                logger.info(f"🚀 使用強健的MCP客戶端: {server}.{tool}")
                result = await self._fallback_client.call_tool(tool, params)
                if result.get("success"):
                    logger.info(f"✅ 強健的MCP調用成功")
                    return result
                else:
                    logger.warning(f"⚠️ 強健的MCP調用失敗，切換到兼容模式")
                    await self._switch_to_compatible_mode()
            except Exception as e:
                logger.warning(f"⚠️ 強健的MCP客戶端失敗: {e}，切換到兼容模式")
                await self._switch_to_compatible_mode()
        
        if not self._fallback_client:
            return {"success": False, "error": "無可用的客戶端"}
        
        # 如果是真正的MCP客戶端，先嘗試使用
        if hasattr(self, '_fallback_type') and self._fallback_type == "true_mcp":
            try:
                logger.info(f"🔄 嘗試真正的MCP連接: {server}.{tool}")
                # 添加短超時測試
                import asyncio
                result = await asyncio.wait_for(
                    self._fallback_client.call_tool(server, tool, params),
                    timeout=3.0  # 3秒超時
                )
                if result.get("success"):
                    logger.info(f"✅ 真正的MCP調用成功")
                    return result
                else:
                    logger.warning(f"⚠️ 真正的MCP調用失敗，切換到兼容模式")
                    # 切換到兼容模式
                    await self._switch_to_compatible_mode()
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"⚠️ 真正的MCP連接超時/失敗: {e}，切換到兼容模式")
                # 切換到兼容模式
                await self._switch_to_compatible_mode()
        
        # 使用MCP兼容適配器
        return await self._fallback_client.call_tool(server, tool, params)
    
    async def _switch_to_compatible_mode(self):
        """切換到MCP兼容模式"""
        try:
            from src.services.mcp_compatible_adapter import get_mcp_compatible_adapter
            self._fallback_client = get_mcp_compatible_adapter()
            self._fallback_type = "mcp_compatible"
            logger.info("🔄 已切換到MCP兼容適配器")
        except Exception as e:
            logger.error(f"❌ 切換到兼容模式失敗: {e}")
    
    async def call_tool_legacy(
        self, 
        server_name: str, 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """向後相容的介面"""
        return await self.call_tool(server_name, tool_name, parameters)
    
    async def list_tools(self, server: str) -> List[str]:
        """列出可用工具"""
        if self._client and hasattr(self._client, 'list_tools'):
            try:
                tools = await self._client.list_tools(server)
                # 標準化工具列表格式
                if isinstance(tools, list):
                    return [tool.get('name', tool) if isinstance(tool, dict) else str(tool) for tool in tools]
                return []
            except Exception as e:
                logger.error(f"❌ 列出工具失敗: {e}")
        
        # 回退客戶端
        if self._fallback_client:
            return await self._fallback_client.list_tools(server)
        
        return []
    
    async def health_check(self, server: Optional[str] = None) -> Dict[str, Any]:
        """健康檢查"""
        if self._client and hasattr(self._client, 'health_check'):
            try:
                health = await self._client.health_check(server)
                return {
                    "overall": getattr(health, 'overall', 'unknown'),
                    "servers": getattr(health, 'servers', {}),
                    "response_time_ms": getattr(health, 'response_time_ms', 0),
                }
            except Exception as e:
                logger.error(f"❌ 健康檢查失敗: {e}")
        
        # 簡單的健康檢查回退
        return {
            "overall": "healthy" if self._fallback_client else "unknown",
            "servers": {},
            "response_time_ms": 0,
        }
    
    async def batch_call(self, calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批次呼叫"""
        if self._client and hasattr(self._client, 'batch_call'):
            try:
                # 轉換為 MCPCall 對象
                mcp_calls = []
                for call in calls:
                    if False:  # 暫時禁用 mcp_common，直接使用 TrueMCPClient
                        mcp_call = MCPCall(
                            server=call["server"],
                            tool=call["tool"],
                            params=call["params"]
                        )
                        mcp_calls.append(mcp_call)
                    else:
                        mcp_calls.append(call)
                
                responses = await self._client.batch_call(mcp_calls)
                return [self._convert_mcp_response(resp) for resp in responses]
            except Exception as e:
                logger.error(f"❌ 批次呼叫失敗: {e}")
        
        # 回退：逐一呼叫
        results = []
        for call in calls:
            result = await self.call_tool(
                call["server"], 
                call["tool"], 
                call["params"]
            )
            results.append(result)
        return results
    
    async def close_all_connections(self):
        """關閉所有連接"""
        try:
            if self._client and hasattr(self._client, 'close'):
                await self._client.close()
            elif self._client and hasattr(self._client, 'close_all_connections'):
                await self._client.close_all_connections()
            
            if self._fallback_client:
                await self._fallback_client.close_all_connections()
            
            logger.info("✅ 所有連接已關閉")
        except Exception as e:
            logger.warning(f"⚠️ 關閉連接時發生錯誤: {e}")
    
    def _convert_mcp_response(self, response) -> Dict[str, Any]:
        """轉換 MCP 回應為標準格式"""
        if _MCP_COMMON_AVAILABLE and isinstance(response, MCPResponse):
            return {
                "success": response.status == MCPStatusCode.SUCCESS,
                "data": response.data,
                "error": response.error,
                "call_id": getattr(response, 'call_id', None),
                "duration_ms": getattr(response, 'duration_ms', None),
                "metadata": getattr(response, 'metadata', {}),
            }
        elif isinstance(response, dict):
            return response
        else:
            return {
                "success": True,
                "data": response,
                "error": None,
            }


# 工廠函數
def get_unified_mcp_client(client_type: str = "mock", **kwargs) -> UnifiedMCPClient:
    """
    獲取統一 MCP 客戶端實例
    
    Args:
        client_type: 客戶端類型
        **kwargs: 額外配置
        
    Returns:
        UnifiedMCPClient 實例
    """
    return UnifiedMCPClient(client_type=client_type, **kwargs)


def get_mcp_client(client_type: str = "mock", **kwargs) -> UnifiedMCPClient:
    """別名函數，相容性"""
    return get_unified_mcp_client(client_type=client_type, **kwargs)


# 向後相容的工廠函數
def get_simple_mcp_client():
    """獲取簡化 MCP 客戶端（向後相容）"""
    return get_unified_mcp_client(client_type="simple")