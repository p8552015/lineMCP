#!/usr/bin/env python3
"""
AI 模型服務
支援多種免費和付費 AI 模型用於自然語言處理
"""

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

import httpx
import structlog

from src.settings import get_settings

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
    cost_per_1k_input: float  # USD
    cost_per_1k_output: float  # USD
    free_tier_limit: int | None = None  # 每月免費 tokens
    context_window: int = 4096


class AIModelService:
    """AI 模型服務"""

    def __init__(self):
        self.models = self._init_models()
        self.default_model = self._get_default_model()
        logger.info(f"✅ AI模型服務初始化完成，支援 {len(self.models)} 個模型")

    def _init_models(self) -> dict[str, ModelConfig]:
        """初始化支援的模型配置"""
        models = {}

        # OpenAI GPT-4o-mini (免費額度有限，價格最低)
        if settings.openai_api_key:
            models["gpt-4o-mini"] = ModelConfig(
                name="gpt-4o-mini",
                provider=ModelProvider.OPENAI,
                api_key=settings.openai_api_key,
                endpoint="https://api.openai.com/v1/chat/completions",
                max_tokens=4096,
                cost_per_1k_input=0.15,  # $0.15 per 1M tokens = $0.00015 per 1K
                cost_per_1k_output=0.60,  # $0.60 per 1M tokens = $0.0006 per 1K
                context_window=128000,
            )

        # OpenAI GPT-3.5-turbo (備用選項)
        if settings.openai_api_key:
            models["gpt-3.5-turbo"] = ModelConfig(
                name="gpt-3.5-turbo",
                provider=ModelProvider.OPENAI,
                api_key=settings.openai_api_key,
                endpoint="https://api.openai.com/v1/chat/completions",
                max_tokens=4096,
                cost_per_1k_input=0.50,
                cost_per_1k_output=1.50,
                context_window=16385,
            )

        # Google Gemini 1.5 Flash (免費額度較高)
        if settings.google_api_key:
            models["gemini-1.5-flash"] = ModelConfig(
                name="gemini-1.5-flash",
                provider=ModelProvider.GOOGLE,
                api_key=settings.google_api_key,
                endpoint="https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
                max_tokens=8192,
                cost_per_1k_input=0.075,  # 降價 78% 後
                cost_per_1k_output=0.30,  # 降價 71% 後
                free_tier_limit=15000000,  # 每月 15M tokens 免費
                context_window=1000000,
            )

        return models

    def _get_default_model(self) -> str:
        """獲取預設模型（根據配置決定優先順序）"""
        provider_preference = settings.ai_model_provider.lower()

        # 根據配置的供應商偏好選擇預設模型
        if provider_preference == "google":
            if "gemini-1.5-flash" in self.models:
                logger.info("🌟 選擇 Gemini 1.5 Flash 作為預設模型（配置偏好：Google）")
                return "gemini-1.5-flash"
            else:
                logger.warning("⚠️ Google 偏好但 Gemini 不可用，切換到 OpenAI")

        elif provider_preference == "openai":
            if "gpt-4o-mini" in self.models:
                logger.info("🤖 選擇 GPT-4o-mini 作為預設模型（配置偏好：OpenAI）")
                return "gpt-4o-mini"
            elif "gpt-3.5-turbo" in self.models:
                logger.info("🤖 選擇 GPT-3.5-turbo 作為預設模型（配置偏好：OpenAI）")
                return "gpt-3.5-turbo"
            else:
                logger.warning("⚠️ OpenAI 偏好但模型不可用，切換到其他供應商")

        # auto 模式或回退選擇：優先 Gemini（免費額度高），然後 OpenAI
        if "gemini-1.5-flash" in self.models:
            logger.info("🌟 選擇 Gemini 1.5 Flash 作為預設模型（自動選擇）")
            return "gemini-1.5-flash"
        elif "gpt-4o-mini" in self.models:
            logger.info("🤖 選擇 GPT-4o-mini 作為預設模型（自動選擇）")
            return "gpt-4o-mini"
        elif "gpt-3.5-turbo" in self.models:
            logger.info("🤖 選擇 GPT-3.5-turbo 作為預設模型（自動選擇）")
            return "gpt-3.5-turbo"

        # 沒有可用模型
        else:
            logger.warning("⚠️ 沒有可用的 AI 模型，需要設定 API 金鑰")
            return ""

    async def enhance_natural_language_query(
        self,
        user_query: str,
        database_schema: dict[str, Any],
        model_name: str | None = None,
    ) -> tuple[str, float]:
        """
        使用 AI 模型增強自然語言查詢理解

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

        model_name = model_name or self.default_model
        if model_name not in self.models:
            logger.error(f"模型 {model_name} 不存在，使用預設模型")
            model_name = self.default_model

        model_config = self.models[model_name]

        try:
            if model_config.provider == ModelProvider.OPENAI:
                return await self._call_openai_api(
                    user_query, database_schema, model_config
                )
            elif model_config.provider == ModelProvider.GOOGLE:
                return await self._call_google_api(
                    user_query, database_schema, model_config
                )
            else:
                logger.error(f"不支援的模型供應商: {model_config.provider}")
                return user_query, 0.3

        except Exception as e:
            logger.error(f"AI模型調用失敗: {e}")
            return user_query, 0.3

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

        return (
            f"你是一個專業的資料庫查詢助手。請分析使用者的中文自然語言查詢，"
            f"理解其意圖並提供結構化回應。\n\n"
            f"資料庫結構：\n{schema_info}\n"
            f"請以JSON格式回應：\n"
            f"{{\n"
            f'    "enhanced_query": "增強後的查詢描述，包含具體的表格和欄位資訊",\n'
            f'    "query_type": "查詢類型 '
            f'(machine_status|fault_analysis|production_stats|all_machines|department_status)",\n'
            f'    "target_entities": ["相關的機台ID、部門名稱等"],\n'
            f'    "confidence": 0.9,\n'
            f'    "explanation": "解析說明"\n'
            f"}}"
        )

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

    def get_available_models(self) -> list[dict[str, Any]]:
        """獲取可用模型列表"""
        models_info : list[Any] = []
        for name, config in self.models.items():
            models_info.append(
                {
                    "name": name,
                    "provider": config.provider.value,
                    "cost_per_1k_input": config.cost_per_1k_input,
                    "cost_per_1k_output": config.cost_per_1k_output,
                    "free_tier_limit": config.free_tier_limit,
                    "context_window": config.context_window,
                    "is_default": name == self.default_model,
                }
            )
        return models_info

    def estimate_cost(
        self, input_tokens: int, output_tokens: int, model_name: str | None = None
    ) -> float:
        """估算使用成本（美元）"""
        model_name = model_name or self.default_model
        if model_name not in self.models:
            return 0.0

        config = self.models[model_name]
        input_cost = (input_tokens / 1000) * config.cost_per_1k_input
        output_cost = (output_tokens / 1000) * config.cost_per_1k_output

        total_cost = input_cost + output_cost
        return float(total_cost)

    async def query_with_custom_prompt(
        self,
        user_query: str,
        system_prompt: str,
        model_name: str | None = None,
    ) -> tuple[str, float]:
        """
        使用自定義系統提示詞查詢 AI 模型

        Args:
            user_query: 使用者查詢
            system_prompt: 自定義系統提示詞
            model_name: 指定使用的模型，None 則使用預設

        Returns:
            Tuple[AI 回應, 信心度]
        """
        if not self.models:
            logger.warning("沒有可用的 AI 模型")
            return user_query, 0.3

        model_name = model_name or self.default_model
        if model_name not in self.models:
            logger.error(f"模型 {model_name} 不存在，使用預設模型")
            model_name = self.default_model

        model_config = self.models[model_name]

        try:
            if model_config.provider == ModelProvider.OPENAI:
                return await self._call_openai_with_custom_prompt(
                    user_query, system_prompt, model_config
                )
            elif model_config.provider == ModelProvider.GOOGLE:
                return await self._call_google_with_custom_prompt(
                    user_query, system_prompt, model_config
                )
            else:
                logger.error(f"不支援的模型供應商: {model_config.provider}")
                return user_query, 0.3

        except Exception as e:
            logger.error(f"AI模型調用失敗: {e}")
            return user_query, 0.3

    async def _call_openai_with_custom_prompt(
        self, user_query: str, system_prompt: str, config: ModelConfig
    ) -> tuple[str, float]:
        """使用自定義系統提示詞調用 OpenAI API"""

        payload = {
            "model": config.name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query},
            ],
            "max_tokens": min(config.max_tokens, 500),
            "temperature": 0.1,  # 降低溫度以獲得更一致的 JSON 回應
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

            logger.info(
                "OpenAI自定義提示完成", model=config.name, content_length=len(content)
            )
            return content, 0.9

    async def _call_google_with_custom_prompt(
        self, user_query: str, system_prompt: str, config: ModelConfig
    ) -> tuple[str, float]:
        """使用自定義系統提示詞調用 Google Gemini API"""

        full_prompt = f"{system_prompt}\n\n用戶查詢: {user_query}"

        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": 0.1,  # 降低溫度以獲得更一致的 JSON 回應
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

            logger.info(
                "Google自定義提示完成", model=config.name, content_length=len(content)
            )
            return content, 0.9

    async def generate_user_guidance(
        self,
        user_input: str,
        guidance_prompt: str,
        model_name: str | None = None,
    ) -> tuple[str, float]:
        """
        專門用於生成用戶指導的AI方法（不使用JSON格式）

        Args:
            user_input: 用戶原始輸入
            guidance_prompt: 指導提示詞
            model_name: 指定使用的模型，None 則使用預設

        Returns:
            Tuple[用戶指導回應, 信心度]
        """
        if not self.models:
            logger.warning("沒有可用的 AI 模型")
            return f"無法處理查詢「{user_input}」，請稍後再試。", 0.3

        model_name = model_name or self.default_model
        if model_name not in self.models:
            logger.error(f"模型 {model_name} 不存在，使用預設模型")
            model_name = self.default_model

        model_config = self.models[model_name]

        # 創建用戶友善的系統提示詞（非JSON格式）
        system_prompt = """你是一個友善、專業的製造業智能助手。
