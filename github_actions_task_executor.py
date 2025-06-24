#!/usr/bin/env python3
"""
GitHub Actions 任務執行器核心邏輯
基於任務規劃模板，實現任務狀態即時更新和 Markdown 表格管理
"""

import os
import re
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from dataclasses import dataclass
import traceback

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Task:
    """任務數據結構"""
    id: str
    name: str
    description: str
    priority: str
    assignee: str
    status: str
    start_time: str
    end_time: str


class MarkdownTaskManager:
    """Markdown 任務表格管理器"""
    
    def __init__(self, spec_file_path: str):
        self.spec_file_path = Path(spec_file_path)
        self.start_marker = "<!-- TASKS START -->"
        self.end_marker = "<!-- TASKS END -->"
        
    def read_spec_file(self) -> str:
        """讀取規格檔案"""
        try:
            with open(self.spec_file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"規格檔案不存在: {self.spec_file_path}")
            raise
        except Exception as e:
            logger.error(f"讀取規格檔案失敗: {e}")
            raise
    
    def write_spec_file(self, content: str) -> None:
        """寫入規格檔案"""
        try:
            with open(self.spec_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"規格檔案已更新: {self.spec_file_path}")
        except Exception as e:
            logger.error(f"寫入規格檔案失敗: {e}")
            raise
    
    def extract_task_table(self, content: str) -> str:
        """提取任務表格區域"""
        start_idx = content.find(self.start_marker)
        end_idx = content.find(self.end_marker)
        
        if start_idx == -1 or end_idx == -1:
            raise ValueError("找不到任務表格標記")
        
        return content[start_idx:end_idx + len(self.end_marker)]
    
    def parse_tasks(self, table_content: str) -> List[Task]:
        """解析任務表格"""
        tasks = []
        
        # 找到表格行
        lines = table_content.split('\n')
        table_lines = []
        in_table = False
        
        for line in lines:
            if '| ID |' in line:
                in_table = True
                continue
            elif in_table and line.strip().startswith('|') and not line.strip().startswith('|---'):
                table_lines.append(line.strip())
            elif in_table and not line.strip().startswith('|'):
                break
        
        # 解析每一行
        for line in table_lines:
            if not line.strip():
                continue
                
            # 分割表格欄位
            columns = [col.strip() for col in line.split('|')[1:-1]]  # 去掉首尾空元素
            
            if len(columns) >= 8:
                task = Task(
                    id=columns[0],
                    name=columns[1],
                    description=columns[2],
                    priority=columns[3],
                    assignee=columns[4],
                    status=columns[5],
                    start_time=columns[6],
                    end_time=columns[7]
                )
                tasks.append(task)
        
        logger.info(f"解析到 {len(tasks)} 個任務")
        return tasks
    
    def update_task_status(self, task_id: str, new_status: str, 
                          start_time: Optional[str] = None,
                          end_time: Optional[str] = None) -> bool:
        """更新任務狀態"""
        try:
            content = self.read_spec_file()
            
            # 準備時間戳記
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            if new_status == "DOING" and not start_time:
                start_time = current_time
            elif new_status == "DONE" and not end_time:
                end_time = current_time
            
            # 更新狀態的正則表達式
            pattern = rf'(\| {re.escape(task_id)} \| [^|]+ \| [^|]+ \| [^|]+ \| [^|]+ \| )([^|]+)( \| )([^|]*)( \| )([^|]*)( \|)'
            
            def replace_task(match):
                current_start = match.group(4).strip()
                current_end = match.group(6).strip()
                
                # 更新開始時間
                if start_time:
                    new_start = start_time
                else:
                    new_start = current_start if current_start else ""
                
                # 更新結束時間
                if end_time:
                    new_end = end_time
                else:
                    new_end = current_end if current_end else ""
                
                return f'{match.group(1)}{new_status}{match.group(3)}{new_start}{match.group(5)}{new_end}{match.group(7)}'
            
            new_content = re.sub(pattern, replace_task, content)
            
            if new_content != content:
                self.write_spec_file(new_content)
                logger.info(f"任務 {task_id} 狀態更新為 {new_status}")
                return True
            else:
                logger.warning(f"任務 {task_id} 狀態更新失敗，可能找不到匹配的任務")
                return False
                
        except Exception as e:
            logger.error(f"更新任務狀態失敗: {e}")
            return False
    
    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """根據 ID 獲取任務"""
        try:
            content = self.read_spec_file()
            table_content = self.extract_task_table(content)
            tasks = self.parse_tasks(table_content)
            
            for task in tasks:
                if task.id == task_id:
                    return task
            
            return None
        except Exception as e:
            logger.error(f"獲取任務失敗: {e}")
            return None
    
    def get_all_tasks(self) -> List[Task]:
        """獲取所有任務"""
        try:
            content = self.read_spec_file()
            table_content = self.extract_task_table(content)
            return self.parse_tasks(table_content)
        except Exception as e:
            logger.error(f"獲取任務列表失敗: {e}")
            return []


