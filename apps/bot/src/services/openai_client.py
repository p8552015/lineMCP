import json
from typing import Any

import httpx
import structlog
from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from src.models.mcp_manifest import get_mcp_manifest
from src.services.cost_tracker import CostTracker
from src.settings import get_settings
from src.utils.observability import get_tracer

logger = structlog.get_logger()
settings = get_settings()
tracer = get_tracer(__name__)


class OpenAIClient:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.cost_tracker = CostTracker()
        self.mcp_manifest = get_mcp_manifest()

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential_jitter(initial=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    )
    async def call_mcp_tool(
        self, user_id: str, tool_name: str, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        with tracer.start_as_current_span("call_mcp_tool") as span:
            span.set_attribute("tool.name", tool_name)
            span.set_attribute("user.id_hash", user_id)

            if not await self.cost_tracker.check_budget():
                logger.warning("Monthly budget exceeded")
                return {
                    "success": False,
                    "error": "月度預算已達上限，請聯繫管理員",
                }

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an assistant that helps users query machine data. "
                        "When users need machine status, trends, or suggestions, "
                        "use the appropriate MCP tools. For status queries, prefer "
                        "the status tool unless specifically asked for trends or fixes."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Call the {tool_name} tool with parameters: "
                        f"{json.dumps(parameters)}"
                    ),
                },
            ]

            tools = self._convert_manifest_to_tools()

            try:
                response = await self.client.chat.completions.create(
                    model=settings.openai_model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    max_tokens=settings.openai_max_tokens,
                    temperature=0.3,
                )

                await self.cost_tracker.track_usage(
                    user_id=user_id,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                )

                if response.choices[0].message.tool_calls:
                    tool_call = response.choices[0].message.tool_calls[0]
                    return {
                        "success": True,
                        "data": json.loads(tool_call.function.arguments),
                    }
                else:
                    return {
                        "success": False,
                        "error": "No tool call was made",
                    }

            except Exception as e:
                logger.error("OpenAI API call failed", error=str(e), exc_info=e)
                return {
                    "success": False,
                    "error": "API 呼叫失敗",
                }

    async def process_natural_language(
        self, user_id: str, message: str
    ) -> dict[str, Any]:
        with tracer.start_as_current_span("process_natural_language") as span:
            span.set_attribute("message.length", len(message))

            if not await self.cost_tracker.check_budget():
                logger.warning("Monthly budget exceeded")
                return {
                    "type": "text",
                    "content": "月度預算已達上限，請聯繫管理員",
                }

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an assistant for a factory monitoring system. "
                        "Help users query machine status, trends, and get maintenance "
                        "suggestions. "
                        "Use the MCP tools when appropriate. "
                        "Respond in Traditional Chinese. "
                        "For queries about multiple machines or complex analysis, "
                        "you may call "
                        "multiple tools. Format your response appropriately "
                        "for the user."
                    ),
                },
                {
                    "role": "user",
                    "content": message,
                },
            ]

            tools = self._convert_manifest_to_tools()

            try:
                response = await self.client.chat.completions.create(
                    model=settings.openai_model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    max_tokens=settings.openai_max_tokens,
                    temperature=settings.openai_temperature,
                )

                await self.cost_tracker.track_usage(
                    user_id=user_id,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                )

                result_message = response.choices[0].message

                if result_message.tool_calls:
                    tool_results = []
                    for tool_call in result_message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)

                        tool_result = await self._execute_mcp_tool(
                            user_id, tool_name, tool_args
                        )
                        tool_results.append(tool_result)

                    return self._format_tool_results(tool_results)
                else:
                    return {
                        "type": "text",
                        "content": result_message.content,
                    }

            except Exception as e:
                logger.error(
                    "Natural language processing failed", error=str(e), exc_info=e
                )
                return {
                    "type": "text",
                    "content": "處理您的訊息時發生錯誤，請稍後再試。",
                }

    def _convert_manifest_to_tools(self) -> list[dict[str, Any]]:
        tools = []
        for tool_name, tool_config in self.mcp_manifest.items():
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": tool_config["description"],
                        "parameters": tool_config["parameters"],
                    },
                }
            )
        return tools

    async def _execute_mcp_tool(
        self, user_id: str, tool_name: str, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {settings.mcp_api_key}",
                "Content-Type": "application/json",
                "X-User-ID": user_id,
            }

            url = f"{settings.mcp_server_url}/tools/{tool_name}"

            try:
                response = await client.post(
                    url,
                    headers=headers,
                    json=parameters,
                    timeout=10.0,
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(
                    "MCP tool execution failed",
                    tool=tool_name,
                    error=str(e),
                    exc_info=e,
                )
                return {
                    "success": False,
                    "error": "工具執行失敗",
                }

    def _format_tool_results(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        if len(results) == 1 and results[0].get("success"):
            data = results[0].get("data", {})
            if isinstance(data, dict) and "status" in data:
                return {
                    "type": "flex",
                    "title": "查詢結果",
                    "data": data,
                }

        combined_data = {
            "results": results,
            "count": len(results),
        }

        return {
            "type": "flex",
            "title": "綜合查詢結果",
            "data": combined_data,
        }
