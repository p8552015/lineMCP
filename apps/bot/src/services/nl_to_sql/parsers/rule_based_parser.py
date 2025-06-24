"""
基於規則的自然語言解析器

實現 SRP (單一職責原則)：
- 專門負責基於規則的自然語言解析
- 不包含其他職責如統計、建構 SQL 等

實現 LSP (里氏替換原則)：
- 完全實現 IParser 介面契約
- 可與其他解析器實現互換使用

實現 DIP (依賴倒置原則)：
- 依賴 IConfiguration 抽象介面
- 不直接依賴具體的配置實現
"""

import re
from typing import Any

import structlog

from ..interfaces.parsing_interfaces import IParser
from ..interfaces.statistics_interfaces import IConfiguration
from ..models.query_models import ParsedQuery, QueryType

logger = structlog.get_logger()


class RuleBasedParser(IParser):
    """
    基於規則的自然語言解析器

    職責：
    - 使用預定義規則和正規表達式解析自然語言
    - 識別機台 ID 和查詢模式
    - 返回結構化的解析結果

    設計原則：
    - SRP: 只負責規則解析，不處理統計、建構等
    - DIP: 依賴 IConfiguration 抽象介面
    - OCP: 透過配置擴展規則，無需修改代碼
    """

    def __init__(self, configuration: IConfiguration):
        """
        初始化規則解析器

        Args:
            configuration: 配置管理介面
        """
        self._config = configuration
        self._machine_id_pattern = re.compile(r"[Mm](\d{2,4})", re.IGNORECASE)

        # 從配置載入查詢模式
        self._query_patterns = self._config.get_query_patterns()

        # 部門名稱映射
        self._department_mapping = {
            "加工": "加工部",
            "組裝": "組裝部",
            "品管": "品管部",
            "維修": "維修部",
            "生產": "生產部",
        }

        logger.info(
            "🔧 規則解析器初始化完成",
            patterns_count=len(self._query_patterns),
            departments_count=len(self._department_mapping),
        )

    async def parse(
        self, text: str, context: dict[str, Any] | None = None
    ) -> ParsedQuery:
        """
        解析自然語言文字

        Args:
            text: 使用者輸入的自然語言文字
            context: 可選的解析上下文

        Returns:
            ParsedQuery: 解析結果
        """
        if not text or not text.strip():
            return self._create_unknown_query("空輸入")

        # 標準化輸入文字
        normalized_text = text.strip().lower()

        logger.debug("🔍 開始規則解析", text=text, normalized=normalized_text)

        # 1. 檢查特定機台 ID
        machine_match = self._machine_id_pattern.search(normalized_text)
        if machine_match:
            # 2-3位數補零到3位，4位數保持原樣
            digits = machine_match.group(1)
            machine_id = f"M{digits.zfill(3)}" if len(digits) <= 3 else f"M{digits}"
            return self._create_machine_query(machine_id, text)

        # 2. 按優先級檢查查詢模式（按信心度排序，高信心度優先）
        sorted_patterns = sorted(
            self._query_patterns.items(),
            key=lambda x: x[1].get("confidence", 0.7),
            reverse=True,
        )

        for query_type_name, pattern_config in sorted_patterns:
            try:
                query_type = QueryType(query_type_name)
                patterns = pattern_config.get("patterns", [])
                confidence = pattern_config.get("confidence", 0.7)

                for pattern in patterns:
                    if re.search(pattern, normalized_text, re.IGNORECASE):
                        logger.debug(
                            "✅ 模式匹配成功",
                            query_type=query_type.value,
                            pattern=pattern,
                            confidence=confidence,
                        )
                        return self._create_typed_query(query_type, text, confidence)

            except ValueError as e:
                logger.warning(
                    "⚠️ 無效的查詢類型", query_type=query_type_name, error=str(e)
                )
                continue

        # 3. 未識別的查詢
        logger.debug("❓ 規則解析無法識別", text=text)
        return self._create_unknown_query(text)

    def can_handle(self, text: str) -> float:
        """
        評估處理能力

        Args:
            text: 要評估的文字

        Returns:
            float: 處理能力信心度 (0-1)
        """
        if not text or not text.strip():
            return 0.0

        normalized_text = text.strip().lower()

        # 檢查機台 ID 模式
        if self._machine_id_pattern.search(normalized_text):
            return 0.95  # 機台 ID 模式信心度很高

        # 檢查查詢模式匹配
        max_confidence = 0.0
        for _query_type_name, pattern_config in self._query_patterns.items():
            patterns = pattern_config.get("patterns", [])
            confidence = pattern_config.get("confidence", 0.7)

            for pattern in patterns:
                if re.search(pattern, normalized_text, re.IGNORECASE):
                    max_confidence = max(max_confidence, confidence)

        return max_confidence

    def get_parser_info(self) -> dict[str, Any]:
        """
        獲取解析器資訊

        Returns:
            Dict[str, Any]: 解析器資訊
        """
        return {
            "name": "RuleBasedParser",
            "version": "1.0.0",
            "type": "rule_based",
            "capabilities": [
                "machine_id_detection",
                "pattern_matching",
                "chinese_language_support",
            ],
            "supported_query_types": list(self._query_patterns.keys()),
            "pattern_count": len(self._query_patterns),
            "department_mapping_count": len(self._department_mapping),
            "machine_id_pattern": self._machine_id_pattern.pattern,
        }

    def _create_machine_query(self, machine_id: str, original_text: str) -> ParsedQuery:
        """
        創建特定機台查詢

        Args:
            machine_id: 機台 ID
            original_text: 原始輸入文字

        Returns:
            ParsedQuery: 機台查詢結果
        """
        return ParsedQuery(
            query_type=QueryType.SPECIFIC_MACHINE,
            sql_query="",  # SQL 將由 QueryBuilder 建構
            parameters={"machine_id": machine_id},
            confidence=0.9,
            explanation=f"查詢機台 {machine_id} 的詳細狀態",
        )

    def _create_typed_query(
        self, query_type: QueryType, original_text: str, confidence: float
    ) -> ParsedQuery:
        """
        創建類型化查詢

        Args:
            query_type: 查詢類型
            original_text: 原始輸入文字
            confidence: 信心度

        Returns:
            ParsedQuery: 類型化查詢結果
        """
        # 根據查詢類型提取特定參數
        parameters = self._extract_type_specific_parameters(query_type, original_text)
        explanation = self._generate_explanation(query_type, parameters)

        return ParsedQuery(
            query_type=query_type,
            sql_query="",  # SQL 將由 QueryBuilder 建構
            parameters=parameters,
            confidence=confidence,
            explanation=explanation,
        )

    def _extract_type_specific_parameters(
        self, query_type: QueryType, text: str
    ) -> dict[str, Any]:
        """
        提取查詢類型特定的參數

        Args:
            query_type: 查詢類型
            text: 輸入文字

        Returns:
            Dict[str, Any]: 提取的參數
        """
        parameters = {}
        normalized_text = text.lower()

        if query_type == QueryType.FAULT_ANALYSIS:
            # 提取時間範圍參數
            days = 30  # 預設 30 天
            if re.search(r"7天|一週|一个星期", normalized_text, re.IGNORECASE):
                days = 7
            elif re.search(r"一個月|30天", normalized_text, re.IGNORECASE):
                days = 30
            elif re.search(r"三個月|90天", normalized_text, re.IGNORECASE):
                days = 90

            parameters["days"] = days

        elif query_type == QueryType.DEPARTMENT_STATUS:
            # 提取部門參數
            for key, value in self._department_mapping.items():
                if key in normalized_text:
                    parameters["department"] = value
                    break

        return parameters

    def _generate_explanation(
        self, query_type: QueryType, parameters: dict[str, Any]
    ) -> str:
        """
        生成查詢說明

        Args:
            query_type: 查詢類型
            parameters: 查詢參數

        Returns:
            str: 查詢說明
        """
        explanations = {
            QueryType.ALL_MACHINES: "查詢所有機台的狀態概覽",
            QueryType.FAULT_ANALYSIS: f"分析近 {parameters.get('days', 30)} 天的故障記錄",
            QueryType.PRODUCTION_STATS: "生產統計報告（按部門）",
            QueryType.MACHINE_STATUS: "查詢機台運行狀態",
        }

        if query_type == QueryType.DEPARTMENT_STATUS:
            department = parameters.get("department", "未指定部門")
            return f"查詢 {department} 的機台狀態"

        return explanations.get(query_type, f"執行 {query_type.value} 查詢")

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
            explanation=f"規則解析器無法識別的查詢：{original_text}",
        )

    def reload_patterns(self) -> None:
        """
        重新載入查詢模式

        用於支援配置熱更新
        """
        try:
            self._config.reload_config()
            self._query_patterns = self._config.get_query_patterns()
            logger.info(
                "🔄 查詢模式重新載入完成", patterns_count=len(self._query_patterns)
            )
        except Exception as e:
            logger.error("❌ 查詢模式重新載入失敗", error=str(e))
            raise

    def get_supported_query_types(self) -> list[QueryType]:
        """
        獲取支援的查詢類型

        Returns:
            List[QueryType]: 支援的查詢類型列表
        """
        supported_types = []
        for query_type_name in self._query_patterns:
            try:
                query_type = QueryType(query_type_name)
                supported_types.append(query_type)
            except ValueError:
                continue

        # 添加機台查詢類型（總是支援）
        if QueryType.SPECIFIC_MACHINE not in supported_types:
            supported_types.append(QueryType.SPECIFIC_MACHINE)

        return supported_types

    def validate_pattern_config(self) -> dict[str, Any]:
        """
        驗證模式配置的有效性

        Returns:
            Dict[str, Any]: 驗證結果
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "pattern_stats": {},
        }

        for query_type_name, pattern_config in self._query_patterns.items():
            # 檢查查詢類型是否有效
            try:
                QueryType(query_type_name)
            except ValueError:
                validation_result["errors"].append(f"無效的查詢類型: {query_type_name}")
                validation_result["is_valid"] = False
                continue

            # 檢查模式配置結構
            if not isinstance(pattern_config, dict):
                validation_result["errors"].append(
                    f"查詢類型 {query_type_name} 的配置格式錯誤"
                )
                validation_result["is_valid"] = False
                continue

            patterns = pattern_config.get("patterns", [])
            if not patterns:
                validation_result["warnings"].append(
                    f"查詢類型 {query_type_name} 沒有定義模式"
                )

            # 驗證正規表達式
            invalid_patterns = []
            for pattern in patterns:
                try:
                    re.compile(pattern, re.IGNORECASE)
                except re.error:
                    invalid_patterns.append(pattern)

            if invalid_patterns:
                validation_result["errors"].append(
                    f"查詢類型 {query_type_name} 包含無效的正規表達式: {invalid_patterns}"
                )
                validation_result["is_valid"] = False

            # 記錄統計
            validation_result["pattern_stats"][query_type_name] = {
                "pattern_count": len(patterns),
                "confidence": pattern_config.get("confidence", 0.7),
                "has_invalid_patterns": bool(invalid_patterns),
            }

        return validation_result
