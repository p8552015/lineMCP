"""
應用程式啟動健康檢查模組
在應用程式啟動時自動驗證資料庫Schema和關鍵功能
"""

import asyncio
import logging
import sys
from typing import Any

try:
    # 嘗試相對導入（在應用程式中運行時）
    from .database_health_check import DatabaseHealthChecker
except ImportError:
    # 回退到絕對導入（直接運行腳本時）
    from database_health_check import DatabaseHealthChecker

logger = logging.getLogger(__name__)


class StartupHealthChecker:
    """啟動時健康檢查器"""

    def __init__(self, database_url: str, strict_mode: bool = True):
        self.database_url = database_url
        self.strict_mode = strict_mode  # 嚴格模式下，任何問題都會阻止啟動
        self.health_checker = DatabaseHealthChecker(database_url)

    async def verify_startup_requirements(self) -> bool:
        """驗證啟動需求，返回是否可以安全啟動"""
        logger.info("🚀 開始應用程式啟動健康檢查...")

        try:
            # 執行健康檢查
            health_report = await self.health_checker.comprehensive_health_check()
            verification_report = (
                await self.health_checker.verify_critical_functionality()
            )

            # 記錄檢查結果
            self._log_health_report(health_report)
            self._log_verification_report(verification_report)

            # 判斷是否可以啟動
            can_start = self._evaluate_startup_safety(
                health_report, verification_report
            )

            if can_start:
                logger.info("✅ 啟動健康檢查通過，應用程式可以安全啟動")
            else:
                logger.error("❌ 啟動健康檢查失敗，應用程式啟動被阻止")

            return can_start

        except Exception as e:
            logger.error(f"❌ 啟動健康檢查過程中發生錯誤: {e}")
            return False

    def _log_health_report(self, health_report: dict[str, Any]):
        """記錄健康檢查報告"""
        status = health_report["overall_status"]

        if status == "healthy":
            logger.info("✅ 資料庫健康狀態: 良好")
        elif status == "warning":
            logger.warning("⚠️ 資料庫健康狀態: 警告")
        else:
            logger.error("❌ 資料庫健康狀態: 嚴重問題")

        # 記錄連接狀態
        if health_report.get("connection", {}).get("status") == "healthy":
            logger.info("✅ 資料庫連接: 正常")
        else:
            logger.error("❌ 資料庫連接: 失敗")

        # 記錄資料表狀態
        tables_info = health_report.get("tables", {})
        if tables_info.get("status") == "critical":
            missing_tables = tables_info.get("details", {}).get("missing_tables", [])
            if missing_tables:
                logger.error(f"❌ 缺失關鍵資料表: {', '.join(missing_tables)}")

        # 記錄功能狀態
        functionality_info = health_report.get("functionality", {})
        if functionality_info.get("status") != "healthy":
            logger.warning(
                f"⚠️ 功能檢查: {functionality_info.get('message', '未知問題')}"
            )

        # 記錄錯誤
        if "error" in health_report:
            logger.error(f"❌ 錯誤: {health_report['error']}")

    def _log_verification_report(self, verification_report: dict[str, Any]):
        """記錄功能驗證報告"""
        overall_status = verification_report["overall_status"]

        if overall_status == "passed":
            logger.info("✅ 功能驗證: 全部通過")
        else:
            logger.error("❌ 功能驗證: 存在失敗項目")

        # 記錄各項測試結果
        for test_name, test_result in verification_report["tests"].items():
            if test_result["status"] == "passed":
                logger.info(f"✅ {test_name}: {test_result['message']}")
            else:
                logger.error(f"❌ {test_name}: {test_result['message']}")

    def _evaluate_startup_safety(
        self, health_report: dict[str, Any], verification_report: dict[str, Any]
    ) -> bool:
        """評估是否可以安全啟動"""
        # 連接失敗絕對不能啟動
        if health_report.get("connection", {}).get("status") != "healthy":
            logger.error("🚫 資料庫連接失敗，無法啟動應用程式")
            return False

        # 關鍵資料表缺失不能啟動
        critical_tables = ["machines", "machine_faults"]
        tables_info = health_report.get("tables", {})
        missing_tables = tables_info.get("details", {}).get("missing_tables", [])
        missing_critical = [
            table for table in missing_tables if table in critical_tables
        ]

        if missing_critical:
            logger.error(f"🚫 關鍵資料表缺失 {missing_critical}，無法啟動應用程式")
            return False

        # 在嚴格模式下，任何功能驗證失敗都不能啟動
        if self.strict_mode and verification_report["overall_status"] != "passed":
            logger.error("🚫 嚴格模式下功能驗證失敗，無法啟動應用程式")
            return False

        # 檢查關鍵功能
        critical_tests = ["machine_query", "fault_query"]
        for test_name in critical_tests:
            if test_name in verification_report["tests"]:
                if verification_report["tests"][test_name]["status"] != "passed":
                    logger.error(f"🚫 關鍵功能 {test_name} 驗證失敗，無法啟動應用程式")
                    return False

        # 如果只是警告級別的問題，可以啟動但需要記錄
        if health_report["overall_status"] == "warning":
            logger.warning("⚠️ 存在非關鍵問題，但應用程式可以啟動")

        return True


async def verify_database_schema() -> None:
    """
    驗證資料庫Schema是否符合應用程式期望
    這個函數可以在 FastAPI 的 startup 事件中調用
    """
    database_url = "postgresql://admin:admin@localhost:5432/mydb"
    checker = StartupHealthChecker(database_url, strict_mode=False)  # 非嚴格模式

    max_retries = 3
    retry_delay = 2  # 秒

    for attempt in range(max_retries):
        try:
            logger.info(f"🔍 執行資料庫健康檢查 (嘗試 {attempt + 1}/{max_retries})")
            can_start = await checker.verify_startup_requirements()

            if can_start:
                logger.info("✅ 資料庫健康檢查通過，應用程式可以啟動")
                return
            else:
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ 健康檢查失敗，{retry_delay} 秒後重試...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("❌ 所有重試都失敗，但應用程式將以降級模式啟動")
                    logger.warning("⚠️ 某些功能可能無法正常工作")
                    return  # 允許應用程式啟動，但發出警告

        except Exception as e:
            logger.error(
                f"❌ 健康檢查過程中發生錯誤 (嘗試 {attempt + 1}/{max_retries}): {e}"
            )
            if attempt < max_retries - 1:
                logger.info(f"🔄 {retry_delay} 秒後重試...")
                await asyncio.sleep(retry_delay)
            else:
                logger.warning("⚠️ 健康檢查完全失敗，應用程式將以最小功能模式啟動")
                logger.warning("⚠️ 資料庫相關功能可能無法使用")
                return  # 即使健康檢查失敗也允許啟動


async def verify_database_schema_strict() -> None:
    """
    嚴格模式的資料庫Schema驗證
    任何問題都會阻止應用程式啟動
    """
    database_url = "postgresql://admin:admin@localhost:5432/mydb"
    checker = StartupHealthChecker(database_url, strict_mode=True)

    can_start = await checker.verify_startup_requirements()

    if not can_start:
        logger.fatal("❌ 嚴格模式啟動檢查失敗，應用程式將退出")
        sys.exit(1)


if __name__ == "__main__":
    # 直接執行啟動檢查
    logging.basicConfig(level=logging.INFO)
    asyncio.run(verify_database_schema())
