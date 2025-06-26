"""
測試查詢應用服務
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.application.query_service import QueryApplicationService
from src.domain.exceptions import DatabaseQueryException, ValidationException


class TestQueryApplicationService:
    """查詢應用服務測試"""

    @pytest.fixture
    def mock_mcp_client_factory(self):
        """模擬 MCP 客戶端工廠"""
        factory = AsyncMock()
        mock_client = Mock()
        mock_client.call_tool = AsyncMock()
        factory.return_value = mock_client
        return factory

    @pytest.fixture
    def mock_db_service(self):
        """模擬資料庫服務"""
        return Mock()

    @pytest.fixture
    def mock_response_parser(self):
        """模擬回應解析器"""
        parser = Mock()
        parser.parse_query_result = Mock()
        return parser

    @pytest.fixture
    def query_service(
        self, mock_mcp_client_factory, mock_db_service, mock_response_parser
    ):
        """查詢服務實例"""
        return QueryApplicationService(
            mcp_client_factory=mock_mcp_client_factory,
            db_service=mock_db_service,
            response_parser=mock_response_parser,
        )

    @pytest.mark.asyncio
    async def test_execute_sql_query_success(
        self, query_service, mock_mcp_client_factory, mock_response_parser
    ):
        """測試成功執行 SQL 查詢"""
        # 設置模擬
        mock_client = await mock_mcp_client_factory()
        mock_client.call_tool.return_value = {"status": "success", "data": "raw_data"}
        mock_response_parser.parse_query_result.return_value = [
            {"id": 1, "name": "test"}
        ]
        query_service._initialized = True

        # 執行
        result = await query_service.execute_sql_query(
            query="SELECT * FROM test", user_id="test_user"
        )

        # 驗證
        assert result["success"] is True
        assert result["data"] == [{"id": 1, "name": "test"}]
        assert result["row_count"] == 1
        assert result["cached"] is False
        assert "execution_time" in result

        # 驗證統計更新
        assert query_service._query_stats["total_queries"] == 1
        assert len(query_service._query_history) == 1

    @pytest.mark.asyncio
    async def test_execute_sql_query_with_cache(self, query_service):
        """測試使用快取的查詢"""
        query_service._initialized = True

        # 預設快取結果
        cache_key = query_service._generate_cache_key("SELECT * FROM test")
        cached_result = {
            "success": True,
            "data": [{"id": 1, "name": "cached"}],
            "cached": True,
        }
        query_service._query_cache[cache_key] = {
            "data": cached_result,
            "cached_at": datetime.now().isoformat(),
        }

        # 執行
        result = await query_service.execute_sql_query(
            query="SELECT * FROM test", user_id="test_user", use_cache=True
        )

        # 驗證返回快取結果
        assert result == cached_result
        assert query_service._query_stats["cached_queries"] == 1

    @pytest.mark.asyncio
    async def test_execute_sql_query_expired_cache(
        self, query_service, mock_mcp_client_factory, mock_response_parser
    ):
        """測試過期快取的處理"""
        # 設置過期快取
        cache_key = query_service._generate_cache_key("SELECT * FROM test")
        expired_time = datetime.now() - timedelta(seconds=400)  # 超過5分鐘TTL
        query_service._query_cache[cache_key] = {
            "data": {"old": "data"},
            "cached_at": expired_time.isoformat(),
        }

        # 設置模擬
        mock_client = await mock_mcp_client_factory()
        mock_client.call_tool.return_value = {"status": "success"}
        mock_response_parser.parse_query_result.return_value = [
            {"id": 1, "name": "fresh"}
        ]
        query_service._initialized = True

        # 執行
        result = await query_service.execute_sql_query(
            query="SELECT * FROM test", user_id="test_user"
        )

        # 驗證執行新查詢而非使用過期快取
        assert result["data"] == [{"id": 1, "name": "fresh"}]
        assert result["cached"] is False

    @pytest.mark.asyncio
    async def test_execute_sql_query_error(
        self, query_service, mock_mcp_client_factory
    ):
        """測試查詢執行錯誤"""
        # 設置模擬拋出異常
        mock_client = await mock_mcp_client_factory()
        mock_client.call_tool.side_effect = Exception("Database error")
        query_service._initialized = True

        # 執行並預期拋出異常
        with pytest.raises(DatabaseQueryException):
            await query_service.execute_sql_query(
                query="SELECT * FROM test", user_id="test_user"
            )

        # 驗證錯誤統計
        assert query_service._query_stats["failed_queries"] == 1
        assert len(query_service._query_history) == 1
        assert not query_service._query_history[0]["success"]

    def test_validate_query_valid(self, query_service):
        """測試有效查詢驗證"""
        # 這些查詢應該通過驗證
        valid_queries = [
            "SELECT * FROM machines",
            "select id, name from users",
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'machines'",
            "EXPLAIN SELECT * FROM test",
        ]

        for query in valid_queries:
            query_service._validate_query(query)  # 不應拋出異常

    def test_validate_query_invalid(self, query_service):
        """測試無效查詢驗證"""
        # 測試空查詢
        with pytest.raises(ValidationException):
            query_service._validate_query("")

        # 測試禁止的操作
        forbidden_queries = [
            "DROP TABLE machines",
            "DELETE FROM users",
            "UPDATE machines SET status = 'off'",
            "INSERT INTO logs VALUES (1, 'test')",
            "ALTER TABLE machines ADD COLUMN test",
            "CREATE TABLE test (id int)",
        ]

        for query in forbidden_queries:
            with pytest.raises(ValidationException):
                query_service._validate_query(query)

        # 測試過長查詢
        long_query = "SELECT * FROM test WHERE " + "a = 1 AND " * 1000
        with pytest.raises(ValidationException):
            query_service._validate_query(long_query)

    def test_generate_cache_key(self, query_service):
        """測試快取鍵生成"""
        # 相同查詢應該產生相同鍵
        query1 = "SELECT * FROM machines"
        query2 = "select   *   from   machines"  # 不同空白

        key1 = query_service._generate_cache_key(query1)
        key2 = query_service._generate_cache_key(query2)

        assert key1 == key2
        assert len(key1) == 32  # MD5 hash length

    def test_is_cache_expired(self, query_service):
        """測試快取過期檢查"""
        # 新快取項目
        fresh_cache = {"cached_at": datetime.now().isoformat()}
        assert not query_service._is_cache_expired(fresh_cache)

        # 過期快取項目
        expired_cache = {
            "cached_at": (datetime.now() - timedelta(seconds=400)).isoformat()
        }
        assert query_service._is_cache_expired(expired_cache)

    def test_should_cache_result(self, query_service):
        """測試快取決策"""
        # 成功的小查詢應該被快取
        good_result = {"success": True, "execution_time": 0.5, "row_count": 100}
        assert query_service._should_cache_result(good_result)

        # 失敗的查詢不應該被快取
        failed_result = {"success": False, "execution_time": 0.5, "row_count": 0}
        assert not query_service._should_cache_result(failed_result)

        # 執行時間過長的查詢不應該被快取
        slow_result = {"success": True, "execution_time": 6.0, "row_count": 100}
        assert not query_service._should_cache_result(slow_result)

        # 結果過大的查詢不應該被快取
        large_result = {"success": True, "execution_time": 0.5, "row_count": 2000}
        assert not query_service._should_cache_result(large_result)

    def test_cache_result(self, query_service):
        """測試結果快取"""
        result = {"success": True, "data": [{"id": 1}], "execution_time": 0.5}

        cache_key = "test_key"
        query_service._cache_result(cache_key, result)

        assert cache_key in query_service._query_cache
        cached_item = query_service._query_cache[cache_key]
        assert cached_item["data"] == result
        assert "cached_at" in cached_item

    def test_cache_size_limit(self, query_service):
        """測試快取大小限制"""
        # 填滿快取
        for i in range(101):  # 超過100的限制
            query_service._cache_result(f"key_{i}", {"data": f"result_{i}"})

        # 驗證快取大小限制
        assert len(query_service._query_cache) == 100

    def test_cleanup_expired_cache(self, query_service):
        """測試過期快取清理"""
        # 添加新鮮和過期的快取項目
        fresh_time = datetime.now().isoformat()
        expired_time = (datetime.now() - timedelta(seconds=400)).isoformat()

        query_service._query_cache["fresh"] = {
            "data": {"fresh": True},
            "cached_at": fresh_time,
        }
        query_service._query_cache["expired"] = {
            "data": {"expired": True},
            "cached_at": expired_time,
        }

        # 清理過期快取
        query_service._cleanup_expired_cache()

        # 驗證只有新鮮的快取保留
        assert "fresh" in query_service._query_cache
        assert "expired" not in query_service._query_cache

    def test_update_query_stats(self, query_service):
        """測試查詢統計更新"""
        # 成功的快速查詢
        query_service._update_query_stats(0.5, success=True)
        assert query_service._query_stats["total_queries"] == 1
        assert query_service._query_stats["failed_queries"] == 0
        assert query_service._query_stats["slow_queries"] == 0
        assert query_service._query_stats["avg_execution_time"] == 0.5

        # 失敗的慢查詢
        query_service._update_query_stats(1.5, success=False)
        assert query_service._query_stats["total_queries"] == 2
        assert query_service._query_stats["failed_queries"] == 1
        assert query_service._query_stats["slow_queries"] == 1
        assert (
            query_service._query_stats["avg_execution_time"] == 1.0
        )  # (0.5 + 1.5) / 2

    def test_add_to_history(self, query_service):
        """測試查詢歷史記錄"""
        result = {"success": True, "row_count": 5}

        query_service._add_to_history(
            query="SELECT * FROM test",
            user_id="test_user",
            result=result,
            execution_time=0.5,
        )

        assert len(query_service._query_history) == 1
        history_entry = query_service._query_history[0]
        assert history_entry["user_id"] == "test_user"
        assert history_entry["query"] == "SELECT * FROM test"
        assert history_entry["success"] is True
        assert history_entry["execution_time"] == 0.5
        assert history_entry["row_count"] == 5

    def test_history_size_limit(self, query_service):
        """測試歷史大小限制"""
        # 添加超過限制的歷史記錄
        for i in range(105):  # 超過100的限制
            query_service._add_to_history(
                query=f"SELECT {i}",
                user_id="test_user",
                result={"success": True, "row_count": 1},
                execution_time=0.1,
            )

        # 驗證歷史大小限制
        assert len(query_service._query_history) == 100

        # 驗證最舊的記錄被移除
        assert "SELECT 0" not in query_service._query_history[0]["query"]
        assert "SELECT 104" in query_service._query_history[-1]["query"]

    @pytest.mark.asyncio
    async def test_get_table_info_specific_table(self, query_service):
        """測試獲取特定資料表資訊"""
        with patch.object(query_service, "execute_sql_query") as mock_execute:
            # 設置模擬回傳值
            mock_execute.side_effect = [
                {  # schema result
                    "data": [
                        {
                            "cid": 0,
                            "name": "id",
                            "type": "INTEGER",
                            "notnull": 1,
                            "dflt_value": None,
                            "pk": 1,
                        },
                        {
                            "cid": 1,
                            "name": "name",
                            "type": "TEXT",
                            "notnull": 1,
                            "dflt_value": None,
                            "pk": 0,
                        },
                    ]
                },
                {"data": [{"count": 10}]},  # count result
            ]

            result = await query_service.get_table_info("machines")

            assert result["success"] is True
            assert result["table_name"] == "machines"
            assert result["row_count"] == 10
            assert len(result["schema"]) == 2

            # 驗證正確的查詢被調用
            assert mock_execute.call_count == 2
            calls = mock_execute.call_args_list
            assert "FROM information_schema.columns" in calls[0][0][0]  # 第一個位置參數
            assert (
                "SELECT COUNT(*) as count FROM machines" in calls[1][0][0]
            )  # 第一個位置參數

    @pytest.mark.asyncio
    async def test_get_table_info_all_tables(self, query_service):
        """測試獲取所有資料表列表"""
        with patch.object(query_service, "execute_sql_query") as mock_execute:
            mock_execute.return_value = {
                "data": [
                    {"name": "machines"},
                    {"name": "departments"},
                    {"name": "logs"},
                ]
            }

            result = await query_service.get_table_info()

            assert result["success"] is True
            assert result["tables"] == ["machines", "departments", "logs"]
            assert result["table_count"] == 3

            # 驗證正確的查詢被調用
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args[0][0]  # 第一個位置參數
            # PostgreSQL 查詢表名使用 information_schema.tables
            assert "FROM information_schema.tables" in call_args
            assert "table_schema = 'public'" in call_args

    def test_get_query_statistics(self, query_service):
        """測試獲取查詢統計"""
        # 設置一些統計數據
        query_service._query_stats = {
            "total_queries": 100,
            "cached_queries": 20,
            "failed_queries": 5,
            "avg_execution_time": 0.8,
            "slow_queries": 10,
        }
        query_service._query_cache = {"key1": {}, "key2": {}}
        query_service._query_history = [{}] * 15

        stats = query_service.get_query_statistics()

        assert stats["total_queries"] == 100
        assert stats["cached_queries"] == 20
        assert stats["failed_queries"] == 5
        assert stats["cache_hit_rate"] == 20.0  # 20/100 * 100
        assert stats["success_rate"] == 95.0  # (100-5)/100 * 100
        assert stats["cached_results"] == 2
        assert stats["history_size"] == 15

    def test_get_recent_queries(self, query_service):
        """測試獲取最近查詢"""
        # 添加一些歷史記錄
        for i in range(20):
            query_service._query_history.append({"query": f"SELECT {i}"})

        # 測試限制數量
        recent = query_service.get_recent_queries(5)
        assert len(recent) == 5
        assert recent[-1]["query"] == "SELECT 19"  # 最新的

        # 測試獲取全部
        all_queries = query_service.get_recent_queries(0)
        assert len(all_queries) == 20

    def test_clear_cache(self, query_service):
        """測試清除快取"""
        # 添加一些快取項目
        query_service._query_cache = {
            "key1": {"data": "value1"},
            "key2": {"data": "value2"},
            "key3": {"data": "value3"},
        }

        cleared_count = query_service.clear_cache()

        assert cleared_count == 3
        assert len(query_service._query_cache) == 0

    @pytest.mark.asyncio
    async def test_health_checks(self, query_service, mock_mcp_client_factory):
        """測試健康檢查"""
        # 設置 MCP 客戶端成功回應
        mock_client = await mock_mcp_client_factory()
        mock_client.call_tool.return_value = {"result": "1"}

        # 設置一些統計數據
        query_service._query_stats["total_queries"] = 50
        query_service._query_stats["cached_queries"] = 10

        checks = await query_service._perform_health_checks()

        assert "mcp_connection" in checks
        assert checks["mcp_connection"]["status"] == "healthy"

        assert "cache" in checks
        assert checks["cache"]["status"] == "healthy"

        assert "query_performance" in checks
        assert checks["query_performance"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_checks_mcp_error(
        self, query_service, mock_mcp_client_factory
    ):
        """測試 MCP 連接錯誤的健康檢查"""
        # 設置 MCP 客戶端拋出異常
        mock_client = await mock_mcp_client_factory()
        mock_client.call_tool.side_effect = Exception("Connection failed")

        checks = await query_service._perform_health_checks()

        assert checks["mcp_connection"]["status"] == "unhealthy"
        assert "error" in checks["mcp_connection"]

    @pytest.mark.asyncio
    async def test_shutdown_service(self, query_service):
        """測試服務關閉"""
        # 設置一些數據
        query_service._query_cache = {"key": "value"}
        query_service._query_history = [{"query": "test"}]
        query_service._query_stats["total_queries"] = 100

        await query_service._shutdown_service()

        # 驗證清理
        assert len(query_service._query_cache) == 0
        assert len(query_service._query_history) == 0
        assert query_service._query_stats["total_queries"] == 0


class TestQueryServiceIntegration:
    """查詢服務集成測試"""

    @pytest.mark.asyncio
    async def test_full_query_lifecycle(self):
        """測試完整的查詢生命週期"""
        # 創建服務
        mcp_factory = AsyncMock()
        mock_client = Mock()
        mock_client.call_tool = AsyncMock(return_value={"data": "raw"})
        mcp_factory.return_value = mock_client

        db_service = Mock()
        response_parser = Mock()
        response_parser.parse_query_result.return_value = [{"id": 1, "name": "test"}]

        service = QueryApplicationService(
            mcp_client_factory=mcp_factory,
            db_service=db_service,
            response_parser=response_parser,
        )

        # 初始化
        await service.initialize()
        assert service.is_initialized

        # 執行查詢
        result = await service.execute_sql_query(
            query="SELECT * FROM machines", user_id="test_user"
        )

        assert result["success"] is True
        assert result["data"] == [{"id": 1, "name": "test"}]

        # 驗證統計
        stats = service.get_query_statistics()
        assert stats["total_queries"] == 1

        # 獲取歷史
        history = service.get_recent_queries(1)
        assert len(history) == 1

        # 關閉服務
        await service.shutdown()
        assert not service.is_initialized
