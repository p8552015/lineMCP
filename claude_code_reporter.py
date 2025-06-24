#!/usr/bin/env python3
"""
Claude Code回報介面
提供簡潔的狀態回報和修復日誌給Claude Code使用者
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import asdict


class ClaudeCodeReporter:
    """Claude Code回報介面"""
    
    def __init__(self, output_dir: str = "claude_reports"):
        """
        初始化回報器
        
        Args:
            output_dir: 輸出目錄
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.setup_logging()
        
        # 當前狀態
        self.current_status = "idle"
        self.last_report_time = None
        
        # 報告歷史
        self.reports_history = []
    
    def setup_logging(self):
        """設置日誌"""
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def report_system_start(self, config: Dict[str, Any]):
        """報告系統啟動"""
        message = f"""
🚀 自動CI監控修復系統已啟動

⚙️ 配置資訊：
- 監控倉庫: {config.get('repo', 'lineMCP')}
- 檢查間隔: {config.get('check_interval', 300)}秒
- 自動修復: {'啟用' if config.get('auto_fix_enabled', True) else '停用'}

🎯 系統將持續監控GitHub Actions狀態，當檢測到失敗時自動進行分析和修復。
        """
        
        self._send_report("系統啟動", message)
        self.current_status = "monitoring"
    
    def report_ci_failure_detected(self, run_id: str, problems_count: int):
        """報告CI失敗檢測"""
        message = f"""
🚨 檢測到CI失敗

📋 失敗資訊：
- Run ID: {run_id}
- 檢測到問題數: {problems_count}個

🔧 系統正在自動分析問題並生成修復方案...
        """
        
        self._send_report("CI失敗檢測", message)
        self.current_status = "analyzing"
    
    def report_fix_progress(self, session_id: str, fixes_applied: int, fixes_successful: int, total_fixes: int):
        """報告修復進度"""
        success_rate = (fixes_successful / fixes_applied * 100) if fixes_applied > 0 else 0
        
        message = f"""
⚙️ 修復進度更新

📊 會話: {session_id}
- 已應用修復: {fixes_applied}/{total_fixes}
- 成功修復: {fixes_successful}個
- 成功率: {success_rate:.1f}%

🔄 系統持續應用修復方案中...
        """
        
        self._send_report("修復進度", message)
        self.current_status = "fixing"
    
    def report_fix_completion(self, session_id: str, success: bool, summary: Dict[str, Any]):
        """報告修復完成"""
        if success:
            message = f"""
✅ 修復會話完成

🎉 會話: {session_id}
- 狀態: 成功完成
- 問題數: {summary.get('problems_found', 0)}
- 修復成功: {summary.get('fixes_successful', 0)}個
- 總修復數: {summary.get('fixes_applied', 0)}個

🔍 系統正在等待CI驗證修復效果...
            """
        else:
            message = f"""
❌ 修復會話失敗

⚠️ 會話: {session_id}
- 狀態: 失敗
- 問題數: {summary.get('problems_found', 0)}
- 嘗試修復: {summary.get('fixes_applied', 0)}個
- 成功修復: {summary.get('fixes_successful', 0)}個

🔄 系統將繼續監控，等待下次修復機會...
            """
        
        self._send_report("修復完成", message)
        self.current_status = "monitoring"
    
    def report_ci_recovery(self, run_id: str):
        """報告CI恢復"""
        message = f"""
🎉 檢測到CI恢復

✅ CI狀態已恢復正常
- Run ID: {run_id}
- 修復效果: 已驗證

👍 自動修復系統成功解決了CI問題！
系統將繼續監控以確保穩定性。
        """
        
        self._send_report("CI恢復", message)
        self.current_status = "monitoring"
    
    def report_system_stats(self, stats: Dict[str, Any]):
        """報告系統統計"""
        success_rate = (stats.get('total_fixes_successful', 0) / stats.get('total_fixes_attempted', 1) * 100) if stats.get('total_fixes_attempted', 0) > 0 else 0
        
        message = f"""
📊 系統運行統計

🔍 監控統計：
- 總檢查次數: {stats.get('total_checks', 0)}
- 發現問題數: {stats.get('total_problems', 0)}
- 嘗試修復數: {stats.get('total_fixes_attempted', 0)}
- 成功修復數: {stats.get('total_fixes_successful', 0)}

📈 成功率：
- 修復成功率: {success_rate:.1f}%
- 成功會話: {stats.get('successful_sessions', 0)}個
- 失敗會話: {stats.get('failed_sessions', 0)}個

🎯 系統運行正常，持續保護您的CI/CD流程。
        """
        
        self._send_report("系統統計", message)
    
    def report_error(self, error_type: str, error_message: str):
        """報告錯誤"""
        message = f"""
❌ 系統錯誤

🚫 錯誤類型: {error_type}
📝 錯誤訊息: {error_message}

🔧 系統正在嘗試自動恢復，請稍後...
如果問題持續，請檢查系統日誌。
        """
        
        self._send_report("系統錯誤", message)
        self.current_status = "error"
    
    def _send_report(self, title: str, message: str):
        """發送報告"""
        timestamp = datetime.now().isoformat()
        
        report = {
            "timestamp": timestamp,
            "title": title,
            "message": message.strip(),
            "status": self.current_status
        }
        
        # 保存到文件
        self._save_report(report)
        
        # 添加到歷史
        self.reports_history.append(report)
        
        # 保留最近50個報告
        if len(self.reports_history) > 50:
            self.reports_history = self.reports_history[-50:]
        
        # 更新最後報告時間
        self.last_report_time = timestamp
        
        # 顯示在控制台
        print(f"\n{'='*60}")
        print(f"📣 Claude Code 報告 - {title}")
        print(f"⏰ {timestamp}")
        print(f"{'='*60}")
        print(message)
        print(f"{'='*60}\n")
    
    def _save_report(self, report: Dict[str, Any]):
        """保存報告到文件"""
        try:
            # 保存單個報告
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = self.output_dir / f"report_{timestamp}.json"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            # 更新最新狀態文件
            status_file = self.output_dir / "latest_status.json"
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "current_status": self.current_status,
                    "last_report": report,
                    "last_update": datetime.now().isoformat()
                }, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            self.logger.error(f"❌ 保存報告失敗: {e}")
    
    def get_current_status(self) -> Dict[str, Any]:
        """獲取當前狀態"""
        return {
            "status": self.current_status,
            "last_report_time": self.last_report_time,
            "reports_count": len(self.reports_history)
        }
    
    def get_recent_reports(self, count: int = 10) -> List[Dict[str, Any]]:
        """獲取最近的報告"""
        return self.reports_history[-count:] if self.reports_history else []
    
    def generate_summary_report(self) -> str:
        """生成摘要報告"""
        if not self.reports_history:
            return "📭 暫無報告歷史"
        
        recent_reports = self.reports_history[-10:]
        
        summary = f"""
📋 Claude Code 系統摘要報告

⏰ 生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📊 當前狀態: {self.current_status}
📝 報告總數: {len(self.reports_history)}

🔖 最近活動:
"""
        
        for report in recent_reports:
            time_str = report['timestamp'][:19].replace('T', ' ')
            summary += f"   • {time_str} - {report['title']}\n"
        
        return summary


def main():
    """測試主函數"""
    reporter = ClaudeCodeReporter()
    
    print("📣 測試Claude Code回報介面...")
    
    # 測試各種報告
    reporter.report_system_start({
        "repo": "p8552015/lineMCP",
        "check_interval": 300,
        "auto_fix_enabled": True
    })
    
    reporter.report_ci_failure_detected("12345", 3)
    
    reporter.report_fix_progress("fix_001", 2, 1, 3)
    
    reporter.report_fix_completion("fix_001", True, {
        "problems_found": 3,
        "fixes_applied": 3,
        "fixes_successful": 2
    })
    
    reporter.report_ci_recovery("12346")
    
    # 生成摘要
    summary = reporter.generate_summary_report()
    print(summary)
    
    print("✅ Claude Code回報介面測試完成")


if __name__ == "__main__":
    main()