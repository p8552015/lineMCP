#!/usr/bin/env python3
"""
資料庫查詢服務
統一處理所有資料庫相關操作
"""

from typing import Any

import structlog

from .error_handlers import ErrorContext, async_retry, mcp_error_handler
from .mcp_response_parser import MCPParseError, MCPQueryError, MCPResponseParser
from .nl_to_sql.models.query_models import ParsedQuery, QueryType

logger = structlog.get_logger()


class DatabaseService:
    """資料庫查詢服務"""

    def __init__(self, mcp_client_getter):
        """
        初始化資料庫服務

        Args:
            mcp_client_getter: 獲取 MCP 客戶端的函數
        """
        self.get_mcp_client = mcp_client_getter
        self.parser = MCPResponseParser()

    @async_retry(max_attempts=3, delay_seconds=1.0)
    async def _execute_query(self, sql_query: str) -> list[dict[str, Any]]:
        """
        執行 SQL 查詢（內部方法，帶重試）

        Args:
            sql_query: SQL 查詢語句

        Returns:
            查詢結果列表
        """
        # 🔥 緊急修復：檢查空查詢
        if not sql_query or not sql_query.strip():
            logger.error(
                "❌ 緊急阻止：嘗試執行空查詢",
                query_repr=repr(sql_query),
                query_length=len(sql_query) if sql_query else 0,
            )
            raise ValueError("SQL 查詢不能為空")

        with ErrorContext("database_query") as ctx:
            ctx.add_context(query_preview=sql_query[:100])

            mcp_client = await self.get_mcp_client()
            result = await mcp_client.call_tool("postgres", "query", {"sql": sql_query})

            parsed_result = self.parser.parse_query_result(result)
            return list(parsed_result) if parsed_result is not None else []

    async def execute_parsed_query(self, parsed_query: ParsedQuery) -> dict[str, Any]:
        """
        執行解析後的查詢

        Args:
            parsed_query: 解析後的查詢物件

        Returns:
            格式化的查詢結果
        """
        if parsed_query.query_type == QueryType.UNKNOWN:
            return {
                "success": False,
                "error": "無法理解的查詢",
                "suggestion": "請嘗試：M001狀況、所有機台、故障記錄等",
            }

        # 🔥 緊急修復：檢查解析後的查詢是否為空
        if not parsed_query.sql_query or not parsed_query.sql_query.strip():
            logger.error(
                "❌ 緊急阻止：解析後的查詢為空",
                query_type=parsed_query.query_type.value,
                parameters=parsed_query.parameters,
                confidence=parsed_query.confidence,
            )
            return {
                "success": False,
                "error": "查詢解析失敗：生成的 SQL 查詢為空",
                "query_type": parsed_query.query_type.value,
                "suggestion": "請檢查查詢模板或聯絡系統管理員",
            }

        try:
            raw_data = await self._execute_query(parsed_query.sql_query)

            # 根據查詢類型格式化結果
            formatted_result = await self._format_query_result(
                parsed_query.query_type, raw_data, parsed_query.parameters
            )

            return {
                "success": True,
                "query_type": parsed_query.query_type.value,
                "data": formatted_result,
                "explanation": parsed_query.explanation,
                "confidence": parsed_query.confidence,
            }

        except (MCPQueryError, MCPParseError) as e:
            logger.error(f"Query execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "query_type": parsed_query.query_type.value,
            }

    async def _format_query_result(
        self,
        query_type: QueryType,
        raw_data: list[dict[str, Any]],
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """
        根據查詢類型格式化結果

        Args:
            query_type: 查詢類型
            raw_data: 原始查詢結果
            parameters: 查詢參數

        Returns:
            格式化後的結果
        """
        if query_type == QueryType.SPECIFIC_MACHINE:
            return await self._format_machine_status(
                raw_data, str(parameters.get("machine_id", ""))
            )
        elif query_type == QueryType.ALL_MACHINES:
            return await self._format_all_machines(raw_data)
        elif query_type == QueryType.FAULT_ANALYSIS:
            return await self._format_fault_analysis(
                raw_data, parameters.get("days", 30)
            )
        elif query_type == QueryType.PRODUCTION_STATS:
            return await self._format_production_stats(raw_data)
        elif query_type == QueryType.DEPARTMENT_STATUS:
            return await self._format_department_status(
                raw_data, str(parameters.get("department", ""))
            )
        else:
            return {"raw_data": raw_data}

    async def _format_machine_status(
        self, data: list[dict[str, Any]], machine_id: str
    ) -> dict[str, Any]:
        """格式化機台狀態資料"""
        if not data:
            return {
                "machine_id": machine_id,
                "found": False,
                "message": f"找不到機台 {machine_id}",
            }

        machine_data = data[0]

        # 獲取故障記錄
        fault_count = await self._get_recent_fault_count(machine_id, days=7)

        return {
            "machine_id": machine_data.get("machine_id"),
            "machine_name": machine_data.get("machine_name"),
            "department": machine_data.get("department"),
            "utilization_rate": float(machine_data.get("avg_utilization", 0)),
            "efficiency_rate": float(machine_data.get("avg_efficiency", 0)),
            "good_parts": int(machine_data.get("total_good_parts", 0)),
            "defective_parts": int(machine_data.get("total_defective_parts", 0)),
            "last_record_date": machine_data.get("last_record_date"),
            "recent_fault_count": fault_count,
            "found": True,
        }

    async def _format_all_machines(self, data: list[dict[str, Any]]) -> dict[str, Any]:
        """格式化所有機台資料"""
        if not data:
            return {"machines": [], "total_count": 0, "message": "沒有找到任何機台"}

        machines : list[Any] = []
        for machine in data:
            machines.append(
                {
                    "machine_id": machine.get("machine_id"),
                    "machine_name": machine.get("machine_name"),
                    "department": machine.get("department"),
                    "utilization_rate": float(machine.get("avg_utilization", 0)),
                    "efficiency_rate": float(machine.get("avg_efficiency", 0)),
                    "last_record_date": machine.get("last_record_date"),
                }
            )

        # 計算統計資訊
        total_machines = len(machines)
        avg_utilization = (
            sum(m["utilization_rate"] or 0 for m in machines) / total_machines
            if total_machines > 0
            else 0
        )
        avg_efficiency = (
            sum(m["efficiency_rate"] or 0 for m in machines) / total_machines
            if total_machines > 0
            else 0
        )

        return {
            "machines": machines,
            "total_count": total_machines,
            "summary": {
                "average_utilization": avg_utilization,
                "average_efficiency": avg_efficiency,
                "high_performance_count": len(
                    [m for m in machines if (m["utilization_rate"] or 0) > 0.8]
                ),
                "low_performance_count": len(
                    [m for m in machines if (m["utilization_rate"] or 0) < 0.6]
                ),
            },
        }

    async def _format_fault_analysis(
        self, data: list[dict[str, Any]], days: int
    ) -> dict[str, Any]:
        """格式化故障分析資料"""
        if not data:
            return {
                "total_faults": 0,
                "analysis_period_days": days,
                "fault_types": [],
                "message": f"近 {days} 天沒有故障記錄",
            }

        # 修復資料類型轉換問題
        total_faults = 0
        for row in data:
            try:
                count = row.get("total_faults", 0)
                # 確保轉換為整數
                if isinstance(count, str | float):
                    count = int(count)
                total_faults += count
            except (ValueError, TypeError):
                logger.warning(f"無法轉換故障計數: {row.get('total_faults')}")
                continue

        fault_types : list[Any] = []
        for row in data:
            try:
                count = row.get("total_faults", 0)
                percentage = row.get("percentage", 0)

                # 安全的類型轉換
                if isinstance(count, str | float):
                    count = int(count)

                if isinstance(percentage, str):
                    percentage = float(percentage)

                fault_types.append(
                    {
                        "fault_type": row.get("fault_type", "未知"),
                        "severity": row.get("severity", "未知"),
                        "count": count,
                        "percentage": percentage,
                    }
                )
            except (ValueError, TypeError) as e:
                logger.warning(f"故障資料轉換錯誤: {e}, row: {row}")
                continue

        return {
            "total_faults": total_faults,
            "analysis_period_days": days,
            "fault_types": fault_types,
            "most_common_fault": fault_types[0] if fault_types else None,
        }

    async def _format_production_stats(
        self, data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """格式化生產統計資料"""
        if not data:
            return {"departments": [], "message": "沒有生產統計資料"}

        departments : list[Any] = []
        for dept in data:
            departments.append(
                {
                    "department": dept.get("department"),
                    "machine_count": int(dept.get("machine_count", 0)),
                    "avg_utilization": float(dept.get("avg_utilization", 0)),
                    "avg_efficiency": float(dept.get("avg_efficiency", 0)),
                    "total_good_parts": int(dept.get("total_good_parts", 0)),
                    "total_defective_parts": int(dept.get("total_defective_parts", 0)),
                }
            )

        # 計算整體統計
        total_machines = sum(d["machine_count"] or 0 for d in departments)
        total_good_parts = sum(d["total_good_parts"] or 0 for d in departments)
        total_defective_parts = sum(
            d["total_defective_parts"] or 0 for d in departments
        )

        return {
            "departments": departments,
            "summary": {
                "total_machines": total_machines,
                "total_good_parts": total_good_parts,
                "total_defective_parts": total_defective_parts,
                "overall_quality_rate": (
                    total_good_parts / (total_good_parts + total_defective_parts) * 100
                    if (total_good_parts + total_defective_parts) > 0
                    else 0
                ),
            },
        }

    async def _format_department_status(
        self, data: list[dict[str, Any]], department: str
    ) -> dict[str, Any]:
        """格式化部門狀態資料"""
        if not data:
            return {
                "department": department,
                "machines": [],
                "message": f"{department} 沒有機台或資料",
            }

        machines : list[Any] = []
        for machine in data:
            machines.append(
                {
                    "machine_id": machine.get("machine_id"),
                    "machine_name": machine.get("machine_name"),
                    "utilization_rate": float(machine.get("avg_utilization", 0)),
                    "efficiency_rate": float(machine.get("avg_efficiency", 0)),
                    "last_record_date": machine.get("last_record_date"),
                }
            )

        return {
            "department": department,
            "machines": machines,
            "machine_count": len(machines),
        }

    async def _get_recent_fault_count(self, machine_id: str, days: int = 7) -> int:
        """獲取近期故障次數"""
        try:
            # 🔥 緊急修復：檢查參數
            if not machine_id or not machine_id.strip():
                logger.warning(
                    "❌ machine_id 為空，無法查詢故障次數", machine_id=repr(machine_id)
                )
                return 0

            fault_query = f"""
                SELECT COUNT(*) as fault_count
                FROM machine_faults
                WHERE machine_id = '{machine_id}'
                AND fault_date >= CURRENT_DATE - INTERVAL '{days} days'
            """

            result = await self._execute_query(fault_query)
            if result:
                count_result = self.parser.parse_count_result(
                    {"success": True, "data": result}
                )
                return int(count_result) if count_result is not None else 0
            return 0

        except Exception as e:
            logger.warning(f"Failed to get fault count for {machine_id}: {e}")
            return 0

    @mcp_error_handler("資料庫連接測試失敗")
    async def test_connection(self) -> bool:
        """測試資料庫連接"""
        try:
            result = await self._execute_query("SELECT 1 as test")
            return len(result) > 0
        except Exception:
            return False

    async def get_table_info(self) -> dict[str, Any]:
        """獲取資料庫表格資訊"""
        try:
            # 獲取表格列表
            tables_query = (
                "SELECT table_name as name FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
            await self._execute_query(tables_query)

            # 手動定義已知的表格結構，基於實際 PostgreSQL 資料庫
            table_info = {
                "machines": {
                    "columns": [
                        {"name": "id", "type": "TEXT"},
                        {"name": "name", "type": "TEXT"},
                        {"name": "location", "type": "TEXT"},
                        {"name": "utilization_rate", "type": "REAL"},
                        {"name": "status", "type": "TEXT"},
                        {"name": "temperature", "type": "REAL"},
                        {"name": "last_maintenance", "type": "TIMESTAMP"},
                        {"name": "created_at", "type": "TIMESTAMP"},
                    ],
                    "row_count": 0,
                },
                "machine_utilization": {
                    "columns": [
                        {"name": "machine_id", "type": "TEXT"},
                        {"name": "date", "type": "DATE"},
                        {"name": "utilization_rate", "type": "REAL"},
                        {"name": "efficiency_rate", "type": "REAL"},
                        {"name": "good_parts", "type": "INTEGER"},
                        {"name": "defective_parts", "type": "INTEGER"},
                    ],
                    "row_count": 0,
                },
                "machine_faults": {
                    "columns": [
                        {"name": "machine_id", "type": "TEXT"},
                        {"name": "fault_date", "type": "TIMESTAMP"},
                        {"name": "fault_type", "type": "TEXT"},
                        {"name": "severity", "type": "TEXT"},
                    ],
                    "row_count": 0,
                },
            }

            # 獲取每個表格的行數
            for table_name in table_info:
                try:
                    count_query = f"SELECT COUNT(*) as count FROM {table_name}"
                    count_result = await self._execute_query(count_query)
                    table_info[table_name]["row_count"] = (
                        count_result[0]["count"] if count_result else 0
                    )
                except Exception:
                    logger.warning(f"Failed to get row count for {table_name}")

            return table_info

        except Exception as e:
            logger.error(f"Failed to get table info: {e}")
            return {}
