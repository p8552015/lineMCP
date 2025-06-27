#!/usr/bin/env python3
"""
增強版 AI 模型服務
添加重試機制、速率限制控制和備用模型切換功能
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import structlog

from src.config import get_settings

from .ai_model_service import AIModelService, ModelConfig, ModelProvider

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class RetryConfig:
    """重試配置"""

    max_retries: int = 3
    base_delay: float = 1.0  # 基礎延遲秒數
    max_delay: float = 60.0  # 最大延遲秒數
    exponential_backoff: bool = True


class RateLimiter:
    """速率限制器"""

    def __init__(self):
        self._calls = defaultdict(list)  # model_name -> [timestamp, ...]

    def can_call(self, model_name: str, config: ModelConfig) -> bool:
        """檢查是否可以調用 API"""
        now = time.time()
        calls = self._calls[model_name]

        # 清理過期記錄（保留最近1小時）
        calls[:] = [t for t in calls if now - t < 3600]

        # 檢查每分鐘限制
        minute_calls = [t for t in calls if now - t < 60]
        if len(minute_calls) >= getattr(config, "rate_limit_per_minute", 30):
            return False

        # 檢查每小時限制
        return not len(calls) >= getattr(config, "rate_limit_per_hour", 1000)

    def record_call(self, model_name: str):
        """記錄 API 調用"""
        self._calls[model_name].append(time.time())

    def get_wait_time(self, model_name: str, config: ModelConfig) -> float:
        """計算需要等待的時間（秒）"""
        now = time.time()
        calls = self._calls[model_name]

        # 檢查分鐘限制
        minute_calls = [t for t in calls if now - t < 60]
        rate_limit = getattr(config, "rate_limit_per_minute", 30)
        if len(minute_calls) >= rate_limit:
            # 等到最早的調用過期
            return 60 - (now - minute_calls[0]) + 1

        return 0


class EnhancedAIModelService(AIModelService):
    """增強版 AI 模型服務 - 繼承基礎 AIModelService"""

    def __init__(self):
        # 調用父類初始化
        super().__init__()

        # 增強功能初始化
        self.fallback_models = self._get_fallback_models()
        self.rate_limiter = RateLimiter()
        self.retry_config = RetryConfig()

        # 模型健康狀態跟蹤
        self._model_health = defaultdict(
            lambda: {"failures": 0, "last_success": time.time()}
        )

        logger.info(f"✅ 增強版AI模型服務初始化完成，支援 {len(self.models)} 個模型")
        logger.info(
            f"🔄 預設模型: {self.default_model}, 備用模型: {self.fallback_models}"
        )

    def _get_fallback_models(self) -> list[str]:
        """獲取備用模型列表（優化備用模型順序）"""
        models = [self.default_model] if self.default_model in self.models else []

        # 如果預設是Google，優先選擇OpenAI作為備用
        if self.default_model == "gemini-1.5-flash" and "gpt-4o-mini" in self.models:
            models.append("gpt-4o-mini")
        elif self.default_model == "gpt-4o-mini" and "gemini-1.5-flash" in self.models:
            models.append("gemini-1.5-flash")

        # 添加其他模型
        for model_name in self.models:
            if model_name not in models:
                models.append(model_name)

        logger.info(f"🔄 備用模型順序: {models}")
        return models

    async def enhance_natural_language_query(
        self,
        user_query: str,
        database_schema: dict[str, Any],
        model_name: str | None = None,
    ) -> tuple[str, float]:
        """
        使用 AI 模型增強自然語言查詢理解（增強版帶重試和備用模型）

        Args:
            user_query: 使用者原始查詢
            database_schema: 資料庫結構資訊
            model_name: 指定使用的模型，None 則使用預設

        Returns:
            Tuple[增強後的查詢意圖, 信心度]
        """
        if not self.models:
            logger.warning("沒有可用的 AI 模型，使用基礎規則解析")
            return user_query, 0.5

        # 確定要使用的模型列表（主模型 + 備用模型）
        target_models = [model_name] if model_name else self.fallback_models
        target_models = [m for m in target_models if m in self.models]

        if not target_models:
            logger.error("沒有可用的模型")
            return user_query, 0.3

        # 嘗試每個模型，直到成功
        for model in target_models:
            try:
                logger.info(f"🔄 嘗試使用模型: {model}")
                result = await self._call_model_with_retry(
                    user_query, database_schema, model
                )

                # 記錄成功
                self._model_health[model]["failures"] = 0
                self._model_health[model]["last_success"] = time.time()

                logger.info(f"✅ 模型 {model} 調用成功")
                return result

            except Exception as e:
                logger.warning(f"❌ 模型 {model} 調用失敗: {e}")
                self._model_health[model]["failures"] += 1

                # 如果不是最後一個模型，繼續嘗試下一個
                if model != target_models[-1]:
                    logger.info("🔄 切換到備用模型...")
                    continue

        # 所有模型都失敗了
        logger.error("❌ 所有 AI 模型都調用失敗，返回基礎結果")
        return user_query, 0.3

    async def _call_model_with_retry(
        self, user_query: str, database_schema: dict[str, Any], model_name: str
    ) -> tuple[str, float]:
        """帶重試機制的模型調用"""
        config = self.models[model_name]

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                # 速率限制檢查
                if not self.rate_limiter.can_call(model_name, config):
                    wait_time = self.rate_limiter.get_wait_time(model_name, config)
                    if wait_time > 0:
                        logger.warning(f"⏰ 速率限制，等待 {wait_time:.1f} 秒")
                        await asyncio.sleep(wait_time)

                # 記錄調用
                self.rate_limiter.record_call(model_name)

                # 調用基礎類的方法
                if config.provider == ModelProvider.OPENAI:
                    result = await self._call_openai_api(
                        user_query, database_schema, config
                    )
                elif config.provider == ModelProvider.GOOGLE:
                    result = await self._call_google_api(
                        user_query, database_schema, config
                    )
                else:
                    raise ValueError(f"不支援的模型供應商: {config.provider}")

                return result

            except Exception as e:
                if attempt < self.retry_config.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    logger.warning(
                        f"⏳ 模型調用失敗 "
                        f"(嘗試 {attempt + 1}/{self.retry_config.max_retries + 1}): {e}"
                    )
                    logger.info(f"⏰ 等待 {delay:.1f} 秒後重試...")
                    await asyncio.sleep(delay)
                else:
                    raise

    def _calculate_retry_delay(self, attempt: int) -> float:
        """計算重試延遲時間"""
        if self.retry_config.exponential_backoff:
            delay = self.retry_config.base_delay * (2**attempt)
        else:
            delay = self.retry_config.base_delay

        return min(delay, self.retry_config.max_delay)

    def get_model_health_status(self) -> dict[str, Any]:
        """獲取模型健康狀況"""
        now = time.time()
        health_status = {}

        for model_name in self.models:
            health = self._model_health[model_name]
            health_status[model_name] = {
                "failures": health["failures"],
                "last_success": health["last_success"],
                "seconds_since_success": now - health["last_success"],
                "healthy": health["failures"] < 3
                and (now - health["last_success"]) < 3600,
            }

        return {
            "models": health_status,
            "default_model": self.default_model,
            "fallback_models": self.fallback_models,
            "rate_limiter_active": len(self.rate_limiter._calls) > 0,
        }

    def get_available_models(self) -> list[dict[str, Any]]:
        """獲取可用模型列表（增強版資訊）"""
        models = []
        for name, config in self.models.items():
            health = self._model_health[name]
            models.append(
                {
                    "name": name,
                    "provider": config.provider.value,
                    "max_tokens": config.max_tokens,
                    "cost_per_1k_input": config.cost_per_1k_input,
                    "cost_per_1k_output": config.cost_per_1k_output,
                    "free_tier_limit": config.free_tier_limit,
                    "context_window": config.context_window,
                    "rate_limit_per_minute": getattr(
                        config, "rate_limit_per_minute", 30
                    ),
                    "rate_limit_per_hour": getattr(config, "rate_limit_per_hour", 1000),
                    "failures": health["failures"],
                    "healthy": health["failures"] < 3,
                    "is_default": name == self.default_model,
                    "is_fallback": name in self.fallback_models,
                }
            )
        return models
