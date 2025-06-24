#!/usr/bin/env python3
"""
增強版 AI 模型服務
添加重試機制、速率限制控制和備用模型切換功能
"""

import asyncio
import json
import time
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Any

import httpx
import structlog

from src.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class ModelProvider(Enum):
    """AI 模型供應商"""
    OPENAI = "openai"
    GOOGLE = "google"
    LOCAL = "local"


@dataclass
class ModelConfig:
    """模型配置"""
    name: str
    provider: ModelProvider
    api_key: str
    endpoint: str
    max_tokens: int
    cost_per_1k_input: float
    cost_per_1k_output: float
    free_tier_limit: int | None = None
    context_window: int = 4096
    # 速率限制配置
    rate_limit_per_minute: int = 30
    rate_limit_per_hour: int = 1000


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
        if len(minute_calls) >= config.rate_limit_per_minute:
            return False
            
        # 檢查每小時限制
        if len(calls) >= config.rate_limit_per_hour:
            return False
            
        return True
    
    def record_call(self, model_name: str):
        """記錄 API 調用"""
        self._calls[model_name].append(time.time())
    
    def get_wait_time(self, model_name: str, config: ModelConfig) -> float:
        """計算需要等待的時間（秒）"""
        now = time.time()
        calls = self._calls[model_name]
        
        # 檢查分鐘限制
        minute_calls = [t for t in calls if now - t < 60]
        if len(minute_calls) >= config.rate_limit_per_minute:
            # 等到最早的調用過期
            return 60 - (now - minute_calls[0]) + 1
            
        return 0


