#!/usr/bin/env python3
"""
測試錯誤分析器的簡化版本
"""

import requests
import re
from datetime import datetime

# 配置
OWNER = "p8552015"
REPO = "lineMCP"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

def get_failed_runs():
    """獲取失敗的 runs"""
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/actions/runs"
    params = {
        "status": "failure",
        "per_page": 5
    }
    
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    
    data = response.json()
    runs = data.get("workflow_runs", [])
    
    print("最近失敗的 workflow runs:")
    for i, run in enumerate(runs, 1):
        print(f"{i}. Run ID: {run['id']}")
        print(f"   名稱: {run['name']}")
        print(f"   分支: {run['head_branch']}")
        print(f"   狀態: {run['status']} - {run['conclusion']}")
        print(f"   時間: {run['created_at']}")
        print(f"   HTML URL: {run['html_url']}")
        print()
    
    return runs

def analyze_workflow_issues():
    """分析 workflow 常見問題"""
    runs = get_failed_runs()
    
    if not runs:
        print("沒有找到失敗的 workflow runs")
        return
    
    latest_run = runs[0]
    run_id = latest_run['id']
    
    print(f"分析最新失敗的 run: {run_id}")
    
    # 獲取 jobs
    jobs_url = f"https://api.github.com/repos/{OWNER}/{REPO}/actions/runs/{run_id}/jobs"
    jobs_response = requests.get(jobs_url, headers=HEADERS)
    jobs_response.raise_for_status()
    
    jobs_data = jobs_response.json()
    failed_jobs = [j for j in jobs_data.get('jobs', []) if j['conclusion'] == 'failure']
    
    print(f"失敗的 jobs 數量: {len(failed_jobs)}")
    
    for job in failed_jobs:
        print(f"\n失敗的 Job: {job['name']}")
        print(f"Job ID: {job['id']}")
        print(f"狀態: {job['status']} - {job['conclusion']}")
        
        # 分析 steps
        for step in job.get('steps', []):
            if step['conclusion'] == 'failure':
                print(f"  失敗的步驟: {step['name']}")
                print(f"  步驟號: {step['number']}")
    
    # 生成基本建議
    print("\n🔧 基於失敗模式的建議:")
    
    # 檢查是否是 pytest 相關問題
    pytest_jobs = [j for j in failed_jobs if 'test' in j['name'].lower() or 'pytest' in j['name'].lower()]
    if pytest_jobs:
        print("- 發現測試相關失敗，建議檢查:")
        print("  1. pytest 配置和參數")
        print("  2. 測試環境依賴")
        print("  3. 最近的代碼變更")
    
    # 檢查是否是品質檢查問題
    quality_jobs = [j for j in failed_jobs if 'quality' in j['name'].lower() or 'lint' in j['name'].lower()]
    if quality_jobs:
        print("- 發現程式碼品質檢查失敗，建議執行:")
        print("  1. cd apps/bot && poetry run black src/")
        print("  2. cd apps/bot && poetry run ruff check src/ --fix")
        print("  3. cd apps/bot && poetry run mypy src/")
    
    # 檢查是否是依賴問題
    ci_jobs = [j for j in failed_jobs if 'ci' in j['name'].lower()]
    if ci_jobs:
        print("- 發現 CI 失敗，建議檢查:")
        print("  1. 依賴安裝問題")
        print("  2. 環境配置")
        print("  3. workflow 文件語法")

if __name__ == "__main__":
    try:
        analyze_workflow_issues()
    except Exception as e:
        print(f"錯誤: {e}")