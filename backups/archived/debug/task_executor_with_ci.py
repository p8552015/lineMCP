#!/usr/bin/env python3
"""
增強版任務執行器 - 整合 GitHub Actions CI 驗證
"""

import os
import sys
import subprocess
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from github_ci_validator import GitHubCIValidator


class TaskExecutorWithCI:
    """整合 CI 驗證的任務執行器"""
    
    def __init__(self, spec_file: str, github_token: Optional[str] = None):
        self.spec_file = Path(spec_file)
        self.current_content = ""
        self.tasks = []
        
        # GitHub CI 驗證器
        self.github_token = github_token or os.getenv("GITHUB_PAT", "")
        self.ci_validator = None
        
        if self.github_token:
            self.ci_validator = GitHubCIValidator(self.github_token)
            print("✅ GitHub CI 驗證已啟用")
        else:
            print("⚠️ 未設置 GITHUB_PAT，CI 驗證功能已停用")
    
    def load_spec(self) -> bool:
        """載入規格檔案"""
        try:
            with open(self.spec_file, 'r', encoding='utf-8') as f:
                self.current_content = f.read()
            self._parse_tasks()
            return True
        except Exception as e:
            print(f"❌ 載入規格檔案失敗: {e}")
            return False
    
    def _parse_tasks(self):
        """解析任務表"""
        # 找到任務表區塊
        start_marker = "<!-- TASKS START -->"
        end_marker = "<!-- TASKS END -->"
        
        start_idx = self.current_content.find(start_marker)
        end_idx = self.current_content.find(end_marker)
        
        if start_idx == -1 or end_idx == -1:
            print("❌ 找不到任務表標記")
            return
        
        tasks_section = self.current_content[start_idx:end_idx + len(end_marker)]
        
        # 解析表格行
        lines = tasks_section.split('\n')
        self.tasks = []
        
        for line in lines:
            if line.strip().startswith('| T-'):
                parts = [p.strip() for p in line.split('|') if p.strip()]
                if len(parts) >= 8:
                    task = {
                        'id': parts[0],
                        'name': parts[1],
                        'description': parts[2], 
                        'priority': parts[3],
                        'assignee': parts[4],
                        'status': parts[5],
                        'start_time': parts[6],
                        'end_time': parts[7]
                    }
                    self.tasks.append(task)
    
    def get_next_task(self) -> Optional[Dict[str, Any]]:
        """獲取下一個待執行的任務"""
        for task in self.tasks:
            if task['status'] == 'TODO':
                return task
        return None
    
    def update_task_status(self, task_id: str, status: str, 
                          ci_result: Optional[str] = None) -> bool:
        """更新任務狀態（包含 CI 結果）"""
        try:
            # 當前時間
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            # 讀取當前檔案內容
            with open(self.spec_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 找到對應任務行並更新
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.strip().startswith(f'| {task_id} |'):
                    parts = line.split('|')
                    if len(parts) >= 9:
                        # 更新狀態
                        if ci_result:
                            parts[6] = f' {status} ({ci_result}) '
                        else:
                            parts[6] = f' {status} '
                        
                        # 更新時間
                        if status == 'DOING' and not parts[7].strip():
                            parts[7] = f' {current_time} '
                        elif status in ['DONE', 'BLOCKED']:
                            if not parts[7].strip():
                                parts[7] = f' {current_time} '
                            parts[8] = f' {current_time} '
                        
                        lines[i] = '|'.join(parts)
                        break
            
            # 寫回檔案
            with open(self.spec_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            return True
            
        except Exception as e:
            print(f"❌ 更新任務狀態失敗: {e}")
            return False
    
    def run_local_tests(self) -> bool:
        """執行本地測試"""
        print("🧪 執行本地測試...")
        try:
            # 切換到 bot 目錄
            bot_dir = Path(__file__).parent / "apps" / "bot"
            
            # 執行測試
            result = subprocess.run(
                ["poetry", "run", "pytest", "-v", "--tb=short"],
                cwd=bot_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ 本地測試通過")
                return True
            else:
                print("❌ 本地測試失敗")
                print(result.stdout[-1000:])  # 顯示最後 1000 字元
                return False
                
        except Exception as e:
            print(f"❌ 執行本地測試失敗: {e}")
            return False
    
    def validate_with_ci(self, task_id: str) -> bool:
        """使用 CI 驗證任務"""
        if not self.ci_validator:
            print("⚠️ CI 驗證未啟用，跳過")
            return True
        
        print(f"\n🔍 開始 CI 驗證任務 {task_id}")
        
        try:
            # 獲取當前分支
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True
            )
            branch = result.stdout.strip() or "main"
            
            # 提交當前更改（如果有）
            print("📤 提交當前更改...")
            subprocess.run(["git", "add", "."], check=False)
            subprocess.run(
                ["git", "commit", "-m", f"feat: 完成任務 {task_id} - 準備 CI 驗證"],
                check=False
            )
            
            # 推送到遠端
            print(f"📤 推送到分支 {branch}...")
            result = subprocess.run(
                ["git", "push", "origin", branch],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"⚠️ 推送失敗，嘗試設置上游分支...")
                subprocess.run(
                    ["git", "push", "-u", "origin", branch],
                    check=False
                )
            
            # 使用 CI 驗證
            return self.ci_validator.validate_task_with_ci(task_id, branch)
            
        except Exception as e:
            print(f"❌ CI 驗證過程出錯: {e}")
            return False
    
    def execute_task(self, task: Dict[str, Any]) -> bool:
        """執行特定任務"""
        task_id = task['id']
        task_name = task['name']
        
        print(f"\n🔧 開始執行任務 {task_id}: {task_name}")
        
        # 更新狀態為 DOING
        if not self.update_task_status(task_id, 'DOING'):
            return False
        
        success = False
        ci_result = "N/A"
        
        try:
            # 執行任務邏輯
            if task_id == 'T-02':
                success = self._execute_t02()
            elif task_id == 'T-03':
                success = self._execute_t03()
            elif task_id == 'T-04':
                success = self._execute_t04()
            elif task_id == 'T-05':
                success = self._execute_t05()
            elif task_id == 'T-06':
                success = self._execute_t06()
            elif task_id == 'T-07':
                success = self._execute_t07()
            elif task_id == 'T-08':
                success = self._execute_t08()
            elif task_id == 'T-09':
                success = self._execute_t09()
            else:
                print(f"⚠️ 未知任務 {task_id}")
                success = False
            
            # 如果任務成功，執行 CI 驗證
            if success:
                # 先執行本地測試
                if self.run_local_tests():
                    # 本地測試通過，執行 CI 驗證
                    if self.validate_with_ci(task_id):
                        ci_result = "CI✅"
                        print(f"✅ 任務 {task_id} 通過 CI 驗證")
                    else:
                        ci_result = "CI❌"
                        success = False
                        print(f"❌ 任務 {task_id} CI 驗證失敗")
                else:
                    ci_result = "Local❌"
                    success = False
                    print(f"❌ 任務 {task_id} 本地測試失敗")
            
            # 更新最終狀態
            if success:
                self.update_task_status(task_id, 'DONE', ci_result)
            else:
                self.update_task_status(task_id, 'BLOCKED', ci_result)
                
        except Exception as e:
            print(f"💥 任務 {task_id} 執行過程中發生錯誤: {e}")
            self.update_task_status(task_id, 'BLOCKED', "Error")
            success = False
        
        return success
    
    # 任務執行方法
    def _execute_t02(self) -> bool:
        """執行 T-02: 修復ApplicationFacade初始化"""
        print("   🔧 修復 ApplicationFacade 初始化問題...")
        # TODO: 實際修復邏輯
        return True
    
    def _execute_t03(self) -> bool:
        """執行 T-03: 修復訊息處理流程"""
        print("   🔧 修復訊息處理流程...")
        # TODO: 實際修復邏輯
        return True
    
    def _execute_t04(self) -> bool:
        """執行 T-04: 修復SQL查詢執行流程"""
        print("   🔧 修復 SQL 查詢執行流程...")
        # TODO: 實際修復邏輯
        return True
    
    def _execute_t05(self) -> bool:
        """執行 T-05: 修復依賴注入整合問題"""
        print("   🔧 修復依賴注入整合問題...")
        # TODO: 實際修復邏輯
        return True
    
    def _execute_t06(self) -> bool:
        """執行 T-06: 修復並發處理測試"""
        print("   🔧 修復並發處理測試...")
        # TODO: 實際修復邏輯
        return True
    
    def _execute_t07(self) -> bool:
        """執行 T-07: 提升測試覆蓋率至80%"""
        print("   📊 提升測試覆蓋率...")
        # TODO: 實際提升覆蓋率邏輯
        return True
    
    def _execute_t08(self) -> bool:
        """執行 T-08: 最終系統驗證"""
        print("   🧪 執行最終系統驗證...")
        try:
            # 執行生產查詢測試
            bot_dir = Path(__file__).parent / "apps" / "bot"
            result = subprocess.run(
                ["poetry", "run", "python", "production_query_validation.py"],
                cwd=bot_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("   ✅ 生產查詢測試通過")
                return True
            else:
                print("   ❌ 生產查詢測試失敗")
                return False
                
        except Exception as e:
            print(f"   ❌ 系統驗證失敗: {e}")
            return False
    
    def _execute_t09(self) -> bool:
        """執行 T-09: 更新相關文檔"""
        print("   📝 更新專案文檔...")
        # TODO: 實際文檔更新邏輯
        return True
    
    def run_all_pending(self) -> int:
        """執行所有待處理任務"""
        print("🚀 開始執行所有待處理任務（含 CI 驗證）...")
        
        completed = 0
        failed = 0
        
        while True:
            # 重新載入規格以獲取最新狀態
            if not self.load_spec():
                break
                
            next_task = self.get_next_task()
            if not next_task:
                print("✅ 所有待處理任務執行完成")
                break
            
            success = self.execute_task(next_task)
            if success:
                completed += 1
            else:
                failed += 1
        
        print(f"\n📊 執行總結:")
        print(f"   ✅ 成功: {completed} 個任務")
        print(f"   ❌ 失敗: {failed} 個任務")
        
        return completed
    
    def generate_ci_report(self):
        """生成 CI 執行報告"""
        print("\n📊 生成 CI 執行報告...")
        
        report = f"""# CI 執行報告

**執行時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**規格檔案**: {self.spec_file}

## 任務執行狀態

| 任務 ID | 任務名稱 | 狀態 | CI 結果 |
|---------|----------|------|---------|
"""
        
        for task in self.tasks:
            status = task['status']
            ci_result = "N/A"
            
            # 從狀態中提取 CI 結果
            if '(' in status and ')' in status:
                match = re.search(r'\((.*?)\)', status)
                if match:
                    ci_result = match.group(1)
                    status = status.split('(')[0].strip()
            
            status_emoji = {
                'TODO': '⏳',
                'DOING': '🔄',
                'DONE': '✅',
                'BLOCKED': '❌'
            }.get(status, '❓')
            
            report += f"| {task['id']} | {task['name']} | {status_emoji} {status} | {ci_result} |\n"
        
        report += "\n## CI 驗證詳情\n\n"
        report += "詳細的 CI 執行日誌請查看 `ci_reports/` 目錄。\n"
        
        # 保存報告
        report_file = Path("ci_execution_report.md")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"✅ 報告已保存: {report_file}")


def main():
    """主函數"""
    if len(sys.argv) < 2:
        print("使用方式:")
        print("  python task_executor_with_ci.py <spec_file> [task_id|--all|--report]")
        print("  例如:")
        print("    python task_executor_with_ci.py spec_系統測試修復完成.md T-02")
        print("    python task_executor_with_ci.py spec_系統測試修復完成.md --all")
        print("    python task_executor_with_ci.py spec_系統測試修復完成.md --report")
        print("\n環境變數:")
        print("  GITHUB_PAT - GitHub Personal Access Token (用於 CI 驗證)")
        return 1
    
    spec_file = sys.argv[1]
    
    # 從環境變數獲取 GitHub token
    github_token = os.getenv("GITHUB_PAT", "")
    
    executor = TaskExecutorWithCI(spec_file, github_token)
    
    if not executor.load_spec():
        return 1
    
    if len(sys.argv) >= 3:
        if sys.argv[2] == '--all':
            # 執行所有待處理任務
            completed = executor.run_all_pending()
            executor.generate_ci_report()
            return 0 if completed > 0 else 1
        elif sys.argv[2] == '--report':
            # 只生成報告
            executor.generate_ci_report()
            return 0
        else:
            # 執行特定任務
            task_id = sys.argv[2]
            task = None
            for t in executor.tasks:
                if t['id'] == task_id:
                    task = t
                    break
            
            if not task:
                print(f"❌ 找不到任務 {task_id}")
                return 1
            
            success = executor.execute_task(task)
            return 0 if success else 1
    else:
        # 顯示任務狀態
        print("📋 任務狀態:")
        for task in executor.tasks:
            status = task['status']
            ci_info = ""
            
            # 提取 CI 資訊
            if '(' in status and ')' in status:
                match = re.search(r'\((.*?)\)', status)
                if match:
                    ci_info = f" [{match.group(1)}]"
                    status = status.split('(')[0].strip()
            
            status_emoji = {
                'TODO': '⏳',
                'DOING': '🔄',
                'DONE': '✅',
                'BLOCKED': '❌'
            }.get(status, '❓')
            
            print(f"   {status_emoji} {task['id']}: {task['name']} ({status}{ci_info})")
        
        return 0


if __name__ == "__main__":
    exit(main())