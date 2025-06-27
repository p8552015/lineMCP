"""
延遲初始化錯誤處理和恢復機制
為 T-08 任務實現增強的錯誤處理和用戶體驗
"""

import asyncio
import time
import traceback
from collections.abc import Callable
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class InitializationState(Enum):
    """初始化狀態"""

    PENDING = "pending"  # 等待初始化
    INITIALIZING = "initializing"  # 正在初始化
    READY = "ready"  # 已就緒
    FAILED = "failed"  # 初始化失敗
    RECOVERING = "recovering"  # 恢復中


class ErrorSeverity(Enum):
    """錯誤嚴重程度"""

    LOW = "low"  # 輕微錯誤，可自動恢復
    MEDIUM = "medium"  # 中等錯誤，需要重試
    HIGH = "high"  # 嚴重錯誤，需要人工干預
    CRITICAL = "critical"  # 致命錯誤，系統不可用


@dataclass
class InitializationError:
    """初始化錯誤記錄"""

    timestamp: float = field(default_factory=time.time)
    error_type: str = ""
    error_message: str = ""
    stack_trace: str = ""
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    retry_count: int = 0
    recovery_attempted: bool = False
    user_friendly_message: str = ""


@dataclass
class LazyServiceConfig:
    """延遲服務配置"""

    service_name: str
    max_retry_attempts: int = 3
    retry_delay_base: float = 1.0  # 基礎重試延遲（秒）
    retry_delay_multiplier: float = 2.0  # 延遲倍數
    max_retry_delay: float = 30.0  # 最大重試延遲
    timeout_seconds: float = 10.0  # 初始化超時
    auto_recovery: bool = True
    user_notifications: bool = True


