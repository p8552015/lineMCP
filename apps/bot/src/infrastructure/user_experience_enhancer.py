"""
用戶體驗增強器
為延遲初始化和錯誤處理提供更好的用戶體驗
"""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

import structlog

logger = structlog.get_logger()


class ServiceStatus(Enum):
    """服務狀態"""
    AVAILABLE = "available"      # 可用
    INITIALIZING = "initializing"  # 初始化中
    RECOVERING = "recovering"    # 恢復中
    UNAVAILABLE = "unavailable"  # 不可用
    DEGRADED = "degraded"       # 降級服務


@dataclass
class UserNotification:
    """用戶通知"""
    message: str
    icon: str
    severity: str  # info, warning, error
    show_progress: bool = False
    estimated_time: Optional[float] = None


class UserExperienceEnhancer:
    """
    用戶體驗增強器
    
    功能：
    - 友好的狀態消息
    - 進度指示
    - 預期時間估算
    - 降級服務建議
    - 個性化錯誤處理
    """
    
    def __init__(self):
        self.service_statuses: Dict[str, ServiceStatus] = {}
        self.user_preferences: Dict[str, Dict] = {}
        self.notification_history: List[UserNotification] = []
        
        # 狀態圖標映射
        self.status_icons = {
            ServiceStatus.AVAILABLE: "✅",
            ServiceStatus.INITIALIZING: "🔄",
            ServiceStatus.RECOVERING: "🔧",
            ServiceStatus.UNAVAILABLE: "❌",
            ServiceStatus.DEGRADED: "⚠️"
        }
        
        # 狀態消息模板
        self.status_messages = {
            ServiceStatus.AVAILABLE: "{service} 服務正常運行",
            ServiceStatus.INITIALIZING: "{service} 正在啟動中，預計需要 {time} 秒",
            ServiceStatus.RECOVERING: "{service} 正在恢復中，請稍候",
            ServiceStatus.UNAVAILABLE: "{service} 暫時不可用，請稍後再試",
            ServiceStatus.DEGRADED: "{service} 運行在降級模式"
        }
        
        # 建議操作模板
        self.suggestion_templates = {
            "retry": "💡 建議：您可以稍後重試這個操作",
            "alternative": "💡 建議：您可以嘗試使用 {alternative} 替代功能",
            "contact_support": "💡 建議：如果問題持續，請聯繫技術支援",
            "check_connection": "💡 建議：請檢查您的網絡連接",
            "wait_and_retry": "💡 建議：請等待 {time} 秒後重試"
        }

    def update_service_status(self, service_name: str, status: ServiceStatus):
        """更新服務狀態"""
        old_status = self.service_statuses.get(service_name)
        self.service_statuses[service_name] = status
        
        if old_status != status:
            logger.info(f"服務狀態變更: {service_name} {old_status} -> {status}")

    def create_status_notification(self, service_name: str, 
                                 estimated_time: Optional[float] = None) -> UserNotification:
        """創建狀態通知"""
        status = self.service_statuses.get(service_name, ServiceStatus.UNAVAILABLE)
        icon = self.status_icons[status]
        
        message_template = self.status_messages[status]
        message = message_template.format(
            service=service_name,
            time=f"{estimated_time:.1f}" if estimated_time else "幾"
        )
        
        severity = self._get_severity_for_status(status)
        show_progress = status in [ServiceStatus.INITIALIZING, ServiceStatus.RECOVERING]
        
        return UserNotification(
            message=f"{icon} {message}",
            icon=icon,
            severity=severity,
            show_progress=show_progress,
            estimated_time=estimated_time
        )

    def create_error_notification(self, error_type: str, service_name: str,
                                retry_count: int = 0) -> UserNotification:
        """創建錯誤通知"""
        base_messages = {
            "connection": f"🔌 無法連接到 {service_name} 服務",
            "timeout": f"⏱️ {service_name} 服務響應超時",
            "permission": f"🔒 {service_name} 服務權限不足",
            "resource": f"💾 {service_name} 服務資源不足",
            "configuration": f"⚙️ {service_name} 服務配置錯誤",
            "unknown": f"❓ {service_name} 服務出現未知錯誤"
        }
        
        message = base_messages.get(error_type, base_messages["unknown"])
        
        if retry_count > 0:
            message += f"\n已自動重試 {retry_count} 次"
        
        return UserNotification(
            message=message,
            icon="❌",
            severity="error"
        )

    def create_initialization_feedback(self, service_name: str, 
                                     step: str, progress: float) -> UserNotification:
        """創建初始化反饋"""
        progress_bar = self._create_progress_bar(progress)
        
        message = f"🔄 {service_name} 初始化中...\n"
        message += f"當前步驟: {step}\n"
        message += f"進度: {progress_bar} {progress:.0f}%"
        
        return UserNotification(
            message=message,
            icon="🔄",
            severity="info",
            show_progress=True
        )

    def create_recovery_feedback(self, service_name: str, 
                               recovery_step: str) -> UserNotification:
        """創建恢復反饋"""
        message = f"🔧 {service_name} 正在恢復中...\n"
        message += f"恢復步驟: {recovery_step}\n"
        message += "系統正在自動修復問題"
        
        return UserNotification(
            message=message,
            icon="🔧",
            severity="warning",
            show_progress=True
        )

    def create_degraded_service_notification(self, service_name: str,
                                           available_features: List[str]) -> UserNotification:
        """創建降級服務通知"""
        message = f"⚠️ {service_name} 運行在降級模式\n"
        message += "可用功能:\n"
        for feature in available_features:
            message += f"• {feature}\n"
        message += "\n其他功能將在服務恢復後可用"
        
        return UserNotification(
            message=message,
            icon="⚠️",
            severity="warning"
        )

    def create_suggestion_message(self, suggestion_type: str, **kwargs) -> str:
        """創建建議消息"""
        template = self.suggestion_templates.get(suggestion_type, "")
        return template.format(**kwargs)

    def create_comprehensive_error_message(self, service_name: str, error_type: str,
                                         retry_count: int = 0,
                                         suggestions: List[str] = None) -> str:
        """創建綜合錯誤消息"""
        # 基本錯誤通知
        error_notification = self.create_error_notification(error_type, service_name, retry_count)
        message = error_notification.message
        
        # 添加狀態信息
        status = self.service_statuses.get(service_name, ServiceStatus.UNAVAILABLE)
        if status == ServiceStatus.RECOVERING:
            message += "\n\n🔧 系統正在自動修復問題..."
        elif status == ServiceStatus.DEGRADED:
            message += "\n\n⚠️ 某些功能可能在降級模式下可用"
        
        # 添加建議
        if suggestions:
            message += "\n\n💡 建議操作:"
            for suggestion in suggestions:
                message += f"\n• {suggestion}"
        else:
            # 默認建議
            if error_type == "connection":
                message += f"\n\n{self.create_suggestion_message('check_connection')}"
            elif error_type == "timeout":
                message += f"\n\n{self.create_suggestion_message('wait_and_retry', time='30')}"
            else:
                message += f"\n\n{self.create_suggestion_message('retry')}"
        
        return message

    def create_success_recovery_message(self, service_name: str, 
                                      downtime_seconds: float) -> str:
        """創建恢復成功消息"""
        message = f"✅ {service_name} 服務已恢復正常\n"
        message += f"停機時間: {downtime_seconds:.1f} 秒\n"
        message += "感謝您的耐心等待！"
        
        return message

    def get_service_health_summary(self) -> str:
        """獲取服務健康摘要"""
        if not self.service_statuses:
            return "📊 系統狀態: 初始化中..."
        
        available_count = sum(1 for status in self.service_statuses.values() 
                            if status == ServiceStatus.AVAILABLE)
        total_count = len(self.service_statuses)
        
        if available_count == total_count:
            return f"✅ 系統狀態: 全部正常 ({available_count}/{total_count})"
        elif available_count == 0:
            return f"❌ 系統狀態: 服務不可用 ({available_count}/{total_count})"
        else:
            return f"⚠️ 系統狀態: 部分可用 ({available_count}/{total_count})"

    def _get_severity_for_status(self, status: ServiceStatus) -> str:
        """獲取狀態對應的嚴重程度"""
        severity_map = {
            ServiceStatus.AVAILABLE: "info",
            ServiceStatus.INITIALIZING: "info",
            ServiceStatus.RECOVERING: "warning",
            ServiceStatus.UNAVAILABLE: "error",
            ServiceStatus.DEGRADED: "warning"
        }
        return severity_map.get(status, "info")

    def _create_progress_bar(self, progress: float, width: int = 10) -> str:
        """創建進度條"""
        filled = int(progress / 100 * width)
        empty = width - filled
        return "█" * filled + "░" * empty

    def set_user_preference(self, user_id: str, preference_key: str, value: any):
        """設置用戶偏好"""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {}
        self.user_preferences[user_id][preference_key] = value

    def get_user_preference(self, user_id: str, preference_key: str, default: any = None):
        """獲取用戶偏好"""
        return self.user_preferences.get(user_id, {}).get(preference_key, default)

    def should_show_technical_details(self, user_id: str) -> bool:
        """是否顯示技術細節"""
        return self.get_user_preference(user_id, "show_technical_details", False)

    def get_preferred_language(self, user_id: str) -> str:
        """獲取偏好語言"""
        return self.get_user_preference(user_id, "language", "zh-TW")


# 全局用戶體驗增強器
_global_ux_enhancer = UserExperienceEnhancer()


def get_user_experience_enhancer() -> UserExperienceEnhancer:
    """獲取全局用戶體驗增強器"""
    return _global_ux_enhancer