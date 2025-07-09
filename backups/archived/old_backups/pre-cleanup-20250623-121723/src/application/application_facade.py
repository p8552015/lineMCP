"""
應用服務門面 (Application Facade)
提供統一的應用服務訪問入口
"""
from typing import Optional, Dict, Any
import structlog
from linebot.v3.messaging import Message

from .base_service import ApplicationServiceContext, get_application_context
from .messaging_service import MessagingApplicationService
from .query_service import QueryApplicationService
from .monitoring_service import MonitoringApplicationService
from src.domain.command_handler import CommandContext
from src.config import get_settings
from src.infrastructure.service_factory_interface import IServiceFactory

logger = structlog.get_logger()


class ApplicationFacade:
    """
    應用服務門面
    
    職責：
    - 提供統一的應用層入口
    - 協調多個應用服務之間的交互
    - 管理應用服務的生命週期
    - 提供高層次的業務操作介面
    """
    
    def __init__(self, service_factory: IServiceFactory):
        """
        初始化應用門面
        
        Args:
            service_factory: 實現 IServiceFactory 介面的服務工廠
        """
        self.service_factory = service_factory
            
        # 創建新的應用上下文，避免重複註冊問題
        self.context = ApplicationServiceContext()
        self._initialized = False
        
        # 應用服務實例
        self._messaging_service: Optional[MessagingApplicationService] = None
        self._query_service: Optional[QueryApplicationService] = None
        self._monitoring_service: Optional[MonitoringApplicationService] = None
    
    
    async def initialize(self) -> None:
        """初始化應用門面和所有服務"""
        if self._initialized:
            return
        
        logger.info("正在初始化應用門面")
        
        try:
            # 創建應用服務
            await self._create_application_services()
            
            # 註冊所有服務到上下文
            self._register_services()
            
            # 初始化所有服務
            await self.context.initialize_all()
            
            self._initialized = True
            logger.info("應用門面初始化完成")
            
        except Exception as e:
            logger.error("應用門面初始化失敗", error=str(e))
            raise
    
    async def _create_application_services(self) -> None:
        """創建所有應用服務"""
        # 使用增強版服務工廠
        self._messaging_service = self.service_factory.get_service(MessagingApplicationService)
        self._query_service = self.service_factory.get_service(QueryApplicationService)
        self._monitoring_service = self.service_factory.get_service(MonitoringApplicationService)
    
    def _register_services(self) -> None:
        """註冊所有服務到應用上下文"""
        if self._messaging_service:
            self.context.register_service(self._messaging_service)
        
        if self._query_service:
            self.context.register_service(self._query_service)
        
        if self._monitoring_service:
            self.context.register_service(self._monitoring_service)
    
    async def process_message(self, 
                            user_id: str, 
                            message_text: str, 
                            reply_token: str,
                            additional_context: Optional[Dict[str, Any]] = None) -> Message:
        """
        處理訊息（高層次介面）
        
        Args:
            user_id: 用戶 ID
            message_text: 訊息內容
            reply_token: 回覆 token
            additional_context: 額外上下文
            
        Returns:
            處理結果訊息
        """
        if not self._initialized:
            await self.initialize()
        
        # 記錄監控指標
        start_time = self._get_current_time()
        
        try:
            # 使用訊息處理服務
            result = await self._messaging_service.process_message(
                user_id=user_id,
                message_text=message_text,
                reply_token=reply_token,
                additional_context=additional_context
            )
            
            # 記錄成功指標
            duration = self._get_current_time() - start_time
            if self._monitoring_service:
                self._monitoring_service.record_request_metrics(
                    duration=duration,
                    status="success",
                    endpoint="process_message"
                )
            
            return result
            
        except Exception as e:
            # 記錄錯誤指標
            duration = self._get_current_time() - start_time
            if self._monitoring_service:
                self._monitoring_service.record_request_metrics(
                    duration=duration,
                    status="error",
                    endpoint="process_message"
                )
            raise
    
    async def execute_sql_query(self, 
                               query: str, 
                               user_id: str,
                               use_cache: bool = True) -> Dict[str, Any]:
        """
        執行 SQL 查詢（高層次介面）
        
        Args:
            query: SQL 查詢語句
            user_id: 用戶 ID
            use_cache: 是否使用快取
            
        Returns:
            查詢結果
        """
        if not self._initialized:
            await self.initialize()
        
        # 記錄監控指標
        start_time = self._get_current_time()
        
        try:
            # 使用查詢服務
            result = await self._query_service.execute_sql_query(
                query=query,
                user_id=user_id,
                use_cache=use_cache
            )
            
            # 記錄成功指標
            duration = self._get_current_time() - start_time
            if self._monitoring_service:
                self._monitoring_service.record_request_metrics(
                    duration=duration,
                    status="success",
                    endpoint="execute_sql_query"
                )
                
                # 記錄查詢特定指標
                self._monitoring_service.record_metric(
                    "query.rows_returned", 
                    result.get("row_count", 0), 
                    "count"
                )
            
            return result
            
        except Exception as e:
            # 記錄錯誤指標
            duration = self._get_current_time() - start_time
            if self._monitoring_service:
                self._monitoring_service.record_request_metrics(
                    duration=duration,
                    status="error",
                    endpoint="execute_sql_query"
                )
            raise
    
    async def get_system_health(self) -> Dict[str, Any]:
        """
        獲取系統健康狀態（高層次介面）
        
        Returns:
            系統健康狀態
        """
        if not self._initialized:
            await self.initialize()
        
        if self._monitoring_service:
            return await self._monitoring_service.perform_comprehensive_health_check()
        else:
            # 回退到基本健康檢查
            return await self.context.health_check_all()
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        獲取儀表板數據（高層次介面）
        
        Returns:
            儀表板數據
        """
        if not self._initialized or not self._monitoring_service:
            return {"error": "監控服務未初始化"}
        
        dashboard_data = self._monitoring_service.get_dashboard_data()
        
        # 添加額外的應用層統計
        if self._messaging_service:
            messaging_stats = self._messaging_service.get_processing_stats()
            dashboard_data["messaging_stats"] = messaging_stats
        
        if self._query_service:
            query_stats = self._query_service.get_query_statistics()
            dashboard_data["query_stats"] = query_stats
        
        return dashboard_data
    
    def get_user_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取用戶會話資訊
        
        Args:
            user_id: 用戶 ID
            
        Returns:
            用戶會話資訊
        """
        if self._messaging_service:
            return self._messaging_service.get_user_session(user_id)
        return None
    
    def clear_user_session(self, user_id: str) -> bool:
        """
        清除用戶會話
        
        Args:
            user_id: 用戶 ID
            
        Returns:
            是否成功清除
        """
        if self._messaging_service:
            return self._messaging_service.clear_user_session(user_id)
        return False
    
    def get_query_statistics(self) -> Dict[str, Any]:
        """獲取查詢統計資訊"""
        if self._query_service:
            return self._query_service.get_query_statistics()
        return {}
    
    def clear_query_cache(self) -> int:
        """
        清除查詢快取
        
        Returns:
            清除的快取項數量
        """
        if self._query_service:
            return self._query_service.clear_cache()
        return 0
    
    def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """
        獲取效能報告
        
        Args:
            hours: 報告時間範圍（小時）
            
        Returns:
            效能報告
        """
        if self._monitoring_service:
            return self._monitoring_service.get_performance_report(hours)
        return {}
    
    async def shutdown(self) -> None:
        """關閉應用門面和所有服務"""
        if not self._initialized:
            return
        
        logger.info("正在關閉應用門面")
        
        try:
            # 關閉所有服務
            await self.context.shutdown_all()
            
            # 清理引用
            self._messaging_service = None
            self._query_service = None
            self._monitoring_service = None
            
            self._initialized = False
            logger.info("應用門面已關閉")
            
        except Exception as e:
            logger.error("關閉應用門面時發生錯誤", error=str(e))
    
    def _get_current_time(self) -> float:
        """獲取當前時間戳"""
        import time
        return time.time()
    
    @property
    def is_initialized(self) -> bool:
        """檢查是否已初始化"""
        return self._initialized
    
    def get_facade_info(self) -> Dict[str, Any]:
        """獲取門面資訊"""
        services_info = {}
        
        if self._messaging_service:
            services_info["messaging"] = self._messaging_service.get_service_info()
        
        if self._query_service:
            services_info["query"] = self._query_service.get_service_info()
        
        if self._monitoring_service:
            services_info["monitoring"] = self._monitoring_service.get_service_info()
        
        return {
            "initialized": self._initialized,
            "services": services_info,
            "context_info": self.context.get_context_info()
        }


# 全域應用門面實例
_application_facade: Optional[ApplicationFacade] = None


def get_application_facade(service_factory: IServiceFactory) -> ApplicationFacade:
    """
    獲取全域應用門面實例
    
    Args:
        service_factory: 實現 IServiceFactory 介面的服務工廠
        
    Returns:
        應用門面實例
    """
    global _application_facade
    if _application_facade is None:
        _application_facade = ApplicationFacade(service_factory)
    return _application_facade