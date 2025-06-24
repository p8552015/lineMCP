#!/usr/bin/env python3
"""
自動CI監控修復系統 - 主控制器
整合所有模組，提供完整的自動化修復流程
"""

import os
import asyncio
import signal
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict

# 導入所有模組
from ci_monitor_daemon import CIMonitorDaemon
from intelligent_problem_analyzer import IntelligentProblemAnalyzer, AnalysisResult
from auto_fix_generator import AutoFixGenerator, FixSolution
from git_automation_module import GitAutomationModule


@dataclass
class SystemStatus:
    """系統狀態"""
    status: str  # 'idle', 'monitoring', 'analyzing', 'fixing', 'error'
    last_check_time: Optional[str] = None
    current_run_id: Optional[str] = None
    problems_detected: int = 0
    fixes_attempted: int = 0
    fixes_successful: int = 0
    uptime: str = "0s"
    error_message: Optional[str] = None


@dataclass
class FixSession:
    """修復會話"""
    session_id: str
    run_id: str
    start_time: str
    problems_found: int
    solutions_generated: int
    fixes_applied: int
    fixes_successful: int
    status: str  # 'in_progress', 'completed', 'failed'
    end_time: Optional[str] = None
    
    def to_dict(self):
        return asdict(self)


class AutoCIMasterController:
    """自動CI監控修復系統主控制器"""
    
    def __init__(self, 
                 github_token: str,
                 repo_owner: str = "p8552015",
                 repo_name: str = "lineMCP",
                 project_root: str = "/Users/yen/Desktop/lineMCP",
                 config: Optional[Dict] = None):
        """
        初始化主控制器
        
        Args:
            github_token: GitHub Personal Access Token
            repo_owner: 倉庫擁有者
            repo_name: 倉庫名稱
            project_root: 專案根目錄
            config: 額外配置
        """
        self.github_token = github_token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.project_root = Path(project_root)
        self.config = config or {}
        
        # 系統狀態
        self.system_status = SystemStatus(status="idle")
        self.start_time = datetime.now()
        self.running = False
        
        # 修復會話歷史
        self.fix_sessions: List[FixSession] = []
        
        # 設置日誌
        self.setup_logging()
        
        # 初始化所有模組
        self.setup_modules()
        
        # 設置信號處理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # 統計資訊
        self.stats = {
            "total_checks": 0,
            "total_problems": 0,
            "total_fixes_attempted": 0,
            "total_fixes_successful": 0,
            "successful_sessions": 0,
            "failed_sessions": 0
        }
    
    def setup_logging(self):
        """設置日誌系統"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "master_controller.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("🚀 自動CI監控修復系統主控制器啟動")
    
    def setup_modules(self):
        """初始化所有模組"""
        try:
            # CI監控守護程式
            check_interval = self.config.get("check_interval", 300)  # 5分鐘
            self.monitor = CIMonitorDaemon(
                token=self.github_token,
                owner=self.repo_owner,
                repo=self.repo_name,
                check_interval=check_interval
            )
            
            # 註冊回調函數
            self.monitor.register_callbacks(
                on_failure=self._on_ci_failure_detected,
                on_recovery=self._on_ci_recovery_detected,
                on_status_change=self._on_ci_status_change
            )
            
            # 問題分析器
            self.analyzer = IntelligentProblemAnalyzer()
            
            # 修復生成器
            self.fix_generator = AutoFixGenerator(project_root=str(self.project_root))
            
            # Git自動化模組
            self.git_module = GitAutomationModule(repo_path=str(self.project_root))
            
            self.logger.info("✅ 所有模組初始化完成")
            
        except Exception as e:
            self.logger.error(f"❌ 模組初始化失敗: {e}")
            raise
    
    async def start_system(self):
        """啟動完整系統"""
        try:
            self.logger.info("🎯 啟動自動CI監控修復系統")
            self.running = True
            self.system_status.status = "monitoring"
            
            # 啟動監控守護程式
            await self.monitor.start_monitoring()
            
        except KeyboardInterrupt:
            self.logger.info("🛑 收到中斷信號，正在停止系統...")
            await self.stop_system()
        except Exception as e:
            self.logger.error(f"❌ 系統運行錯誤: {e}")
            self.system_status.status = "error"
            self.system_status.error_message = str(e)
            raise
        finally:
            await self.stop_system()
    
    async def stop_system(self):
        """停止系統"""
        self.logger.info("🔚 正在停止自動CI監控修復系統...")
        self.running = False
        
        # 停止監控
        if hasattr(self, 'monitor'):
            self.monitor.stop_monitoring()
        
        # 保存最終報告
        await self.generate_final_report()
        
        self.logger.info("✅ 系統已停止")
    
    def _signal_handler(self, signum, frame):
        """信號處理器"""
        self.logger.info(f"📡 收到信號 {signum}，準備停止系統...")
        self.running = False
    
    async def _on_ci_failure_detected(self, ci_report: Dict[str, Any]):
        """CI失敗檢測回調"""
        self.logger.info(f"🚨 檢測到CI失敗: Run {ci_report.get('run_id')}")
        
        # 更新系統狀態
        self.system_status.status = "analyzing"
        self.system_status.current_run_id = ci_report.get("run_id")
        self.stats["total_checks"] += 1
        
        try:
            # 啟動自動修復流程
            await self.execute_auto_fix_workflow(ci_report)
            
        except Exception as e:
            self.logger.error(f"❌ 自動修復流程失敗: {e}")
            self.system_status.status = "error"
            self.system_status.error_message = str(e)
        finally:
            # 恢復監控狀態
            self.system_status.status = "monitoring"
    
    async def _on_ci_recovery_detected(self, ci_report: Dict[str, Any]):
        """CI恢復檢測回調"""
        self.logger.info(f"🎉 檢測到CI恢復: Run {ci_report.get('run_id')}")
        
        # 清除錯誤狀態
        if self.system_status.status == "error":
            self.system_status.status = "monitoring"
            self.system_status.error_message = None
    
    async def _on_ci_status_change(self, ci_report: Dict[str, Any]):
        """CI狀態變化回調"""
        self.logger.info(f"🔄 CI狀態變化: {ci_report.get('previous_status')} → {ci_report.get('conclusion')}")
        self.system_status.last_check_time = datetime.now().isoformat()
    
    async def execute_auto_fix_workflow(self, ci_report: Dict[str, Any]) -> bool:
        """
        執行自動修復工作流程
        
        Args:
            ci_report: CI失敗報告
            
        Returns:
            是否修復成功
        """
        session_id = f"fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        run_id = str(ci_report.get("run_id", "unknown"))
        
        self.logger.info(f"🔧 開始修復會話: {session_id}")
        
        # 創建修復會話
        session = FixSession(
            session_id=session_id,
            run_id=run_id,
            start_time=datetime.now().isoformat(),
            problems_found=0,
            solutions_generated=0,
            fixes_applied=0,
            fixes_successful=0,
            status="in_progress"
        )
        
        try:
            # 階段1: 分析問題
            self.logger.info("📊 階段1: 分析CI失敗問題...")
            self.system_status.status = "analyzing"
            
            analysis_results = self.analyzer.analyze_ci_failure(ci_report)
            
            if not analysis_results:
                self.logger.warning("⚠️ 未檢測到任何問題")
                session.status = "completed"
                return False
            
            total_problems = sum(len(result.problems) for result in analysis_results)
            session.problems_found = total_problems
            self.stats["total_problems"] += total_problems
            
            self.logger.info(f"   發現 {total_problems} 個問題需要修復")
            
            # 階段2: 生成修復方案
            self.logger.info("🧠 階段2: 生成修復方案...")
            self.system_status.status = "fixing"
            
            solutions = await self.fix_generator.generate_fixes(analysis_results)
            
            if not solutions:
                self.logger.warning("⚠️ 未能生成任何修復方案")
                session.status = "failed"
                return False
            
            session.solutions_generated = len(solutions)
            self.logger.info(f"   生成 {len(solutions)} 個修復方案")
            
            # 階段3: 應用修復
            self.logger.info("⚙️ 階段3: 應用修復方案...")
            
            successful_fixes = 0
            
            for i, solution in enumerate(solutions, 1):
                self.logger.info(f"   應用修復 {i}/{len(solutions)}: {solution.solution_name}")
                
                # 應用修復
                fix_success = await self.git_module.apply_fix_solution(solution)
                
                session.fixes_applied += 1
                self.stats["total_fixes_attempted"] += 1
                
                if fix_success:
                    successful_fixes += 1
                    session.fixes_successful += 1
                    self.stats["total_fixes_successful"] += 1
                    
                    self.logger.info(f"   ✅ 修復成功: {solution.solution_name}")
                    
                    # 如果是高信心度修復，等待CI驗證
                    if solution.estimated_success_rate > 0.8:
                        verification_success = await self._verify_fix_with_ci(solution)
                        if verification_success:
                            self.logger.info(f"   🎯 修復驗證成功")
                            break  # 如果修復成功，停止應用更多修復
                else:
                    self.logger.error(f"   ❌ 修復失敗: {solution.solution_name}")
            
            # 階段4: 總結結果
            success_rate = successful_fixes / len(solutions) if solutions else 0
            
            if successful_fixes > 0:
                session.status = "completed"
                self.stats["successful_sessions"] += 1
                self.logger.info(f"✅ 修復會話完成: {successful_fixes}/{len(solutions)} 個修復成功")
            else:
                session.status = "failed"
                self.stats["failed_sessions"] += 1
                self.logger.error(f"❌ 修復會話失敗: 沒有成功的修復")
            
            return successful_fixes > 0
            
        except Exception as e:
            self.logger.error(f"❌ 修復工作流程失敗: {e}")
            session.status = "failed"
            self.stats["failed_sessions"] += 1
            return False
            
        finally:
            # 結束會話
            session.end_time = datetime.now().isoformat()
            self.fix_sessions.append(session)
            
            # 保存會話報告
            await self.save_session_report(session)
    
    async def _verify_fix_with_ci(self, solution: FixSolution, timeout: int = 1800) -> bool:
        """
        透過CI驗證修復效果
        
        Args:
            solution: 修復方案
            timeout: 超時時間（秒）
            
        Returns:
            驗證是否成功
        """
        try:
            self.logger.info(f"🔍 等待CI驗證修復效果...")
            
            # 等待一段時間讓CI開始運行
            await asyncio.sleep(60)
            
            start_time = datetime.now()
            while (datetime.now() - start_time).seconds < timeout:
                # 檢查最新的CI狀態
                latest_run = self.monitor.validator.get_latest_workflow_run()
                
                if latest_run and latest_run["status"] == "completed":
                    if latest_run["conclusion"] == "success":
                        self.logger.info("✅ CI驗證成功 - 修復有效")
                        return True
                    elif latest_run["conclusion"] == "failure":
                        self.logger.warning("⚠️ CI驗證失敗 - 修復無效或不完整")
                        return False
                
                # 等待30秒再檢查
                await asyncio.sleep(30)
            
            self.logger.warning("⏰ CI驗證超時")
            return False
            
        except Exception as e:
            self.logger.error(f"❌ CI驗證過程錯誤: {e}")
            return False
    
    async def save_session_report(self, session: FixSession):
        """保存修復會話報告"""
        try:
            report_dir = Path("session_reports")
            report_dir.mkdir(exist_ok=True)
            
            report_file = report_dir / f"session_{session.session_id}.json"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"📄 會話報告已保存: {report_file}")
            
        except Exception as e:
            self.logger.error(f"❌ 保存會話報告失敗: {e}")
    
    async def generate_final_report(self):
        """生成最終報告"""
        try:
            uptime = datetime.now() - self.start_time
            
            report = {
                "system_info": {
                    "start_time": self.start_time.isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "uptime": str(uptime),
                    "repo": f"{self.repo_owner}/{self.repo_name}"
                },
                "statistics": self.stats,
                "system_status": asdict(self.system_status),
                "fix_sessions": [session.to_dict() for session in self.fix_sessions],
                "module_stats": {
                    "monitor": self.monitor.get_monitoring_stats(),
                    "fix_generator": self.fix_generator.get_stats(),
                    "git_module": self.git_module.get_status_summary()
                }
            }
            
            report_dir = Path("final_reports")
            report_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = report_dir / f"final_report_{timestamp}.json"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"📊 最終報告已生成: {report_file}")
            
            # 生成摘要
            self._print_summary_report(report)
            
        except Exception as e:
            self.logger.error(f"❌ 生成最終報告失敗: {e}")
    
    def _print_summary_report(self, report: Dict[str, Any]):
        """列印摘要報告"""
        print("\n" + "="*60)
        print("🤖 自動CI監控修復系統 - 運行摘要")
        print("="*60)
        
        stats = report["statistics"]
        system_info = report["system_info"]
        
        print(f"📅 運行時間: {system_info['uptime']}")
        print(f"🔍 總檢查次數: {stats['total_checks']}")
        print(f"🐛 發現問題數: {stats['total_problems']}")
        print(f"🔧 嘗試修復數: {stats['total_fixes_attempted']}")
        print(f"✅ 成功修復數: {stats['total_fixes_successful']}")
        print(f"📝 成功會話數: {stats['successful_sessions']}")
        print(f"❌ 失敗會話數: {stats['failed_sessions']}")
        
        if stats['total_fixes_attempted'] > 0:
            success_rate = stats['total_fixes_successful'] / stats['total_fixes_attempted'] * 100
            print(f"📊 修復成功率: {success_rate:.1f}%")
        
        print("\n🎯 最近的修復會話:")
        for session in report["fix_sessions"][-3:]:  # 顯示最近3個會話
            status_emoji = "✅" if session["status"] == "completed" else "❌"
            print(f"   {status_emoji} {session['session_id']}: {session['fixes_successful']}/{session['fixes_applied']} 修復成功")
        
        print("="*60)
    
    def get_system_status(self) -> Dict[str, Any]:
        """獲取系統狀態"""
        uptime = datetime.now() - self.start_time
        self.system_status.uptime = str(uptime)
        
        return {
            "system_status": asdict(self.system_status),
            "statistics": self.stats,
            "recent_sessions": [session.to_dict() for session in self.fix_sessions[-5:]],
            "module_status": {
                "monitor_running": hasattr(self, 'monitor') and self.monitor.running,
                "modules_initialized": all([
                    hasattr(self, 'monitor'),
                    hasattr(self, 'analyzer'),
                    hasattr(self, 'fix_generator'),
                    hasattr(self, 'git_module')
                ])
            }
        }


async def main():
    """主函數"""
    # 從環境變數獲取GitHub token
    github_token = os.getenv("GITHUB_PAT", "")
    
    if not github_token:
        print("❌ 請設置 GITHUB_PAT 環境變數")
        return
    
    # 創建控制器
    controller = AutoCIMasterController(
        github_token=github_token,
        config={
            "check_interval": 300,  # 5分鐘檢查間隔
            "auto_fix_enabled": True,
            "max_concurrent_fixes": 3
        }
    )
    
    try:
        # 啟動系統
        await controller.start_system()
        
    except KeyboardInterrupt:
        print("\n🛑 收到中斷信號...")
    except Exception as e:
        print(f"❌ 系統錯誤: {e}")
    finally:
        await controller.stop_system()


if __name__ == "__main__":
    print("🚀 啟動自動CI監控修復系統...")
    asyncio.run(main())