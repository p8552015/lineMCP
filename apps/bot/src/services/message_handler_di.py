#!/usr/bin/env python3
"""
MessageHandler 依賴注入版本
採用構造函數注入模式，提升可測試性和可維護性
"""

import asyncio
from typing import Optional, Callable, Awaitable

import structlog
from linebot.v3.messaging import (
    Message,
    TextMessage,
)

from src.models.commands import Command, parse_command
from src.utils.observability import get_tracer

from .ai_model_service import AIModelService
from .database_service import DatabaseService
from .error_handlers import ErrorContext, log_performance, mcp_error_handler
from .mcp_response_parser import MCPResponseParser
from .message_formatter import MessageFormatter
from .nl_to_sql_service import NaturalLanguageToSQLService, QueryType
from .openai_client import OpenAIClient

logger = structlog.get_logger()
tracer = get_tracer(__name__)


class MessageHandlerDI:
    """
    依賴注入版本的訊息處理器
    - 構造函數注入所有依賴
    - 易於測試和模擬
    - 清晰的依賴關係宣告
    """

    def __init__(self,
                 mcp_client_factory: Callable[[], Awaitable],
                 ai_model_service: AIModelService,
                 nl_service: NaturalLanguageToSQLService,
                 db_service: DatabaseService,
                 formatter: MessageFormatter,
                 openai_client: Optional[OpenAIClient] = None):
        """
        初始化訊息處理器
        
        Args:
            mcp_client_factory: MCP 客戶端工廠函數
            ai_model_service: AI 模型服務
            nl_service: 自然語言處理服務
            db_service: 資料庫服務
            formatter: 訊息格式化器
            openai_client: OpenAI 客戶端（可選）
        """
        self.mcp_client_factory = mcp_client_factory
        self.ai_model_service = ai_model_service
        self.nl_service = nl_service
        self.db_service = db_service
        self.formatter = formatter
        self.openai_client = openai_client
        
        # 內部狀態
        self._mcp_client = None
        
        # TaskMaster 整合暫時禁用
        self.taskmaster = None

        logger.info("✅ 依賴注入版訊息處理器初始化完成")

    async def _get_mcp_client(self):
        """獲取 MCP 客戶端（延遲初始化）"""
        if self._mcp_client is None:
            self._mcp_client = await self.mcp_client_factory()
        return self._mcp_client

    @property
    async def mcp_client(self):
        """MCP 客戶端屬性（異步）"""
        return await self._get_mcp_client()

    def process_message_sync(
        self, user_id: str, message_text: str, reply_token: str
    ) -> Message:
        """同步版本的訊息處理，避免 event loop 衝突"""
        try:
            # 如果已經在 event loop 中，直接處理
            loop = asyncio.get_running_loop()
            return TextMessage(
                text=f"收到您的訊息：{message_text}\\n正在處理中，請稍後..."
            )
        except RuntimeError:
            # 沒有運行的 event loop，可以創建新的
            return asyncio.run(self.process_message(user_id, message_text, reply_token))

    @log_performance(include_args=False)
    async def process_message(
        self, user_id: str, message_text: str, reply_token: str
    ) -> Message:
        """
        主要訊息處理入口
        支援指令和自然語言查詢
        """
        with tracer.start_as_current_span("process_message") as span:
            span.set_attribute("message.length", len(message_text))
            span.set_attribute("user.id", user_id)

            try:
                # 解析指令
                command = parse_command(message_text)

                if command:
                    span.set_attribute("message.type", "command")
                    span.set_attribute("command.name", command.name)
                    return await self._handle_command(user_id, command)
                else:
                    span.set_attribute("message.type", "natural_language")
                    return await self._handle_natural_language(user_id, message_text)

            except Exception as e:
                # 使用統一錯誤處理
                from src.infrastructure.error_handler import handle_error_gracefully
                logger.error(f"Message processing failed: {e}", exc_info=True)
                return handle_error_gracefully(e, {"user_id": user_id, "message_text": message_text})

    async def _handle_command(self, user_id: str, command: Command) -> Message:
        """處理指令式查詢（使用 Command Pattern）"""
        logger.info(f"Processing command: {command.name}", args=command.args)
        
        # 使用指令執行器處理指令
        if not hasattr(self, '_command_executor'):
            self._initialize_command_executor()
        
        # 重建完整的指令文字以供執行器解析
        command_text = f"/{command.name}"
        if command.args:
            command_text += " " + " ".join(command.args)
        
        return await self._command_executor.execute_command(user_id, command_text)
    
    def _initialize_command_executor(self):
        """初始化指令執行器"""
        from src.domain.command_handler import CommandContext
        from src.domain.command_executor import CommandExecutor
        
        # 創建指令上下文
        context = CommandContext(
            mcp_client_factory=self.mcp_client_factory,
            ai_model_service=self.ai_model_service,
            nl_service=self.nl_service,
            db_service=self.db_service,
            formatter=self.formatter,
            openai_client=self.openai_client
        )
        
        # 創建並初始化指令執行器
        self._command_executor = CommandExecutor(context)
        self._command_executor.initialize()
        
        logger.info("✅ 指令執行器已初始化")

    @mcp_error_handler(
        "SQL查詢失敗", timeout_seconds=30, include_technical_details=True
    )
    async def _handle_sql_command(self, user_id: str, args: list[str]) -> Message:
        """處理SQL查詢指令"""
        if not args:
            return TextMessage(
                text="請提供SQL查詢語句，例如：/sql SELECT * FROM machines LIMIT 5"
            )

        sql_query = " ".join(args)

        with ErrorContext("sql_command") as ctx:
            ctx.add_context(query_preview=sql_query[:100])

            # 使用注入的資料庫服務
            mcp_client = await self._get_mcp_client()
            result = await mcp_client.call_tool(
                "sqlite", "read_query", {"query": sql_query}
            )

            parser = MCPResponseParser()
            data = parser.parse_query_result(result)

            # 格式化結果
            if data:
                response = f"📊 SQL查詢結果：\\n```\\n{sql_query}\\n```\\n\\n"
                for i, row in enumerate(data[:10]):  # 限制顯示前10行
                    response += f"{i+1}. {row}\\n"
                if len(data) > 10:
                    response += f"\\n... 共 {len(data)} 行結果，僅顯示前10行"
                return TextMessage(text=response)
            else:
                return TextMessage(
                    text=f"查詢執行成功，但沒有返回數據：\\n```\\n{sql_query}\\n```"
                )

    @mcp_error_handler("獲取表格列表失敗")
    async def _handle_tables_command(self, user_id: str, args: list[str]) -> Message:
        """顯示資料庫表格列表"""
        table_info = await self.db_service.get_table_info()

        if not table_info:
            return TextMessage(text="❌ 無法獲取資料庫表格資訊")

        message = "📋 資料庫表格列表：\\n"
        message += "━━━━━━━━━━━━━━━━━━━━\\n"

        for table_name, info in table_info.items():
            row_count = info.get("row_count", 0)
            column_count = len(info.get("columns", []))
            message += f"📊 {table_name}\\n"
            message += f"   欄位數：{column_count} | 資料筆數：{row_count:,}\\n"

        message += "\\n💡 使用 /sql PRAGMA table_info(表格名) 查看表格結構"
        return TextMessage(text=message)

    async def _handle_status_command(self, user_id: str, args: list[str]) -> Message:
        """處理狀態查詢指令"""
        if not args:
            # 系統狀態
            connection_ok = await self.db_service.test_connection()
            status_icon = "🟢" if connection_ok else "🔴"

            message = f"{status_icon} 系統狀態報告\\n"
            message += "━━━━━━━━━━━━━━━━━━━━\\n"
            message += f"🗄️ 資料庫連接：{'正常' if connection_ok else '異常'}\\n"
            message += "🧠 自然語言服務：正常\\n"
            message += "📝 訊息格式化：正常\\n"

            return TextMessage(text=message)
        else:
            # 特定狀態查詢，轉為自然語言處理
            query_text = " ".join(args)
            return await self._handle_natural_language(user_id, query_text)

    async def _handle_help_command(self, user_id: str, args: list[str]) -> Message:
        """處理幫助指令"""
        message = "🤖 LINE MCP Bot 使用說明\\n"
        message += "━━━━━━━━━━━━━━━━━━━━\\n"
        message += "💬 自然語言查詢：\\n"
        message += "   • M001機台狀況如何？\\n"
        message += "   • 查看所有機台\\n"
        message += "   • 近期故障記錄\\n"
        message += "   • 生產統計報告\\n"
        message += "   • 加工部狀況\\n\\n"
        message += "🛠️ 指令查詢：\\n"
        message += "   • /sql [SQL語句] - 執行SQL查詢\\n"
        message += "   • /tables - 查看資料庫表格\\n"
        message += "   • /status - 查看系統狀態\\n"
        message += "   • /models - 查看AI模型狀態\\n"
        message += "   • /help - 顯示此幫助\\n\\n"
        message += "💡 提示：支援中文自然語言查詢，\\n讓對話更自然！"

        return TextMessage(text=message)

    async def _handle_info_command(self, user_id: str, args: list[str]) -> Message:
        """處理資訊查詢指令"""
        suggested_queries = self.nl_service.get_suggested_queries()

        message = "💡 建議查詢範例：\\n"
        message += "━━━━━━━━━━━━━━━━━━━━\\n"

        for i, query in enumerate(suggested_queries, 1):
            message += f"{i}. {query}\\n"

        message += "\\n🔍 您也可以直接輸入想查詢的內容，\\n系統會自動理解並執行查詢。"

        return TextMessage(text=message)

    async def _handle_models_command(self, user_id: str, args: list[str]) -> Message:
        """處理AI模型狀態查詢指令"""
        models_info = self.ai_model_service.get_available_models()

        if not models_info:
            message = "❌ 沒有可用的AI模型\\n"
            message += "💡 請設定 OPENAI_API_KEY 或 GOOGLE_API_KEY"
            return TextMessage(text=message)

        message = "🤖 AI模型狀態報告\\n"
        message += "━━━━━━━━━━━━━━━━━━━━\\n"

        for model in models_info:
            name = model["name"]
            provider = model["provider"]
            is_default = model["is_default"]
            free_limit = model.get("free_tier_limit")

            status_icon = "⭐" if is_default else "🔹"
            message += f"{status_icon} {name} ({provider})\\n"

            # 成本資訊
            input_cost = model["cost_per_1k_input"]
            output_cost = model["cost_per_1k_output"]
            message += (
                f"   💰 成本: ${input_cost:.3f}/${output_cost:.3f} per 1K tokens\\n"
            )

            # 免費額度
            if free_limit:
                message += f"   🎁 免費額度: {free_limit:,} tokens/月\\n"

            # 上下文窗口
            context = model.get("context_window", 0)
            if context:
                message += f"   📏 上下文: {context:,} tokens\\n"

        # AI增強狀態
        ai_enabled = self.nl_service.enable_ai_enhancement
        message += f"\\n🧠 AI增強解析: {'✅ 啟用' if ai_enabled else '❌ 禁用'}\\n"
        message += f"🔄 規則回退: {'✅ 啟用' if self.nl_service.fallback_to_rules else '❌ 禁用'}\\n"

        # 使用建議
        message += "\\n💡 建議：\\n"
        if any(m.get("free_tier_limit") for m in models_info):
            message += "   • Gemini 1.5 Flash 提供最高免費額度\\n"
        message += "   • GPT-4o-mini 價格最低，適合大量使用\\n"
        message += "   • 使用 AI_ENABLE_ENHANCED_NL=true 啟用智能解析"

        return TextMessage(text=message)

    @mcp_error_handler("自然語言查詢失敗", timeout_seconds=30)
    async def _handle_natural_language(
        self, user_id: str, message_text: str
    ) -> Message:
        """
        處理自然語言查詢
        核心功能：將自然語言轉換為SQL並執行
        """
        with ErrorContext("natural_language_query") as ctx:
            ctx.add_context(query_text=message_text[:100])

            # 1. 獲取資料庫結構（用於AI增強）
            database_schema = await self.db_service.get_table_info()

            # 2. 解析自然語言（支援AI增強）
            parsed_query = await self.nl_service.parse_natural_language(
                message_text, database_schema
            )

            logger.info(
                "Natural language parsed",
                query_type=parsed_query.query_type.value,
                confidence=parsed_query.confidence,
                explanation=parsed_query.explanation,
            )

            # 2. 檢查解析結果
            if (
                parsed_query.query_type == QueryType.UNKNOWN
                or parsed_query.confidence < 0.3
            ):
                return self._handle_unknown_query(message_text)

            # 3. 執行資料庫查詢
            result = await self.db_service.execute_parsed_query(parsed_query)

            # 4. 格式化並返回結果
            return self.formatter.format_query_result(result)

    def _handle_unknown_query(self, message_text: str) -> Message:
        """處理無法識別的查詢"""
        if self._is_greeting(message_text):
            return self._handle_greeting()
        else:
            return self.formatter.format_suggestion_message()

    def _is_greeting(self, text: str) -> bool:
        """檢查是否為問候語"""
        greetings = [
            "你好",
            "hi",
            "hello",
            "嗨",
            "哈囉",
            "安安",
            "早安",
            "午安",
            "晚安",
        ]
        return any(greeting in text.lower() for greeting in greetings)

    def _handle_greeting(self) -> Message:
        """處理問候語"""
        message = "👋 您好！我是產線管理助手\\n"
        message += "━━━━━━━━━━━━━━━━━━━━\\n"
        message += "🔍 我可以幫您查詢：\\n"
        message += "   • 機台狀態和效能\\n"
        message += "   • 故障記錄和分析\\n"
        message += "   • 生產統計報告\\n"
        message += "   • 部門運行狀況\\n\\n"
        message += "💡 試試問我：「M001機台狀況如何？」"

        return TextMessage(text=message)

    # 保留一些舊方法以確保向後相容性
    async def _call_mcp_tool_compatible(
        self, server: str, tool: str, params: dict
    ) -> dict:
        """
        相容性方法：統一的 MCP 工具呼叫方法
        """
        try:
            logger.info(f"🛠️ MCP 工具調用：{server}.{tool}")

            mcp_client = await self._get_mcp_client()
            response = await mcp_client.call_tool(server, tool, params)

            if isinstance(response, dict):
                return response
            else:
                logger.warning(f"⚠️ 未預期的回應格式：{type(response)}")
                return {"success": False, "error": "回應格式錯誤"}

        except Exception as e:
            from src.domain.exceptions import create_mcp_error
            logger.error(f"❌ MCP 工具調用失敗 {server}.{tool}：{e}", exc_info=True)
            raise create_mcp_error(server, tool, str(e))

    def _is_machine_query(self, text: str) -> bool:
        """檢查是否為機台查詢（向後相容性）"""
        # 現在統一由自然語言服務處理
        return True  # 讓所有查詢都進入自然語言處理流程