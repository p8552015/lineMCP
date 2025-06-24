#!/usr/bin/env python3
"""
GitHub CI 驗證工具
使用 GitHub Workflow Run API 查詢和驗證 CI 測試結果
"""

import os
import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path


class GitHubCIValidator:
    """GitHub CI 驗證器"""
    
    def __init__(self, token: str, owner: str = "p8552015", repo: str = "lineMCP"):
        """
        初始化驗證器
        
        Args:
            token: GitHub Personal Access Token
            owner: Repository owner
            repo: Repository name
        """
        self.token = token
        self.owner = owner
        self.repo = repo
        self.base_url = f"https://api.github.com/repos/{owner}/{repo}"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def get_latest_workflow_run(self, workflow_name: str = "Enhanced CI", 
                                branch: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        獲取最新的 workflow run
        
        Args:
            workflow_name: Workflow 名稱
            branch: 分支名稱（可選）
        
        Returns:
            Workflow run 資訊
        """
        # 獲取所有 workflows
        workflows_url = f"{self.base_url}/actions/workflows"
        response = requests.get(workflows_url, headers=self.headers)
        
        if response.status_code != 200:
            print(f"❌ 無法獲取 workflows: {response.status_code}")
            return None
        
        workflows = response.json()["workflows"]
        
        # 找到目標 workflow
        target_workflow = None
        for workflow in workflows:
            if workflow["name"] == workflow_name:
                target_workflow = workflow
                break
        
        if not target_workflow:
            print(f"❌ 找不到 workflow: {workflow_name}")
            return None
        
        # 獲取該 workflow 的最新 runs
        runs_url = f"{self.base_url}/actions/workflows/{target_workflow['id']}/runs"
        params = {"per_page": 10}
        
        if branch:
            params["branch"] = branch
        
        response = requests.get(runs_url, headers=self.headers, params=params)
        
        if response.status_code != 200:
            print(f"❌ 無法獲取 workflow runs: {response.status_code}")
            return None
        
        runs = response.json()["workflow_runs"]
        
        if not runs:
            print(f"❌ 沒有找到 workflow runs")
            return None
        
        # 返回最新的 run
        return runs[0]
    
    def wait_for_workflow_completion(self, run_id: int, timeout: int = 1800) -> Dict[str, Any]:
        """
        等待 workflow 完成
        
        Args:
            run_id: Workflow run ID
            timeout: 超時時間（秒）
        
        Returns:
            最終的 workflow run 狀態
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            run_url = f"{self.base_url}/actions/runs/{run_id}"
            response = requests.get(run_url, headers=self.headers)
            
            if response.status_code != 200:
                print(f"❌ 無法獲取 run 狀態: {response.status_code}")
                return {"status": "error", "conclusion": "error"}
            
            run = response.json()
            status = run["status"]
            
            print(f"⏳ Workflow 狀態: {status}")
            
            if status == "completed":
                return run
            
            # 等待 30 秒再檢查
            time.sleep(30)
        
        print(f"❌ Workflow 執行超時 ({timeout}秒)")
        return {"status": "timeout", "conclusion": "timeout"}
    
    def get_job_logs(self, run_id: int) -> Dict[str, str]:
        """
        獲取 job 日誌
        
        Args:
            run_id: Workflow run ID
        
        Returns:
            Job 名稱到日誌的映射
        """
        jobs_url = f"{self.base_url}/actions/runs/{run_id}/jobs"
        response = requests.get(jobs_url, headers=self.headers)
        
        if response.status_code != 200:
            print(f"❌ 無法獲取 jobs: {response.status_code}")
            return {}
        
        jobs = response.json()["jobs"]
        logs = {}
        
        for job in jobs:
            job_name = job["name"]
            job_id = job["id"]
            
            # 獲取 job 日誌
            logs_url = f"{self.base_url}/actions/jobs/{job_id}/logs"
            response = requests.get(logs_url, headers=self.headers)
            
            if response.status_code == 200:
                logs[job_name] = response.text
            else:
                logs[job_name] = f"無法獲取日誌: {response.status_code}"
        
        return logs
    
    def parse_test_results(self, run: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析測試結果
        
        Args:
            run: Workflow run 資訊
        
        Returns:
            結構化的測試結果
        """
        conclusion = run.get("conclusion", "unknown")
        
        # 獲取 jobs 詳情
        jobs_url = f"{self.base_url}/actions/runs/{run['id']}/jobs"
        response = requests.get(jobs_url, headers=self.headers)
        
        jobs_data = []
        if response.status_code == 200:
            for job in response.json()["jobs"]:
                job_info = {
                    "name": job["name"],
                    "status": job["status"],
                    "conclusion": job.get("conclusion", ""),
                    "started_at": job.get("started_at", ""),
                    "completed_at": job.get("completed_at", ""),
                    "steps": []
                }
                
                # 收集失敗的步驟
                for step in job.get("steps", []):
                    if step.get("conclusion") == "failure":
                        job_info["steps"].append({
                            "name": step["name"],
                            "conclusion": step["conclusion"]
                        })
                
                jobs_data.append(job_info)
        
        return {
            "run_id": run["id"],
            "status": run["status"],
            "conclusion": conclusion,
            "created_at": run["created_at"],
            "updated_at": run["updated_at"],
            "html_url": run["html_url"],
            "jobs": jobs_data,
            "summary": self._generate_summary(conclusion, jobs_data)
        }
    
    def _generate_summary(self, conclusion: str, jobs: List[Dict[str, Any]]) -> str:
        """生成測試摘要"""
        if conclusion == "success":
            return "✅ 所有測試通過"
        elif conclusion == "failure":
            failed_jobs = [job["name"] for job in jobs if job["conclusion"] == "failure"]
            return f"❌ 測試失敗: {', '.join(failed_jobs)}"
        elif conclusion == "cancelled":
            return "⚠️ 測試被取消"
        else:
            return f"❓ 未知狀態: {conclusion}"
    
    def validate_task_with_ci(self, task_id: str, branch: str = "main") -> bool:
        """
        使用 CI 驗證任務
        
        Args:
            task_id: 任務 ID
            branch: 分支名稱
        
        Returns:
            是否通過驗證
        """
        print(f"\n🔍 開始 CI 驗證任務 {task_id}")
        
        # 獲取最新的 workflow run
        run = self.get_latest_workflow_run(branch=branch)
        
        if not run:
            print("❌ 無法獲取 workflow run")
            return False
        
        print(f"📊 Workflow Run ID: {run['id']}")
        print(f"🔗 URL: {run['html_url']}")
        
        # 如果還在運行中，等待完成
        if run["status"] != "completed":
            print("⏳ 等待 CI 執行完成...")
            run = self.wait_for_workflow_completion(run["id"])
        
        # 解析結果
        results = self.parse_test_results(run)
        
        # 保存結果報告
        self.save_ci_report(task_id, results)
        
        # 顯示摘要
        print(f"\n📊 CI 測試結果:")
        print(f"   狀態: {results['status']}")
        print(f"   結論: {results['conclusion']}")
        print(f"   摘要: {results['summary']}")
        
        return results["conclusion"] == "success"
    
    def save_ci_report(self, task_id: str, results: Dict[str, Any]):
        """保存 CI 測試報告"""
        report_dir = Path("ci_reports")
        report_dir.mkdir(exist_ok=True)
        
        report_file = report_dir / f"ci_report_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"📄 CI 報告已保存: {report_file}")
        
        # 創建 Markdown 格式報告
        md_file = report_dir / f"ci_report_{task_id}.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(f"# CI 測試報告 - {task_id}\n\n")
            f.write(f"**Run ID**: {results['run_id']}\n")
            f.write(f"**時間**: {results['updated_at']}\n")
            f.write(f"**結果**: {results['summary']}\n")
            f.write(f"**連結**: [{results['run_id']}]({results['html_url']})\n\n")
            
            f.write("## Jobs 詳情\n\n")
            for job in results["jobs"]:
                emoji = "✅" if job["conclusion"] == "success" else "❌"
                f.write(f"### {emoji} {job['name']}\n")
                f.write(f"- 狀態: {job['conclusion']}\n")
                
                if job["steps"]:
                    f.write("- 失敗步驟:\n")
                    for step in job["steps"]:
                        f.write(f"  - {step['name']}\n")
                
                f.write("\n")


def main():
    """測試主函數"""
    # 從環境變數或命令行獲取 token
    token = os.getenv("GITHUB_PAT", "")
    
    if not token:
        print("❌ 請設置 GITHUB_PAT 環境變數")
        return
    
    validator = GitHubCIValidator(token)
    
    # 測試獲取最新的 workflow run
    run = validator.get_latest_workflow_run()
    
    if run:
        print(f"✅ 找到最新的 workflow run:")
        print(f"   ID: {run['id']}")
        print(f"   狀態: {run['status']}")
        print(f"   結論: {run.get('conclusion', 'N/A')}")
        
        # 驗證任務
        validator.validate_task_with_ci("TEST-01")


if __name__ == "__main__":
    main()