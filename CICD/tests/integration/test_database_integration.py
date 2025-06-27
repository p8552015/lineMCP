"""
資料庫整合測試
測試與 PostgreSQL 資料庫的實際互動，包括連接、Schema驗證、查詢功能等
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta

import asyncpg
import pytest

# 添加 src 到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from src.utils.database_health_check import DatabaseHealthChecker


@pytest.fixture
def database_url():
    """資料庫連接字串"""
    return "postgresql://admin:admin@localhost:5432/mydb"


@pytest.fixture
async def db_connection(database_url):
    """建立資料庫連接"""
    try:
        conn = await asyncpg.connect(database_url)
        yield conn
        await conn.close()
    except Exception as e:
        pytest.skip(f"無法連接到資料庫: {e}")


@pytest.fixture
async def health_checker(database_url):
    """建立資料庫健康檢查器"""
    return DatabaseHealthChecker(database_url)


class TestDatabaseConnection:
    """資料庫連接測試"""

    @pytest.mark.asyncio
    async def test_database_connection_basic(self, database_url):
        """測試基本資料庫連接"""
        try:
            conn = await asyncpg.connect(database_url)
            result = await conn.fetchval("SELECT 1")
            assert result == 1
            await conn.close()
        except Exception as e:
            pytest.fail(f"資料庫連接失敗: {e}")

    @pytest.mark.asyncio
    async def test_database_connection_with_timeout(self, database_url):
        """測試帶超時的資料庫連接"""
        try:
            conn = await asyncio.wait_for(asyncpg.connect(database_url), timeout=10.0)
            result = await conn.fetchval("SELECT version()")
            assert "PostgreSQL" in result
            await conn.close()
        except TimeoutError:
            pytest.fail("資料庫連接超時")
        except Exception as e:
            pytest.fail(f"資料庫連接失敗: {e}")

    @pytest.mark.asyncio
    async def test_database_connection_pool(self, database_url):
        """測試資料庫連接池"""
        try:
            pool = await asyncpg.create_pool(
                database_url, min_size=1, max_size=5, command_timeout=60
            )

            async with pool.acquire() as conn:
                result = await conn.fetchval("SELECT current_database()")
                assert result == "mydb"

            await pool.close()
        except Exception as e:
            pytest.fail(f"資料庫連接池測試失敗: {e}")


class TestDatabaseSchema:
    """資料庫Schema測試"""

    @pytest.mark.asyncio
    async def test_required_tables_exist(self, db_connection):
        """測試必需的資料表是否存在"""
        required_tables = [
            "machines",
            "machine_faults",
            "machine_utilization",
            "employees",
            "products",
            "orders",
        ]

        for table in required_tables:
            exists = await db_connection.fetchval(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = $1
                )
            """,
                table,
            )
            assert exists, f"必需的資料表 '{table}' 不存在"

    @pytest.mark.asyncio
    async def test_machines_table_structure(self, db_connection):
        """測試 machines 資料表結構"""
        columns = await db_connection.fetch(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'machines' AND table_schema = 'public'
            ORDER BY ordinal_position
        """
        )

        column_names = [col["column_name"] for col in columns]
        required_columns = ["id", "name", "status", "temperature", "utilization_rate"]

        for required_col in required_columns:
            assert (
                required_col in column_names
            ), f"machines 表缺少必需欄位: {required_col}"

    @pytest.mark.asyncio
    async def test_machine_faults_table_structure(self, db_connection):
        """測試 machine_faults 資料表結構"""
        columns = await db_connection.fetch(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'machine_faults' AND table_schema = 'public'
            ORDER BY ordinal_position
        """
        )

        column_names = [col["column_name"] for col in columns]
        required_columns = [
            "fault_id",
            "machine_id",
            "fault_type",
            "severity",
            "fault_date",
        ]

        for required_col in required_columns:
            assert (
                required_col in column_names
            ), f"machine_faults 表缺少必需欄位: {required_col}"

    @pytest.mark.asyncio
    async def test_foreign_key_constraints(self, db_connection):
        """測試外鍵約束"""
        # 檢查 machine_faults.machine_id -> machines.id 外鍵
        fk_exists = await db_connection.fetchval(
            """
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu 
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu 
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_name = 'machine_faults'
                    AND kcu.column_name = 'machine_id'
                    AND ccu.table_name = 'machines'
                    AND ccu.column_name = 'id'
            )
        """
        )

        assert fk_exists, "machine_faults.machine_id 外鍵約束不存在"