class TaskExecutor:
    """任務執行器"""
    
    def __init__(self, spec_file_path: str, project_root: str):
        self.task_manager = MarkdownTaskManager(spec_file_path)
        self.project_root = Path(project_root)
        self.task_handlers: Dict[str, Callable] = {}
        self.execution_log = []
        
    def register_task_handler(self, task_id: str, handler: Callable) -> None:
        """註冊任務處理器"""
        self.task_handlers[task_id] = handler
        logger.info(f"註冊任務處理器: {task_id}")
    
    async def execute_task(self, task_id: str) -> bool:
        """執行單一任務"""
        task = self.task_manager.get_task_by_id(task_id)
        if not task:
            logger.error(f"任務不存在: {task_id}")
            return False
        
        logger.info(f"開始執行任務: {task_id} - {task.name}")
        
        # 更新狀態為 DOING
        self.task_manager.update_task_status(task_id, "DOING")
        
        try:
            # 檢查是否有註冊的處理器
            if task_id in self.task_handlers:
                handler = self.task_handlers[task_id]
                
                # 執行處理器
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(task)
                else:
                    result = handler(task)
                
                # 根據結果更新狀態
                if result:
                    self.task_manager.update_task_status(task_id, "DONE")
                    logger.info(f"任務執行成功: {task_id}")
                    self.execution_log.append({
                        "task_id": task_id,
                        "status": "success",
                        "timestamp": datetime.now().isoformat()
                    })
                    return True
                else:
                    self.task_manager.update_task_status(task_id, "BLOCKED")
                    logger.error(f"任務執行失敗: {task_id}")
                    self.execution_log.append({
                        "task_id": task_id,
                        "status": "failed",
                        "timestamp": datetime.now().isoformat()
                    })
                    return False
            else:
                # 如果沒有處理器，標記為 BLOCKED
                self.task_manager.update_task_status(task_id, "BLOCKED")
                logger.warning(f"任務缺少處理器: {task_id}")
                return False
                
        except Exception as e:
            logger.error(f"任務執行出現異常: {task_id} - {e}")
            logger.error(traceback.format_exc())
            self.task_manager.update_task_status(task_id, "BLOCKED")
            self.execution_log.append({
                "task_id": task_id,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            return False
    
    async def execute_task_sequence(self, task_ids: List[str], 
                                  stop_on_failure: bool = True) -> Dict[str, bool]:
        """執行任務序列"""
        results = {}
        
        logger.info(f"開始執行任務序列: {task_ids}")
        
        for task_id in task_ids:
            success = await self.execute_task(task_id)
            results[task_id] = success
            
            if not success and stop_on_failure:
                logger.warning(f"任務失敗，停止執行序列: {task_id}")
                break
        
        logger.info(f"任務序列執行完成，結果: {results}")
        return results
    
    async def execute_all_pending_tasks(self) -> Dict[str, bool]:
        """執行所有待處理的任務"""
        tasks = self.task_manager.get_all_tasks()
        pending_tasks = [task.id for task in tasks if task.status == "TODO"]
        
        logger.info(f"發現 {len(pending_tasks)} 個待處理任務")
        
        if not pending_tasks:
            logger.info("沒有待處理的任務")
            return {}
        
        return await self.execute_task_sequence(pending_tasks)
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """獲取執行摘要"""
        total_tasks = len(self.execution_log)
        successful_tasks = len([log for log in self.execution_log if log["status"] == "success"])
        failed_tasks = len([log for log in self.execution_log if log["status"] in ["failed", "error"]])
        
        return {
            "total_executed": total_tasks,
            "successful": successful_tasks,
            "failed": failed_tasks,
            "success_rate": successful_tasks / total_tasks if total_tasks > 0 else 0,
            "execution_log": self.execution_log
        }
    
    def save_execution_report(self, output_path: str) -> None:
        """保存執行報告"""
        summary = self.get_execution_summary()
        
        report = {
            "execution_summary": summary,
            "timestamp": datetime.now().isoformat(),
            "spec_file": str(self.task_manager.spec_file_path),
            "project_root": str(self.project_root)
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"執行報告已保存: {output_path}")


# =============================================================================
# 示例任務處理器
# =============================================================================

async def sample_github_api_handler(task: Task) -> bool:
    """示例：GitHub API 日誌獲取處理器"""
    logger.info(f"執行 GitHub API 任務: {task.description}")
    
    # 模擬 API 呼叫
    await asyncio.sleep(1)
    
    # 這裡會整合實際的 GitHub API 邏輯
    logger.info("GitHub API 日誌獲取完成")
    return True


async def sample_mcp_search_handler(task: Task) -> bool:
    """示例：MCP 搜尋處理器"""
    logger.info(f"執行 MCP 搜尋任務: {task.description}")
    
    # 模擬 MCP 搜尋
    await asyncio.sleep(1)
    
    # 這裡會整合實際的 MCP 搜尋邏輯
    logger.info("MCP 文件搜尋完成")
    return True


def sample_production_test_handler(task: Task) -> bool:
    """示例：生產環境測試處理器"""
    logger.info(f"執行生產測試任務: {task.description}")
    
    # 這裡會整合實際的生產測試邏輯
    logger.info("生產環境測試完成")
    return True


# =============================================================================
# 主函數和測試
# =============================================================================

async def main():
    """主函數示例"""
    spec_file = "/Users/yen/Desktop/lineMCP/spec_Github_actions_錯誤診斷.md"
    project_root = "/Users/yen/Desktop/lineMCP"
    
    # 創建任務執行器
    executor = TaskExecutor(spec_file, project_root)
    
    # 註冊任務處理器
    executor.register_task_handler("T-01", sample_github_api_handler)
    executor.register_task_handler("T-02", sample_mcp_search_handler)
    executor.register_task_handler("T-07", sample_production_test_handler)
    
    # 執行特定任務序列
    task_sequence = ["T-01", "T-02", "T-07"]
    results = await executor.execute_task_sequence(task_sequence)
    
    # 顯示結果
    print("任務執行結果:")
    for task_id, success in results.items():
        status = "✅ 成功" if success else "❌ 失敗"
        print(f"  {task_id}: {status}")
    
    # 獲取執行摘要
    summary = executor.get_execution_summary()
    print(f"\n執行摘要:")
    print(f"  總任務數: {summary['total_executed']}")
    print(f"  成功: {summary['successful']}")
    print(f"  失敗: {summary['failed']}")
    print(f"  成功率: {summary['success_rate']:.2%}")
    
    # 保存執行報告
    report_path = f"/tmp/task_execution_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    executor.save_execution_report(report_path)
    print(f"\n執行報告已保存: {report_path}")


if __name__ == "__main__":
    # 測試任務管理器
    spec_file = "/Users/yen/Desktop/lineMCP/spec_Github_actions_錯誤診斷.md"
    
    if os.path.exists(spec_file):
        print("測試任務管理器...")
        manager = MarkdownTaskManager(spec_file)
        
        # 獲取所有任務
        tasks = manager.get_all_tasks()
        print(f"發現 {len(tasks)} 個任務:")
        for task in tasks:
            print(f"  {task.id}: {task.name} ({task.status})")
        
        print("\n執行完整任務流程...")
        asyncio.run(main())
    else:
        print(f"規格檔案不存在: {spec_file}")
        print("請先執行 github_actions_error_diagnosis.sh 創建規格檔案")