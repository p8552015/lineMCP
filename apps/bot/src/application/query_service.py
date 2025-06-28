"""
查詢應用服務
負責協調數據查詢和分析流程
"""

from datetime import datetime
from typing import Any

import structlog

from src.domain.exceptions import create_db_error, create_validation_error

from .base_service import BaseApplicationService

logger = structlog.get_logger()


class QueryApplicationService(BaseApplicationService):
    """
    查詢應用服務

    職責：
    - 協調 SQL 查詢執行
    - 管理查詢快取和優化
    - 提供查詢分析和統計
    - 處理複雜的多步驟查詢
    """

    def __init__(self, mcp_client_factory, db_service, response_parser):
        """
        初始化查詢服務

        Args:
            mcp_client_factory: MCP 客戶端工廠
            db_service: 資料庫服務
            response_parser: 回應解析器
        """
        super().__init__("query")
        self.mcp_client_factory = mcp_client_factory
        self.db_service = db_service
        self.response_parser = response_parser

        # 查詢快取
        self._query_cache: dict[str, dict[str, Any]] = {}
        self._cache_ttl_seconds = 300  # 5分鐘

        # 查詢統計
        self._query_stats = {
            "total_queries": 0,
            "cached_queries": 0,
            "failed_queries": 0,
            "avg_execution_time": 0.0,
            "slow_queries": 0,  # > 1秒的查詢
        }

        # 查詢歷史（最近100條）
        self._query_history: list[dict[str, Any]] = []
        self._max_history_size = 100

    async def _initialize_service(self) -> None:
        """初始化查詢服務"""
        # 初始化查詢快取和統計
        self.logger.info("查詢服務初始化完成")

    async def execute_sql_query(
        self,
        query: str,
        user_id: str,
        use_cache: bool = True,
        timeout_seconds: int = 30,
    ) -> dict[str, Any]:
        """
        執行 SQL 查詢

        Args:
            query: SQL 查詢語句
            user_id: 執行查詢的用戶 ID
            use_cache: 是否使用快取
            timeout_seconds: 查詢超時時間

        Returns:
            查詢結果字典
        """
        if not self._initialized:
            await self.initialize()

        # 🔥 緊急修復：檢查空查詢
        if not query or not query.strip():
            logger.error(
                "❌ 緊急阻止：嘗試執行空查詢", user_id=user_id, query_repr=repr(query)
            )
            raise create_validation_error("query", query, "查詢不能為空")

        # 驗證查詢
        self._validate_query(query)

        # 生成快取鍵
        cache_key = self._generate_cache_key(query)

        # 檢查快取
        if use_cache and cache_key in self._query_cache:
            cached_result = self._query_cache[cache_key]
            if not self._is_cache_expired(cached_result):
                self._query_stats["cached_queries"] += 1
                self.logger.info("返回快取查詢結果", cache_key=cache_key)
                return cached_result["data"]

        # 執行查詢
        start_time = datetime.now()

        try:
            self.logger.info("執行 SQL 查詢", query=query[:100], user_id=user_id)

            # 使用 MCP 客戶端執行查詢
            mcp_client = await self.mcp_client_factory()
            raw_result = await mcp_client.call_tool("postgres", "query", {"sql": query})

            # 解析結果
            parsed_data = self.response_parser.parse_query_result(raw_result)

            # 計算執行時間
            execution_time = (datetime.now() - start_time).total_seconds()

            # 構建結果
            result = {
                "success": True,
                "data": parsed_data,
                "query": query,
                "execution_time": execution_time,
                "row_count": len(parsed_data) if parsed_data else 0,
                "cached": False,
                "timestamp": datetime.now().isoformat(),
            }

            # 更新統計
            self._update_query_stats(execution_time, success=True)

            # 記錄查詢歷史
            self._add_to_history(query, user_id, result, execution_time)

            # 快取結果（如果適合快取）
            if use_cache and self._should_cache_result(result):
                self._cache_result(cache_key, result)

            self.logger.info(
                "查詢執行成功",
                execution_time=execution_time,
                row_count=result["row_count"],
            )

            return result

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_query_stats(execution_time, success=False)

            error_result = {
                "success": False,
                "error": str(e),
                "query": query,
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat(),
            }

            # 記錄失敗的查詢
            self._add_to_history(query, user_id, error_result, execution_time)

            self.logger.error(
                "查詢執行失敗",
                query=query[:100],
                error=str(e),
                execution_time=execution_time,
            )

            # 拋出領域異常
            raise create_db_error(query, str(e), "SELECT") from e

    def _validate_query(self, query: str) -> None:
        """
        驗證查詢安全性

        Args:
            query: SQL 查詢語句

        Raises:
            ValidationException: 查詢不符合安全要求
        """
        query_lower = query.lower().strip()

        # 檢查是否為空
        if not query_lower:
            raise create_validation_error("query", query, "查詢不能為空")

        # 安全檢查：只允許 SELECT 查詢
        allowed_prefixes = ["select", "explain"]
        if not any(query_lower.startswith(prefix) for prefix in allowed_prefixes):
            raise create_validation_error("query", query, "只允許 SELECT 和 EXPLAIN 查詢")

        # 禁止的關鍵字
        forbidden_keywords = [
            "drop",
            "delete",
            "update",
            "insert",
            "alter",
            "create",
            "truncate",
            "replace",
            "merge",
        ]

        for keyword in forbidden_keywords:
            if keyword in query_lower:
                raise create_validation_error("query", query, f"查詢包含禁止的關鍵字: {keyword}")

        # 檢查查詢長度
        if len(query) > 10000:  # 10KB 限制
            raise create_validation_error("query", query, "查詢語句過長（超過10KB）")

    def _generate_cache_key(self, query: str) -> str:
        """生成快取鍵"""
        import hashlib

        normalized_query = " ".join(query.lower().split())
        return hashlib.md5(normalized_query.encode()).hexdigest()

    def _is_cache_expired(self, cached_result: dict[str, Any]) -> bool:
        """檢查快取是否過期"""
        cache_time = datetime.fromisoformat(cached_result["cached_at"])
        return (datetime.now() - cache_time).total_seconds() > self._cache_ttl_seconds

    def _should_cache_result(self, result: dict[str, Any]) -> bool:
        """判斷結果是否應該被快取"""
        # 只快取成功的查詢
        if not result["success"]:
            return False

        # 不快取執行時間過長的查詢（可能包含實時數據）
        if result["execution_time"] > 5.0:
            return False

        # 不快取結果過大的查詢（節省記憶體）
        return not result["row_count"] > 1000

    def _cache_result(self, cache_key: str, result: dict[str, Any]) -> None:
        """快取查詢結果"""
        # 清理過期的快取
        self._cleanup_expired_cache()

        # 限制快取大小
        if len(self._query_cache) >= 100:
            # 移除最舊的快取項
            oldest_key = min(
                self._query_cache.keys(),
                key=lambda k: self._query_cache[k]["cached_at"],
            )
            del self._query_cache[oldest_key]

        # 添加到快取
        self._query_cache[cache_key] = {
            "data": result,
            "cached_at": datetime.now().isoformat(),
        }

    def _cleanup_expired_cache(self) -> None:
        """清理過期的快取項"""
        expired_keys = [
            key
            for key, cached_result in self._query_cache.items()
            if self._is_cache_expired(cached_result)
        ]

        for key in expired_keys:
            del self._query_cache[key]

    def _update_query_stats(self, execution_time: float, success: bool) -> None:
        """更新查詢統計"""
        self._query_stats["total_queries"] += 1

        if not success:
            self._query_stats["failed_queries"] += 1

        if execution_time > 1.0:
            self._query_stats["slow_queries"] += 1

        # 更新平均執行時間
        total_time = (
            self._query_stats["avg_execution_time"]
            * (self._query_stats["total_queries"] - 1)
            + execution_time
        )
        self._query_stats["avg_execution_time"] = (
            total_time / self._query_stats["total_queries"]
        )

    def _add_to_history(
        self, query: str, user_id: str, result: dict[str, Any], execution_time: float
    ) -> None:
        """添加到查詢歷史"""
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "query": query[:200],  # 保留前200字符
            "success": result["success"],
            "execution_time": execution_time,
            "row_count": result.get("row_count", 0) if result["success"] else 0,
            "error": result.get("error") if not result["success"] else None,
        }

        self._query_history.append(history_entry)

        # 保持歷史大小限制
        if len(self._query_history) > self._max_history_size:
            self._query_history.pop(0)

    async def get_table_info(self, table_name: str | None = None) -> dict[str, Any]:
        """
        獲取資料表資訊

        Args:
            table_name: 特定資料表名稱，如果為 None 則返回所有資料表

        Returns:
            資料表資訊
        """
        if table_name:
            # 獲取特定資料表的詳細資訊
            schema_query = f"""
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    ordinal_position
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                AND table_schema = 'public'
                ORDER BY ordinal_position
            """
            count_query = f"SELECT COUNT(*) as count FROM {table_name}"

            try:
                schema_result = await self.execute_sql_query(
                    schema_query, "system", use_cache=True
                )
                count_result = await self.execute_sql_query(
                    count_query, "system", use_cache=True
                )

                return {
                    "table_name": table_name,
                    "schema": schema_result["data"],
                    "row_count": (
                        count_result["data"][0]["count"] if count_result["data"] else 0
                    ),
                    "success": True,
                }
            except Exception as e:
                return {"table_name": table_name, "success": False, "error": str(e)}
        else:
            # 獲取所有資料表列表
            tables_query = (
                "SELECT table_name as name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name"
            )

            try:
                result = await self.execute_sql_query(
                    tables_query, "system", use_cache=True
                )

                return {
                    "tables": [row["name"] for row in result["data"]],
                    "table_count": len(result["data"]),
                    "success": True,
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

    def get_query_statistics(self) -> dict[str, Any]:
        """獲取查詢統計資訊"""
        return {
            **self._query_stats,
            "cache_hit_rate": (
                self._query_stats["cached_queries"]
                / max(self._query_stats["total_queries"], 1)
            )
            * 100,
            "success_rate": (
                (
                    self._query_stats["total_queries"]
                    - self._query_stats["failed_queries"]
                )
                / max(self._query_stats["total_queries"], 1)
            )
            * 100,
            "cached_results": len(self._query_cache),
            "history_size": len(self._query_history),
        }

    def get_recent_queries(self, limit: int = 10) -> list[dict[str, Any]]:
        """獲取最近的查詢記錄"""
        return self._query_history[-limit:] if limit > 0 else self._query_history[:]

    def clear_cache(self) -> int:
        """清除所有快取"""
        cache_count = len(self._query_cache)
        self._query_cache.clear()
        self.logger.info("已清除查詢快取", cleared_count=cache_count)
        return cache_count

    async def _perform_health_checks(self) -> dict[str, dict[str, Any]]:
        """執行健康檢查"""
        checks = {}

        # 檢查 MCP 連接
        try:
            mcp_client = await self.mcp_client_factory()
            test_result = await mcp_client.call_tool(
                "postgres", "query", {"sql": "SELECT 1 as test"}
            )

            checks["mcp_connection"] = {
                "status": "healthy" if test_result else "unhealthy",
                "test_query": "SELECT 1 as test",
            }
        except Exception as e:
            checks["mcp_connection"] = {"status": "unhealthy", "error": str(e)}

        # 檢查快取狀態
        checks["cache"] = {
            "status": "healthy",
            "cached_results": len(self._query_cache),
            "cache_hit_rate": (
                self._query_stats["cached_queries"]
                / max(self._query_stats["total_queries"], 1)
            )
            * 100,
        }

        # 檢查查詢統計
        stats = self.get_query_statistics()
        checks["query_performance"] = {"status": "healthy", **stats}

        return checks

    async def _shutdown_service(self) -> None:
        """關閉服務"""
        # 清理快取和歷史
        self._query_cache.clear()
        self._query_history.clear()

        # 重置統計
        self._query_stats = {
            "total_queries": 0,
            "cached_queries": 0,
            "failed_queries": 0,
            "avg_execution_time": 0.0,
            "slow_queries": 0,
        }

        self.logger.info("查詢服務已清理")
