"""
SQL 查詢建構器

實現 SRP (單一職責原則)：
- 專門負責 SQL 查詢的建構和參數化
- 不包含解析、統計等其他職責

實現 DIP (依賴倒置原則)：
- 依賴 ITemplateManager 抽象介面
- 不直接依賴具體的模板管理實現

實現 LSP (里氏替換原則)：
- 完全實現 IQueryBuilder 介面契約
- 可與其他建構器實現互換使用
"""

import html
import re
from typing import Any

import structlog

from ..interfaces.query_builder_interfaces import IQueryBuilder, ITemplateManager
from ..models.query_models import QueryType

logger = structlog.get_logger()


class SQLQueryBuilder(IQueryBuilder):
    """
    SQL 查詢建構器

    職責：
    - 根據查詢類型和參數建構 SQL 查詢
    - 確保 SQL 參數安全和正確轉義
    - 驗證查詢參數的有效性

    設計原則：
    - SRP: 只負責 SQL 建構，不處理解析、統計等
    - DIP: 依賴 ITemplateManager 抽象介面
    - LSP: 完全實現 IQueryBuilder 契約
    """

    def __init__(self, template_manager: ITemplateManager):
        """
        初始化 SQL 查詢建構器

        Args:
            template_manager: 模板管理器介面
        """
        self._template_manager = template_manager

        # 參數驗證規則
        self._parameter_validators = self._build_parameter_validators()

        # 查詢複雜度估算規則
        self._complexity_patterns = self._build_complexity_patterns()

        logger.info(
            "🔨 SQL 查詢建構器初始化完成",
            supported_types=len(self.get_supported_query_types()),
        )

    def build_query(self, query_type: QueryType, parameters: dict[str, Any]) -> str:
        """
        建構 SQL 查詢語句

        Args:
            query_type: 查詢類型枚舉
            parameters: 查詢參數字典

        Returns:
            str: 完整的 SQL 查詢語句

        Raises:
            InvalidQueryTypeError: 不支援的查詢類型
            InvalidParametersError: 參數驗證失敗
            QueryBuildError: 查詢建構失敗
        """
        # 驗證查詢類型（修復：使用值比較而非物件比較）
        supported_types = self.get_supported_query_types()
        if not any(query_type.value == qt.value for qt in supported_types):
            supported_values = [qt.value for qt in supported_types]
            raise ValueError(
                f"不支援的查詢類型: {query_type.value}，支援的類型: {supported_values}"
            )

        # 驗證參數
        if not self.validate_parameters(query_type, parameters):
            missing_params = set(self.get_required_parameters(query_type)) - set(
                parameters.keys()
            )
            raise ValueError(f"缺少必要參數: {missing_params}")

        logger.debug(
            "🔨 開始建構 SQL 查詢", query_type=query_type.value, parameters=parameters
        )

        try:
            # 獲取模板
            template = self._template_manager.get_template(query_type)

            # 🔥 關鍵修復：驗證模板不為空
            if not template or not template.strip():
                raise ValueError(f"查詢類型 {query_type.value} 的模板為空")

            # 準備安全參數
            safe_parameters = self._prepare_safe_parameters(parameters)

            # 建構查詢
            sql_query = self._build_query_from_template(template, safe_parameters)

            # 🔥 關鍵修復：驗證建構的查詢不為空
            if not sql_query or not sql_query.strip():
                raise ValueError(f"查詢類型 {query_type.value} 建構的 SQL 為空")

            # 後處理和優化
            optimized_query = self._optimize_query(sql_query)

            # 🔥 關鍵修復：最終驗證優化後的查詢不為空
            if not optimized_query or not optimized_query.strip():
                raise ValueError(f"查詢類型 {query_type.value} 優化後的 SQL 為空")

            logger.debug(
                "✅ SQL 查詢建構完成",
                query_type=query_type.value,
                query_length=len(optimized_query),
                has_parameters=bool(safe_parameters),
                query_preview=optimized_query[:100],
            )

            return optimized_query

        except Exception as e:
            logger.error(
                "❌ SQL 查詢建構失敗",
                query_type=query_type.value,
                parameters=parameters,
                error=str(e),
            )
            raise RuntimeError(f"SQL 查詢建構失敗: {str(e)}") from e

    def validate_parameters(
        self, query_type: QueryType, parameters: dict[str, Any]
    ) -> bool:
        """
        驗證查詢參數的有效性

        Args:
            query_type: 查詢類型
            parameters: 要驗證的參數

        Returns:
            bool: 參數是否有效
        """
        try:
            # 檢查必要參數
            required_params = self.get_required_parameters(query_type)
            for param in required_params:
                if param not in parameters:
                    logger.warning(
                        "⚠️ 缺少必要參數", param=param, query_type=query_type.value
                    )
                    return False

            # 使用參數驗證器檢查
            validator = self._parameter_validators.get(query_type)
            if validator:
                return bool(validator(parameters))

            # 預設驗證（參數存在即可）
            return True

        except Exception as e:
            logger.error("❌ 參數驗證異常", error=str(e))
            return False

    def get_required_parameters(self, query_type: QueryType) -> list[str]:
        """
        獲取指定查詢類型所需的參數列表

        Args:
            query_type: 查詢類型

        Returns:
            list[str]: 必要參數名稱列表
        """
        parameter_requirements: dict[QueryType, list[str]] = {
            QueryType.SPECIFIC_MACHINE: ["machine_id"],
            QueryType.DEPARTMENT_STATUS: ["department"],
            QueryType.FAULT_ANALYSIS: [],  # days 參數是可選的
            QueryType.ALL_MACHINES: [],
            QueryType.PRODUCTION_STATS: [],
            QueryType.MACHINE_STATUS: [],
        }

        # 明確返回類型以避免 MyPy 錯誤
        if query_type in parameter_requirements:
            return parameter_requirements[query_type]
        else:
            return []

    def get_supported_query_types(self) -> list[QueryType]:
        """
        獲取支援的查詢類型列表

        Returns:
            list[QueryType]: 支援的查詢類型
        """
        return [
            QueryType.SPECIFIC_MACHINE,
            QueryType.ALL_MACHINES,
            QueryType.FAULT_ANALYSIS,
            QueryType.PRODUCTION_STATS,
            QueryType.DEPARTMENT_STATUS,
            QueryType.MACHINE_STATUS,
        ]

    def get_query_metadata(self, query_type: QueryType) -> dict[str, Any]:
        """
        獲取查詢類型的元數據資訊

        Args:
            query_type: 查詢類型

        Returns:
            dict[str, Any]: 查詢元數據
        """
        metadata = {
            QueryType.SPECIFIC_MACHINE: {
                "description": "查詢特定機台的詳細狀態和效能資料",
                "estimated_complexity": "medium",
                "performance_hint": "使用機台 ID 索引，查詢速度較快",
                "typical_response_time": "50-100ms",
                "data_freshness": "即時",
            },
            QueryType.ALL_MACHINES: {
                "description": "獲取所有機台的狀態概覽",
                "estimated_complexity": "high",
                "performance_hint": "查詢範圍較大，建議加上時間限制",
                "typical_response_time": "200-500ms",
                "data_freshness": "近 7 天",
            },
            QueryType.FAULT_ANALYSIS: {
                "description": "分析機台故障記錄和統計",
                "estimated_complexity": "medium",
                "performance_hint": "根據時間範圍過濾，預設 30 天",
                "typical_response_time": "100-300ms",
                "data_freshness": "歷史資料",
            },
            QueryType.PRODUCTION_STATS: {
                "description": "生產統計報告，按部門分組",
                "estimated_complexity": "high",
                "performance_hint": "涉及多表聯接和聚合計算",
                "typical_response_time": "300-800ms",
                "data_freshness": "近 7 天",
            },
            QueryType.DEPARTMENT_STATUS: {
                "description": "查詢特定部門的機台狀態",
                "estimated_complexity": "medium",
                "performance_hint": "使用部門索引，效能良好",
                "typical_response_time": "100-200ms",
                "data_freshness": "近 7 天",
            },
        }

        default_metadata = {
            "description": f"執行 {query_type.value} 查詢",
            "estimated_complexity": "unknown",
            "performance_hint": "無特定優化建議",
            "typical_response_time": "未知",
            "data_freshness": "未知",
        }

        return metadata.get(query_type, default_metadata)

    def _build_parameter_validators(self) -> dict[QueryType, Any]:
        """
        建構參數驗證器

        Returns:
            dict[QueryType, callable]: 驗證器字典
        """

        def validate_machine_id(params: dict[str, Any]) -> bool:
            machine_id = params.get("machine_id", "")
            return bool(re.match(r"^M\d{3,4}$", machine_id))

        def validate_department(params: dict[str, Any]) -> bool:
            department = params.get("department", "")
            valid_departments = ["加工部", "組裝部", "品管部", "維修部", "生產部"]
            return department in valid_departments

        def validate_time_range(params: dict[str, Any]) -> bool:
            days = params.get("days")
            if days is None:
                return True  # 可選參數
            return isinstance(days, int) and 1 <= days <= 365

        return {
            QueryType.SPECIFIC_MACHINE: validate_machine_id,
            QueryType.DEPARTMENT_STATUS: validate_department,
            QueryType.FAULT_ANALYSIS: validate_time_range,
        }

    def _build_complexity_patterns(self) -> dict[str, int]:
        """
        建構複雜度評估模式

        Returns:
            dict[str, int]: 複雜度模式字典
        """
        return {
            r"LEFT JOIN": 2,
            r"INNER JOIN": 1,
            r"GROUP BY": 2,
            r"ORDER BY": 1,
            r"HAVING": 3,
            r"UNION": 3,
            r"SUBQUERY": 4,
            r"AVG\(|SUM\(|COUNT\(|MAX\(|MIN\(": 1,
            r"CASE WHEN": 2,
            r"EXISTS": 3,
        }

    def _prepare_safe_parameters(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """
        準備安全的查詢參數

        Args:
            parameters: 原始參數

        Returns:
            dict[str, Any]: 安全參數
        """
        safe_params = {}

        for key, value in parameters.items():
            if isinstance(value, str):
                # 字串參數需要轉義
                safe_params[key] = self._escape_sql_parameter(value)
            elif isinstance(value, int | float):
                # 數值參數直接使用
                safe_params[key] = str(value)
            elif isinstance(value, bool):
                # 布林參數轉換為整數
                safe_params[key] = str(1 if value else 0)
            else:
                # 其他類型轉為字串並轉義
                safe_params[key] = self._escape_sql_parameter(str(value))

        return safe_params

    def _escape_sql_parameter(self, value: str) -> str:
        """
        轉義 SQL 參數以防止注入攻擊

        Args:
            value: 要轉義的字串值

        Returns:
            str: 轉義後的字串
        """
        if not isinstance(value, str):
            return str(value)

        # 基本的 SQL 注入防護
        # 移除或轉義危險字符
        value = value.replace("'", "''")  # SQL 字串轉義
        value = value.replace("--", "")  # 移除註釋符號
        value = value.replace(";", "")  # 移除語句分隔符
        value = html.escape(value)  # HTML 轉義作為額外保護

        # 檢查是否包含 SQL 關鍵字（簡化版）
        dangerous_keywords = [
            "DROP",
            "DELETE",
            "UPDATE",
            "INSERT",
            "ALTER",
            "CREATE",
            "TRUNCATE",
            "EXEC",
            "UNION",
            "SCRIPT",
        ]

        upper_value = value.upper()
        for keyword in dangerous_keywords:
            if keyword in upper_value:
                logger.warning("⚠️ 參數包含潛在危險關鍵字", keyword=keyword, value=value)
                # 可以選擇拒絕或進一步清理
                value = value.replace(keyword.lower(), "").replace(keyword.upper(), "")

        return value

    def _build_query_from_template(
        self, template: str, parameters: dict[str, Any]
    ) -> str:
        """
        從模板建構查詢

        Args:
            template: SQL 查詢模板
            parameters: 查詢參數

        Returns:
            str: 建構的 SQL 查詢
        """
        try:
            # 使用 Python 字串格式化建構查詢
            formatted_query = template.format(**parameters)

            # 清理多餘的空白和換行
            lines = formatted_query.split("\n")
            cleaned_lines = [line.strip() for line in lines if line.strip()]

            return " ".join(cleaned_lines)

        except KeyError as e:
            raise ValueError(f"模板中的參數 {e} 未提供") from e
        except Exception as e:
            raise RuntimeError(f"查詢建構失敗: {str(e)}") from e

    def _optimize_query(self, sql_query: str) -> str:
        """
        優化 SQL 查詢

        Args:
            sql_query: 原始 SQL 查詢

        Returns:
            str: 優化後的查詢
        """
        # 基本的查詢優化
        optimized = sql_query

        # 移除多餘的空格
        optimized = re.sub(r"\s+", " ", optimized)

        # 確保查詢以分號結尾（如果需要）
        optimized = optimized.strip()
        if not optimized.endswith(";") and not optimized.upper().startswith("SELECT"):
            pass  # 對於 SELECT 查詢通常不需要分號

        return optimized

    def estimate_query_cost(self, sql_query: str) -> dict[str, Any]:
        """
        估算查詢成本

        Args:
            sql_query: SQL 查詢語句

        Returns:
            dict[str, Any]: 成本估算結果
        """
        complexity_score = 0

        # 根據複雜度模式計算分數
        for pattern, score in self._complexity_patterns.items():
            matches = len(re.findall(pattern, sql_query, re.IGNORECASE))
            complexity_score += matches * score

        # 估算執行時間範圍
        if complexity_score <= 2:
            time_estimate = "fast (< 100ms)"
            risk_level = "low"
        elif complexity_score <= 5:
            time_estimate = "medium (100-500ms)"
            risk_level = "medium"
        else:
            time_estimate = "slow (> 500ms)"
            risk_level = "high"

        return {
            "complexity_score": complexity_score,
            "estimated_execution_time": time_estimate,
            "risk_level": risk_level,
            "optimization_suggestions": self._get_optimization_suggestions(
                sql_query, complexity_score
            ),
        }

    def _get_optimization_suggestions(
        self, sql_query: str, complexity_score: int
    ) -> list[str]:
        """
        獲取查詢優化建議

        Args:
            sql_query: SQL 查詢
            complexity_score: 複雜度分數

        Returns:
            list[str]: 優化建議列表
        """
        suggestions: list[Any] = []

        if complexity_score > 5:
            suggestions.append("考慮添加適當的索引")
            suggestions.append("檢查是否可以減少 JOIN 操作")

        if "SELECT *" in sql_query:
            suggestions.append("避免使用 SELECT *，明確指定需要的欄位")

        if re.search(r"WHERE.*LIKE.*%.*%", sql_query, re.IGNORECASE):
            suggestions.append("避免在 LIKE 語句開頭使用萬用字符")

        if not re.search(r"LIMIT|TOP", sql_query, re.IGNORECASE):
            suggestions.append("考慮添加 LIMIT 限制結果集大小")

        return suggestions

    def validate_query_security(self, sql_query: str) -> dict[str, Any]:
        """
        驗證查詢的安全性

        Args:
            sql_query: 要驗證的 SQL 查詢

        Returns:
            dict[str, Any]: 安全性檢查結果
        """
        security_issues: list[Any] = []
        risk_level = "low"

        # 檢查危險的 SQL 操作
        dangerous_patterns = [
            (r"DROP\s+TABLE", "包含 DROP TABLE 操作"),
            (r"DELETE\s+FROM", "包含 DELETE 操作"),
            (r"UPDATE\s+.*SET", "包含 UPDATE 操作"),
            (r"INSERT\s+INTO", "包含 INSERT 操作"),
            (r"ALTER\s+TABLE", "包含 ALTER TABLE 操作"),
            (r"EXEC\s*\(", "包含動態執行操作"),
            (r"--", "包含 SQL 註釋符號"),
            (r";.*SELECT", "包含多個 SQL 語句"),
        ]

        for pattern, message in dangerous_patterns:
            if re.search(pattern, sql_query, re.IGNORECASE):
                security_issues.append(message)
                risk_level = "high"

        # 檢查是否只包含 SELECT 操作
        if not sql_query.strip().upper().startswith("SELECT"):
            security_issues.append("查詢不是以 SELECT 開始")
            risk_level = "medium"

        return {
            "is_safe": len(security_issues) == 0,
            "security_issues": security_issues,
            "risk_level": risk_level,
            "query_type": (
                "read_only"
                if sql_query.strip().upper().startswith("SELECT")
                else "write_operation"
            ),
        }