用戶向你詢問了一個關於工業設備或生產的問題，但系統無法直接處理這個查詢。

請以自然、友善的語氣回應用戶，幫助他們：
1. 理解為什麼無法直接處理他們的查詢
2. 提供具體、實用的建議
3. 給出 2-3 個相關的查詢範例

回應要求：
- 使用繁體中文
- 語氣友善專業，避免過於技術性
- 直接回應，不要使用JSON格式
- 保持簡潔實用（200字以內）
- 聚焦在幫助用戶獲得所需資訊"""

        try:
            if model_config.provider == ModelProvider.OPENAI:
                return await self._call_openai_for_guidance(
                    user_input, guidance_prompt, system_prompt, model_config
                )
            elif model_config.provider == ModelProvider.GOOGLE:
                return await self._call_google_for_guidance(
                    user_input, guidance_prompt, system_prompt, model_config
                )
            else:
                logger.error(f"不支援的模型供應商: {model_config.provider}")
                return f"無法處理查詢「{user_input}」，請稍後再試。", 0.3

        except Exception as e:
            logger.error(f"AI用戶指導生成失敗: {e}")
            return f"無法處理查詢「{user_input}」，請稍後再試。", 0.3

    async def _call_openai_for_guidance(
        self,
        user_input: str,
        guidance_prompt: str,
        system_prompt: str,
        config: ModelConfig,
    ) -> tuple[str, float]:
        """為用戶指導調用 OpenAI API（無JSON格式限制）"""

        payload = {
            "model": config.name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": guidance_prompt},
            ],
            "max_tokens": min(config.max_tokens, 300),  # 限制用戶指導長度
            "temperature": 0.7,  # 較高溫度生成更自然的回應
            # 注意：不使用 response_format，允許自然語言回應
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

            logger.info(
                "OpenAI用戶指導生成完成", model=config.name, content_length=len(content)
            )
            return content.strip(), 0.9

    async def _call_google_for_guidance(
        self,
        user_input: str,
        guidance_prompt: str,
        system_prompt: str,
        config: ModelConfig,
    ) -> tuple[str, float]:
        """為用戶指導調用 Google Gemini API（無JSON格式限制）"""

        full_prompt = f"{system_prompt}\n\n{guidance_prompt}"

        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": 0.7,  # 較高溫度生成更自然的回應
                "maxOutputTokens": min(config.max_tokens, 300),
                # 注意：不使用 responseMimeType，允許自然語言回應
            },
        }

        url = f"{config.endpoint}?key={config.api_key}"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

            result = response.json()
            content = result["candidates"][0]["content"]["parts"][0]["text"]

            logger.info(
                "Google用戶指導生成完成", model=config.name, content_length=len(content)
            )
            return content.strip(), 0.9
