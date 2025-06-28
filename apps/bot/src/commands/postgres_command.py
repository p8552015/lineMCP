#!/usr/bin/env python3
"""
PostgreSQL 查詢命令
支援自然語言查詢和直接 SQL 查詢
"""

from typing import Any

import structlog

from src.infrastructure.service_factory_interface import IServiceFactory
from src.services.nl_to_sql_service import NaturalLanguageToSQLService
from src.services.unified_mcp_client import get_unified_mcp_client

logger = structlog.get_logger()


class PostgreSQLCommand:
    """PostgreSQL 查詢命令處理器"""

    def __init__(self, service_factory: IServiceFactory):
        """初始化 PostgreSQL 命令"""
        self.service_factory = service_factory
        self.nl_to_sql_service = service_factory.get_service(
            NaturalLanguageToSQLService
        )

        # PostgreSQL 特定的查詢模板
        self.postgres_queries = {
            "員工數": "SELECT COUNT(*) as total_employees FROM employees",
            "部門統計": (
                "SELECT department, COUNT(*) as emp_count, AVG(salary) as avg_salary "
                "FROM employees GROUP BY department ORDER BY emp_count DESC"
            ),
            "薪資統計": (
                "SELECT department, MIN(salary) as min_salary, "
                "MAX(salary) as max_salary, "
                "AVG(salary) as avg_salary FROM employees GROUP BY department "
                "ORDER BY avg_salary DESC"
            ),
            "機台狀態": (
                "SELECT status, COUNT(*) as count FROM machines "
                "GROUP BY status ORDER BY count DESC"
            ),
            "產品庫存": (
                "SELECT category, COUNT(*) as product_count, SUM(stock) as total_stock "
                "FROM products GROUP BY category ORDER BY total_stock DESC"
            ),
            "訂單統計": (
                "SELECT status, COUNT(*) as order_count, "
                "SUM(total_amount) as total_value "
                "FROM orders GROUP BY status ORDER BY total_value DESC"
            ),
            "高薪員工": (
                "SELECT name, department, salary FROM employees "
                "WHERE salary > 75000 ORDER BY salary DESC"
            ),
            "缺貨產品": (
                "SELECT name, category, stock FROM products "
                "WHERE stock < 20 ORDER BY stock ASC"
            ),
            "運行機台": (
                "SELECT id, name, status, utilization_rate FROM machines "
                "WHERE status = '運行中' ORDER BY utilization_rate DESC"
            ),
            "待處理訂單": (
                "SELECT id, customer_name, total_amount, order_date FROM orders "
                "WHERE status = 'pending' ORDER BY order_date DESC"
            ),
        }

        logger.info("🐘 PostgreSQL 命令處理器已初始化")

    async def execute(self, user_input: str, user_id: str = None) -> dict[str, Any]:
        """
        執行 PostgreSQL 查詢命令

        Args:
            user_input: 用戶輸入的查詢
            user_id: 用戶 ID

        Returns:
            查詢結果
        """
        try:
            logger.info("🔍 開始執行 PostgreSQL 查詢", query=user_input, user_id=user_id)

            # 檢查是否為預定義查詢
            if user_input in self.postgres_queries:
                sql_query = self.postgres_queries[user_input]
                logger.info("📋 使用預定義查詢", template=user_input)
            else:
                # 使用 NL-to-SQL 服務轉換
                nl_result = await self._convert_natural_language_to_sql(user_input)

                if not nl_result.get("success"):
                    return {
                        "success": False,
                        "error": f"無法解析查詢: {nl_result.get('error', '未知錯誤')}",
                        "suggestions": self._get_query_suggestions(user_input),
                    }

                sql_query = nl_result.get("sql_query")
                if not sql_query:
                    return {
                        "success": False,
                        "error": "未能生成有效的 SQL 查詢",
                        "suggestions": self._get_query_suggestions(user_input),
                    }

            # 執行 PostgreSQL 查詢
            return await self._execute_postgres_query(sql_query, user_input)

        except Exception as e:
            logger.error("❌ PostgreSQL 查詢執行失敗", error=str(e), exc_info=True)
            return {
                "success": False,
                "error": f"查詢執行失敗: {str(e)}",
                "suggestions": ["請檢查查詢語法", "嘗試使用預定義查詢關鍵字"],
            }

    async def _convert_natural_language_to_sql(self, user_input: str) -> dict[str, Any]:
        """將自然語言轉換為 SQL 查詢"""
        try:
            # 針對 PostgreSQL 調整 NL-to-SQL 配置
            {
                "database_type": "postgresql",
                "tables": {
                    "employees": ["id", "name", "department", "salary", "hire_date"],
                    "products": ["id", "name", "category", "price", "stock"],
                    "orders": [
                        "id",
                        "customer_name",
                        "product_id",
                        "quantity",
                        "total_amount",
                        "status",
                    ],
                    "machines": [
                        "id",
                        "name",
                        "status",
                        "temperature",
                        "utilization_rate",
                        "location",
                    ],
                },
                "common_queries": list(self.postgres_queries.keys()),
            }

            # 調用 NL-to-SQL 服務
            parsed_query = await self.nl_to_sql_service.parse_natural_language(
                user_input
            )

            # 轉換 ParsedQuery 對象為字典格式
            if parsed_query.is_successful() and parsed_query.has_sql_query():
                return {
                    "success": True,
                    "sql_query": parsed_query.sql_query,
                    "confidence": parsed_query.confidence,
                    "query_type": parsed_query.query_type.value,
                    "explanation": parsed_query.explanation,
                }
            else:
                return {
                    "success": False,
                    "error": f"解析失敗: {parsed_query.explanation}",
                    "confidence": parsed_query.confidence,
                }

        except Exception as e:
            logger.error("❌ NL-to-SQL 轉換失敗", error=str(e))
            return {"success": False, "error": str(e)}

    async def _execute_postgres_query(
        self, sql_query: str, original_query: str
    ) -> dict[str, Any]:
        """執行 PostgreSQL 查詢"""
        try:
            # 獲取 MCP 客戶端管理器
            client = await get_unified_mcp_client()

            # 調用 PostgreSQL MCP 服務
            result = await client.call_tool("postgres", "query", {"sql": sql_query})

            if result.get("success"):
                # 處理查詢結果
                return await self._format_postgres_result(
                    result, sql_query, original_query
                )
            else:
                error_msg = result.get("error", "未知錯誤")
                logger.error("❌ PostgreSQL 查詢失敗", sql=sql_query, error=error_msg)

                return {
                    "success": False,
                    "error": f"數據庫查詢失敗: {error_msg}",
                    "sql_query": sql_query,
                    "suggestions": self._get_error_suggestions(error_msg),
                }

        except Exception as e:
            logger.error("❌ PostgreSQL 查詢執行異常", sql=sql_query, error=str(e))
            return {
                "success": False,
                "error": f"查詢執行異常: {str(e)}",
                "sql_query": sql_query,
            }

    async def _format_postgres_result(
        self, result: dict[str, Any], sql_query: str, original_query: str
    ) -> dict[str, Any]:
        """格式化 PostgreSQL 查詢結果"""
        try:
            content = result.get("content", [])

            if not content:
                return {
                    "success": True,
                    "message": "查詢執行成功，但沒有返回數據",
                    "data": [],
                    "sql_query": sql_query,
                    "original_query": original_query,
                }

            # 解析 PostgreSQL MCP 返回的結果
            formatted_data = []
            summary = {}

            for item in content:
                if hasattr(item, "text"):
                    import json

                    try:
                        data = json.loads(item.text)
                        if isinstance(data, list):
                            formatted_data.extend(data)
                        else:
                            formatted_data.append(data)
                    except json.JSONDecodeError:
                        formatted_data.append({"raw_text": item.text})

            # 生成摘要信息
            if formatted_data:
                summary = {
                    "total_records": len(formatted_data),
                    "columns": list(formatted_data[0].keys()) if formatted_data else [],
                    "query_type": self._detect_query_type(sql_query),
                }

            # 格式化顯示文本
            display_text = self._format_display_text(
                formatted_data, original_query, summary
            )

            return {
                "success": True,
                "message": "PostgreSQL 查詢執行成功",
                "data": formatted_data,
                "summary": summary,
                "display_text": display_text,
                "sql_query": sql_query,
                "original_query": original_query,
            }

        except Exception as e:
            logger.error("❌ 結果格式化失敗", error=str(e))
            return {
                "success": False,
                "error": f"結果格式化失敗: {str(e)}",
                "raw_result": result,
            }

    def _format_display_text(
        self, data: list[dict], original_query: str, summary: dict
    ) -> str:
        """格式化顯示文本"""
        if not data:
            return f"📊 查詢「{original_query}」執行完成，但沒有找到相關數據。"

        text_lines = [f"📊 查詢結果 - {original_query}"]
        text_lines.append("=" * 30)

        # 顯示摘要
        if summary:
            text_lines.append(f"📈 總計: {summary.get('total_records', 0)} 筆記錄")
            if summary.get("query_type"):
                text_lines.append(f"🔍 查詢類型: {summary['query_type']}")
            text_lines.append("")

        # 顯示數據（最多顯示前 10 筆）
        display_count = min(len(data), 10)
        for i, record in enumerate(data[:display_count]):
            text_lines.append(f"📋 記錄 {i+1}:")
            for key, value in record.items():
                text_lines.append(f"  • {key}: {value}")
            text_lines.append("")

        if len(data) > display_count:
            text_lines.append(f"... 還有 {len(data) - display_count} 筆記錄")

        return "\n".join(text_lines)

    def _detect_query_type(self, sql_query: str) -> str:
        """檢測查詢類型"""
        sql_upper = sql_query.upper().strip()

        if sql_upper.startswith("SELECT COUNT"):
            return "計數查詢"
        elif sql_upper.startswith("SELECT") and "GROUP BY" in sql_upper:
            return "分組統計"
        elif sql_upper.startswith("SELECT") and "ORDER BY" in sql_upper:
            return "排序查詢"
        elif sql_upper.startswith("SELECT"):
            return "數據查詢"
        else:
            return "其他查詢"

    def _get_query_suggestions(self, user_input: str) -> list[str]:
        """獲取查詢建議"""
        suggestions = [
            "嘗試使用以下預定義查詢關鍵字:",
            "• 員工數 - 查看員工總數",
            "• 部門統計 - 各部門員工統計",
            "• 機台狀態 - 機台狀態分布",
            "• 產品庫存 - 產品庫存統計",
            "• 高薪員工 - 薪資超過75000的員工",
        ]

        # 基於用戶輸入提供相關建議
        user_lower = user_input.lower()
        if "員工" in user_lower or "employee" in user_lower:
            suggestions.extend(["💡 相關查詢: 員工數、部門統計、薪資統計、高薪員工"])
        elif "機台" in user_lower or "machine" in user_lower:
            suggestions.extend(["💡 相關查詢: 機台狀態、運行機台"])
        elif "產品" in user_lower or "product" in user_lower:
            suggestions.extend(["💡 相關查詢: 產品庫存、缺貨產品"])
        elif "訂單" in user_lower or "order" in user_lower:
            suggestions.extend(["💡 相關查詢: 訂單統計、待處理訂單"])

        return suggestions

    def _get_error_suggestions(self, error_msg: str) -> list[str]:
        """基於錯誤信息提供建議"""
        suggestions = ["請檢查查詢語法並重試"]

        error_lower = error_msg.lower()
        if "table" in error_lower and "not exist" in error_lower:
            suggestions.append("可用的表格: employees, products, orders, machines")
        elif "column" in error_lower and "not exist" in error_lower:
            suggestions.append("請檢查列名是否正確")
        elif "syntax" in error_lower:
            suggestions.append("SQL 語法錯誤，請檢查查詢格式")

        return suggestions

    def get_help_text(self) -> str:
        """獲取幫助文本"""
        help_text = """
🐘 PostgreSQL 查詢命令幫助

📋 預定義查詢關鍵字:
• 員工數 - 查看員工總數
• 部門統計 - 各部門員工統計和平均薪資
• 薪資統計 - 各部門薪資統計
• 機台狀態 - 機台狀態分布
• 產品庫存 - 產品庫存統計
• 訂單統計 - 訂單狀態統計
• 高薪員工 - 薪資超過75000的員工
• 缺貨產品 - 庫存少於20的產品
• 運行機台 - 正在運行的機台
• 待處理訂單 - 狀態為pending的訂單

💡 使用示例:
• 直接輸入關鍵字: "員工數"
• 自然語言查詢: "有多少個員工在工程部"
• 直接 SQL: "SELECT * FROM employees WHERE department = '工程部'"

📊 可用數據表:
• employees - 員工資料
• products - 產品資料
• orders - 訂單資料
• machines - 機台資料
"""
        return help_text.strip()
