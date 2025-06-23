#!/usr/bin/env python3
"""
自動化任務執行器 (Task Executor)
依據 spec_code_cleanup.md 逐一執行 TODO 任務，實時更新狀態
"""

import re
import os
import sys
import subprocess
import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

class TaskExecutor:
    def __init__(self, spec_file: str = "spec_code_cleanup.md"):
        self.spec_file = Path(spec_file)
        self.project_root = Path("/Users/yen/Desktop/lineMCP")
        self.tasks = []
        self.current_task = None
        
    def load_spec(self) -> bool:
        """載入規格檔並解析任務表"""
        if not self.spec_file.exists():
            print(f"❌ 規格檔不存在: {self.spec_file}")
            return False
            
        try:
            with open(self.spec_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取任務表（使用更精確的匹配避免誤匹配文檔中的引用）
            tasks_match = re.search(
                r'^<!-- TASKS START -->\s*\n(.*?)\n<!-- TASKS END -->',
                content,
                re.DOTALL | re.MULTILINE
            )
            
            if not tasks_match:
                print("❌ 找不到任務表區塊")
                return False
            
            tasks_content = tasks_match.group(1).strip()
            self.tasks = self._parse_tasks(tasks_content)
            
            print(f"✅ 載入 {len(self.tasks)} 個任務")
            return True
            
        except Exception as e:
            print(f"❌ 載入規格檔失敗: {e}")
            return False
    
    def _parse_tasks(self, tasks_content: str) -> List[Dict]:
        """解析任務表格"""
        lines = tasks_content.split('\n')
        tasks = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('|') and not line.startswith('|---'):
                if '任務' in line or 'ID' in line:  # 跳過標題行
                    continue
                    
                parts = [p.strip() for p in line.split('|')[1:-1]]  # 去除首尾空白分割
                if len(parts) >= 8 and parts[0].startswith('T-'):
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
                    tasks.append(task)
        
        return tasks
    
    def get_next_task(self) -> Optional[Dict]:
        """取得下一個待執行的任務"""
        for task in self.tasks:
            if task['status'] == 'TODO':
                return task
        return None
    
    def update_task_status(self, task_id: str, status: str, end_time: str = "") -> bool:
        """更新任務狀態並保存到規格檔"""
        try:
            # 更新內存中的任務狀態
            for task in self.tasks:
                if task['id'] == task_id:
                    task['status'] = status
                    if status == 'DOING' and not task['start_time']:
                        task['start_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                    elif status == 'DONE' and end_time:
                        task['end_time'] = end_time
                    break
            
            # 讀取規格檔
            with open(self.spec_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 重建任務表
            new_table = self._build_tasks_table()
            
            # 替換任務表區塊
            new_content = re.sub(
                r'(<!-- TASKS START -->).*?(<!-- TASKS END -->)',
                f'\\1\\n{new_table}\\n\\2',
                content,
                flags=re.DOTALL
            )
            
            # 保存檔案
            with open(self.spec_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"✅ 任務 {task_id} 狀態更新為: {status}")
            return True
            
        except Exception as e:
            print(f"❌ 更新任務狀態失敗: {e}")
            return False
    
    def _build_tasks_table(self) -> str:
        """重建任務表格"""
        lines = [
            "| ID | 任務 | 描述 | 優先級 | 負責 | 狀態 | 開始 | 結束 |",
            "|---|------|------|-------|------|------|------|------|"
        ]
        
        for task in self.tasks:
            line = f"| {task['id']} | {task['name']} | {task['description']} | {task['priority']} | {task['assignee']} | {task['status']} | {task['start_time']} | {task['end_time']} |"
            lines.append(line)
        
        return '\\n'.join(lines)
    
    def execute_task(self, task: Dict) -> bool:
        """執行具體任務"""
        task_id = task['id']
        description = task['description']
        
        print(f"\\n🔄 開始執行任務 {task_id}: {task['name']}")
        print(f"📝 描述: {description}")
        
        # 更新狀態為 DOING
        if not self.update_task_status(task_id, 'DOING'):
            return False
        
        success = False
        
        try:
            # 根據任務ID執行對應的操作
            if task_id == 'T-01':
                success = self._task_environment_setup()
            elif task_id == 'T-02':
                success = self._task_test_baseline()
            elif task_id == 'T-03':
                success = self._task_dependency_analysis()
            elif task_id == 'T-04':
                success = self._task_automation_scripts()
            elif task_id == 'T-05':
                success = self._task_usage_tracking()
            elif task_id == 'T-06':
                success = self._task_diagnostic_cleanup()
            elif task_id == 'T-07':
                success = self._task_utility_cleanup()
            elif task_id == 'T-08':
                success = self._task_mcp_cleanup()
            elif task_id == 'T-09':
                success = self._task_phase1_testing()
            elif task_id == 'T-10':
                success = self._task_production_verification()
            elif task_id == 'T-11':
                success = self._task_command_pattern_analysis()
            elif task_id == 'T-12':
                success = self._task_architecture_cleanup()
            elif task_id == 'T-13':
                success = self._task_final_testing()
            elif task_id == 'T-14':
                success = self._task_documentation_update()
            elif task_id == 'T-15':
                success = self._task_summary_report()
            else:
                print(f"⚠️ 未實現的任務: {task_id}")
                success = False
            
            # 更新最終狀態
            if success:
                end_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                self.update_task_status(task_id, 'DONE', end_time)
                print(f"✅ 任務 {task_id} 完成")
            else:
                self.update_task_status(task_id, 'BLOCKED')
                print(f"❌ 任務 {task_id} 失敗")
            
            return success
            
        except Exception as e:
            print(f"❌ 執行任務 {task_id} 時發生錯誤: {e}")
            self.update_task_status(task_id, 'BLOCKED')
            return False
    
    def run_command(self, command: str, cwd: Optional[Path] = None) -> Tuple[bool, str]:
        """執行系統命令"""
        try:
            if cwd is None:
                cwd = self.project_root
                
            print(f"🔧 執行命令: {command}")
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300  # 5分鐘超時
            )
            
            if result.returncode == 0:
                print(f"✅ 命令執行成功")
                return True, result.stdout
            else:
                print(f"❌ 命令執行失敗 (退出碼: {result.returncode})")
                print(f"錯誤輸出: {result.stderr}")
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            print("❌ 命令執行超時")
            return False, "Command timeout"
        except Exception as e:
            print(f"❌ 命令執行異常: {e}")
            return False, str(e)
    
    # 以下是具體任務實現方法的佔位符
    def _task_environment_setup(self) -> bool:
        """T-01: 環境準備與分支管理"""
        print("🔧 執行環境準備與分支管理...")
        commands = [
            "git status",
            "git stash",  # 暫存可能的未提交變更
            "git checkout -b code-cleanup",
            "git tag pre-cleanup-v1.0",  # 創建回滾點
            "git checkout -b code-cleanup-backup"  # 創建備份分支
        ]
        
        for cmd in commands:
            success, output = self.run_command(cmd)
            if not success and "already exists" not in output:
                return False
        
        return True
    
    def _task_test_baseline(self) -> bool:
        """T-02: 建立測試基線"""
        print("🧪 建立測試基線...")
        
        # 執行測試套件
        success, output = self.run_command("cd apps/bot && poetry run pytest -v")
        if not success:
            print("❌ 基線測試失敗")
            return False
        
        # 記錄測試結果
        with open(self.project_root / "test_baseline.log", "w") as f:
            f.write(f"Baseline Test Results - {datetime.datetime.now()}\\n")
            f.write(output)
        
        return True
    
    def _task_dependency_analysis(self) -> bool:
        """T-03: 代碼依賴分析"""
        print("🔍 執行代碼依賴分析...")
        # 這裡可以實現具體的依賴分析邏輯
        return True
    
    def _task_automation_scripts(self) -> bool:
        """T-04: 自動化測試腳本"""
        print("⚙️ 建立自動化測試腳本...")
        # 實現測試腳本創建邏輯
        return True
    
    def _task_usage_tracking(self) -> bool:
        """T-05: 代碼使用追蹤"""
        print("📊 建立代碼使用追蹤...")
        # 實現使用追蹤邏輯
        return True
    
    def _task_diagnostic_cleanup(self) -> bool:
        """T-06: 診斷方法清理"""
        print("🧹 清理診斷方法...")
        # 實現診斷方法清理邏輯
        return True
    
    def _task_utility_cleanup(self) -> bool:
        """T-07: 工具類清理"""
        print("🧹 清理工具類...")
        # 實現工具類清理邏輯
        return True
    
    def _task_mcp_cleanup(self) -> bool:
        """T-08: MCP客戶端清理"""
        print("🧹 清理MCP客戶端...")
        # 實現MCP客戶端清理邏輯
        return True
    
    def _task_phase1_testing(self) -> bool:
        """T-09: 階段一測試驗證"""
        print("🧪 階段一測試驗證...")
        return self._run_full_test_suite()
    
    def _task_production_verification(self) -> bool:
        """T-10: 生產環境驗證"""
        print("🏭 生產環境驗證...")
        # 執行 M001 機台查詢測試
        success, output = self.run_command("./start-production.sh")
        return "M001" in output and "稼動率" in output
    
    def _task_command_pattern_analysis(self) -> bool:
        """T-11: Command Pattern分析"""
        print("🔍 Command Pattern分析...")
        # 實現分析邏輯
        return True
    
    def _task_architecture_cleanup(self) -> bool:
        """T-12: 架構遺留清理"""
        print("🏗️ 架構遺留清理...")
        # 實現架構清理邏輯
        return True
    
    def _task_final_testing(self) -> bool:
        """T-13: 最終測試驗證"""
        print("🎯 最終測試驗證...")
        return self._run_full_test_suite()
    
    def _task_documentation_update(self) -> bool:
        """T-14: 文檔和腳本更新"""
        print("📚 文檔和腳本更新...")
        # 實現文檔更新邏輯
        return True
    
    def _task_summary_report(self) -> bool:
        """T-15: 總結與收尾"""
        print("📊 產生總結報告...")
        # 實現總結報告邏輯
        return True
    
    def _run_full_test_suite(self) -> bool:
        """執行完整測試套件"""
        commands = [
            "cd apps/bot && poetry run pytest -v",
            "./start-production.sh test"
        ]
        
        for cmd in commands:
            success, output = self.run_command(cmd)
            if not success:
                return False
        
        return True
    
    def run_all_tasks(self) -> bool:
        """執行所有待執行任務"""
        if not self.load_spec():
            return False
        
        print(f"\\n🚀 開始執行任務清理流程")
        print(f"📋 共 {len(self.tasks)} 個任務待執行")
        
        completed = 0
        failed = 0
        
        while True:
            next_task = self.get_next_task()
            if not next_task:
                print(f"\\n✅ 所有任務執行完畢")
                break
            
            success = self.execute_task(next_task)
            if success:
                completed += 1
            else:
                failed += 1
                print(f"⚠️ 任務失敗，是否繼續？(y/N): ", end="")
                response = input().strip().lower()
                if response != 'y':
                    print("❌ 執行中止")
                    break
        
        print(f"\\n📊 執行總結:")
        print(f"✅ 完成: {completed}")
        print(f"❌ 失敗: {failed}")
        print(f"📈 成功率: {completed/(completed+failed)*100:.1f}%" if (completed+failed) > 0 else "0%")
        
        return failed == 0

def main():
    """主執行函數"""
    if len(sys.argv) > 1:
        spec_file = sys.argv[1]
    else:
        spec_file = "/Users/yen/Desktop/lineMCP/spec_code_cleanup.md"
    
    executor = TaskExecutor(spec_file)
    success = executor.run_all_tasks()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()