"""
狀態檢查指令處理器
處理 /status 指令的系統狀態檢查
"""
from typing import List
import structlog
from linebot.v3.messaging import Message, TextMessage

from src.domain.command_handler import CommandHandler, CommandContext
from src.services.error_handlers import ErrorContext

logger = structlog.get_logger()


class StatusCommandHandler(CommandHandler):
    """狀態檢查指令處理器"""
    
    def __init__(self, context: CommandContext):
        self.context = context
    
    @property
    def command_name(self) -> str:
        return "status"
    
    @property
    def description(self) -> str:
        return "檢查系統和服務的運行狀態"
    
    @property
    def aliases(self) -> List[str]:
        return ["health", "check"]
    
    def get_usage(self) -> str:
        return "/status"
    
    async def handle(self, user_id: str, args: List[str]) -> Message:
        """處理狀態檢查指令"""
        logger.info("執行系統狀態檢查", user_id=user_id)
        
        try:
            with ErrorContext("status_check") as ctx:
                ctx.add_context(user_id=user_id)
                
                # 檢查各個服務的狀態
                status_checks = await self._perform_status_checks()
                
                return self._format_status_report(status_checks)
                
        except Exception as e:
            logger.error(f"狀態檢查失敗: {e}", exc_info=True)
            return TextMessage(
                text="❌ 狀態檢查過程中發生錯誤\\n\\n"
                     "請聯絡系統管理員檢查服務狀態"
            )
    
    async def _perform_status_checks(self) -> dict:
        """執行各項狀態檢查"""
        status_checks = {
            "timestamp": self._get_current_time(),
            "mcp_connection": await self._check_mcp_connection(),
            "ai_service": self._check_ai_service(), 
            "database_service": self._check_database_service(),
            "services": self._check_internal_services()
        }
        
        return status_checks
    
    def _get_current_time(self) -> str:
        """獲取當前時間"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    async def _check_mcp_connection(self) -> dict:
        """檢查 MCP 連接狀態"""
        try:
            mcp_client = await self.context.get_mcp_client()
            
            # 嘗試簡單的查詢測試連接
            test_query = "SELECT 1 as test"
            result = await mcp_client.call_tool(
                "sqlite", "read_query", {"query": test_query}
            )
            
            if result:
                return {"status": "healthy", "message": "MCP 連接正常"}
            else:
                return {"status": "warning", "message": "MCP 連接異常"}
                
        except Exception as e:
            return {"status": "error", "message": f"MCP 連接失敗: {str(e)[:50]}"}
    
    def _check_ai_service(self) -> dict:
        """檢查 AI 服務狀態"""
        try:
            ai_service = self.context.ai_model_service
            if hasattr(ai_service, 'available_models'):
                model_count = len(getattr(ai_service, 'available_models', []))
                return {
                    "status": "healthy", 
                    "message": f"AI 服務正常，支援 {model_count} 個模型"
                }
            else:
                return {"status": "healthy", "message": "AI 服務已載入"}
                
        except Exception as e:
            return {"status": "error", "message": f"AI 服務異常: {str(e)[:50]}"}
    
    def _check_database_service(self) -> dict:
        """檢查資料庫服務狀態"""
        try:
            db_service = self.context.db_service
            if db_service:
                return {"status": "healthy", "message": "資料庫服務已初始化"}
            else:
                return {"status": "warning", "message": "資料庫服務未初始化"}
                
        except Exception as e:
            return {"status": "error", "message": f"資料庫服務異常: {str(e)[:50]}"}
    
    def _check_internal_services(self) -> dict:
        """檢查內部服務狀態"""
        services_status = []
        
        # 檢查各個服務
        services_to_check = [
            ("自然語言服務", self.context.nl_service),
            ("訊息格式化器", self.context.formatter),
            ("Flex建構器", self.context.flex_builder)
        ]
        
        healthy_count = 0
        total_count = len(services_to_check)
        
        for service_name, service in services_to_check:
            if service is not None:
                services_status.append(f"✅ {service_name}")
                healthy_count += 1
            else:
                services_status.append(f"❌ {service_name}")
        
        if healthy_count == total_count:
            status = "healthy"
        elif healthy_count > 0:
            status = "warning"
        else:
            status = "error"
        
        return {
            "status": status,
            "message": f"{healthy_count}/{total_count} 服務正常",
            "details": services_status
        }
    
    def _format_status_report(self, status_checks: dict) -> TextMessage:
        """格式化狀態報告"""
        response_lines = [
            "🔍 系統狀態檢查報告",
            "━━━━━━━━━━━━━━━━━━━━",
            f"🕐 檢查時間：{status_checks['timestamp']}",
            ""
        ]
        
        # 處理各項狀態檢查結果
        checks = [
            ("MCP 連接", status_checks['mcp_connection']),
            ("AI 服務", status_checks['ai_service']),
            ("資料庫服務", status_checks['database_service']),
            ("內部服務", status_checks['services'])
        ]
        
        overall_status = "healthy"
        
        for check_name, check_result in checks:
            status = check_result['status']
            message = check_result['message']
            
            # 選擇狀態圖示
            if status == "healthy":
                icon = "✅"
            elif status == "warning":
                icon = "⚠️"
                if overall_status == "healthy":
                    overall_status = "warning"
            else:
                icon = "❌"
                overall_status = "error"
            
            response_lines.append(f"{icon} {check_name}: {message}")
            
            # 如果有詳細資訊
            if 'details' in check_result:
                for detail in check_result['details']:
                    response_lines.append(f"   {detail}")
        
        # 添加整體狀態總結
        response_lines.append("")
        if overall_status == "healthy":
            response_lines.append("🎉 系統狀態良好，所有服務正常運行")
        elif overall_status == "warning":
            response_lines.append("⚠️ 系統部分服務有警告，建議檢查")
        else:
            response_lines.append("🚨 系統存在問題，請聯絡管理員")
        
        return TextMessage(text="\\n".join(response_lines))