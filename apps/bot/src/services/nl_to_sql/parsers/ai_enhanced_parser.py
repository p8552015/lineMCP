"""
AI 增強的自然語言解析器

實現 SRP (單一職責原則)：
- 專門負責基於 AI 的自然語言解析
- 不包含其他職責如統計、配置管理等

實現 LSP (里氏替換原則)：
- 完全實現 IParser 介面契約
- 可與其他解析器實現互換使用

實現 DIP (依賴倒置原則)：
- 依賴 IAIModelService 抽象介面
- 不直接依賴具體的 AI 服務實現
"""

import json
from typing import Any

import structlog

from ..interfaces.parsing_interfaces import IParser
from ..models.query_models import ParsedQuery, QueryType

logger = structlog.get_logger()


class AIEnhancedParser(IParser):
    """
    AI 增強的自然語言解析器

    職責：
    - 使用 AI 模型增強自然語言理解能力
    - 處理複雜和模糊的查詢語句
    - 提供結構化的 AI 解析結果

    設計原則：
    - SRP: 只負責 AI 增強解析，不處理統計、配置等
    - DIP: 依賴 IAIModelService 抽象介面
    - LSP: 完全實現 IParser 契約，可與其他解析器互換
    """

    def __init__(self, ai_model_service):
        """
        初始化 AI 增強解析器

        Args:
            ai_model_service: AI 模型服務介面（暫時使用 Any，待 ADR-005 統一後改為抽象介面）
        """
        self._ai_service = ai_model_service

        # AI 解析系統提示
        self._system_prompt = self._build_system_prompt()

        # 查詢類型映射（用於 AI 結果解析）
        self._query_type_mapping = {
            "machine_status": QueryType.MACHINE_STATUS,
            "fault_analysis": QueryType.FAULT_ANALYSIS,
            "production_stats": QueryType.PRODUCTION_STATS,
            "all_machines": QueryType.ALL_MACHINES,
            "department_status": QueryType.DEPARTMENT_STATUS,
            "specific_machine": QueryType.SPECIFIC_MACHINE,
        }

        logger.info(
            "🤖 AI 增強解析器初始化完成",
            ai_service_available=self._ai_service is not None,
            supported_types=len(self._query_type_mapping),
        )

    async def parse(
        self, text: str, context: dict[str, Any] | None = None
    ) -> ParsedQuery:
        """
        使用 AI 增強解析自然語言文字

        Args:
            text: 使用者輸入的自然語言文字
            context: 可選的解析上下文（包含資料庫結構等）

        Returns:
            ParsedQuery: AI 解析結果
        """
        if not text or not text.strip():
            return self._create_unknown_query("空輸入")

        if not self._ai_service:
            logger.warning("⚠️ AI 服務不可用")
            return self._create_unknown_query("AI 服務不可用")

        logger.debug("🤖 開始 AI 增強解析", text=text)

        try:
            # 準備 AI 查詢上下文
            ai_context = self._prepare_ai_context(text, context)

            # 調用 AI 服務進行增強解析
            # 🔥 修復：將 ai_context 轉換為 database_schema 格式
            database_schema = ai_context.get("database_schema", {})
            enhanced_result, confidence = (
                await self._ai_service.enhance_natural_language_query(
                    text, database_schema
                )
            )

            # 解析 AI 返回的結果
            logger.debug(
                "🔍 AI 返回結果", ai_result=enhanced_result[:200], confidence=confidence
            )
            parsed_query = self._parse_ai_result(enhanced_result, text, confidence)

            logger.debug(
                "✅ AI 解析完成",
                query_type=parsed_query.query_type.value,
                confidence=parsed_query.confidence,
            )

            return parsed_query

        except Exception as e:
            logger.error("❌ AI模型調用失敗", error=str(e), text=text)
            return self._create_error_query(text, str(e))

    def can_handle(self, text: str) -> float:
        """
        評估 AI 解析器的處理能力

        Args:
            text: 要評估的文字

        Returns:
            float: 處理能力信心度 (0-1)
        """
        if not text or not text.strip():
            return 0.0

        if not self._ai_service:
            return 0.0

        # AI 解析器對複雜查詢有較好的處理能力
        complexity_score = self._assess_query_complexity(text)

        # 基礎信心度 + 複雜度加成
        base_confidence = 0.6
        complexity_bonus = min(0.3, complexity_score * 0.3)

        return base_confidence + complexity_bonus

    def get_parser_info(self) -> dict[str, Any]:
        """
        獲取 AI 解析器資訊

        Returns:
            Dict[str, Any]: 解析器資訊
        """
        return {
            "name": "AIEnhancedParser",
            "version": "1.0.0",
            "type": "ai_enhanced",
            "capabilities": [
                "complex_query_understanding",
                "contextual_interpretation",
                "multilingual_support",
                "intent_recognition",
            ],
            "supported_query_types": list(self._query_type_mapping.keys()),
            "ai_service_available": self._ai_service is not None,
            "requires_context": True,
            "min_confidence_threshold": 0.6,
        }

    def _build_system_prompt(self) -> str:
        """
        建構 AI 系統提示

        Returns:
            str: 系統提示字串
        """
        return """你是一個專業的工業製造查詢分析助手。你的任務是將自然語言查詢轉換為結構化的查詢意圖。

支援的查詢類型：
1. machine_status - 機台狀態查詢
2. fault_analysis - 故障分析查詢
3. production_stats - 生產統計查詢
4. all_machines - 所有機台概覽
5. department_status - 部門狀態查詢
6. specific_machine - 特定機台查詢

請分析用戶的自然語言輸入，返回 JSON 格式：
{
  "query_type": "查詢類型",
  "confidence": 0.8,
  "target_entities": ["識別的實體"],
  "parameters": {"提取的參數"},
  "explanation": "查詢意圖說明"
}

注意：
- confidence 值在 0-1 之間
- target_entities 包含機台 ID、部門名稱等
- parameters 包含時間範圍、篩選條件等
- 如果無法識別，返回 query_type: "unknown"
"""

    def _prepare_ai_context(
        self, text: str, context: dict[str, Any] | None
    ) -> dict[str, Any]:
        """
        準備 AI 查詢上下文

        Args:
            text: 查詢文字
            context: 原始上下文

        Returns:
            Dict[str, Any]: AI 查詢上下文
        """
        ai_context = {
            "query_text": text,
            "language": "zh-TW",
            "domain": "manufacturing",
            "supported_entities": [
                "machine_id",
                "department",
                "time_range",
                "fault_type",
                "production_metric",
            ],
        }

        # 添加資料庫結構資訊（如果有）
        if context and "schema" in context:
            ai_context["database_schema"] = context["schema"]

        # 添加常見實體範例
        ai_context["entity_examples"] = {
            "machine_id": ["M001", "M002", "M100"],
            "department": ["加工部", "組裝部", "品管部", "維修部"],
            "time_range": ["7天", "一個月", "近期", "最近"],
        }

        return ai_context

    def _parse_ai_result(
        self, ai_result: str, original_text: str, ai_confidence: float
    ) -> ParsedQuery:
        """
        解析 AI 返回的結果

        Args:
            ai_result: AI 返回的結果字串
            original_text: 原始查詢文字
            ai_confidence: AI 服務返回的信心度

        Returns:
            ParsedQuery: 解析結果
        """
        try:
            # 🔥 安全檢查：確保 ai_result 是字符串
            if not isinstance(ai_result, str):
                logger.error("❌ AI 結果不是字符串類型", result_type=type(ai_result))
                return self._create_error_query(
                    original_text, f"AI 結果類型錯誤: {type(ai_result)}"
                )

            ai_result = ai_result.strip()
            if not ai_result:
                logger.warning("⚠️ AI 返回空結果")
                return self._parse_text_ai_result(
                    original_text, original_text, ai_confidence
                )

            # 嘗試解析 JSON 格式的 AI 結果
            if ai_result.startswith("{") and ai_result.endswith("}"):
                try:
                    result_data = json.loads(ai_result)
                    if isinstance(result_data, dict):
                        return self._create_query_from_ai_data(
                            result_data, original_text, ai_confidence
                        )
                    else:
                        logger.warning(
                            "⚠️ AI JSON 結果不是字典格式", result_type=type(result_data)
                        )
                        return self._parse_text_ai_result(
                            ai_result, original_text, ai_confidence
                        )
                except json.JSONDecodeError as e:
                    logger.warning(
                        "⚠️ AI 結果 JSON 解析失敗",
                        error=str(e),
                        ai_result=ai_result[:100],
                    )
                    return self._parse_text_ai_result(
                        ai_result, original_text, ai_confidence
                    )
            else:
                # 處理非 JSON 格式的 AI 回應
                return self._parse_text_ai_result(
                    ai_result, original_text, ai_confidence
                )

        except Exception as e:
            logger.error(
                "❌ AI 結果解析異常",
                error=str(e),
                ai_result_preview=str(ai_result)[:100] if ai_result else "None",
            )
            return self._create_error_query(original_text, f"AI 結果解析失敗: {str(e)}")

    def _create_query_from_ai_data(
        self, ai_data: dict[str, Any], original_text: str, ai_confidence: float
    ) -> ParsedQuery:
        """
        從 AI JSON 數據創建查詢

        Args:
            ai_data: AI 返回的結構化數據
            original_text: 原始查詢文字
            ai_confidence: AI 信心度

        Returns:
            ParsedQuery: 結構化查詢
        """
        # 解析查詢類型
        query_type_str = ai_data.get("query_type", "unknown")
        query_type = self._query_type_mapping.get(query_type_str, QueryType.UNKNOWN)

        # 解析信心度（使用 AI 數據中的信心度，如果有的話）
        confidence = float(ai_data.get("confidence", ai_confidence))
        confidence = max(0.0, min(1.0, confidence))  # 確保在 0-1 範圍內

        # 解析參數
        parameters = ai_data.get("parameters", {})
        target_entities = ai_data.get("target_entities", [])

        # 🔥 關鍵修復：智能查詢類型推斷
        if query_type == QueryType.UNKNOWN:
            query_type = self._infer_query_type_from_content(
                original_text, target_entities, parameters
            )

        # 處理特定機台查詢
        if query_type == QueryType.UNKNOWN and target_entities:
            machine_entities = [e for e in target_entities if e.upper().startswith("M")]
            if machine_entities:
                query_type = QueryType.SPECIFIC_MACHINE
                parameters["machine_id"] = machine_entities[0].upper()

        # 生成說明
        explanation = ai_data.get("explanation", f"AI 解析: {query_type.value}")

        # 🔥 重要：確保有效查詢類型才返回結果
        if query_type == QueryType.UNKNOWN:
            logger.warning(
                "⚠️ AI 無法確定查詢類型，使用文字解析", original_text=original_text
            )
            return self._parse_text_ai_result(original_text, original_text, confidence)

        return ParsedQuery(
            query_type=query_type,
            sql_query="",  # SQL 將由 QueryBuilder 建構
            parameters=parameters,
            confidence=confidence,
            explanation=explanation,
        )

    def _parse_text_ai_result(
        self, ai_result: str, original_text: str, ai_confidence: float
    ) -> ParsedQuery:
        """
        解析文字格式的 AI 結果

        Args:
            ai_result: AI 文字結果
            original_text: 原始查詢文字
            ai_confidence: AI 信心度

        Returns:
            ParsedQuery: 解析結果
        """
        # 🔥 修復：智能查詢類型推斷
        query_type = self._infer_query_type_from_content(original_text, [], {})

        # 如果仍無法推斷，嘗試從 AI 結果推斷
        if query_type == QueryType.UNKNOWN:
            query_type = self._infer_query_type_from_sql(ai_result)

        # 如果仍然無法確定，使用內容關鍵詞檢查
        if query_type == QueryType.UNKNOWN:
            lower_result = ai_result.lower()

            # 檢查是否包含查詢類型關鍵詞
            for type_key, mapped_type in self._query_type_mapping.items():
                if type_key in lower_result:
                    query_type = mapped_type
                    break

        # 如果還是無法確定，至少根據原始文字做基本推斷
        if query_type == QueryType.UNKNOWN:
            logger.warning(
                "⚠️ 無法從 AI 結果推斷查詢類型，使用預設",
                ai_result=ai_result[:100],
                original_text=original_text,
            )
            query_type = QueryType.MACHINE_STATUS  # 預設查詢類型

        # 提取參數
        parameters = self._extract_parameters_from_text(original_text, ai_result)

        return ParsedQuery(
            query_type=query_type,
            sql_query="",  # SQL 將由 QueryBuilder 建構
            parameters=parameters,
            confidence=ai_confidence * 0.8,  # 稍微降低信心度
            explanation=f"AI 文字解析: {ai_result[:100]}...",
        )

    def _infer_query_type_from_content(
        self, text: str, target_entities: list, parameters: dict
    ) -> QueryType:
        """
        從內容推斷查詢類型

        Args:
            text: 原始查詢文字
            target_entities: 目標實體
            parameters: 解析參數

        Returns:
            QueryType: 推斷的查詢類型
        """
        text_lower = text.lower()
        import re

        # 🔥 首先檢查部門查詢模式（最高優先級，避免被其他關鍵詞覆蓋）
        department_patterns = [
            r".*部.*機台.*",
            r".*部.*狀況.*", 
            r".*部.*狀態.*",
            r".*部.*概覽.*",
            r".*部.*設備.*"
        ]
        
        if any(re.search(pattern, text_lower) for pattern in department_patterns):
            return QueryType.DEPARTMENT_STATUS
            
        # 部門查詢關鍵詞檢查
        if any(
            keyword in text_lower
            for keyword in ["部門", "加工部", "組裝部", "品管部", "維修部", "生產部"]
        ):
            return QueryType.DEPARTMENT_STATUS

        # 檢查是否有機台ID（高優先級，具體查詢）
        machine_pattern = re.compile(r"[Mm]\d{2,4}")
        if machine_pattern.search(text) or any(
            "M" in entity.upper() for entity in target_entities
        ):
            return QueryType.SPECIFIC_MACHINE

        # 故障相關關鍵詞（但排除已確認的部門查詢）
        fault_keywords = ["故障", "問題", "錯誤", "異常", "近期"]
        if any(keyword in text_lower for keyword in fault_keywords):
            return QueryType.FAULT_ANALYSIS
        
        # 維修關鍵詞單獨檢查（避免與維修部混淆）
        if "維修" in text_lower and "維修部" not in text_lower:
            return QueryType.FAULT_ANALYSIS

        # 生產統計關鍵詞
        if any(
            keyword in text_lower
            for keyword in ["統計", "報告", "生產", "產量", "效率"]
        ):
            return QueryType.PRODUCTION_STATS

        # 所有機台關鍵詞
        if any(
            keyword in text_lower
            for keyword in ["所有機台", "全部機台", "整體", "概覽"]
        ):
            return QueryType.ALL_MACHINES

        # 機台狀態關鍵詞（最後檢查，較通用）
        if any(keyword in text_lower for keyword in ["狀態", "狀況", "運行", "機台"]):
            return QueryType.MACHINE_STATUS

        # 預設返回機台狀態查詢
        return QueryType.MACHINE_STATUS

    def _infer_query_type_from_sql(self, sql: str) -> QueryType:
        """
        從 SQL 查詢推斷查詢類型

        Args:
            sql: SQL 查詢字符串

        Returns:
            QueryType: 推斷的查詢類型
        """
        sql_lower = sql.lower()

        # 故障記錄相關表
        if any(table in sql_lower for table in ["fault", "error", "failure"]):
            return QueryType.FAULT_ANALYSIS

        # 生產統計相關表
        if any(table in sql_lower for table in ["production", "statistics", "stats"]):
            return QueryType.PRODUCTION_STATS

        # 特定機台查詢（有機台 ID 條件，優先檢查）
        if "machine_id" in sql_lower and (
            "where" in sql_lower or "machine_id =" in sql_lower
        ):
            return QueryType.SPECIFIC_MACHINE

        # 機台狀態相關表（優先檢查具體表名）
        if any(table in sql_lower for table in ["machine_status", "status"]):
            return QueryType.MACHINE_STATUS

        # 所有機台查詢（沒有 WHERE 條件的機台查詢，且不是狀態表）
        if "machine" in sql_lower and "where" not in sql_lower and "status" not in sql_lower:
            return QueryType.ALL_MACHINES

        # 預設返回機台狀態
        return QueryType.MACHINE_STATUS

    def _extract_parameters_from_text(self, original_text: str, ai_result: str) -> dict:
        """
        從文字中提取參數

        Args:
            original_text: 原始查詢文字
            ai_result: AI 結果

        Returns:
            dict: 提取的參數
        """
        parameters = {}

        # 提取機台 ID
        import re

        machine_pattern = re.compile(r"[Mm](\d{3,4})")
        machine_match = machine_pattern.search(original_text)
        if machine_match:
            parameters["machine_id"] = f"M{machine_match.group(1).zfill(3)}"

        # 從 AI SQL 結果中提取機台 ID
        sql_machine_pattern = re.compile(
            r"machine_id\s*=\s*['\"]([^'\"]+)['\"]", re.IGNORECASE
        )
        sql_machine_match = sql_machine_pattern.search(ai_result)
        if sql_machine_match:
            parameters["machine_id"] = sql_machine_match.group(1)

        # 提取時間範圍
        text_lower = original_text.lower()
        if any(keyword in text_lower for keyword in ["近期", "最近", "7天"]):
            parameters["days"] = 7
        elif any(keyword in text_lower for keyword in ["一個月", "30天"]):
            parameters["days"] = 30

        # 提取部門
        department_mapping = {
            "加工": "加工部",
            "組裝": "組裝部",
            "品管": "品管部",
            "維修": "維修部",
        }

        for keyword, department in department_mapping.items():
            if keyword in text_lower:
                parameters["department"] = department
                break

        return parameters

    def _assess_query_complexity(self, text: str) -> float:
        """
        評估查詢複雜度

        Args:
            text: 查詢文字

        Returns:
            float: 複雜度評分 (0-1)
        """
        complexity_factors = [
            len(text) > 50,  # 長度較長
            "和" in text or "或" in text or "但是" in text,  # 包含邏輯連詞
            "比較" in text or "對比" in text,  # 比較查詢
            "什麼時候" in text or "為什麼" in text or "怎麼" in text,  # 複雜疑問詞
            text.count("，") > 1 or text.count("。") > 0,  # 多個句子
        ]

        return sum(complexity_factors) / len(complexity_factors)

    def _create_unknown_query(self, original_text: str) -> ParsedQuery:
        """
        創建未知查詢結果

        Args:
            original_text: 原始輸入文字

        Returns:
            ParsedQuery: 未知查詢結果
        """
        return ParsedQuery(
            query_type=QueryType.UNKNOWN,
            sql_query="",
            parameters={},
            confidence=0.0,
            explanation=f"AI 解析器無法識別的查詢：{original_text}",
        )

    def _create_error_query(
        self, original_text: str, error_message: str
    ) -> ParsedQuery:
        """
        創建錯誤查詢結果

        Args:
            original_text: 原始輸入文字
            error_message: 錯誤訊息

        Returns:
            ParsedQuery: 錯誤查詢結果
        """
        return ParsedQuery(
            query_type=QueryType.UNKNOWN,
            sql_query="",
            parameters={"error": error_message},
            confidence=0.0,
            explanation=f"AI 解析錯誤 ({error_message}): {original_text}",
        )

    def get_ai_service_status(self) -> dict[str, Any]:
        """
        獲取 AI 服務狀態

        Returns:
            Dict[str, Any]: AI 服務狀態資訊
        """
        if not self._ai_service:
            return {
                "available": False,
                "status": "not_configured",
                "message": "AI 服務未配置",
            }

        try:
            # 這裡可以添加 AI 服務健康檢查
            # 暫時返回簡單狀態
            return {
                "available": True,
                "status": "ready",
                "message": "AI 服務可用",
                "service_type": type(self._ai_service).__name__,
            }
        except Exception as e:
            return {
                "available": False,
                "status": "error",
                "message": f"AI 服務錯誤: {str(e)}",
            }

    def update_system_prompt(self, new_prompt: str) -> None:
        """
        更新系統提示

        Args:
            new_prompt: 新的系統提示
        """
        self._system_prompt = new_prompt
        logger.info("🔄 AI 系統提示已更新", prompt_length=len(new_prompt))

    def get_supported_query_types(self) -> list[QueryType]:
        """
        獲取支援的查詢類型

        Returns:
            List[QueryType]: 支援的查詢類型列表
        """
        return list(self._query_type_mapping.values())
