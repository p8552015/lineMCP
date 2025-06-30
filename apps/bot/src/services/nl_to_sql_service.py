"""
自然語言轉 SQL 服務 - 向後兼容包裝器

這是一個向後兼容的包裝器，維持舊有的 NaturalLanguageToSQLService 介面，
但內部使用新的 SOLID 重構架構組件。

SOLID 重構完成後，此檔案作為適配器模式實現，
確保現有代碼無需修改即可使用新架構。
"""

from typing import Any

import structlog

from .ai_model_service import AIModelService
from .nl_to_sql.interfaces.parsing_interfaces import IParser
from .nl_to_sql.interfaces.query_builder_interfaces import IQueryBuilder
from .nl_to_sql.interfaces.statistics_interfaces import (
    IConfiguration,
    IStatistics,
    StatisticsEventType,
)
from .nl_to_sql.models.query_models import ParsedQuery, QueryType

logger = structlog.get_logger()


class NaturalLanguageToSQLService:
    """
    自然語言轉 SQL 服務 (向後兼容包裝器)

    這個類別維持舊有的 API 介面，但內部委託給新的 SOLID 重構組件。
    實現適配器模式，確保向後兼容性。

    注意：此為過渡期間的兼容性實現，
    建議新代碼直接使用 SOLID 組件介面。
    """

    def __init__(self, ai_model_service: AIModelService):
        """
        初始化自然語言轉 SQL 服務

        Args:
            ai_model_service: AI 模型服務實例

        注意：新的 SOLID 組件會通過依賴注入框架自動注入
        """
        self.ai_model_service = ai_model_service

        # SOLID 組件將會通過服務定位器模式延遲注入
        self._parser: IParser | None = None
        self._query_builder: IQueryBuilder | None = None
        self._statistics: IStatistics | None = None
        self._configuration: IConfiguration | None = None

        logger.info("🔄 自然語言轉 SQL 服務 (兼容包裝器) 初始化完成")

    def _get_parser(self) -> IParser:
        """延遲獲取解析器（服務定位器模式）"""
        if self._parser is None:
            # 通過全域服務工廠獲取
            from ..infrastructure.enhanced_service_factory import (
                get_enhanced_service_factory,
            )

            factory = get_enhanced_service_factory()
            self._parser = factory.get_parser()
        return self._parser

    def _get_query_builder(self) -> IQueryBuilder:
        """延遲獲取查詢建構器（服務定位器模式）"""
        if self._query_builder is None:
            from ..infrastructure.enhanced_service_factory import (
                get_enhanced_service_factory,
            )

            factory = get_enhanced_service_factory()
            self._query_builder = factory.get_builder()
        return self._query_builder

    def _get_statistics(self) -> IStatistics:
        """延遲獲取統計服務（服務定位器模式）"""
        if self._statistics is None:
            from ..infrastructure.enhanced_service_factory import (
                get_enhanced_service_factory,
            )

            factory = get_enhanced_service_factory()
            self._statistics = factory.get_statistics()
        return self._statistics

    def _get_configuration(self) -> IConfiguration:
        """延遲獲取配置服務（服務定位器模式）"""
        if self._configuration is None:
            from ..infrastructure.enhanced_service_factory import (
                get_enhanced_service_factory,
            )

            factory = get_enhanced_service_factory()
            self._configuration = factory.get_configuration()
        return self._configuration

    def _validate_input(self, text: str) -> dict[str, Any]:
        """
        輸入驗證 - 防護空查詢和無效輸入

        Args:
            text: 自然語言文字

        Returns:
            Dict: 驗證結果 {"valid": bool, "error": str, "normalized_text": str}
        """
        # 基本空值檢查
        if not text:
            return {"valid": False, "error": "輸入不能為空", "normalized_text": ""}

        # 字串清理和標準化
        normalized_text = text.strip()
        if not normalized_text:
            return {
                "valid": False,
                "error": "輸入只包含空白字符",
                "normalized_text": "",
            }

        # 長度檢查
        if len(normalized_text) < 2:
            return {
                "valid": False,
                "error": "輸入過短，需要至少2個字符",
                "normalized_text": normalized_text,
            }

        if len(normalized_text) > 1000:
            return {
                "valid": False,
                "error": "輸入過長，請簡化查詢",
                "normalized_text": normalized_text,
            }

        # 惡意輸入檢查
        suspicious_patterns = [
            "drop table",
            "delete from",
            "truncate",
            "alter table",
            "create table",
            "insert into",
            "update set",
            "--",
            "/*",
            "*/",
        ]

        text_lower = normalized_text.lower()
        for pattern in suspicious_patterns:
            if pattern in text_lower:
                logger.warning(f"檢測到可疑輸入模式: {pattern}")
                return {
                    "valid": False,
                    "error": "檢測到不安全的輸入內容",
                    "normalized_text": normalized_text,
                }

        # 特殊字符檢查（允許中文、英文、數字、基本標點）
        import re

        if not re.match(r"^[\u4e00-\u9fff\w\s\.,?!，。？！\-/]+$", normalized_text):
            return {
                "valid": False,
                "error": "包含不支持的特殊字符",
                "normalized_text": normalized_text,
            }

        return {"valid": True, "error": "", "normalized_text": normalized_text}

    async def parse_natural_language(
        self, text: str, context: dict[str, Any] | None = None
    ) -> ParsedQuery:
        """
        解析自然語言為 SQL 查詢（向後兼容介面）- 增強輸入驗證

        Args:
            text: 自然語言文字
            context: 可選的上下文資訊

        Returns:
            ParsedQuery: 解析結果
        """
        try:
            # 🛡️ 輸入驗證 - 防護空查詢和無效輸入
            validation_result = self._validate_input(text)
            if not validation_result["valid"]:
                logger.warning(
                    "❌ 輸入驗證失敗",
                    error=validation_result["error"],
                    original_text=text[:50],
                )

                # 記錄失敗統計
                self._get_statistics().record_failure(
                    operation_type="input_validation",
                    error_type="ValidationError",
                    error_message=validation_result["error"],
                    metadata={"original_text_length": len(text)},
                )

                return ParsedQuery(
                    query_type=QueryType.UNKNOWN,
                    sql_query="",
                    parameters={},
                    confidence=0.0,
                    explanation=f"輸入驗證失敗: {validation_result['error']}",
                )

            # 使用驗證後的文字
            normalized_text = validation_result["normalized_text"]

            # 記錄開始統計
            self._get_statistics().record_event(
                event_type=StatisticsEventType.PARSE_SUCCESS,
                metadata={
                    "text_length": len(normalized_text),
                    "original_length": len(text),
                },
            )

            # 使用新的 SOLID 解析器（使用標準化文字）
            parser = self._get_parser()
            parse_result = await parser.parse(normalized_text, context)

            # 🔥 修復：如果解析成功但無 SQL，則使用查詢建構器生成 SQL
            if parse_result.query_type != QueryType.UNKNOWN:
                # 嘗試使用查詢建構器生成 SQL
                try:
                    builder = self._get_query_builder()
                    sql_query = builder.build_query(
                        parse_result.query_type, parse_result.parameters
                    )

                    # 建構完整的查詢結果
                    result = ParsedQuery(
                        query_type=parse_result.query_type,
                        sql_query=sql_query,
                        parameters=parse_result.parameters,
                        confidence=parse_result.confidence,
                        explanation=parse_result.explanation,
                    )

                    logger.info(
                        "✅ SQL 查詢建構成功",
                        query_type=parse_result.query_type.value,
                        sql_length=len(sql_query),
                        confidence=parse_result.confidence,
                    )

                except Exception as e:
                    logger.error(
                        "❌ SQL 建構失敗，提供用戶指導",
                        query_type=parse_result.query_type.value,
                        error=str(e),
                    )

                    # 生成用戶指導作為回退
                    user_guidance = await self._generate_user_guidance(
                        parse_result.query_type,
                        parse_result.parameters,
                        normalized_text,
                    )

                    result = ParsedQuery(
                        query_type=QueryType.UNKNOWN,
                        sql_query="",
                        parameters={
                            "user_guidance": user_guidance,
                            "original_query_type": parse_result.query_type.value,
                            "original_parameters": parse_result.parameters,
                            "guidance_type": "sql_build_failed",
                            "error": str(e),
                        },
                        confidence=0.0,
                        explanation=f"SQL 建構失敗：{user_guidance}",
                    )
            else:
                result = parse_result

            # 🛡️ 最終防護 - 確保絕對不會返回空 SQL 查詢
            if result.query_type != QueryType.UNKNOWN and (
                not result.sql_query or not result.sql_query.strip()
            ):
                logger.error(
                    "🚨 嚴重錯誤：最終結果仍包含空 SQL！強制設為 UNKNOWN",
                    query_type=result.query_type.value,
                    parameters=result.parameters,
                )

                # 記錄嚴重錯誤統計
                self._get_statistics().record_failure(
                    operation_type="final_sql_validation",
                    error_type="EmptySQLError",
                    error_message="最終結果包含空 SQL",
                    metadata={"original_query_type": result.query_type.value},
                )

                # 強制返回安全的失敗結果
                result = ParsedQuery(
                    query_type=QueryType.UNKNOWN,
                    sql_query="",
                    parameters={},
                    confidence=0.0,
                    explanation="系統無法生成有效的 SQL 查詢，請嘗試重新描述您的需求",
                )

            # 記錄成功統計
            if result.query_type != QueryType.UNKNOWN:
                self._get_statistics().record_success(
                    operation_type="natural_language_parsing",
                    duration=0.0,  # 在實際實現中應該測量時間
                    metadata={
                        "confidence": result.confidence,
                        "sql_length": len(result.sql_query),
                        "has_parameters": bool(result.parameters),
                    },
                )

            logger.info(
                "✅ 自然語言解析完成",
                query_type=result.query_type.value,
                confidence=result.confidence,
                sql_length=len(result.sql_query) if result.sql_query else 0,
            )

            return result

        except Exception as e:
            # 記錄失敗統計
            self._get_statistics().record_failure(
                operation_type="natural_language_parsing",
                error_type=type(e).__name__,
                error_message=str(e),
            )

            logger.error("❌ 自然語言解析失敗", error=str(e))

            # 返回失敗的解析結果
            return ParsedQuery(
                query_type=QueryType.UNKNOWN,
                sql_query="",
                parameters={},
                confidence=0.0,
                explanation=f"解析失敗: {str(e)}",
            )

    def can_handle_query(self, text: str) -> float:
        """
        檢查是否能處理給定的查詢（向後兼容介面）

        Args:
            text: 查詢文字

        Returns:
            float: 處理能力信心度 (0-1)
        """
        try:
            parser = self._get_parser()
            return parser.can_handle(text)
        except Exception:
            return 0.0

    def get_supported_query_types(self) -> list[QueryType]:
        """
        獲取支援的查詢類型（向後兼容介面）

        Returns:
            list[QueryType]: 支援的查詢類型列表
        """
        try:
            builder = self._get_query_builder()
            return builder.get_supported_query_types()
        except Exception:
            return list(QueryType)

    def get_service_info(self) -> dict[str, Any]:
        """
        獲取服務資訊（向後兼容介面）

        Returns:
            Dict[str, Any]: 服務資訊
        """
        try:
            config = self._get_configuration()
            stats = self._get_statistics()

            return {
                "service_name": "NaturalLanguageToSQLService",
                "version": "2.0.0-solid-compatible",
                "architecture": "SOLID-refactored-with-compatibility-layer",
                "configuration": config.get_config_metadata(),
                "statistics": stats.get_summary_stats(),
                "features": {
                    "nl_to_sql_enabled": True,
                    "query_statistics": True,
                    "solid_architecture": True,
                },
            }
        except Exception as e:
            return {
                "service_name": "NaturalLanguageToSQLService",
                "version": "2.0.0-solid-compatible",
                "error": str(e),
            }

    async def _generate_user_guidance(
        self, query_type: QueryType, parameters: dict[str, Any], user_input: str
    ) -> str:
        """
        🤖 使用 LLM 生成智能用戶指導

        Args:
            query_type: 解析出的查詢類型
            parameters: 解析參數
            user_input: 用戶原始輸入

        Returns:
            str: 智能用戶指導訊息
        """
        try:
            # 🔥 智能提示詞：根據查詢類型和內容生成自然回覆
            prompt = self._build_intelligent_prompt(query_type, parameters, user_input)

            # 🔥 修復：調用專門的用戶指導方法而非技術性NL-to-SQL方法
            ai_response = await self.ai_model_service.generate_user_guidance(
                user_input=user_input,
                guidance_prompt=prompt,
            )

            # 處理 AI 回應 - 正確處理 tuple 返回值
            if isinstance(ai_response, tuple):
                enhanced_query, confidence = ai_response
                if enhanced_query and enhanced_query.strip():
                    logger.info(
                        "✅ LLM 成功生成用戶指導",
                        input_length=len(user_input),
                        response_length=len(enhanced_query),
                        confidence=confidence,
                    )
                    return enhanced_query.strip()
                else:
                    # AI 返回空內容時的備用指導
                    return self._get_fallback_guidance(query_type, parameters)
            else:
                # 處理意外的返回類型
                logger.warning("⚠️ AI服務返回意外類型", response_type=type(ai_response))
                return self._get_fallback_guidance(query_type, parameters)

        except Exception as e:
            logger.error("❌ LLM 用戶指導生成失敗", error=str(e))
            # 返回備用指導
            return self._get_fallback_guidance(query_type, parameters)

    def _get_fallback_guidance(
        self, query_type: QueryType, parameters: dict[str, Any]
    ) -> str:
        """
        🛡️ 備用用戶指導（當 LLM 失敗時）

        Args:
            query_type: 查詢類型
            parameters: 參數

        Returns:
            str: 備用指導訊息
        """
        guidance_templates = {
            QueryType.MACHINE_STATUS: {
                "description": "查詢機台運行狀態",
                "missing_info": "可能缺少具體機台編號或部門資訊",
                "examples": [
                    "M001 機台狀態",
                    "加工部機台狀態",
                    "所有 CNC 機台狀況",
                    "M002 到 M005 機台運行情況",
                ],
            },
            QueryType.ALL_MACHINES: {
                "description": "查詢所有機台概覽",
                "missing_info": "查詢範圍可能需要更明確",
                "examples": [
                    "所有機台狀態",
                    "整體設備概覽",
                    "工廠機台運行報告",
                    "今日機台狀況統計",
                ],
            },
            QueryType.DEPARTMENT_STATUS: {
                "description": "查詢部門機台狀態",
                "missing_info": "缺少具體部門名稱",
                "examples": [
                    "加工部機台狀態",
                    "組裝部設備狀況",
                    "品管部機台概覽",
                    "維修部機台運行情況",
                ],
            },
            QueryType.PRODUCTION_STATS: {
                "description": "查詢生產統計報告",
                "missing_info": "可能缺少時間範圍或統計指標",
                "examples": [
                    "今日生產統計",
                    "本週產量報告",
                    "加工部生產效率",
                    "月度生產績效分析",
                ],
            },
            QueryType.FAULT_ANALYSIS: {
                "description": "查詢故障分析報告",
                "missing_info": "可能缺少時間範圍或機台範圍",
                "examples": [
                    "近期故障統計",
                    "M001 故障記錄",
                    "本月異常分析",
                    "加工部故障趨勢",
                ],
            },
        }

        template = guidance_templates.get(
            query_type,
            {
                "description": "系統查詢",
                "missing_info": "查詢資訊不完整",
                "examples": ["請提供更具體的查詢條件"],
            },
        )

        examples_text = "\n".join([f"• {ex}" for ex in template["examples"]])

        return f"""🤖 查詢分析建議

📋 您想查詢：{template['description']}
⚠️ 可能問題：{template['missing_info']}

💡 建議查詢範例：
{examples_text}

🔧 提示：請提供更具體的機台編號、部門名稱或時間範圍，讓我能更準確地為您查詢資料。"""

    def _build_intelligent_prompt(
        self, query_type: QueryType, parameters: dict[str, Any], user_input: str
    ) -> str:
        """
        🧠 根據查詢類型和內容生成智能提示詞

        Args:
            query_type: 查詢類型
            parameters: 解析參數
            user_input: 用戶輸入

        Returns:
            str: 智能提示詞
        """
        # 根據查詢內容生成自然的指導
        if "車床" in user_input or "銑床" in user_input or "機台" in user_input:
            # 機台相關查詢
            if len(user_input.strip()) <= 3:
                return f"""
我需要協助用戶明確他們對「{user_input}」的查詢需求。

請以友善、專業的語氣回答，幫助用戶明確：
1. 他們想查詢什麼具體信息？（狀態、產量、故障記錄等）
2. 需要查詢哪個特定機台？（如M001、M002等）
3. 時間範圍是什麼？（今天、本週、即時等）

請提供2-3個具體的查詢範例，並使用製造業術語。回覆要簡潔實用。
"""
            else:
                return f"""
用戶查詢「{user_input}」，請協助他們獲得更精確的製造資訊。

請以製造專業人員的角度，提供友善的建議：
- 分析用戶可能的查詢意圖
- 建議如何完善查詢條件
- 提供2-3個實用的查詢範例

保持回覆簡潔專業，聚焦在實際操作建議上。
"""

        elif "不良率" in user_input or "品質" in user_input:
            # 品質相關查詢
            return f"""
用戶詢問「{user_input}」，但系統目前不支援品質指標的直接查詢。

請協助解釋：
1. 為什麼無法直接查詢不良率數據
2. 建議替代的查詢方式（如機台狀態、產量統計等）
3. 提供2-3個相關的可查詢範例

語氣要專業友善，幫助用戶理解系統功能範圍。
"""

        elif "生產" in user_input or "統計" in user_input or "報告" in user_input:
            # 生產統計查詢
            return f"""
用戶想了解「{user_input}」的相關資訊。

請提供實用的指導：
1. 說明需要哪些具體參數（時間、機台、部門等）
2. 解釋可以查詢的統計類型
3. 提供2-3個完整的查詢範例

回覆要簡潔明瞭，聚焦在如何獲得有用的生產資訊。
"""

        else:
            # 通用查詢
            return f"""
用戶輸入「{user_input}」，需要協助明確查詢需求。

請以製造業智能助手的身分：
1. 友善地分析用戶可能想查詢什麼
2. 建議如何完善查詢條件
3. 提供實用的查詢範例

保持專業但易懂的語氣，幫助用戶快速獲得所需資訊。
"""


# 向後兼容的匯出
__all__ = ["NaturalLanguageToSQLService", "ParsedQuery", "QueryType"]