class LazyInitializationErrorHandler:
    """
    延遲初始化錯誤處理器

    功能：
    - 智能重試機制
    - 錯誤分類和嚴重程度評估
    - 用戶友好的錯誤消息
    - 自動恢復策略
    - 降級服務支持
    """

    def __init__(self, config: LazyServiceConfig):
        self.config = config
        self.state = InitializationState.PENDING
        self.errors: list[InitializationError] = []
        self.last_success_time: float | None = None
        self.initialization_lock = asyncio.Lock()

        # 錯誤模式匹配
        self.error_patterns = {
            "connection": ["connection", "network", "timeout", "unreachable"],
            "permission": ["permission", "access", "denied", "unauthorized"],
            "resource": ["memory", "disk", "resource", "limit"],
            "dependency": ["import", "module", "dependency", "missing"],
            "configuration": ["config", "setting", "env", "variable"],
        }

        # 用戶友好錯誤消息
        self.user_messages = {
            "connection": "🔌 服務連接中斷，正在嘗試重新連接...",
            "permission": "🔒 權限不足，請檢查配置或聯繫管理員",
            "resource": "💾 系統資源不足，請稍後再試",
            "dependency": "📦 系統組件載入失敗，正在修復中...",
            "configuration": "⚙️ 配置問題，正在檢查設置...",
            "unknown": "❓ 未知錯誤，技術團隊已收到通知",
        }

    async def safe_initialize(
        self, initializer: Callable[[], Any]
    ) -> tuple[bool, Any, str | None]:
        """
        安全的延遲初始化

        Args:
            initializer: 初始化函數

        Returns:
            (成功標誌, 結果, 用戶消息)
        """
        async with self.initialization_lock:
            if self.state == InitializationState.READY:
                return True, None, None

            if self.state == InitializationState.INITIALIZING:
                # 等待其他初始化完成
                await self._wait_for_initialization()
                return self.state == InitializationState.READY, None, None

            return await self._attempt_initialization(initializer)

    async def _attempt_initialization(
        self, initializer: Callable[[], Any]
    ) -> tuple[bool, Any, str | None]:
        """嘗試初始化"""
        self.state = InitializationState.INITIALIZING

        for attempt in range(self.config.max_retry_attempts):
            try:
                logger.info(
                    f"🔄 嘗試初始化 {self.config.service_name}，第 {attempt + 1} 次"
                )

                # 設置超時
                result = await asyncio.wait_for(
                    self._run_initializer(initializer),
                    timeout=self.config.timeout_seconds,
                )

                # 初始化成功
                self.state = InitializationState.READY
                self.last_success_time = time.time()
                logger.info(f"✅ {self.config.service_name} 初始化成功")

                return True, result, None

            except Exception as e:
                error = self._create_error_record(e, attempt + 1)
                self.errors.append(error)

                logger.warning(
                    f"❌ {self.config.service_name} 初始化失敗 (嘗試 {attempt + 1}/{self.config.max_retry_attempts})",
                    error=str(e),
                )

                # 如果還有重試機會
                if attempt < self.config.max_retry_attempts - 1:
                    delay = self._calculate_retry_delay(attempt)
                    logger.info(f"⏳ {delay:.1f}秒後重試...")
                    await asyncio.sleep(delay)
                else:
                    # 所有重試都失敗
                    self.state = InitializationState.FAILED
                    user_message = self._generate_user_error_message(error)

                    # 嘗試自動恢復
                    if self.config.auto_recovery:
                        recovery_success = await self._attempt_auto_recovery()
                        if recovery_success:
                            return await self._attempt_initialization(initializer)

                    return False, None, user_message

        return False, None, "初始化失敗，請稍後再試"

    async def _run_initializer(self, initializer: Callable[[], Any]) -> Any:
        """運行初始化器"""
        if asyncio.iscoroutinefunction(initializer):
            return await initializer()
        else:
            # 在線程池中運行同步函數
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, initializer)

    def _create_error_record(
        self, exception: Exception, retry_count: int
    ) -> InitializationError:
        """創建錯誤記錄"""
        error_type = type(exception).__name__
        error_message = str(exception)
        stack_trace = traceback.format_exc()

        # 評估錯誤嚴重程度
        severity = self._assess_error_severity(error_type, error_message)

        # 生成用戶友好消息
        user_message = self._generate_user_error_message_for_exception(exception)

        return InitializationError(
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            severity=severity,
            retry_count=retry_count,
            user_friendly_message=user_message,
        )

    def _assess_error_severity(
        self, error_type: str, error_message: str
    ) -> ErrorSeverity:
        """評估錯誤嚴重程度"""
        message_lower = error_message.lower()

        # 致命錯誤
        if any(
            keyword in message_lower
            for keyword in ["out of memory", "disk full", "system", "fatal"]
        ):
            return ErrorSeverity.CRITICAL

        # 高嚴重性錯誤
        if any(
            keyword in message_lower
            for keyword in ["permission denied", "access denied", "unauthorized"]
        ):
            return ErrorSeverity.HIGH

        # 中等嚴重性錯誤
        if any(
            keyword in message_lower
            for keyword in ["connection", "timeout", "network", "import"]
        ):
            return ErrorSeverity.MEDIUM

        # 低嚴重性錯誤
        return ErrorSeverity.LOW

    def _generate_user_error_message(self, error: InitializationError) -> str:
        """生成用戶友好的錯誤消息"""
        # 識別錯誤類型
        error_category = self._categorize_error(error.error_message)
        base_message = self.user_messages.get(
            error_category, self.user_messages["unknown"]
        )

        # 根據嚴重程度添加額外信息
        if error.severity == ErrorSeverity.CRITICAL:
            return f"🚨 {base_message}\n系統處於維護模式，請聯繫技術支援"
        elif error.severity == ErrorSeverity.HIGH:
            return f"⚠️ {base_message}\n請聯繫管理員或稍後再試"
        elif error.retry_count > 1:
            return f"{base_message}\n已重試 {error.retry_count} 次，請稍後再試"
        else:
            return base_message

    def _generate_user_error_message_for_exception(self, exception: Exception) -> str:
        """為特定異常生成用戶消息"""
        error_message = str(exception).lower()
        error_category = self._categorize_error(error_message)
        return self.user_messages.get(error_category, self.user_messages["unknown"])

    def _categorize_error(self, error_message: str) -> str:
        """分類錯誤類型"""
        message_lower = error_message.lower()

        for category, keywords in self.error_patterns.items():
            if any(keyword in message_lower for keyword in keywords):
                return category

        return "unknown"

    def _calculate_retry_delay(self, attempt: int) -> float:
        """計算重試延遲"""
        delay = self.config.retry_delay_base * (
            self.config.retry_delay_multiplier**attempt
        )
        return min(delay, self.config.max_retry_delay)

    async def _wait_for_initialization(self, max_wait: float = 30.0) -> None:
        """等待初始化完成"""
        start_time = time.time()
        while self.state == InitializationState.INITIALIZING:
            if time.time() - start_time > max_wait:
                logger.warning(f"等待 {self.config.service_name} 初始化超時")
                break
            await asyncio.sleep(0.1)

    async def _attempt_auto_recovery(self) -> bool:
        """嘗試自動恢復"""
        if not self.config.auto_recovery:
            return False

        # 防止無限恢復循環
        if hasattr(self, "_recovery_attempts"):
            self._recovery_attempts += 1
            if self._recovery_attempts > 3:  # 最多恢復3次
                logger.warning(f"🚫 {self.config.service_name} 自動恢復次數已達上限")
                return False
        else:
            self._recovery_attempts = 1

        logger.info(
            f"🔧 嘗試自動恢復 {self.config.service_name} (第{self._recovery_attempts}次)"
        )
        self.state = InitializationState.RECOVERING

        try:
            # 清理錯誤狀態
            self.errors.clear()

            # 等待一段時間後重置狀態
            await asyncio.sleep(0.5)  # 減少等待時間避免測試超時
            self.state = InitializationState.PENDING

            logger.info(f"🔄 {self.config.service_name} 自動恢復完成，準備重新初始化")
            return True

        except Exception as e:
            logger.error(f"自動恢復失敗: {e}")
            self.state = InitializationState.FAILED
            return False

    def get_health_status(self) -> dict[str, Any]:
        """獲取健康狀態"""
        return {
            "service_name": self.config.service_name,
            "state": self.state.value,
            "last_success": self.last_success_time,
            "error_count": len(self.errors),
            "recent_errors": [
                {
                    "timestamp": error.timestamp,
                    "type": error.error_type,
                    "severity": error.severity.value,
                    "message": error.user_friendly_message,
                }
                for error in self.errors[-3:]  # 最近3個錯誤
            ],
            "auto_recovery_enabled": self.config.auto_recovery,
        }

    def clear_errors(self) -> None:
        """清除錯誤記錄"""
        self.errors.clear()
        logger.info(f"清除 {self.config.service_name} 的錯誤記錄")

    def reset_state(self) -> None:
        """重置狀態"""
        self.state = InitializationState.PENDING
        self.clear_errors()
        logger.info(f"重置 {self.config.service_name} 狀態")


