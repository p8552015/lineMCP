#!/usr/bin/env python3
"""
Git自動化操作模組
處理修復代碼的自動提交、推送和回滾操作
"""

import os
import re
import subprocess
import tempfile
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
from auto_fix_generator import FixSolution, FixAction


@dataclass
class GitOperation:
    """Git操作記錄"""
    operation_id: str
    operation_type: str  # 'create_branch', 'commit', 'push', 'rollback'
    branch_name: str
    commit_hash: Optional[str] = None
    files_modified: List[str] = None
    timestamp: str = None
    success: bool = False
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.files_modified is None:
            self.files_modified = []
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class GitAutomationModule:
    """Git自動化操作模組"""
    
    def __init__(self, 
                 repo_path: str = "/Users/yen/Desktop/lineMCP",
                 log_file: str = "git_automation.log"):
        """
        初始化Git自動化模組
        
        Args:
            repo_path: Git倉庫路徑
            log_file: 日誌文件路徑
        """
        self.repo_path = Path(repo_path)
        self.setup_logging(log_file)
        
        # 檢查Git倉庫狀態
        self.verify_git_repo()
        
        # 操作歷史
        self.operations_history: List[GitOperation] = []
        
        # 安全設置
        self.auto_push_enabled = True
        self.require_clean_working_tree = True
        self.max_files_per_commit = 10
        
        # 分支命名規則
        self.branch_prefix = "auto-fix"
        
        # 備份標籤
        self.backup_tags: List[str] = []
    
    def setup_logging(self, log_file: str):
        """設置日誌"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def verify_git_repo(self):
        """驗證Git倉庫狀態"""
        if not (self.repo_path / '.git').exists():
            raise ValueError(f"路徑 {self.repo_path} 不是有效的Git倉庫")
        
        # 檢查Git配置
        try:
            self._run_git_command(['config', 'user.name'], check_output=True)
            self._run_git_command(['config', 'user.email'], check_output=True)
            self.logger.info("✅ Git配置驗證通過")
        except subprocess.CalledProcessError:
            self.logger.warning("⚠️ Git用戶配置可能不完整")
    
    def _run_git_command(self, 
                        args: List[str], 
                        check_output: bool = False, 
                        timeout: int = 30) -> Tuple[bool, str]:
        """
        執行Git命令
        
        Args:
            args: Git命令參數
            check_output: 是否獲取輸出
            timeout: 超時時間（秒）
            
        Returns:
            (成功狀態, 輸出內容)
        """
        try:
            cmd = ['git'] + args
            self.logger.debug(f"執行Git命令: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=check_output
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                self.logger.debug(f"Git命令成功: {output}")
                return True, output
            else:
                error = result.stderr.strip()
                self.logger.error(f"Git命令失敗: {error}")
                return False, error
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"Git命令超時: {' '.join(cmd)}")
            return False, "命令執行超時"
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git命令執行錯誤: {e}")
            return False, str(e)
        except Exception as e:
            self.logger.error(f"Git命令意外錯誤: {e}")
            return False, str(e)
    
    def get_current_branch(self) -> Optional[str]:
        """獲取當前分支名稱"""
        success, output = self._run_git_command(['branch', '--show-current'])
        return output if success else None
    
    def get_current_commit_hash(self) -> Optional[str]:
        """獲取當前提交哈希"""
        success, output = self._run_git_command(['rev-parse', 'HEAD'])
        return output if success else None
    
    def is_working_tree_clean(self) -> bool:
        """檢查工作目錄是否乾淨"""
        success, output = self._run_git_command(['status', '--porcelain'])
        return success and len(output.strip()) == 0
    
    def create_backup_tag(self, tag_name: Optional[str] = None) -> Optional[str]:
        """
        創建備份標籤
        
        Args:
            tag_name: 標籤名稱，如果為None則自動生成
            
        Returns:
            創建的標籤名稱
        """
        if not tag_name:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            tag_name = f"auto-backup-{timestamp}"
        
        success, output = self._run_git_command([
            'tag', '-a', tag_name, '-m', f'自動備份標籤 - {datetime.now()}'
        ])
        
        if success:
            self.backup_tags.append(tag_name)
            self.logger.info(f"✅ 創建備份標籤: {tag_name}")
            return tag_name
        else:
            self.logger.error(f"❌ 創建備份標籤失敗: {output}")
            return None
    
    def create_fix_branch(self, problem_description: str) -> Optional[str]:
        """
        創建修復分支
        
        Args:
            problem_description: 問題描述
            
        Returns:
            分支名稱
        """
        # 生成分支名稱
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 清理問題描述，生成安全的分支名稱
        clean_desc = re.sub(r'[^a-zA-Z0-9_-]', '_', problem_description.lower())
        clean_desc = re.sub(r'_+', '_', clean_desc)[:30]  # 限制長度
        
        branch_name = f"{self.branch_prefix}/{clean_desc}_{timestamp}"
        
        # 檢查工作目錄是否乾淨（如果需要）
        if self.require_clean_working_tree and not self.is_working_tree_clean():
            self.logger.error("❌ 工作目錄不乾淨，無法創建修復分支")
            return None
        
        # 創建並切換到新分支
        success, output = self._run_git_command(['checkout', '-b', branch_name])
        
        if success:
            operation = GitOperation(
                operation_id=f"branch_{timestamp}",
                operation_type="create_branch",
                branch_name=branch_name,
                success=True
            )
            self.operations_history.append(operation)
            
            self.logger.info(f"✅ 創建修復分支: {branch_name}")
            return branch_name
        else:
            self.logger.error(f"❌ 創建分支失敗: {output}")
            return None
    
    async def apply_fix_solution(self, solution: FixSolution) -> bool:
        """
        應用修復方案
        
        Args:
            solution: 修復方案
            
        Returns:
            是否成功
        """
        self.logger.info(f"🔧 開始應用修復方案: {solution.solution_name}")
        
        # 創建備份標籤
        backup_tag = self.create_backup_tag()
        if not backup_tag:
            self.logger.error("❌ 無法創建備份標籤，中止修復")
            return False
        
        # 創建修復分支
        branch_name = self.create_fix_branch(solution.solution_name)
        if not branch_name:
            self.logger.error("❌ 無法創建修復分支，中止修復")
            return False
        
        modified_files = []
        success_count = 0
        
        try:
            # 逐個應用修復動作
            for i, action in enumerate(solution.actions, 1):
                self.logger.info(f"   執行動作 {i}/{len(solution.actions)}: {action.description}")
                
                action_success = await self._apply_fix_action(action)
                
                if action_success:
                    success_count += 1
                    if action.target_path not in modified_files:
                        modified_files.append(action.target_path)
                else:
                    self.logger.error(f"❌ 動作執行失敗: {action.description}")
                    
                    # 如果是高風險動作失敗，立即停止
                    if action.risk_level == "high":
                        self.logger.error("❌ 高風險動作失敗，中止修復")
                        break
            
            # 檢查是否有成功的修復
            if success_count == 0:
                self.logger.error("❌ 沒有任何修復動作成功")
                return False
            
            # 提交變更
            commit_success = self._commit_changes(solution, modified_files)
            
            if commit_success and self.auto_push_enabled:
                push_success = self._push_branch(branch_name)
                if not push_success:
                    self.logger.warning("⚠️ 推送失敗，但本地提交成功")
            
            self.logger.info(f"✅ 修復方案應用完成: {success_count}/{len(solution.actions)} 個動作成功")
            return commit_success
            
        except Exception as e:
            self.logger.error(f"❌ 應用修復方案時發生錯誤: {e}")
            return False
    
    async def _apply_fix_action(self, action: FixAction) -> bool:
        """
        應用單個修復動作
        
        Args:
            action: 修復動作
            
        Returns:
            是否成功
        """
        try:
            if action.action_type == "file_edit":
                return self._edit_file(action)
            elif action.action_type == "file_create":
                return self._create_file(action)
            elif action.action_type == "file_delete":
                return self._delete_file(action)
            elif action.action_type == "command_run":
                return self._run_command(action)
            else:
                self.logger.error(f"❌ 未知的動作類型: {action.action_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 執行修復動作失敗: {e}")
            return False
    
    def _edit_file(self, action: FixAction) -> bool:
        """編輯文件"""
        try:
            file_path = self.repo_path / action.target_path
            
            # 確保文件存在
            if not file_path.exists():
                self.logger.error(f"❌ 文件不存在: {file_path}")
                return False
            
            # 備份原文件
            if action.backup_required:
                backup_path = f"{file_path}.backup_{datetime.now().strftime('%H%M%S')}"
                file_path.rename(backup_path)
                self.logger.info(f"📄 已備份文件: {backup_path}")
            
            # 讀取文件內容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 應用修改
            if action.search_pattern and action.replacement:
                # 使用正則表達式替換
                new_content = re.sub(action.search_pattern, action.replacement, content, flags=re.MULTILINE)
                
                if new_content == content:
                    self.logger.warning(f"⚠️ 未找到匹配模式: {action.search_pattern}")
                    return False
            else:
                # 直接替換內容
                new_content = action.content or content
            
            # 寫入新內容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            self.logger.info(f"✅ 文件編輯成功: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 文件編輯失敗: {e}")
            return False
    
    def _create_file(self, action: FixAction) -> bool:
        """創建文件"""
        try:
            file_path = self.repo_path / action.target_path
            
            # 確保目錄存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 檢查文件是否已存在
            if file_path.exists():
                self.logger.warning(f"⚠️ 文件已存在: {file_path}")
                return False
            
            # 創建文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(action.content or "")
            
            self.logger.info(f"✅ 文件創建成功: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 文件創建失敗: {e}")
            return False
    
    def _delete_file(self, action: FixAction) -> bool:
        """刪除文件"""
        try:
            file_path = self.repo_path / action.target_path
            
            if not file_path.exists():
                self.logger.warning(f"⚠️ 文件不存在，無需刪除: {file_path}")
                return True
            
            # 備份後刪除
            if action.backup_required:
                backup_path = f"{file_path}.deleted_{datetime.now().strftime('%H%M%S')}"
                file_path.rename(backup_path)
                self.logger.info(f"📄 文件已備份並刪除: {backup_path}")
            else:
                file_path.unlink()
                self.logger.info(f"✅ 文件刪除成功: {file_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 文件刪除失敗: {e}")
            return False
    
    def _run_command(self, action: FixAction) -> bool:
        """執行命令"""
        try:
            if not action.command:
                self.logger.error("❌ 命令為空")
                return False
            
            # 設置工作目錄
            work_dir = self.repo_path / action.target_path if action.target_path != "." else self.repo_path
            
            self.logger.info(f"🔧 執行命令: {action.command}")
            
            result = subprocess.run(
                action.command,
                shell=True,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5分鐘超時
            )
            
            if result.returncode == 0:
                self.logger.info(f"✅ 命令執行成功")
                if result.stdout.strip():
                    self.logger.debug(f"命令輸出: {result.stdout.strip()}")
                return True
            else:
                self.logger.error(f"❌ 命令執行失敗 (返回碼: {result.returncode})")
                if result.stderr.strip():
                    self.logger.error(f"錯誤輸出: {result.stderr.strip()}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("❌ 命令執行超時")
            return False
        except Exception as e:
            self.logger.error(f"❌ 命令執行異常: {e}")
            return False
    
    def _commit_changes(self, solution: FixSolution, modified_files: List[str]) -> bool:
        """提交變更"""
        try:
            # 檢查是否有變更
            if not self._has_changes():
                self.logger.warning("⚠️ 沒有檢測到變更，跳過提交")
                return True
            
            # 添加修改的文件到暫存區
            if modified_files:
                for file_path in modified_files:
                    success, output = self._run_git_command(['add', file_path])
                    if not success:
                        self.logger.error(f"❌ 添加文件到暫存區失敗: {file_path}")
            else:
                # 添加所有變更
                success, output = self._run_git_command(['add', '.'])
                if not success:
                    self.logger.error(f"❌ 添加變更到暫存區失敗: {output}")
                    return False
            
            # 生成提交訊息
            commit_message = self._generate_commit_message(solution)
            
            # 提交變更
            success, output = self._run_git_command(['commit', '-m', commit_message])
            
            if success:
                # 獲取提交哈希
                commit_hash = self.get_current_commit_hash()
                
                operation = GitOperation(
                    operation_id=f"commit_{datetime.now().strftime('%H%M%S')}",
                    operation_type="commit",
                    branch_name=self.get_current_branch() or "unknown",
                    commit_hash=commit_hash,
                    files_modified=modified_files,
                    success=True
                )
                self.operations_history.append(operation)
                
                self.logger.info(f"✅ 變更提交成功: {commit_hash}")
                return True
            else:
                self.logger.error(f"❌ 提交失敗: {output}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 提交過程發生錯誤: {e}")
            return False
    
    def _has_changes(self) -> bool:
        """檢查是否有變更"""
        # 檢查暫存區
        success, staged = self._run_git_command(['diff', '--cached', '--name-only'])
        if success and staged.strip():
            return True
        
        # 檢查工作目錄
        success, unstaged = self._run_git_command(['diff', '--name-only'])
        if success and unstaged.strip():
            return True
        
        # 檢查未追蹤文件
        success, untracked = self._run_git_command(['ls-files', '--others', '--exclude-standard'])
        if success and untracked.strip():
            return True
        
        return False
    
    def _generate_commit_message(self, solution: FixSolution) -> str:
        """生成提交訊息"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        message = f"""自動修復: {solution.solution_name}

