#!/usr/bin/env python3
"""
MessageHandler 依賴注入版本
採用構造函數注入模式，提升可測試性和可維護性
"""

import asyncio

import structlog
from linebot.v3.messaging import Message, TextMessage

# 移除對已刪除模組的依賴，不再使用 Command 和 parse_command
from src.utils.observability import get_tracer

from .error_handlers import ErrorContext, log_performance, mcp_error_handler
from .mcp_response_parser import MCPResponseParser
from .nl_to_sql.models.query_models import QueryType

logger = structlog.get_logger()
tracer = get_tracer(__name__)


class MessageHandlerDI:
    """
    依賴注入版本的訊息處理器
    - 構造函數注入所有依賴
    - 易於測試和模擬
    - 清晰的依賴關係宣告
    """

    def __init__(self, service_factory):
        """初始化訊息處理器，注入所有依賴服務"""
        self.service_factory = service_factory
        # 延遲初始化依賴服務
        self._initialized = False

    def _is_query_relevant(self, user_input: str, parsed_query) -> bool:
        """
        檢查解析結果是否與用戶輸入相關
        增強空查詢檢測：確保解析結果真正匹配用戶意圖
        """
        user_input_lower = user_input.lower()

        # 🔥 核心修復：對於 UNKNOWN 類型查詢，跳過 SQL 檢查
        if parsed_query.query_type == QueryType.UNKNOWN:
            logger.info("✅ UNKNOWN 查詢跳過 SQL 檢查", user_input=user_input[:50])
            # UNKNOWN 查詢本來就不應該有 SQL，這是正常的
        else:
            # 對其他類型的查詢檢查 SQL 有效性
            if hasattr(parsed_query, "sql_query") and parsed_query.sql_query:
                sql_query = parsed_query.sql_query.strip()
                if not sql_query:
                    logger.warning("❌ 查詢相關性檢查：SQL 查詢為空", user_input=user_input[:50])
                    return False
            else:
                logger.warning("❌ 查詢相關性檢查：無 SQL 查詢", user_input=user_input[:50])
                return False

        # 🔥 增強關鍵字匹配檢查
        if (
            hasattr(parsed_query, "query_type")
            and parsed_query.query_type
            and hasattr(parsed_query.query_type, "value")
        ):
            query_type_str = parsed_query.query_type.value.lower()

            # 機台相關查詢的關鍵字檢查
            if "machine" in query_type_str or "status" in query_type_str:
                machine_keywords = [
                    "機台",
                    "設備",
                    "機器",
                    "車床",
                    "銑床",
                    "包裝機",
                    "焊接機",
                    "切割機",
                    "組裝線",
                    "m001",
                    "m002",
                    "m003",
                    "m004",
                    "m005",
                    "cnc",
                    "加工",
                    "生產",
                    "製造",
                ]
                has_machine_keyword = any(
                    keyword in user_input_lower for keyword in machine_keywords
                )

                if not has_machine_keyword:
                    logger.warning(
                        "❌ 查詢相關性檢查：機台查詢缺少機台關鍵字",
                        user_input=user_input[:50],
                        query_type=query_type_str,
                    )
                    return False

            # 部門相關查詢的關鍵字檢查
            if "department" in query_type_str:
                department_keywords = ["部門", "生產", "加工", "品質", "工廠", "車間"]
                has_department_keyword = any(
                    keyword in user_input_lower for keyword in department_keywords
                )

                if not has_department_keyword:
                    logger.warning(
                        "❌ 查詢相關性檢查：部門查詢缺少部門關鍵字",
                        user_input=user_input[:50],
                        query_type=query_type_str,
                    )
                    return False

            # 指標相關查詢的關鍵字檢查
            if any(
                metric in query_type_str
                for metric in ["utilization", "efficiency", "oee", "defect"]
            ):
                metric_keywords = [
                    "稼動率",
                    "效率",
                    "oee",
                    "不良率",
                    "產量",
                    "故障",
                    "停機",
                    "維護",
                    "統計",
                    "指標",
                ]
                has_metric_keyword = any(
                    keyword in user_input_lower for keyword in metric_keywords
                )

                if not has_metric_keyword:
                    logger.warning(
                        "❌ 查詢相關性檢查：指標查詢缺少指標關鍵字",
                        user_input=user_input[:50],
                        query_type=query_type_str,
                    )
                    return False

        # 🔥 參數完整性檢查
        if hasattr(parsed_query, "parameters") and parsed_query.parameters:
            # 確保關鍵參數不為空
            for key, value in parsed_query.parameters.items():
                if key in ["machine_id", "department", "metric_type"] and not value:
                    logger.warning(
                        "❌ 查詢相關性檢查：關鍵參數為空",
                        user_input=user_input[:50],
                        empty_parameter=key,
                    )
                    return False

        logger.info("✅ 查詢相關性檢查通過", user_input=user_input[:50])
        return True

    def _initialize_services(self):
        """延遲初始化所有依賴服務"""
        if self._initialized:
            return

        # 從服務工廠獲取所有必要的服務
        self.ai_model_service = self.service_factory.get_ai_model_service()
        self.nl_service = self.service_factory.get_nl_service()
        self.db_service = self.service_factory.get_database_service()
        self.formatter = self.service_factory.get_message_formatter()

        # 初始化 MCP 相關屬性
        self.mcp_client_factory = self.service_factory.get_mcp_client_factory
        self._mcp_client = None

        # 初始化 OpenAI 客戶端（如果需要）
        try:
            from src.services.openai_client import OpenAIClient

            self.openai_client = self.service_factory.get_service(OpenAIClient)
        except Exception:
            self.openai_client = None

        self._initialized = True
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
            asyncio.get_running_loop()
            return TextMessage(text=f"收到您的訊息：{message_text}\\n正在處理中，請稍後...")
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
                # 檢查是否為指令格式
                if message_text.strip().startswith("/"):
                    span.set_attribute("message.type", "command")
                    # 委託給指令執行器處理
                    if not hasattr(self, "_command_executor"):
                        self._initialize_command_executor()
                    return await self._command_executor.execute_command(
                        user_id, message_text
                    )
                else:
                    span.set_attribute("message.type", "natural_language")
                    return await self._handle_natural_language(user_id, message_text)

            except Exception as e:
                # 使用統一錯誤處理
                from src.infrastructure.error_handler import handle_error_gracefully

                logger.error(f"Message processing failed: {e}", exc_info=True)
                return handle_error_gracefully(
                    e, {"user_id": user_id, "message_text": message_text}
                )

    # _handle_command 方法已移除，改為直接使用 CommandExecutor

    def _initialize_command_executor(self):
        """初始化指令執行器"""
        from src.domain.command_executor import CommandExecutor
        from src.domain.command_handler import CommandContext

        # 創建指令上下文
        context = CommandContext(
            mcp_client_factory=self.mcp_client_factory,
            ai_model_service=self.ai_model_service,
            nl_service=self.nl_service,
            db_service=self.db_service,
            formatter=self.formatter,
            openai_client=self.openai_client,
        )

        # 創建並初始化指令執行器
        self._command_executor = CommandExecutor(context)
        self._command_executor.initialize()

        logger.info("✅ 指令執行器已初始化")

    def _initialize_suggestion_service(self):
        """初始化建議服務 - 符合 DIP 原則"""
        from .suggestion_service import SuggestionService

        # 🔥 依賴注入：注入 AI 服務和格式化器
        self._suggestion_service = SuggestionService(
            ai_model_service=self.ai_model_service, message_formatter=self.formatter
        )

        logger.info("✅ 建議服務已初始化")

    @mcp_error_handler("SQL查詢失敗", timeout_seconds=30, include_technical_details=True)
    async def _handle_sql_command(self, user_id: str, args: list[str]) -> Message:
        """處理SQL查詢指令"""
        if not args:
            return TextMessage(
                text=("請提供SQL查詢語句，例如：/sql SELECT * FROM machines LIMIT 5")
            )

        sql_query = " ".join(args).strip()

        # 🔥 緊急修復：檢查空查詢
        if not sql_query:
            logger.error("❌ 緊急阻止：MessageHandler SQL 查詢為空", user_id=user_id, args=args)
            return TextMessage(
                text="❌ SQL 查詢不能為空\\n\\n"
                "📝 用法：/sql <SQL查詢語句>\\n"
                "💡 例如：/sql SELECT * FROM machines LIMIT 5"
            )

        with ErrorContext("sql_command") as ctx:
            ctx.add_context(query_preview=sql_query[:100])

            # 使用注入的資料庫服務
            mcp_client = await self._get_mcp_client()
            result = await mcp_client.call_tool("postgres", "query", {"sql": sql_query})

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
                return TextMessage(text=f"查詢執行成功，但沒有返回數據：\\n```\\n{sql_query}\\n```")

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

        message += (
            "\n💡 使用 /sql SELECT column_name, data_type "
            "FROM information_schema.columns WHERE table_name = '表格名' 查看表格結構"
        )
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
            message += f"   💰 成本: ${input_cost:.3f}/${output_cost:.3f} per 1K tokens\\n"

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
        message += (
            f"🔄 規則回退: " f"{'✅ 啟用' if self.nl_service.fallback_to_rules else '❌ 禁用'}\n"
        )

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
        # 確保服務已初始化
        self._initialize_services()

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

            # 2. 🔥 強化空查詢檢測 - 多層驗證機制
            # 檢查解析類型
            is_unknown_type = parsed_query.query_type == QueryType.UNKNOWN

            # 檢查信心度
            is_low_confidence = parsed_query.confidence < 0.6  # 提高門檻從 0.5 到 0.6

            # 檢查 SQL 查詢是否有效
            has_valid_sql = (
                hasattr(parsed_query, "sql_query")
                and parsed_query.sql_query
                and parsed_query.sql_query.strip()
            )

            # 檢查查詢相關性
            is_relevant = self._is_query_relevant(message_text, parsed_query)

            # 記錄檢測狀態
            logger.info(
                "🔍 空查詢檢測狀態",
                user_input=message_text[:50],
                query_type=parsed_query.query_type.value,
                confidence=parsed_query.confidence,
                is_unknown_type=is_unknown_type,
                is_low_confidence=is_low_confidence,
                has_valid_sql=has_valid_sql,
                is_relevant=is_relevant,
            )

            # 🔥 智能檢測：區分真正的 UNKNOWN 查詢和低信心度的有效查詢
            if is_unknown_type:
                logger.warning("❌ 空查詢檢測：查詢類型為 UNKNOWN - 強制進入LLM指導模式")
                return await self._handle_unknown_query(message_text, parsed_query)

            # 🔥 特殊處理：有明確機台 ID 的查詢，即使信心度低也嘗試執行
            has_machine_id = (
                hasattr(parsed_query, "parameters")
                and parsed_query.parameters
                and "machine_id" in parsed_query.parameters
                and parsed_query.parameters["machine_id"]
            )

            # 🔥 模糊查詢檢測：單一詞彙或過於簡短的查詢應觸發 LLM 指導
            is_ambiguous_query = (
                len(message_text.strip()) <= 3  # 3個字符以下
                or message_text.strip() in ["車床", "銑床", "機台", "設備", "生產", "製造", "工廠"]
                or (len(message_text.split()) == 1 and not has_machine_id)  # 單詞且無機台ID
            )

            # 如果是模糊查詢，強制觸發 LLM 指導
            if is_ambiguous_query:
                logger.warning(f"🔍 檢測到模糊查詢：'{message_text}' - 強制進入LLM指導模式")
                return await self._handle_unknown_query(message_text, parsed_query)

            # 如果有機台 ID，降低信心度要求
            effective_confidence_threshold = 0.3 if has_machine_id else 0.6
            is_effectively_low_confidence = (
                parsed_query.confidence < effective_confidence_threshold
            )

            # 任何一項檢測失敗都視為需要 LLM 指導
            if is_effectively_low_confidence or not has_valid_sql or not is_relevant:
                if is_unknown_type:
                    logger.warning("❌ 空查詢檢測：查詢類型為 UNKNOWN")
                elif is_low_confidence:
                    logger.warning(f"❌ 空查詢檢測：信心度過低 ({parsed_query.confidence})")
                elif not has_valid_sql:
                    logger.warning("❌ 空查詢檢測：SQL 查詢無效或為空")
                elif not is_relevant:
                    logger.warning("❌ 空查詢檢測：查詢與用戶輸入不相關")

                return await self._handle_unknown_query(message_text, parsed_query)

            # 3. 執行資料庫查詢
            result = await self.db_service.execute_parsed_query(parsed_query)

            # 4. 格式化並返回結果
            return self.formatter.format_query_result(result)

    async def _handle_unknown_query(
        self, message_text: str, parsed_query=None
    ) -> Message:
        """
        處理無法識別的查詢 - 優先使用 LLM 指導
        🔥 強化版：確保所有空查詢都能獲得智能建議
        """
        logger.info("🤖 進入 LLM 指導模式", user_input=message_text[:50])

        # 🤖 第一優先：檢查是否有 LLM 生成的用戶指導
        if (
            parsed_query
            and parsed_query.parameters
            and "user_guidance" in parsed_query.parameters
        ):
            guidance = parsed_query.parameters["user_guidance"]
            logger.info("✅ 使用已生成的 LLM 指導回覆")
            return TextMessage(text=guidance)

        # 🤖 第二優先：針對查詢類型生成智能指導（包含 UNKNOWN）
        if parsed_query:
            try:
                logger.info(
                    "🔄 為查詢類型生成 LLM 指導",
                    query_type=parsed_query.query_type.value,
                    confidence=parsed_query.confidence,
                )

                # 確保服務已初始化
                self._initialize_services()

                # 🔥 修復：對於 UNKNOWN 查詢，使用通用的品質指標回應模式
                if parsed_query.query_type == QueryType.UNKNOWN:
                    # 對 UNKNOWN 查詢使用特殊處理，模擬為品質指標查詢
                    guidance = await self.nl_service._generate_user_guidance(
                        QueryType.PRODUCTION_STATS,  # 使用生產統計類型作為模板
                        {
                            "quality_metric": "unsupported",
                            "original_query": message_text,
                        },
                        message_text,
                    )
                else:
                    # 生成針對性的 LLM 指導
                    guidance = await self.nl_service._generate_user_guidance(
                        parsed_query.query_type,
                        parsed_query.parameters if parsed_query.parameters else {},
                        message_text,
                    )

                logger.info("✅ 成功生成查詢類型的 LLM 指導")
                return TextMessage(text=guidance)

            except Exception as e:
                logger.error(
                    "❌ 生成查詢類型指導失敗，回退到通用建議",
                    error=str(e),
                    query_type=parsed_query.query_type.value,
                )

        # 🤖 第三優先：檢查是否為問候語
        if self._is_greeting(message_text):
            logger.info("✅ 識別為問候語，返回歡迎訊息")
            return self._handle_greeting()

        # 🤖 最後回退：使用通用建議服務
        try:
            logger.info("🔄 使用通用建議服務生成回覆")
            # 確保建議服務已初始化
            if not hasattr(self, "_suggestion_service"):
                self._initialize_suggestion_service()

            return await self._suggestion_service.generate_suggestion(message_text)

        except Exception as e:
            logger.error("❌ 通用建議服務失敗，使用最終回退", error=str(e))

            # 🚨 最終回退：手動建議
            return TextMessage(
                text=f"❓ 無法理解您的查詢：「{message_text}」\n\n"
                "💡 請嘗試以下格式：\n"
                "• 「M001機台狀況」\n"
                "• 「生產部門今日報告」\n"
                "• 「所有機台稼動率」\n"
                "• 「故障記錄查詢」\n\n"
                "📞 如需協助，請聯絡系統管理員"
            )

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
            raise create_mcp_error(server, tool, str(e)) from e

    def _is_machine_query(self, text: str) -> bool:
        """檢查是否為機台查詢（向後相容性）"""
        # 現在統一由自然語言服務處理
        return True  # 讓所有查詢都進入自然語言處理流程

    # 建議生成功能已移至 SuggestionService，符合 SRP 原則
