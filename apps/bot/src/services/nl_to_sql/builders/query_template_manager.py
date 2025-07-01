"""
查詢模板管理器

實現 SRP (單一職責原則)：
- 專門負責 SQL 模板的管理和載入
- 不包含查詢建構等其他職責

實現 DIP (依賴倒置原則)：
- 依賴 IConfiguration 抽象介面
- 支援不同的模板來源（檔案、資料庫等）

實現 OCP (開閉原則)：
- 支援動態載入和熱更新模板
- 可擴展支援新的模板格式
"""

import re
from typing import Any

import structlog

from ..interfaces.query_builder_interfaces import ITemplateManager
from ..interfaces.statistics_interfaces import IConfiguration
from ..models.query_models import QueryType

logger = structlog.get_logger()


class QueryTemplateManager(ITemplateManager):
    """
    查詢模板管理器

    職責：
    - 載入和管理 SQL 查詢模板
    - 支援模板驗證和參數提取
    - 提供模板熱更新功能

    設計原則：
    - SRP: 只負責模板管理，不處理查詢建構等
    - DIP: 依賴 IConfiguration 抽象介面
    - OCP: 支援多種模板來源和格式擴展
    """

    def __init__(self, configuration: IConfiguration):
        """
        初始化模板管理器

        Args:
            configuration: 配置管理介面
        """
        self._config = configuration
        self._templates: dict[QueryType, str] = {}
        self._template_metadata: dict[QueryType, dict[str, Any]] = {}

        # 載入模板
        self._load_templates()

        logger.info("📋 查詢模板管理器初始化完成", template_count=len(self._templates))

    def get_template(self, query_type: QueryType) -> str:
        """
        獲取指定查詢類型的 SQL 模板

        Args:
            query_type: 查詢類型

        Returns:
            str: SQL 模板字串，包含參數佔位符

        Raises:
            TemplateNotFoundError: 模板不存在
        """
        # 修復：使用值比較而非物件比較
        template_found = any(query_type.value == qt.value for qt in self._templates)
        if not template_found:
            logger.error(
                "❌ 模板不存在，嘗試載入預設模板",
                query_type=query_type.value,
                available_types=[qt.value for qt in self._templates],
            )

            # 🔥 關鍵修復：嘗試載入預設模板
            self._load_default_templates()

            # 再次檢查（修復：使用值比較）
            template_found_after_default = any(
                query_type.value == qt.value for qt in self._templates
            )
            if not template_found_after_default:
                raise KeyError(
                    f"查詢類型 {query_type.value} 的模板不存在，預設模板載入也失敗"
                )

        # 修復：根據值查找正確的模板
        template = None
        for qt, tmpl in self._templates.items():
            if query_type.value == qt.value:
                template = tmpl
                break

        if template is None:
            raise KeyError(f"無法找到查詢類型 {query_type.value} 的模板")

        # 🔥 關鍵修復：雙重檢查模板內容
        if not template or not template.strip():
            logger.error("❌ 發現空模板，嘗試重新載入", query_type=query_type.value)

            # 嘗試重新載入
            self._load_default_templates()
            # 修復：使用值比較重新查找模板
            template = ""
            for qt, tmpl in self._templates.items():
                if query_type.value == qt.value:
                    template = tmpl
                    break

            if not template or not template.strip():
                raise ValueError(f"查詢類型 {query_type.value} 的模板為空或無效")

        logger.debug(
            "📋 獲取模板", query_type=query_type.value, template_length=len(template)
        )

        return template

    def set_template(self, query_type: QueryType, template: str) -> None:
        """
        設置查詢類型的 SQL 模板

        Args:
            query_type: 查詢類型
            template: SQL 模板字串

        Raises:
            InvalidTemplateError: 模板格式不正確
        """
        if not self.validate_template(template):
            raise ValueError(f"模板格式不正確: {template[:100]}...")

        self._templates[query_type] = template
        self._update_template_metadata(query_type, template)

        logger.info(
            "📋 模板已設置", query_type=query_type.value, template_length=len(template)
        )

    def validate_template(self, template: str) -> bool:
        """
        驗證 SQL 模板的有效性

        Args:
            template: 要驗證的模板

        Returns:
            bool: 模板是否有效
        """
        if not template or not template.strip():
            return False

        # 基本的 SQL 模板驗證
        template_upper = template.upper().strip()

        # 檢查是否包含基本的 SQL 結構
        if not template_upper.startswith("SELECT"):
            logger.warning("⚠️ 模板不是以 SELECT 開始", template=template[:50])
            return False

        # 檢查是否包含 FROM 子句
        if "FROM" not in template_upper:
            logger.warning("⚠️ 模板缺少 FROM 子句", template=template[:50])
            return False

        # 檢查參數佔位符格式
        placeholders = re.findall(r"\{(\w+)\}", template)
        for placeholder in placeholders:
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", placeholder):
                logger.warning("⚠️ 無效的參數佔位符", placeholder=placeholder)
                return False

        # 檢查是否包含危險的 SQL 操作（使用配置檔案和改進的檢測邏輯）
        return self._validate_sql_security(template_upper)

    def _validate_sql_security(self, template_upper: str) -> bool:
        """
        驗證 SQL 模板的安全性（增強版本）

        Args:
            template_upper: 大寫的模板內容

        Returns:
            bool: 模板是否安全
        """
        try:
            # 從配置獲取禁止的關鍵字 (安全處理)
            security_config: dict = (
                getattr(self._config, "get_template_security_config", lambda: {})()
                or {}
            )
            forbidden_keywords = security_config.get(
                "forbidden_keywords",
                [
                    "DROP",
                    "DELETE",
                    "UPDATE",
                    "INSERT",
                    "ALTER",
                    "TRUNCATE",
                    "EXEC",
                    "UNION",
                    "SCRIPT",
                ],
            )

            # 使用正規表達式精確匹配 SQL 語句（避免誤判欄位名稱）
            for keyword in forbidden_keywords:
                # 檢查是否為 SQL 語句開頭的關鍵字（非欄位名稱）
                # 模式：行首或分號後的關鍵字，後面跟空白字符
                pattern = rf"(?:^|;\s*){keyword}(?:\s|$)"
                if re.search(pattern, template_upper, re.MULTILINE):
                    logger.warning(
                        "⚠️ 模板包含危險的 SQL 語句",
                        keyword=keyword,
                        template=template_upper[:100],
                    )
                    return False

            # 增強的 MCP 相容性檢查
            if not self._validate_mcp_compatibility(template_upper):
                return False

        except Exception as e:
            # 如果配置無法獲取，使用預設的安全檢查
            # 降級為 debug 級別，因為有預設機制兜底
            logger.debug("⚠️ 無法獲取安全配置，使用預設檢查", error=str(e))

            # 預設的保守檢查：只檢查明確的 SQL 語句模式
            dangerous_patterns = [
                r"(?:^|;\s*)DROP\s+",
                r"(?:^|;\s*)DELETE\s+",
                r"(?:^|;\s*)UPDATE\s+.*SET\s+",
                r"(?:^|;\s*)INSERT\s+INTO\s+",
                r"(?:^|;\s*)ALTER\s+",
                r"(?:^|;\s*)TRUNCATE\s+",
            ]

            for pattern in dangerous_patterns:
                if re.search(pattern, template_upper, re.MULTILINE | re.IGNORECASE):
                    logger.warning("⚠️ 模板包含危險的 SQL 語句模式", pattern=pattern)
                    return False

        return True

    def _validate_mcp_compatibility(self, template_upper: str) -> bool:
        """
        驗證 MCP 服務器相容性

        Args:
            template_upper: 大寫的模板內容

        Returns:
            bool: 是否相容 MCP 服務器
        """
        # 確保是純 SELECT 查詢
        if not template_upper.strip().startswith("SELECT"):
            logger.warning("⚠️ 模板不是以 SELECT 開始，可能被 MCP 服務器拒絕")
            return False

        # 檢查是否包含可能被誤判的構造
        potentially_problematic_patterns = [
            # 檢查是否有複雜的子查詢可能被誤判
            r";\s*SELECT",  # 多個 SELECT 語句
            r"UNION\s+ALL",  # UNION 查詢可能被視為修改操作
            r"WITH\s+RECURSIVE",  # 遞歸查詢可能被限制
            # 檢查是否有動態 SQL 構造
            r"EXEC\s*\(",  # 執行動態 SQL
            r"EXECUTE\s*\(",  # 執行動態 SQL
            # 檢查是否有系統函數調用
            r"PRAGMA\s+",  # SQLite 的 PRAGMA 語句（PostgreSQL 不支援）
            r"VACUUM\s+",  # 數據庫維護操作
            r"ANALYZE\s+",  # 統計更新操作
        ]

        for pattern in potentially_problematic_patterns:
            if re.search(pattern, template_upper, re.IGNORECASE):
                logger.warning(
                    "⚠️ 模板包含可能被 MCP 服務器限制的構造",
                    pattern=pattern,
                    template_preview=template_upper[:200],
                )
                return False

        # 檢查 SQL 格式標準化
        if not self._is_sql_properly_formatted(template_upper):
            logger.warning("⚠️ SQL 格式可能導致 MCP 服務器解析問題")
            return False

        logger.debug("✅ 模板通過 MCP 相容性檢查")
        return True

    def _is_sql_properly_formatted(self, template_upper: str) -> bool:
        """
        檢查 SQL 格式是否符合標準

        Args:
            template_upper: 大寫的模板內容

        Returns:
            bool: 格式是否正確
        """
        # 基本格式檢查
        lines = template_upper.split("\n")

        # 檢查是否有過長的行（可能導致解析問題）
        for line in lines:
            if len(line.strip()) > 500:  # 單行過長
                logger.debug("發現過長的 SQL 行", line_length=len(line.strip()))
                # 不直接返回 False，因為這不是致命問題，只是提醒

        # 檢查是否有不匹配的括號
        open_parens = template_upper.count("(")
        close_parens = template_upper.count(")")
        if open_parens != close_parens:
            logger.warning(
                "⚠️ SQL 括號不匹配", open_count=open_parens, close_count=close_parens
            )
            return False

        # 檢查是否有不匹配的引號
        single_quote_count = template_upper.count("'")
        if single_quote_count % 2 != 0:
            logger.warning("⚠️ SQL 單引號不匹配", quote_count=single_quote_count)
            return False

        return True

    def validate_template_for_mcp(self, template: str) -> dict[str, Any]:
        """
        專門為 MCP 服務器驗證模板

        Args:
            template: 要驗證的模板

        Returns:
            dict[str, Any]: 詳細的驗證結果
        """
        validation_result: dict[str, Any] = {
            "is_valid": True,
            "is_mcp_compatible": True,
            "warnings": [],
            "errors": [],
            "recommendations": [],
        }

        try:
            template_upper = template.upper().strip()

            # 基本 SQL 驗證
            if not self.validate_template(template):
                validation_result["is_valid"] = False
                validation_result["errors"].append("基本 SQL 模板驗證失敗")

            # MCP 相容性檢查
            if not self._validate_mcp_compatibility(template_upper):
                validation_result["is_mcp_compatible"] = False
                validation_result["errors"].append("MCP 服務器相容性檢查失敗")

            # 格式建議
            if len(template) > 1000:
                validation_result["recommendations"].append("考慮簡化查詢以提高性能")

            # 複雜度分析
            complexity_score = (
                len(re.findall(r"JOIN", template_upper)) * 2
                + len(re.findall(r"SUBQUERY|SELECT.*SELECT", template_upper, re.DOTALL))
                * 3
                + len(re.findall(r"GROUP BY", template_upper))
                + len(re.findall(r"ORDER BY", template_upper))
            )

            if complexity_score > 10:
                validation_result["warnings"].append(
                    f"查詢複雜度較高 (分數: {complexity_score})"
                )
                validation_result["recommendations"].append("考慮分解為多個簡單查詢")

            # 最終狀態
            validation_result["is_valid"] = (
                validation_result["is_valid"]
                and validation_result["is_mcp_compatible"]
                and len(validation_result["errors"]) == 0
            )

        except Exception as e:
            validation_result["is_valid"] = False
            validation_result["errors"].append(f"驗證過程中發生錯誤: {str(e)}")
            logger.error("模板 MCP 驗證失敗", error=str(e))

        return validation_result

    def get_template_parameters(self, query_type: QueryType) -> list[str]:
        """
        獲取模板中的參數列表

        Args:
            query_type: 查詢類型

        Returns:
            list[str]: 參數名稱列表
        """
        template = self.get_template(query_type)
        parameters = re.findall(r"\{(\w+)\}", template)

        # 去除重複並排序
        unique_parameters = sorted(set(parameters))

        logger.debug(
            "📋 提取模板參數", query_type=query_type.value, parameters=unique_parameters
        )

        return unique_parameters

    def load_templates_from_file(self, file_path: str) -> None:
        """
        從檔案載入模板配置

        Args:
            file_path: 模板配置檔案路徑

        Raises:
            TemplateLoadError: 載入失敗
        """
        try:
            # 這裡會在實際實現時從檔案載入
            # 暫時使用配置介面
            logger.info("📋 從檔案載入模板", file_path=file_path)
            self._load_templates()

        except Exception as e:
            logger.error("❌ 模板檔案載入失敗", file_path=file_path, error=str(e))
            raise RuntimeError(f"模板載入失敗: {str(e)}") from e

    def reload_templates(self) -> None:
        """
        重新載入所有模板

        用於支援熱更新功能
        """
        try:
            old_count = len(self._templates)

            # 重新載入配置
            self._config.reload_config()

            # 重新載入模板
            self._load_templates()

            new_count = len(self._templates)

            logger.info("🔄 模板重新載入完成", old_count=old_count, new_count=new_count)

        except Exception as e:
            logger.error("❌ 模板重新載入失敗", error=str(e))
            raise

    def _load_templates(self) -> None:
        """
        從配置載入模板
        """
        successfully_loaded: list[Any] = []
        failed_templates: list[Any] = []

        try:
            # 從配置獲取 SQL 模板
            sql_templates = self._config.get_sql_templates()
            logger.info("📋 開始載入模板", config_templates_count=len(sql_templates))

            # 轉換為 QueryType 鍵值
            for type_name, template in sql_templates.items():
                try:
                    query_type = QueryType(type_name)

                    # 🔥 關鍵修復：詳細的模板驗證和記錄
                    if template and template.strip():
                        if self.validate_template(template):
                            stripped_template = template.strip()
                            self._templates[query_type] = stripped_template
                            self._update_template_metadata(
                                query_type, stripped_template
                            )
                            successfully_loaded.append(type_name)
                            logger.debug(
                                "✅ 模板載入成功",
                                query_type=type_name,
                                template_length=len(stripped_template),
                            )
                        else:
                            failed_templates.append((type_name, "模板驗證失敗"))
                            logger.warning(
                                "⚠️ 無效的模板，跳過載入", query_type=type_name
                            )
                    else:
                        failed_templates.append((type_name, "模板為空"))
                        logger.warning("⚠️ 空模板，跳過載入", query_type=type_name)

                except ValueError as e:
                    failed_templates.append((type_name, f"查詢類型無效: {str(e)}"))
                    logger.debug("⚠️ 無效的查詢類型", query_type=type_name, error=str(e))

            # 🔥 關鍵修復：如果沒有成功載入任何模板，強制載入預設模板
            if not successfully_loaded:
                logger.error("❌ 沒有成功載入任何配置模板，載入預設模板")
                self._load_default_templates()
            else:
                logger.info(
                    "📋 配置模板載入完成",
                    successful_count=len(successfully_loaded),
                    failed_count=len(failed_templates),
                    total_templates=len(self._templates),
                )

            # 記錄失敗的模板
            if failed_templates:
                logger.warning("⚠️ 部分模板載入失敗", failed_templates=failed_templates)

        except Exception as e:
            logger.error("❌ 模板載入過程發生嚴重錯誤", error=str(e))
            # 載入預設模板作為後備
            self._load_default_templates()

    def _load_default_templates(self) -> None:
        """
        載入預設模板（後備方案）
        """
        default_templates = {
            QueryType.SPECIFIC_MACHINE: """
                SELECT
                    m.machine_id,
                    m.machine_name,
                    m.department,
                    COALESCE(AVG(u.utilization_rate), 0) as avg_utilization,
                    COALESCE(AVG(u.efficiency_rate), 0) as avg_efficiency,
                    MAX(u.date) as last_record_date,
                    COALESCE(SUM(u.good_parts), 0) as total_good_parts,
                    COALESCE(SUM(u.defective_parts), 0) as total_defective_parts
                FROM machines m
                LEFT JOIN machine_utilization u ON m.machine_id = u.machine_id
                WHERE m.machine_id = '{machine_id}'
                GROUP BY m.machine_id, m.machine_name, m.department
            """,
            QueryType.ALL_MACHINES: """
                SELECT
                    m.machine_id,
                    m.machine_name,
                    m.department,
                    COALESCE(AVG(u.utilization_rate), 0) as avg_utilization,
                    COALESCE(AVG(u.efficiency_rate), 0) as avg_efficiency,
                    MAX(u.date) as last_record_date
                FROM machines m
                LEFT JOIN machine_utilization u ON m.machine_id = u.machine_id
                    AND u.date >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY m.machine_id, m.machine_name, m.department
                ORDER BY m.machine_id
            """,
            QueryType.FAULT_ANALYSIS: """
                SELECT
                    COUNT(*) as total_faults,
                    fault_type,
                    severity,
                    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() as percentage
                FROM machine_faults
                WHERE fault_date >= CURRENT_DATE - INTERVAL '{days} days'
                GROUP BY fault_type, severity
                ORDER BY COUNT(*) DESC
            """,
            QueryType.PRODUCTION_STATS: """
                SELECT
                    m.department,
                    COUNT(DISTINCT m.machine_id) as machine_count,
                    COALESCE(AVG(u.utilization_rate), 0) as avg_utilization,
                    COALESCE(AVG(u.efficiency_rate), 0) as avg_efficiency,
                    COALESCE(SUM(u.good_parts), 0) as total_good_parts,
                    COALESCE(SUM(u.defective_parts), 0) as total_defective_parts
                FROM machines m
                LEFT JOIN machine_utilization u ON m.machine_id = u.machine_id
                    AND u.date >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY m.department
                ORDER BY avg_utilization DESC
            """,
            QueryType.DEPARTMENT_STATUS: """
                SELECT
                    m.machine_id,
                    m.machine_name,
                    COALESCE(AVG(u.utilization_rate), 0) as avg_utilization,
                    COALESCE(AVG(u.efficiency_rate), 0) as avg_efficiency,
                    MAX(u.date) as last_record_date
                FROM machines m
                LEFT JOIN machine_utilization u ON m.machine_id = u.machine_id
                    AND u.date >= CURRENT_DATE - INTERVAL '7 days'
                WHERE m.department = '{department}'
                GROUP BY m.machine_id, m.machine_name
                ORDER BY avg_utilization DESC
            """,
            # 🔥 關鍵修復：添加缺失的 MACHINE_STATUS 模板
            QueryType.MACHINE_STATUS: """
                SELECT
                    m.machine_id,
                    m.machine_name,
                    m.department,
                    m.status,
                    COALESCE(u.utilization_rate, 0) as current_utilization,
                    COALESCE(u.efficiency_rate, 0) as current_efficiency,
                    u.date as last_update
                FROM machines m
                LEFT JOIN machine_utilization u ON m.machine_id = u.machine_id
                    AND u.date = (
                        SELECT MAX(date)
                        FROM machine_utilization
                        WHERE machine_id = m.machine_id
                    )
                ORDER BY m.machine_id
            """,
        }

        # 🔥 關鍵修復：逐個載入並驗證預設模板
        loaded_count = 0
        for query_type, template in default_templates.items():
            try:
                stripped_template = template.strip()

                # 驗證預設模板
                if self.validate_template(stripped_template):
                    self._templates[query_type] = stripped_template
                    self._update_template_metadata(query_type, stripped_template)
                    loaded_count += 1
                    logger.debug("✅ 預設模板載入成功", query_type=query_type.value)
                else:
                    logger.error("❌ 預設模板驗證失敗", query_type=query_type.value)

            except Exception as e:
                logger.error(
                    "❌ 預設模板載入失敗", query_type=query_type.value, error=str(e)
                )

        logger.info(
            "📋 預設模板載入完成",
            total_templates=len(default_templates),
            loaded_count=loaded_count,
            final_template_count=len(self._templates),
        )

    def _update_template_metadata(self, query_type: QueryType, template: str) -> None:
        """
        更新模板元數據

        Args:
            query_type: 查詢類型
            template: 模板內容
        """
        # 提取模板統計資訊
        parameters = self.get_template_parameters(query_type)
        line_count = len(template.split("\n"))
        char_count = len(template)

        # 分析查詢複雜度
        complexity_indicators = {
            "joins": len(re.findall(r"JOIN", template, re.IGNORECASE)),
            "aggregations": len(
                re.findall(r"(AVG|SUM|COUNT|MAX|MIN)\s*\(", template, re.IGNORECASE)
            ),
            "subqueries": len(re.findall(r"\(\s*SELECT", template, re.IGNORECASE)),
            "group_by": len(re.findall(r"GROUP BY", template, re.IGNORECASE)),
            "order_by": len(re.findall(r"ORDER BY", template, re.IGNORECASE)),
        }

        complexity_score = sum(complexity_indicators.values())

        self._template_metadata[query_type] = {
            "parameters": parameters,
            "parameter_count": len(parameters),
            "line_count": line_count,
            "character_count": char_count,
            "complexity_score": complexity_score,
            "complexity_indicators": complexity_indicators,
            "estimated_performance": self._estimate_template_performance(
                complexity_score
            ),
        }

    def _estimate_template_performance(self, complexity_score: int) -> str:
        """
        估算模板效能

        Args:
            complexity_score: 複雜度分數

        Returns:
            str: 效能等級
        """
        if complexity_score <= 2:
            return "fast"
        elif complexity_score <= 5:
            return "medium"
        else:
            return "slow"

    def get_template_metadata(self, query_type: QueryType) -> dict[str, Any]:
        """
        獲取模板元數據

        Args:
            query_type: 查詢類型

        Returns:
            dict[str, Any]: 模板元數據
        """
        return self._template_metadata.get(query_type, {})

    def get_all_templates(self) -> dict[QueryType, str]:
        """
        獲取所有模板

        Returns:
            dict[QueryType, str]: 所有模板字典
        """
        return self._templates.copy()

    def get_template_stats(self) -> dict[str, Any]:
        """
        獲取模板統計資訊

        Returns:
            dict[str, Any]: 統計資訊
        """
        total_templates = len(self._templates)
        total_parameters = sum(
            len(self.get_template_parameters(qt)) for qt in self._templates
        )

        complexity_distribution: dict[str, int] = {}
        for query_type in self._templates:
            metadata = self._template_metadata.get(query_type, {})
            performance = metadata.get("estimated_performance", "unknown")
            complexity_distribution[performance] = (
                complexity_distribution.get(performance, 0) + 1
            )

        return {
            "total_templates": total_templates,
            "total_parameters": total_parameters,
            "complexity_distribution": complexity_distribution,
            "supported_query_types": [qt.value for qt in self._templates],
            "average_complexity": (
                sum(
                    self._template_metadata.get(qt, {}).get("complexity_score", 0)
                    for qt in self._templates
                )
                / total_templates
                if total_templates > 0
                else 0
            ),
        }

    def validate_all_templates(self) -> dict[str, Any]:
        """
        驗證所有模板的有效性（包含 MCP 相容性檢查）

        Returns:
            dict[str, Any]: 驗證結果
        """
        validation_results: dict[str, Any] = {
            "is_valid": True,
            "valid_templates": [],
            "invalid_templates": [],
            "mcp_compatible_templates": [],
            "mcp_incompatible_templates": [],
            "errors": [],
            "warnings": [],
            "detailed_results": {},
        }

        for query_type, template in self._templates.items():
            try:
                # 基本驗證
                basic_valid = self.validate_template(template)

                # MCP 相容性驗證
                mcp_validation = self.validate_template_for_mcp(template)

                # 記錄詳細結果
                validation_results["detailed_results"][query_type.value] = {
                    "basic_valid": basic_valid,
                    "mcp_validation": mcp_validation,
                    "template_length": len(template),
                    "parameter_count": len(self.get_template_parameters(query_type)),
                }

                if basic_valid:
                    validation_results["valid_templates"].append(query_type.value)
                else:
                    validation_results["invalid_templates"].append(query_type.value)
                    validation_results["is_valid"] = False

                if mcp_validation["is_mcp_compatible"]:
                    validation_results["mcp_compatible_templates"].append(
                        query_type.value
                    )
                else:
                    validation_results["mcp_incompatible_templates"].append(
                        query_type.value
                    )
                    validation_results["warnings"].extend(
                        [
                            f"{query_type.value}: {error}"
                            for error in mcp_validation["errors"]
                        ]
                    )

                # 收集建議
                if mcp_validation["recommendations"]:
                    validation_results["warnings"].extend(
                        [
                            f"{query_type.value}: {rec}"
                            for rec in mcp_validation["recommendations"]
                        ]
                    )

            except Exception as e:
                validation_results["errors"].append(f"{query_type.value}: {str(e)}")
                validation_results["invalid_templates"].append(query_type.value)
                validation_results["is_valid"] = False
                logger.error(
                    "模板驗證過程中發生錯誤", query_type=query_type.value, error=str(e)
                )

        # 生成摘要
        validation_results["summary"] = {
            "total_templates": len(self._templates),
            "valid_count": len(validation_results["valid_templates"]),
            "invalid_count": len(validation_results["invalid_templates"]),
            "mcp_compatible_count": len(validation_results["mcp_compatible_templates"]),
            "mcp_incompatible_count": len(
                validation_results["mcp_incompatible_templates"]
            ),
            "overall_valid": validation_results["is_valid"],
            "mcp_ready": len(validation_results["mcp_incompatible_templates"]) == 0,
        }

        logger.info("所有模板驗證完成", summary=validation_results["summary"])

        return validation_results