問題類型: {solution.problem_category.value}
修復描述: {solution.description}
成功率預估: {solution.estimated_success_rate:.1%}
風險評估: {solution.risk_assessment}

修復動作:"""
        
        for i, action in enumerate(solution.actions, 1):
            message += f"\n{i}. {action.description}"
        
        message += f"""

生成時間: {timestamp}
AI生成: {'是' if solution.ai_generated else '否'}

🤖 自動生成提交 - Claude Code CI修復系統
"""
        
        return message
    
    def _push_branch(self, branch_name: str) -> bool:
        """推送分支到遠端"""
        try:
            self.logger.info(f"📤 推送分支到遠端: {branch_name}")
            
            # 設置上游分支並推送
            success, output = self._run_git_command([
                'push', '-u', 'origin', branch_name
            ])
            
            if success:
                operation = GitOperation(
                    operation_id=f"push_{datetime.now().strftime('%H%M%S')}",
                    operation_type="push",
                    branch_name=branch_name,
                    success=True
                )
                self.operations_history.append(operation)
                
                self.logger.info(f"✅ 分支推送成功: {branch_name}")
                return True
            else:
                self.logger.error(f"❌ 分支推送失敗: {output}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 推送過程發生錯誤: {e}")
            return False
    
    def rollback_to_backup(self, backup_tag: str) -> bool:
        """回滾到備份標籤"""
        try:
            self.logger.info(f"🔄 開始回滾到備份標籤: {backup_tag}")
            
            # 檢查標籤是否存在
            success, output = self._run_git_command(['tag', '-l', backup_tag])
            if not success or backup_tag not in output:
                self.logger.error(f"❌ 備份標籤不存在: {backup_tag}")
                return False
            
            # 重置到標籤
            success, output = self._run_git_command(['reset', '--hard', backup_tag])
            
            if success:
                self.logger.info(f"✅ 回滾成功: {backup_tag}")
                return True
            else:
                self.logger.error(f"❌ 回滾失敗: {output}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 回滾過程發生錯誤: {e}")
            return False
    
    def cleanup_fix_branches(self, keep_recent: int = 5) -> int:
        """清理舊的修復分支"""
        try:
            self.logger.info("🧹 開始清理舊的修復分支...")
            
            # 獲取所有修復分支
            success, output = self._run_git_command(['branch', '--list', f'{self.branch_prefix}/*'])
            
            if not success:
                self.logger.error(f"❌ 獲取分支列表失敗: {output}")
                return 0
            
            branches = [branch.strip('* ') for branch in output.split('\n') if branch.strip()]
            fix_branches = [b for b in branches if b.startswith(self.branch_prefix)]
            
            if len(fix_branches) <= keep_recent:
                self.logger.info(f"修復分支數量 ({len(fix_branches)}) 未超過保留數量 ({keep_recent})")
                return 0
            
            # 按時間排序（根據分支名稱中的時間戳）
            fix_branches.sort()
            branches_to_delete = fix_branches[:-keep_recent]
            
            deleted_count = 0
            for branch in branches_to_delete:
                success, output = self._run_git_command(['branch', '-D', branch])
                if success:
                    deleted_count += 1
                    self.logger.info(f"🗑️ 已刪除分支: {branch}")
                else:
                    self.logger.error(f"❌ 刪除分支失敗 {branch}: {output}")
            
            self.logger.info(f"✅ 清理完成，刪除了 {deleted_count} 個舊分支")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"❌ 清理分支過程發生錯誤: {e}")
            return 0
    
    def get_operations_history(self) -> List[GitOperation]:
        """獲取操作歷史"""
        return self.operations_history.copy()
    
    def get_status_summary(self) -> Dict[str, Any]:
        """獲取狀態摘要"""
        return {
            "current_branch": self.get_current_branch(),
            "current_commit": self.get_current_commit_hash(),
            "working_tree_clean": self.is_working_tree_clean(),
            "backup_tags_count": len(self.backup_tags),
            "operations_count": len(self.operations_history),
            "auto_push_enabled": self.auto_push_enabled,
            "require_clean_working_tree": self.require_clean_working_tree
        }


def main():
    """測試主函數"""
    git_module = GitAutomationModule()
    
    print("🔧 測試Git自動化模組...")
    
    # 測試基本功能
    print(f"當前分支: {git_module.get_current_branch()}")
    print(f"當前提交: {git_module.get_current_commit_hash()}")
    print(f"工作目錄乾淨: {git_module.is_working_tree_clean()}")
    
    # 獲取狀態摘要
    status = git_module.get_status_summary()
    print("\n📊 狀態摘要:")
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    print("\n✅ Git自動化模組測試完成")


if __name__ == "__main__":
    main()