class TestDatabaseQueries:
    """資料庫查詢測試"""

    @pytest.mark.asyncio
    async def test_machines_basic_query(self, db_connection):
        """測試機台基本查詢"""
        machines = await db_connection.fetch(
            """
            SELECT id, name, status, temperature, utilization_rate 
            FROM machines 
            LIMIT 5
        """
        )

        assert len(machines) > 0, "機台資料表應該包含資料"

        for machine in machines:
            assert machine["id"] is not None
            assert machine["name"] is not None
            assert machine["status"] in [
                "運行",
                "停機",
                "維修",
                "故障",
                "運行中",
                "維護中",
                "待機中",
                "running",
            ]

    @pytest.mark.asyncio
    async def test_machine_faults_query(self, db_connection):
        """測試機台故障查詢"""
        faults = await db_connection.fetch(
            """
            SELECT fault_id, machine_id, fault_type, severity, fault_date 
            FROM machine_faults 
            ORDER BY fault_date DESC 
            LIMIT 10
        """
        )

        assert len(faults) > 0, "故障資料表應該包含資料"

        for fault in faults:
            assert fault["fault_id"] is not None
            assert fault["machine_id"] is not None
            assert fault["fault_type"] is not None
            assert fault["severity"] in ["low", "medium", "high", "critical"]

    @pytest.mark.asyncio
    async def test_join_query_machines_faults(self, db_connection):
        """測試機台與故障的關聯查詢"""
        results = await db_connection.fetch(
            """
            SELECT 
                m.id as machine_id,
                m.name as machine_name,
                COUNT(mf.fault_id) as fault_count,
                MAX(mf.fault_date) as latest_fault
            FROM machines m
            LEFT JOIN machine_faults mf ON m.id = mf.machine_id
            GROUP BY m.id, m.name
            ORDER BY fault_count DESC
            LIMIT 5
        """
        )

        assert len(results) > 0, "關聯查詢應該返回結果"

        for result in results:
            assert result["machine_id"] is not None
            assert result["machine_name"] is not None
            assert result["fault_count"] >= 0

    @pytest.mark.asyncio
    async def test_utilization_query(self, db_connection):
        """測試使用率查詢"""
        utilizations = await db_connection.fetch(
            """
            SELECT 
                machine_id,
                utilization_rate,
                date
            FROM machine_utilization
            WHERE date >= $1
            ORDER BY date DESC
            LIMIT 10
        """,
            datetime.now() - timedelta(days=7),
        )

        # 即使沒有最近7天的資料，查詢也應該成功執行
        assert isinstance(utilizations, list)

        for util in utilizations:
            assert util["machine_id"] is not None
            from decimal import Decimal

            assert isinstance(util["utilization_rate"], (int, float, Decimal))
            assert 0 <= util["utilization_rate"] <= 100

    @pytest.mark.asyncio
    async def test_critical_faults_query(self, db_connection):
        """測試關鍵故障查詢"""
        critical_faults = await db_connection.fetch(
            """
            SELECT 
                mf.fault_id as fault_id,
                mf.machine_id,
                m.name as machine_name,
                mf.fault_type,
                mf.fault_date,
                mf.description
            FROM machine_faults mf
            JOIN machines m ON mf.machine_id = m.id
            WHERE mf.severity = 'critical'
                AND mf.resolved = false
            ORDER BY mf.fault_date DESC
        """
        )

        # 查詢應該成功執行，即使沒有關鍵故障
        assert isinstance(critical_faults, list)

        for fault in critical_faults:
            assert fault["fault_id"] is not None
            assert fault["machine_id"] is not None
            assert fault["machine_name"] is not None
            assert fault["fault_type"] is not None


class TestDatabaseHealthCheck:
    """資料庫健康檢查測試"""

    @pytest.mark.asyncio
    async def test_health_checker_connection(self, health_checker):
        """測試健康檢查器連接"""
        result = await health_checker.check_connection()

        assert result["status"] == "healthy"
        assert "timestamp" in result
        assert result["message"] == "資料庫連接正常"

    @pytest.mark.asyncio
    async def test_comprehensive_health_check(self, health_checker):
        """測試完整健康檢查"""
        result = await health_checker.comprehensive_health_check()

        assert result["overall_status"] in ["healthy", "warning", "critical"]
        assert "connection" in result
        assert "tables" in result
        assert "functionality" in result
        assert "timestamp" in result

        # 連接應該是健康的
        assert result["connection"]["status"] == "healthy"

        # 資料表檢查應該通過
        assert result["tables"]["status"] in ["healthy", "warning"]

        # 功能測試應該通過
        assert result["functionality"]["status"] in ["healthy", "warning"]

    @pytest.mark.asyncio
    async def test_functionality_verification(self, health_checker):
        """測試功能驗證"""
        result = await health_checker.verify_critical_functionality()

        assert result["overall_status"] in ["passed", "failed", "error"]
        assert "tests" in result
        assert "timestamp" in result

        # 檢查具體的測試項目
        tests = result["tests"]
        assert "machine_query" in tests
        assert "fault_query" in tests

        # 至少一個測試應該通過
        passed_tests = [test for test in tests.values() if test["status"] == "passed"]
        assert len(passed_tests) > 0, "至少應有一個測試通過"


