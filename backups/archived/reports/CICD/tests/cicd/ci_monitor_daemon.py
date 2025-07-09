#!/usr/bin/env python3
"""
GitHub CI 監控守護程式
持續監控 GitHub Actions 狀態，自動檢測失敗並觸發修復流程
"""

import asyncio
import json
import logging
import os
import signal
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from github_ci_validator import GitHubCIValidator


class CIMonitorDaemon:
    """GitHub CI 監控守護程式"""

    def __init__(
        self,
        token: str,
        owner: str = "p8552015",
        repo: str = "lineMCP",
        check_interval: int = 300,  # 5分鐘
        log_file: str = "ci_monitor.log",
    ):
        """
        初始化監控守護程式

        Args:
            token: GitHub Personal Access Token
            owner: Repository owner
            repo: Repository name
            check_interval: 檢查間隔（秒）
            log_file: 日誌文件路徑
        """
        self.validator = GitHubCIValidator(token, owner, repo)
        self.check_interval = check_interval
        self.log_file = log_file
        self.running = False
        self.last_run_status = {}
        self.failure_count = {}
        self.setup_logging()

        # 回調函數註冊
        self.on_failure_detected = None
        self.on_recovery_detected = None
        self.on_status_change = None

        # 監控統計
        self.stats = {
            "total_checks": 0,
            "failures_detected": 0,
            "recoveries_detected": 0,
            "start_time": None,
            "last_check_time": None,
        }

        # 設置優雅關閉
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def setup_logging(self):
        """設置日誌配置"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(self.log_file), logging.StreamHandler()],
        )
        self.logger = logging.getLogger(__name__)

    def register_callbacks(
        self,
        on_failure: Callable | None = None,
        on_recovery: Callable | None = None,
        on_status_change: Callable | None = None,
    ):
        """
        註冊回調函數

        Args:
            on_failure: 檢測到失敗時的回調
            on_recovery: 檢測到恢復時的回調
            on_status_change: 狀態變化時的回調
        """
        self.on_failure_detected = on_failure
        self.on_recovery_detected = on_recovery
        self.on_status_change = on_status_change

    async def check_ci_status(self) -> dict[str, Any]:
        """
        檢查 CI 狀態

        Returns:
            CI 狀態報告
        """
        try:
            self.logger.info("🔍 開始檢查 CI 狀態...")

            # 獲取最新的 workflow run
            run = self.validator.get_latest_workflow_run()

            if not run:
                self.logger.warning("❌ 無法獲取 workflow run")
                return {"status": "error", "message": "無法獲取 workflow run"}

            # 解析測試結果
            results = self.validator.parse_test_results(run)

            # 更新統計
            self.stats["total_checks"] += 1
            self.stats["last_check_time"] = datetime.now()

            # 分析狀態變化
            run_id = str(run["id"])
            current_status = results["conclusion"]
            previous_status = self.last_run_status.get(run_id)

            status_changed = previous_status and previous_status != current_status

            report = {
                "run_id": run_id,
                "workflow_name": "Enhanced CI",
                "status": results["status"],
                "conclusion": current_status,
                "html_url": results["html_url"],
                "created_at": results["created_at"],
                "updated_at": results["updated_at"],
                "jobs": results["jobs"],
                "summary": results["summary"],
                "status_changed": status_changed,
                "previous_status": previous_status,
                "check_time": datetime.now().isoformat(),
                "is_failure": current_status == "failure",
                "is_success": current_status == "success",
            }

            # 處理狀態變化
            if status_changed:
                await self._handle_status_change(report)

            # 處理失敗檢測
            if current_status == "failure":
                await self._handle_failure_detected(report)

            # 處理恢復檢測
            if previous_status == "failure" and current_status == "success":
                await self._handle_recovery_detected(report)

            # 更新狀態記錄
            self.last_run_status[run_id] = current_status

            # 記錄成功檢查
            self.logger.info(f"✅ CI 狀態檢查完成: {results['summary']}")

            return report

        except Exception as e:
            self.logger.error(f"❌ CI 狀態檢查失敗: {e}")
            return {"status": "error", "message": str(e)}

    async def _handle_status_change(self, report: dict[str, Any]):
        """處理狀態變化"""
        self.logger.info(
            f"🔄 CI 狀態變化: {report['previous_status']} → {report['conclusion']}"
        )

        if self.on_status_change:
            try:
                await self._safe_callback_call(self.on_status_change, report)
            except Exception as e:
                self.logger.error(f"❌ 狀態變化回調失敗: {e}")

    async def _handle_failure_detected(self, report: dict[str, Any]):
        """處理失敗檢測"""
        run_id = report["run_id"]

        # 增加失敗計數
        if run_id not in self.failure_count:
            self.failure_count[run_id] = 0
        self.failure_count[run_id] += 1

        self.stats["failures_detected"] += 1

        self.logger.error(f"🚨 檢測到 CI 失敗: {report['summary']}")
        self.logger.error(f"   Run ID: {run_id}")
        self.logger.error(f"   失敗次數: {self.failure_count[run_id]}")
        self.logger.error(f"   URL: {report['html_url']}")

        # 分析失敗的 jobs
        failed_jobs = [job for job in report["jobs"] if job["conclusion"] == "failure"]
        if failed_jobs:
            self.logger.error("   失敗的 Jobs:")
            for job in failed_jobs:
                self.logger.error(f"     - {job['name']}: {job['conclusion']}")
                if job["steps"]:
                    for step in job["steps"]:
                        self.logger.error(
                            f"       * {step['name']}: {step['conclusion']}"
                        )

        if self.on_failure_detected:
            try:
                await self._safe_callback_call(self.on_failure_detected, report)
            except Exception as e:
                self.logger.error(f"❌ 失敗檢測回調失敗: {e}")

    async def _handle_recovery_detected(self, report: dict[str, Any]):
        """處理恢復檢測"""
        run_id = report["run_id"]

        self.stats["recoveries_detected"] += 1

        self.logger.info(f"🎉 檢測到 CI 恢復: {report['summary']}")
        self.logger.info(f"   Run ID: {run_id}")
        self.logger.info(f"   URL: {report['html_url']}")

        # 清除失敗計數
        if run_id in self.failure_count:
            del self.failure_count[run_id]

        if self.on_recovery_detected:
            try:
                await self._safe_callback_call(self.on_recovery_detected, report)
            except Exception as e:
                self.logger.error(f"❌ 恢復檢測回調失敗: {e}")

    async def _safe_callback_call(self, callback: Callable, *args, **kwargs):
        """安全地調用回調函數"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args, **kwargs)
            else:
                callback(*args, **kwargs)
        except Exception as e:
            self.logger.error(f"❌ 回調函數執行失敗: {e}")
            raise

    async def start_monitoring(self):
        """開始監控"""
        self.running = True
        self.stats["start_time"] = datetime.now()

        self.logger.info("🚀 CI 監控守護程式啟動")
        self.logger.info(f"   檢查間隔: {self.check_interval} 秒")
        self.logger.info(f"   監控倉庫: {self.validator.owner}/{self.validator.repo}")

        try:
            while self.running:
                # 執行狀態檢查
                await self.check_ci_status()

                # 保存監控報告
                self.save_monitoring_report()

                # 等待下次檢查
                if self.running:
                    self.logger.debug(
                        f"⏰ 等待 {self.check_interval} 秒後進行下次檢查..."
                    )
                    await asyncio.sleep(self.check_interval)

        except asyncio.CancelledError:
            self.logger.info("🛑 監控被取消")
        except Exception as e:
            self.logger.error(f"❌ 監控過程中發生錯誤: {e}")
            raise
        finally:
            self.logger.info("🔚 CI 監控守護程式停止")

    def stop_monitoring(self):
        """停止監控"""
        self.logger.info("🛑 收到停止監控信號...")
        self.running = False

    def _signal_handler(self, signum, frame):
        """信號處理器"""
        self.logger.info(f"📡 收到信號 {signum}，準備優雅關閉...")
        self.stop_monitoring()

    def get_monitoring_stats(self) -> dict[str, Any]:
        """獲取監控統計資訊"""
        stats = self.stats.copy()

        if stats["start_time"]:
            stats["uptime"] = str(datetime.now() - stats["start_time"])
        else:
            stats["uptime"] = "未啟動"

        stats["current_failure_count"] = len(self.failure_count)
        stats["is_running"] = self.running

        return stats

    def save_monitoring_report(self):
        """保存監控報告"""
        try:
            report_dir = Path("monitoring_reports")
            report_dir.mkdir(exist_ok=True)

            report = {
                "timestamp": datetime.now().isoformat(),
                "stats": self.get_monitoring_stats(),
                "last_run_status": self.last_run_status,
                "failure_count": self.failure_count,
            }

            # 保存當前報告
            current_report_file = report_dir / "current_monitoring_status.json"
            with open(current_report_file, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            # 保存歷史報告
            history_file = (
                report_dir
                / f"monitor_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

        except Exception as e:
            self.logger.error(f"❌ 保存監控報告失敗: {e}")


async def main():
    """主函數 - 用於測試"""
    # 從環境變數獲取 token
    token = os.getenv("GITHUB_PAT", "")

    if not token:
        print("❌ 請設置 GITHUB_PAT 環境變數")
        return

    # 創建監控器
    monitor = CIMonitorDaemon(token, check_interval=60)  # 測試時使用1分鐘間隔

    # 註冊回調函數
    async def on_failure(report):
        print(f"🚨 失敗回調: {report['summary']}")

    async def on_recovery(report):
        print(f"🎉 恢復回調: {report['summary']}")

    async def on_status_change(report):
        print(f"🔄 狀態變化: {report['previous_status']} → {report['conclusion']}")

    monitor.register_callbacks(
        on_failure=on_failure,
        on_recovery=on_recovery,
        on_status_change=on_status_change,
    )

    try:
        # 啟動監控
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\n🛑 收到中斷信號，停止監控...")
        monitor.stop_monitoring()
    except Exception as e:
        print(f"❌ 監控失敗: {e}")
    finally:
        # 顯示統計資訊
        stats = monitor.get_monitoring_stats()
        print("\n📊 監控統計:")
        for key, value in stats.items():
            print(f"   {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
