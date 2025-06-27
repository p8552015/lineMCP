"""
資料庫健康檢查模組
用於驗證資料庫Schema是否符合應用程式期望
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

import asyncpg

# 移除 SQLAlchemy 依賴，使用純 asyncpg

logger = logging.getLogger(__name__)


class DatabaseHealthChecker:
    """資料庫健康檢查器"""

    def __init__(self, database_url: str = None):
        # 如果沒有提供 database_url，使用預設值
        self.database_url = (
            database_url or "postgresql://admin:admin@localhost:5432/mydb"
        )

        # 使用純 asyncpg，不需要 SQLAlchemy engine
        logger.info(
            f"DatabaseHealthChecker 初始化完成，使用資料庫: {self.database_url}"
        )

        self.required_tables = {
            "machines": {
                "required_columns": [
                    "id",
                    "name",
                    "status",
                    "temperature",
                    "utilization_rate",
                ],
                "primary_key": "id",
            },
            "machine_faults": {
                "required_columns": [
                    "fault_id",
                    "machine_id",
                    "fault_type",
                    "severity",
                    "fault_date",
                ],
                "primary_key": "fault_id",
                "foreign_keys": [("machine_id", "machines", "id")],
            },
            "machine_utilization": {
                "required_columns": ["id", "machine_id", "utilization_rate"],
                "primary_key": "id",
                "foreign_keys": [("machine_id", "machines", "id")],
            },
            "employees": {
                "required_columns": ["id", "name", "department"],
                "primary_key": "id",
            },
            "products": {
                "required_columns": ["id", "name", "category", "price"],
                "primary_key": "id",
            },
            "orders": {
                "required_columns": ["id", "customer_name", "quantity", "order_date"],
                "primary_key": "id",
            },
        }

    async def check_connection(self) -> dict[str, Any]:
        """檢查資料庫連接（新接口）"""
        max_retries = 3
        retry_delay = 1  # 秒

        for attempt in range(max_retries):
            try:
                conn = await asyncpg.connect(self.database_url)
                await conn.fetchval("SELECT 1")
                await conn.close()

                if attempt > 0:
                    logger.info(f"✅ 資料庫連接在第 {attempt + 1} 次嘗試後成功")

                return {
                    "status": "healthy",
                    "message": "資料庫連接正常",
                    "timestamp": datetime.now().isoformat(),
                    "attempts": attempt + 1,
                }
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"⚠️ 資料庫連接失敗 (嘗試 {attempt + 1}/{max_retries}): {e}"
                    )
                    logger.info(f"🔄 {retry_delay} 秒後重試...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"❌ 資料庫連接在 {max_retries} 次嘗試後仍然失敗: {e}")
                    return {
                        "status": "unhealthy",
                        "message": f"資料庫連接失敗 (已重試 {max_retries} 次): {str(e)}",
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                        "attempts": max_retries,
                    }

    async def comprehensive_health_check(self) -> dict[str, Any]:
        """執行完整的資料庫健康檢查（新接口）"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "unknown",
            "connection": {},
            "tables": {},
            "functionality": {},
        }

        try:
            # 檢查連接
            connection_status = await self.check_connection()
            result["connection"] = connection_status

            if connection_status["status"] != "healthy":
                result["overall_status"] = "critical"
                return result

            # 檢查資料表
            tables_result = await self._check_tables_new()
            result["tables"] = tables_result

            # 檢查功能
            functionality_result = await self._check_functionality()
            result["functionality"] = functionality_result

            # 計算整體狀態
            if (
                connection_status["status"] == "healthy"
                and tables_result["status"] in ["healthy", "warning"]
                and functionality_result["status"] in ["healthy", "warning"]
            ):

                if (
                    tables_result["status"] == "warning"
                    or functionality_result["status"] == "warning"
                ):
                    result["overall_status"] = "warning"
                else:
                    result["overall_status"] = "healthy"
            else:
                result["overall_status"] = "critical"

        except Exception as e:
            logger.error(f"完整健康檢查失敗: {e}")
            result["overall_status"] = "critical"
            result["error"] = str(e)

        return result

    async def _check_tables_new(self) -> dict[str, Any]:
        """檢查資料表（新格式）"""
        try:
            conn = await asyncpg.connect(self.database_url)

            # 獲取所有資料表
            existing_tables = await conn.fetch(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """
            )
            existing_table_names = {row["table_name"] for row in existing_tables}

            await conn.close()

            # 檢查必需的資料表
            required_table_names = set(self.required_tables.keys())
            missing_tables = required_table_names - existing_table_names

            if missing_tables:
                return {
                    "status": "critical",
                    "message": f"缺少必需的資料表: {list(missing_tables)}",
                    "details": {
                        "found_tables": list(existing_table_names),
                        "missing_tables": list(missing_tables),
                        "required_tables": list(required_table_names),
                    },
                }
            else:
                return {
                    "status": "healthy",
                    "message": "所有必需的資料表都存在",
                    "details": {
                        "found_tables": list(existing_table_names),
                        "missing_tables": [],
                        "required_tables": list(required_table_names),
                    },
                }

        except Exception as e:
            return {
                "status": "critical",
                "message": f"檢查資料表時發生錯誤: {str(e)}",
                "error": str(e),
            }

    async def _check_functionality(self) -> dict[str, Any]:
        """檢查功能（新格式）"""
        try:
            conn = await asyncpg.connect(self.database_url)

            test_results = {}

            # 測試機台查詢
            try:
                result = await conn.fetch("SELECT id, name FROM machines LIMIT 1")
                test_results["machine_query"] = {
                    "status": "passed",
                    "message": f"機台查詢成功，找到 {len(result)} 筆記錄",
                }
            except Exception as e:
                test_results["machine_query"] = {
                    "status": "failed",
                    "message": f"機台查詢失敗: {str(e)}",
                }

            # 測試故障查詢
            try:
                result = await conn.fetch(
                    "SELECT fault_id, machine_id FROM machine_faults LIMIT 1"
                )
                test_results["fault_query"] = {
                    "status": "passed",
                    "message": f"故障查詢成功，找到 {len(result)} 筆記錄",
                }
            except Exception as e:
                test_results["fault_query"] = {
                    "status": "failed",
                    "message": f"故障查詢失敗: {str(e)}",
                }

            await conn.close()

            # 計算整體功能狀態
            passed_tests = sum(
                1 for test in test_results.values() if test["status"] == "passed"
            )
            total_tests = len(test_results)

            if passed_tests == total_tests:
                status = "healthy"
                message = f"所有功能測試通過 ({passed_tests}/{total_tests})"
            elif passed_tests > 0:
                status = "warning"
                message = f"部分功能測試通過 ({passed_tests}/{total_tests})"
            else:
                status = "critical"
                message = f"所有功能測試失敗 (0/{total_tests})"

            return {
                "status": status,
                "message": message,
                "details": {
                    "test_results": test_results,
                    "passed_count": passed_tests,
                    "total_count": total_tests,
                },
            }

        except Exception as e:
            return {
                "status": "critical",
                "message": f"功能檢查時發生錯誤: {str(e)}",
                "error": str(e),
            }

    async def verify_critical_functionality(self) -> dict[str, Any]:
        """驗證關鍵功能是否正常運作（舊接口兼容性）"""
        verification_result = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "overall_status": "unknown",
        }

        try:
            conn = await asyncpg.connect(self.database_url)

            # 測試 1: 機台查詢
            try:
                result = await conn.fetch(
                    "SELECT id, name, status FROM machines LIMIT 5"
                )
                verification_result["tests"]["machine_query"] = {
                    "status": "passed",
                    "message": f"成功查詢到 {len(result)} 台機台",
                    "data_count": len(result),
                }
            except Exception as e:
                verification_result["tests"]["machine_query"] = {
                    "status": "failed",
                    "message": f"機台查詢失敗: {e}",
                    "error": str(e),
                }

            # 測試 2: 故障記錄查詢
            try:
                result = await conn.fetch(
                    "SELECT fault_id, machine_id, fault_type, severity FROM machine_faults LIMIT 5"
                )
                verification_result["tests"]["fault_query"] = {
                    "status": "passed",
                    "message": f"成功查詢到 {len(result)} 筆故障記錄",
                    "data_count": len(result),
                }
            except Exception as e:
                verification_result["tests"]["fault_query"] = {
                    "status": "failed",
                    "message": f"故障記錄查詢失敗: {e}",
                    "error": str(e),
                }

            await conn.close()

            # 計算整體狀態
            all_passed = all(
                test_result["status"] == "passed"
                for test_result in verification_result["tests"].values()
            )
            verification_result["overall_status"] = "passed" if all_passed else "failed"

        except Exception as e:
            logger.error(f"功能驗證失敗: {e}")
            verification_result["overall_status"] = "error"
            verification_result["error"] = str(e)

        return verification_result


async def run_health_check(
    database_url: str = "postgresql://admin:admin@localhost:5432/mydb",
) -> dict[str, Any]:
    """執行完整的資料庫健康檢查"""
    checker = DatabaseHealthChecker(database_url)

    print("🔍 開始資料庫健康檢查...")
    health_report = await checker.comprehensive_health_check()

    print("🧪 開始功能驗證測試...")
    verification_report = await checker.verify_critical_functionality()

    return {
        "health_check": health_report,
        "functionality_verification": verification_report,
    }


if __name__ == "__main__":
    # 直接執行健康檢查
    result = asyncio.run(run_health_check())

    print("\n" + "=" * 50)
    print("資料庫健康檢查報告")
    print("=" * 50)

    health = result["health_check"]
    print(f"整體狀態: {health['overall_status']}")
    print(f"連接狀態: {health['connection']['status']}")

    if health["tables"]["status"] != "healthy":
        print(f"缺失資料表: {health['tables']['message']}")

    if health["tables"]["details"]:
        print(f"缺失資料表詳細資訊: {health['tables']['details']}")

    print("\n" + "=" * 50)
    print("功能驗證報告")
    print("=" * 50)

    verification = result["functionality_verification"]
    print(f"整體狀態: {verification['overall_status']}")

    for test_name, test_result in verification["tests"].items():
        status_icon = "✅" if test_result["status"] == "passed" else "❌"
        print(f"{status_icon} {test_name}: {test_result['message']}")