class TestDatabasePerformance:
    """資料庫效能測試"""

    @pytest.mark.asyncio
    async def test_query_performance(self, db_connection):
        """測試查詢效能"""
        import time

        # 測試簡單查詢效能
        start_time = time.time()
        result = await db_connection.fetchval("SELECT COUNT(*) FROM machines")
        end_time = time.time()

        query_time = end_time - start_time
        assert query_time < 1.0, f"簡單查詢耗時過長: {query_time:.3f}秒"
        assert isinstance(result, int)

    @pytest.mark.asyncio
    async def test_complex_query_performance(self, db_connection):
        """測試複雜查詢效能"""
        import time

        # 測試複雜關聯查詢效能
        start_time = time.time()
        results = await db_connection.fetch(
            """
            SELECT 
                m.name,
                COUNT(mf.fault_id) as fault_count,
                AVG(mu.utilization_rate) as avg_utilization
            FROM machines m
            LEFT JOIN machine_faults mf ON m.id = mf.machine_id
            LEFT JOIN machine_utilization mu ON m.id = mu.machine_id
            GROUP BY m.id, m.name
            ORDER BY fault_count DESC
        """
        )
        end_time = time.time()

        query_time = end_time - start_time
        assert query_time < 5.0, f"複雜查詢耗時過長: {query_time:.3f}秒"
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_concurrent_queries(self, database_url):
        """測試並發查詢"""

        async def execute_query(query_id):
            conn = await asyncpg.connect(database_url)
            try:
                result = await conn.fetchval(f"SELECT {query_id} as query_id")
                return result
            finally:
                await conn.close()

        # 並發執行多個查詢
        tasks = [execute_query(i) for i in range(1, 6)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        for i, result in enumerate(results, 1):
            assert result == i


class TestDatabaseErrorHandling:
    """資料庫錯誤處理測試"""

    @pytest.mark.asyncio
    async def test_invalid_query_handling(self, db_connection):
        """測試無效查詢處理"""
        with pytest.raises(Exception):
            await db_connection.fetchval("SELECT * FROM non_existent_table")

    @pytest.mark.asyncio
    async def test_connection_failure_handling(self):
        """測試連接失敗處理"""
        invalid_url = "postgresql://invalid:invalid@localhost:9999/invalid"

        with pytest.raises(Exception):
            await asyncpg.connect(invalid_url)

    @pytest.mark.asyncio
    async def test_timeout_handling(self, db_connection):
        """測試查詢超時處理"""
        # 測試長時間運行的查詢（模擬）
        try:
            result = await asyncio.wait_for(
                db_connection.fetchval("SELECT pg_sleep(0.1)"), timeout=1.0
            )
            # pg_sleep 返回空值
            assert result is None
        except TimeoutError:
            pytest.fail("查詢不應該超時")


class TestDatabaseTransactions:
    """資料庫事務測試"""

    @pytest.mark.asyncio
    async def test_transaction_commit(self, db_connection):
        """測試事務提交"""
        async with db_connection.transaction():
            # 在事務中執行查詢
            result = await db_connection.fetchval("SELECT 1")
            assert result == 1

        # 事務應該成功提交

    @pytest.mark.asyncio
    async def test_transaction_rollback(self, db_connection):
        """測試事務回滾"""
        try:
            async with db_connection.transaction():
                # 執行正常操作
                await db_connection.fetchval("SELECT 1")

                # 故意引發錯誤來觸發回滾
                raise Exception("測試回滾")
        except Exception as e:
            assert str(e) == "測試回滾"

        # 確認連接仍然可用
        result = await db_connection.fetchval("SELECT 1")
        assert result == 1


if __name__ == "__main__":
    # 直接運行測試
    import subprocess
    import sys

    # 運行當前文件的測試
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )

    sys.exit(result.returncode)