@contextmanager
def lazy_service_context(service_name: str, **config_kwargs):
    """延遲服務上下文管理器"""
    config = LazyServiceConfig(service_name=service_name, **config_kwargs)
    handler = LazyInitializationErrorHandler(config)

    try:
        yield handler
    finally:
        logger.debug(f"退出 {service_name} 延遲服務上下文")


@asynccontextmanager
async def async_lazy_service_context(service_name: str, **config_kwargs):
    """異步延遲服務上下文管理器"""
    config = LazyServiceConfig(service_name=service_name, **config_kwargs)
    handler = LazyInitializationErrorHandler(config)

    try:
        yield handler
    finally:
        logger.debug(f"退出 {service_name} 異步延遲服務上下文")


class LazyServiceRegistry:
    """延遲服務註冊表"""

    def __init__(self):
        self._handlers: dict[str, LazyInitializationErrorHandler] = {}

    def register_service(
        self, service_name: str, config: LazyServiceConfig
    ) -> LazyInitializationErrorHandler:
        """註冊延遲服務"""
        handler = LazyInitializationErrorHandler(config)
        self._handlers[service_name] = handler
        logger.info(f"註冊延遲服務: {service_name}")
        return handler

    def get_handler(
        self, service_name: str
    ) -> LazyInitializationErrorHandler | None:
        """獲取處理器"""
        return self._handlers.get(service_name)

    def get_all_health_status(self) -> dict[str, Any]:
        """獲取所有服務的健康狀態"""
        return {
            name: handler.get_health_status()
            for name, handler in self._handlers.items()
        }

    def reset_all(self) -> None:
        """重置所有服務"""
        for handler in self._handlers.values():
            handler.reset_state()
        logger.info("重置所有延遲服務狀態")


# 全局註冊表
_global_registry = LazyServiceRegistry()


def get_lazy_service_registry() -> LazyServiceRegistry:
    """獲取全局延遲服務註冊表"""
    return _global_registry
