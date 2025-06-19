#!/usr/bin/env python3
"""
自然語言轉 SQL 查詢服務
基於規則和模式匹配的方法將自然語言轉換為 SQL 查詢
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog

from src.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class QueryType(Enum):
    """查詢類型枚舉"""

    MACHINE_STATUS = "machine_status"
    FAULT_ANALYSIS = "fault_analysis"
    PRODUCTION_STATS = "production_stats"
    ALL_MACHINES = "all_machines"
    SPECIFIC_MACHINE = "specific_machine"
    DEPARTMENT_STATUS = "department_status"
    UNKNOWN = "unknown"


@dataclass
class ParsedQuery:
    """解析後的查詢物件"""

    query_type: QueryType
    sql_query: str
    parameters: dict[str, Any]
    confidence: float  # 0-1，查詢解析的信心度
    explanation: str  # 查詢說明


class NaturalLanguageToSQLService:
    """自然語言轉 SQL 查詢服務"""

    def __init__(self, ai_model_service=None):
        # 機台ID模式
        self.machine_id_pattern = re.compile(r"[Mm](\d{3,4})", re.IGNORECASE)

        # AI 模型服務（可選）
        self.ai_model_service = ai_model_service
        self.enable_ai_enhancement = settings.ai_enable_enhanced_nl
        self.fallback_to_rules = settings.ai_fallback_to_rules
        self.rules_first = settings.ai_rules_first

        # 統計追蹤
        self.stats = {
            "rules_success": 0,
            "rules_fail": 0,
            "ai_success": 0,
            "ai_fail": 0,
            "total_queries": 0,
        }

        logger.info("🧠 自然語言服務初始化")
        logger.info(f"   📝 規則優先: {'是' if self.rules_first else '否'}")
        logger.info(f"   🤖 AI增強: {'啟用' if self.enable_ai_enhancement else '禁用'}")
        logger.info(f"   🔄 規則回退: {'啟用' if self.fallback_to_rules else '禁用'}")

        # 查詢模式定義（增強版）
        self.query_patterns = {
            # 機台狀態查詢
            QueryType.MACHINE_STATUS: [
                r"(.*)(機台|設備|機器).*(狀況|狀態|情況|如何|怎麼樣|怎樣)",
                r"(.*)(M\d+).*(狀況|狀態|情況|如何|怎麼樣|現在)",
                r"查詢.*(機台|設備|機器)",
                r"(.*)(運行|運轉|工作|運作).*(情況|狀況|狀態)",
                r"(.*)(機台).*(現在|目前|當前)",
                r"(M\d+).*?$",  # 單獨的機台ID
            ],
            # 故障分析
            QueryType.FAULT_ANALYSIS: [
                r".*(故障|失效|異常|問題|錯誤|壞|修).*(記錄|統計|分析|情況|次數)",
                r".*(近期|最近|近|7天|七天|一週|一周|一個月|30天).*(故障|問題|異常)",
                r"故障.*(統計|分析|報告)",
                r"查詢.*(故障|異常|問題)",
                r".*(維修|保養|檢修).*(記錄|統計)",
                r"異常.*分析",
            ],
            # 生產統計
            QueryType.PRODUCTION_STATS: [
                r".*(生產|產量|產能|產出).*(統計|數據|報告|資料)",
                r".*(良品|不良品|良率|效率|產能).*(統計|數量|比率)",
                r".*(稼動率|效率|利用率|使用率)",
                r"生產.*(報告|狀況|情況)",
                r".*(產線|生產線).*(效能|效率)",
                r"品質.*報告",
            ],
            # 所有機台
            QueryType.ALL_MACHINES: [
                r".*(所有|全部|全體|全|每|各).*(機台|設備|機器)",
                r"查看.*(所有|全部).*(機台|設備)",
                r"列出.*(機台|設備|機器)",
                r"機台.*(列表|清單|總覽)",
                r"顯示.*機台",
                r"全廠.*機台",
            ],
            # 部門狀態
            QueryType.DEPARTMENT_STATUS: [
                r".*(部門|車間|區域|單位).*(狀況|狀態|情況)",
                r"查詢.*(部門|車間)",
                r".*(加工部|組裝部|品管部|維修部|生產部)",
                r".*(加工|組裝|品管|維修).*(部門|區)",
                r"部門.*(報告|統計)",
            ],
        }

        # SQL 模板
        self.sql_templates = {
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
                    AND u.date >= date('now', '-7 days')
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
                WHERE fault_date >= date('now', '-30 days')
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
                    AND u.date >= date('now', '-7 days')
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
                    AND u.date >= date('now', '-7 days')
                WHERE m.department = '{department}'
                GROUP BY m.machine_id, m.machine_name
                ORDER BY avg_utilization DESC
            """,
        }

        # 部門名稱映射
        self.department_mapping = {
            "加工": "加工部",
            "組裝": "組裝部",
            "品管": "品管部",
            "維修": "維修部",
            "生產": "生產部",
        }

    async def parse_natural_language(
        self, text: str, database_schema: dict[str, Any] | None = None
    ) -> ParsedQuery:
        """
        解析自然語言查詢
        優先順序：1. 規則解析 2. AI增強（僅在規則無法識別時）

        Args:
            text: 使用者輸入的自然語言文字
            database_schema: 資料庫結構資訊（用於AI增強）

        Returns:
            ParsedQuery: 解析後的查詢物件
        """
        original_text = text
        text = text.strip().lower()

        # 更新統計
        self.stats["total_queries"] += 1

        # 1. 優先使用基礎規則解析
        logger.info("📝 嘗試規則解析...")
        rule_result = self._parse_with_rules(text, original_text)

        # 如果規則解析成功，直接返回
        if rule_result.query_type != QueryType.UNKNOWN and rule_result.confidence > 0.5:
            logger.info(
                f"✅ 規則解析成功: {rule_result.query_type.value}, 信心度: {rule_result.confidence}"
            )
            self.stats["rules_success"] += 1
            self._log_stats()
            return rule_result
        else:
            self.stats["rules_fail"] += 1

        # 2. 規則解析失敗，嘗試AI增強（如果啟用）
        if self.enable_ai_enhancement and self.ai_model_service and database_schema:
            logger.info("🤖 規則解析無法識別，嘗試AI增強...")
            try:
                enhanced_query, ai_confidence = (
                    await self.ai_model_service.enhance_natural_language_query(
                        original_text, database_schema
                    )
                )

                if ai_confidence > 0.6:  # 降低AI信心度門檻
                    logger.info(f"🤖 使用AI增強解析: {ai_confidence:.2f}")
                    ai_parsed_query = self._parse_ai_enhanced_query(
                        enhanced_query, original_text
                    )
                    if ai_parsed_query.confidence > 0.4:
                        self.stats["ai_success"] += 1
                        self._log_stats()
                        return ai_parsed_query
                    else:
                        self.stats["ai_fail"] += 1

            except Exception as e:
                logger.warning(f"AI增強解析失敗: {e}")
                self.stats["ai_fail"] += 1

        # 3. 都失敗了，返回規則解析結果（即使是UNKNOWN）
        logger.info("⚠️ 無法識別查詢，返回預設結果")
        self._log_stats()
        return rule_result

    def _parse_with_rules(self, text: str, original_text: str) -> ParsedQuery:
        """基於規則的解析方法"""
        # 1. 檢查是否包含特定機台ID
        machine_match = self.machine_id_pattern.search(text)
        if machine_match:
            machine_id = f"M{machine_match.group(1).zfill(3)}"
            return self._create_machine_query(machine_id, text)

        # 2. 按優先級檢查查詢模式
        for query_type, patterns in self.query_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return self._create_query_by_type(query_type, text)

        # 3. 未識別的查詢
        return ParsedQuery(
            query_type=QueryType.UNKNOWN,
            sql_query="",
            parameters={},
            confidence=0.0,
            explanation=f"無法識別的查詢：{original_text}",
        )

    def _parse_ai_enhanced_query(
        self, enhanced_query: str, original_text: str
    ) -> ParsedQuery:
        """解析AI增強後的查詢結果"""
        try:
            import json

            # 如果enhanced_query是JSON字串，嘗試解析
            if enhanced_query.startswith("{"):
                ai_result = json.loads(enhanced_query)

                query_type_str = ai_result.get("query_type", "unknown")
                confidence = float(ai_result.get("confidence", 0.7))
                target_entities = ai_result.get("target_entities", [])
                explanation = ai_result.get("explanation", "AI解析結果")

                # 映射AI識別的查詢類型
                query_type_mapping = {
                    "machine_status": QueryType.MACHINE_STATUS,
                    "fault_analysis": QueryType.FAULT_ANALYSIS,
                    "production_stats": QueryType.PRODUCTION_STATS,
                    "all_machines": QueryType.ALL_MACHINES,
                    "department_status": QueryType.DEPARTMENT_STATUS,
                }

                query_type = query_type_mapping.get(query_type_str, QueryType.UNKNOWN)

                # 根據AI識別的類型和實體創建查詢
                if query_type != QueryType.UNKNOWN:
                    if target_entities and any(
                        "M" in entity for entity in target_entities
                    ):
                        # 特定機台查詢
                        machine_id = next(
                            (entity for entity in target_entities if "M" in entity), ""
                        )
                        if machine_id:
                            return self._create_machine_query(machine_id, original_text)

                    return self._create_query_by_type(query_type, original_text)

            # 如果不是JSON，當作增強描述處理
            return self._parse_with_rules(enhanced_query.lower(), original_text)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"AI結果解析失敗: {e}")
            return self._parse_with_rules(enhanced_query.lower(), original_text)

    def _create_machine_query(self, machine_id: str, text: str) -> ParsedQuery:
        """創建特定機台查詢"""
        sql_query = (
            self.sql_templates[QueryType.SPECIFIC_MACHINE]
            .format(machine_id=machine_id)
            .strip()
        )

        return ParsedQuery(
            query_type=QueryType.SPECIFIC_MACHINE,
            sql_query=sql_query,
            parameters={"machine_id": machine_id},
            confidence=0.9,
            explanation=f"查詢機台 {machine_id} 的詳細狀態",
        )

    def _create_query_by_type(self, query_type: QueryType, text: str) -> ParsedQuery:
        """根據查詢類型創建查詢"""

        if query_type == QueryType.ALL_MACHINES:
            return self._create_all_machines_query(text)
        elif query_type == QueryType.FAULT_ANALYSIS:
            return self._create_fault_analysis_query(text)
        elif query_type == QueryType.PRODUCTION_STATS:
            return self._create_production_stats_query(text)
        elif query_type == QueryType.DEPARTMENT_STATUS:
            return self._create_department_query(text)
        else:
            return self._create_general_query(query_type, text)

    def _create_all_machines_query(self, text: str) -> ParsedQuery:
        """創建所有機台查詢"""
        sql_query = self.sql_templates[QueryType.ALL_MACHINES].strip()

        return ParsedQuery(
            query_type=QueryType.ALL_MACHINES,
            sql_query=sql_query,
            parameters={},
            confidence=0.8,
            explanation="查詢所有機台的狀態概覽",
        )

    def _create_fault_analysis_query(self, text: str) -> ParsedQuery:
        """創建故障分析查詢"""
        # 檢查時間範圍
        days = 30  # 預設30天
        if re.search(r"7天|一週|一个星期", text, re.IGNORECASE):
            days = 7
        elif re.search(r"一個月|30天", text, re.IGNORECASE):
            days = 30

        sql_query = (
            self.sql_templates[QueryType.FAULT_ANALYSIS]
            .replace("date('now', '-30 days')", f"date('now', '-{days} days')")
            .strip()
        )

        return ParsedQuery(
            query_type=QueryType.FAULT_ANALYSIS,
            sql_query=sql_query,
            parameters={"days": days},
            confidence=0.8,
            explanation=f"分析近 {days} 天的故障記錄",
        )

    def _create_production_stats_query(self, text: str) -> ParsedQuery:
        """創建生產統計查詢"""
        sql_query = self.sql_templates[QueryType.PRODUCTION_STATS].strip()

        return ParsedQuery(
            query_type=QueryType.PRODUCTION_STATS,
            sql_query=sql_query,
            parameters={},
            confidence=0.8,
            explanation="生產統計報告（按部門）",
        )

    def _create_department_query(self, text: str) -> ParsedQuery:
        """創建部門查詢"""
        # 尋找部門名稱
        department = None
        for key, value in self.department_mapping.items():
            if key in text:
                department = value
                break

        if department:
            sql_query = (
                self.sql_templates[QueryType.DEPARTMENT_STATUS]
                .format(department=department)
                .strip()
            )

            return ParsedQuery(
                query_type=QueryType.DEPARTMENT_STATUS,
                sql_query=sql_query,
                parameters={"department": department},
                confidence=0.8,
                explanation=f"查詢 {department} 的機台狀態",
            )
        else:
            # 無法識別部門，改為查詢所有機台
            return self._create_all_machines_query(text)

    def _create_general_query(self, query_type: QueryType, text: str) -> ParsedQuery:
        """創建一般查詢"""
        if query_type in self.sql_templates:
            sql_query = self.sql_templates[query_type].strip()
            return ParsedQuery(
                query_type=query_type,
                sql_query=sql_query,
                parameters={},
                confidence=0.7,
                explanation=f"執行 {query_type.value} 查詢",
            )
        else:
            return ParsedQuery(
                query_type=QueryType.UNKNOWN,
                sql_query="",
                parameters={},
                confidence=0.0,
                explanation="未支援的查詢類型",
            )

    def get_suggested_queries(self) -> list[str]:
        """獲取建議的查詢範例"""
        return [
            "M001機台現在狀況如何？",
            "查看所有機台",
            "近期故障記錄",
            "故障統計分析",
            "生產統計報告",
            "加工部狀況",
            "機台稼動率",
            "查詢異常記錄",
        ]

    def _log_stats(self):
        """記錄統計資訊"""
        total = self.stats["total_queries"]
        if total > 0 and total % 10 == 0:  # 每10次查詢記錄一次
            rules_rate = (self.stats["rules_success"] / total) * 100
            ai_rate = (
                (self.stats["ai_success"] / total) * 100
                if self.stats["ai_success"] > 0
                else 0
            )

            logger.info(f"📊 查詢統計 (總計: {total})")
            logger.info(
                f"   📝 規則成功率: {rules_rate:.1f}% ({self.stats['rules_success']}/{total})"
            )
            if self.stats["ai_success"] + self.stats["ai_fail"] > 0:
                logger.info(
                    f"   🤖 AI成功率: {ai_rate:.1f}% ({self.stats['ai_success']}/{self.stats['ai_success'] + self.stats['ai_fail']})"
                )

    def get_stats(self) -> dict[str, Any]:
        """獲取統計資訊"""
        return {
            "total_queries": self.stats["total_queries"],
            "rules_success_rate": (
                (self.stats["rules_success"] / self.stats["total_queries"] * 100)
                if self.stats["total_queries"] > 0
                else 0
            ),
            "ai_usage_rate": (
                (
                    (self.stats["ai_success"] + self.stats["ai_fail"])
                    / self.stats["total_queries"]
                    * 100
                )
                if self.stats["total_queries"] > 0
                else 0
            ),
            "details": self.stats,
        }