class EnhancedAIModelService:
    """增強版 AI 模型服務"""

    def __init__(self):
        self.models = self._init_models()
        self.default_model = self._get_default_model()
        self.fallback_models = self._get_fallback_models()
        self.rate_limiter = RateLimiter()
        self.retry_config = RetryConfig()
        
        # 模型健康狀態跟蹤
        self._model_health = defaultdict(lambda: {"failures": 0, "last_success": time.time()})
        
        logger.info(f"✅ 增強版AI模型服務初始化完成，支援 {len(self.models)} 個模型")
        logger.info(f"🔄 預設模型: {self.default_model}, 備用模型: {self.fallback_models}")

    def _init_models(self) -> dict[str, ModelConfig]:
        """初始化支援的模型配置"""
        models = {}

        # OpenAI GPT-4o-mini
        if settings.openai_api_key:
            models["gpt-4o-mini"] = ModelConfig(
                name="gpt-4o-mini",
                provider=ModelProvider.OPENAI,
                api_key=settings.openai_api_key,
                endpoint="https://api.openai.com/v1/chat/completions",
                max_tokens=4096,
                cost_per_1k_input=0.15,
                cost_per_1k_output=0.60,
                context_window=128000,
                rate_limit_per_minute=20,  # 較保守的限制
                rate_limit_per_hour=500,
            )

        # Google Gemini 1.5 Flash
        if settings.google_api_key:
            models["gemini-1.5-flash"] = ModelConfig(
                name="gemini-1.5-flash",
                provider=ModelProvider.GOOGLE,
                api_key=settings.google_api_key,
                endpoint="https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
                max_tokens=8192,
                cost_per_1k_input=0.075,
                cost_per_1k_output=0.30,
                free_tier_limit=15000000,
                context_window=1000000,
                rate_limit_per_minute=15,  # Google 的限制較嚴格
                rate_limit_per_hour=1000,
            )

        return models

    def _get_default_model(self) -> str:
        """獲取預設模型"""
        provider_preference = settings.ai_model_provider.lower()
        
        if provider_preference == "google" and "gemini-1.5-flash" in self.models:
            logger.info("🌟 選擇 Gemini 1.5 Flash 作為預設模型")
            return "gemini-1.5-flash"
        elif provider_preference == "openai" and "gpt-4o-mini" in self.models:
            logger.info("🤖 選擇 GPT-4o-mini 作為預設模型")
            return "gpt-4o-mini"
        
        # 自動選擇
        if "gemini-1.5-flash" in self.models:
            return "gemini-1.5-flash"
        elif "gpt-4o-mini" in self.models:
            return "gpt-4o-mini"
        
        return ""

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
        使用 AI 模型增強自然語言查詢理解（帶重試和備用模型）
        
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

        # 確定要嘗試的模型列表
        models_to_try = [model_name] if model_name else self.fallback_models
        models_to_try = [m for m in models_to_try if m in self.models]
        
        if not models_to_try:
            logger.error("沒有可用的模型")
            return user_query, 0.3

        last_exception = None
        
        for attempt_model in models_to_try:
            try:
                logger.info(f"🎯 嘗試使用模型: {attempt_model}")
                result = await self._call_model_with_retry(
                    user_query, database_schema, attempt_model
                )
                
                # 更新模型健康狀態
                self._model_health[attempt_model]["failures"] = 0
                self._model_health[attempt_model]["last_success"] = time.time()
                
                logger.info(f"✅ 模型 {attempt_model} 調用成功")
                return result
                
            except Exception as e:
                last_exception = e
                self._model_health[attempt_model]["failures"] += 1
                logger.warning(f"⚠️ 模型 {attempt_model} 調用失敗: {e}")
                
                # 如果還有其他模型可以嘗試，繼續
                if attempt_model != models_to_try[-1]:
                    logger.info(f"🔄 切換到下一個備用模型")
                    continue

        # 所有模型都失敗了
        logger.error(f"❌ 所有AI模型調用失敗，最後錯誤: {last_exception}")
        return user_query, 0.3

    async def _call_model_with_retry(
        self, user_query: str, database_schema: dict[str, Any], model_name: str
    ) -> tuple[str, float]:
        """帶重試機制的模型調用"""
        config = self.models[model_name]
        
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                # 檢查速率限制
                if not self.rate_limiter.can_call(model_name, config):
                    wait_time = self.rate_limiter.get_wait_time(model_name, config)
                    if wait_time > 0:
                        logger.warning(f"⏳ 達到速率限制，等待 {wait_time:.1f} 秒")
                        if wait_time < 10:  # 只有等待時間較短時才等待
                            await asyncio.sleep(wait_time)
                        else:
                            raise Exception(f"速率限制: 需等待 {wait_time:.1f} 秒")
                
                # 記錄調用
                self.rate_limiter.record_call(model_name)
                
                # 調用相應的 API
                if config.provider == ModelProvider.OPENAI:
                    return await self._call_openai_api(user_query, database_schema, config)
                elif config.provider == ModelProvider.GOOGLE:
                    return await self._call_google_api(user_query, database_schema, config)
                else:
                    raise Exception(f"不支援的模型供應商: {config.provider}")
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Too Many Requests
                    logger.warning(f"⚠️ {model_name} API速率限制(429)，立即切換到備用模型")
                    # 429錯誤不重試，直接拋出異常讓上層切換模型
                    raise Exception(f"API速率限制: {model_name} - 切換備用模型")
                else:
                    raise Exception(f"HTTP錯誤: {e.response.status_code}")
                    
            except Exception as e:
                if attempt < self.retry_config.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    logger.warning(f"🔄 調用失敗，第{attempt+1}次重試，等待{delay:.1f}秒: {e}")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise

    def _calculate_retry_delay(self, attempt: int) -> float:
        """計算重試延遲"""
        if self.retry_config.exponential_backoff:
            delay = self.retry_config.base_delay * (2 ** attempt)
        else:
            delay = self.retry_config.base_delay
            
        return min(delay, self.retry_config.max_delay)

    async def _call_openai_api(
        self, user_query: str, database_schema: dict[str, Any], config: ModelConfig
    ) -> tuple[str, float]:
        """調用 OpenAI API"""
        system_prompt = self._build_system_prompt(database_schema)
        user_prompt = self._build_user_prompt(user_query)

        payload = {
            "model": config.name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": min(config.max_tokens, 500),
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(config.endpoint, json=payload, headers=headers)
            response.raise_for_status()

            result = response.json()
            content = result["choices"][0]["message"]["content"]

            try:
                parsed = json.loads(content)
                enhanced_query = parsed.get("enhanced_query", user_query)
                confidence = float(parsed.get("confidence", 0.7))

                logger.info("OpenAI解析完成", model=config.name, confidence=confidence)
                return enhanced_query, confidence

            except json.JSONDecodeError:
                logger.warning("OpenAI回應不是有效JSON")
                return user_query, 0.5

    async def _call_google_api(
        self, user_query: str, database_schema: dict[str, Any], config: ModelConfig
    ) -> tuple[str, float]:
        """調用 Google Gemini API"""
        system_prompt = self._build_system_prompt(database_schema)
        full_prompt = f"{system_prompt}\\n\\n{self._build_user_prompt(user_query)}"

        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": min(config.max_tokens, 500),
                "responseMimeType": "application/json",
            },
        }

        url = f"{config.endpoint}?key={config.api_key}"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

            result = response.json()
            content = result["candidates"][0]["content"]["parts"][0]["text"]

            try:
                parsed = json.loads(content)
                enhanced_query = parsed.get("enhanced_query", user_query)
                confidence = float(parsed.get("confidence", 0.7))

                logger.info("Google解析完成", model=config.name, confidence=confidence)
                return enhanced_query, confidence

            except json.JSONDecodeError:
                logger.warning("Google回應不是有效JSON")
                return user_query, 0.5

    def _build_system_prompt(self, database_schema: dict[str, Any]) -> str:
        """構建系統提示詞"""
        schema_info = ""
        for table_name, table_info in database_schema.items():
            columns = table_info.get("columns", [])
            column_names = [col.get("name", "") for col in columns]
            schema_info += f"- {table_name}: {', '.join(column_names)}\\n"

        return f"""你是一個專業的資料庫查詢助手。請分析使用者的中文自然語言查詢，理解其意圖並提供結構化回應。

資料庫結構：
{schema_info}

請以JSON格式回應：
{{
    "enhanced_query": "增強後的查詢描述，包含具體的表格和欄位資訊",
    "query_type": "查詢類型 (machine_status|fault_analysis|production_stats|all_machines|department_status)",
    "target_entities": ["相關的機台ID、部門名稱等"],
    "confidence": 0.9,
    "explanation": "解析說明"
}}"""

    def _build_user_prompt(self, user_query: str) -> str:
        """構建使用者提示詞"""
        return f"""請分析以下中文查詢：

使用者查詢："{user_query}"

請識別：
1. 查詢的主要意圖
2. 涉及的機台、部門或時間範圍
3. 需要的資料類型（狀態、統計、記錄等）
4. 查詢的具體性程度

以JSON格式回應。"""

    def get_model_health_status(self) -> dict[str, Any]:
        """獲取模型健康狀態"""
        status = {}
        for model_name in self.models:
            health = self._model_health[model_name]
            status[model_name] = {
                "failures": health["failures"],
                "last_success": health["last_success"],
                "is_healthy": health["failures"] < 3,
                "rate_limit_status": "ok" if self.rate_limiter.can_call(model_name, self.models[model_name]) else "limited"
            }
        return status

    def get_available_models(self) -> list[dict[str, Any]]:
        """獲取可用模型列表"""
        models_info = []
        for name, config in self.models.items():
            health = self._model_health[name]
            models_info.append({
                "name": name,
                "provider": config.provider.value,
                "cost_per_1k_input": config.cost_per_1k_input,
                "cost_per_1k_output": config.cost_per_1k_output,
                "free_tier_limit": config.free_tier_limit,
                "context_window": config.context_window,
                "is_default": name == self.default_model,
                "is_healthy": health["failures"] < 3,
                "rate_limit_per_minute": config.rate_limit_per_minute,
            })
        return models_info