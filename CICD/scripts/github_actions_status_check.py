#!/usr/bin/env python3
"""
GitHub Actions 狀態檢測腳本
檢測推送後的 CI 狀態並生成報告
"""

import sys
import os
import requests
import json
import time
from datetime import datetime
from pathlib import Path

# 添加專案根路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def check_github_actions_status(token, owner="p8552015", repo="lineMCP", branch="stable/m001-query-fix-working"):
    """檢查 GitHub Actions 狀態"""
    
    print(f"🔍 檢查 GitHub Actions 狀態...")
    print(f"Repository: {owner}/{repo}")
    print(f"Branch: {branch}")
    print(f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    try:
        # 1. 檢查最近的 workflow runs
        print("\n📋 檢查 Workflow Runs...")
        runs_url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs"
        params = {
            'branch': branch,
            'per_page': 10
        }
        
        response = requests.get(runs_url, headers=headers, params=params)
        
        if response.status_code == 200:
            runs_data = response.json()
            total_runs = runs_data.get('total_count', 0)
            runs = runs_data.get('workflow_runs', [])
            
            print(f"找到 {total_runs} 個 workflow runs")
            
            if runs:
                latest_run = runs[0]
                print(f"\n🎯 最新 Workflow Run:")
                print(f"  ID: {latest_run['id']}")
                print(f"  狀態: {latest_run['status']}")
                print(f"  結論: {latest_run.get('conclusion', 'N/A')}")
                print(f"  工作流程: {latest_run['name']}")
                print(f"  觸發事件: {latest_run['event']}")
                print(f"  開始時間: {latest_run['created_at']}")
                print(f"  更新時間: {latest_run['updated_at']}")
                print(f"  URL: {latest_run['html_url']}")
                
                # 如果運行完成，檢查詳細狀態
                if latest_run['status'] == 'completed':
                    conclusion = latest_run.get('conclusion')
                    if conclusion == 'success':
                        print("✅ CI 測試成功通過！")
                    elif conclusion == 'failure':
                        print("❌ CI 測試失敗")
                        # 獲取失敗詳情
                        get_failure_details(token, owner, repo, latest_run['id'], headers)
                    elif conclusion == 'cancelled':
                        print("⏹️ CI 測試被取消")
                    else:
                        print(f"⚠️ CI 測試結論: {conclusion}")
                        
                elif latest_run['status'] == 'in_progress':
                    print("🔄 CI 測試進行中...")
                    
                elif latest_run['status'] == 'queued':
                    print("⏳ CI 測試排隊中...")
                    
                # 檢查其他最近的 runs
                print(f"\n📊 最近 {min(5, len(runs))} 個 Workflow Runs:")
                for i, run in enumerate(runs[:5]):
                    status_icon = get_status_icon(run['status'], run.get('conclusion'))
                    print(f"  {i+1}. {status_icon} {run['name']} - {run['status']} ({run.get('conclusion', 'N/A')})")
                    
                return {
                    'success': True,
                    'latest_run': latest_run,
                    'total_runs': total_runs,
                    'all_runs': runs[:5]
                }
            else:
                print("⚠️ 沒有找到任何 workflow runs")
                return {'success': False, 'error': 'No workflow runs found'}
                
        else:
            print(f"❌ API 請求失敗: {response.status_code}")
            print(f"回應: {response.text}")
            return {'success': False, 'error': f'API request failed: {response.status_code}'}
            
    except Exception as e:
        print(f"❌ 檢查過程發生錯誤: {e}")
        return {'success': False, 'error': str(e)}

def get_failure_details(token, owner, repo, run_id, headers):
    """獲取失敗的詳細資訊"""
    try:
        print(f"\n🔍 獲取失敗詳情 (Run ID: {run_id})...")
        
        # 獲取 jobs
        jobs_url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/jobs"
        response = requests.get(jobs_url, headers=headers)
        
        if response.status_code == 200:
            jobs_data = response.json()
            jobs = jobs_data.get('jobs', [])
            
            print(f"找到 {len(jobs)} 個 jobs:")
            
            for job in jobs:
                job_status = job['status']
                job_conclusion = job.get('conclusion', 'N/A')
                status_icon = get_status_icon(job_status, job_conclusion)
                
                print(f"  {status_icon} {job['name']}: {job_status} ({job_conclusion})")
                
                if job_conclusion == 'failure':
                    print(f"    URL: {job['html_url']}")
                    
                    # 嘗試獲取步驟詳情
                    steps = job.get('steps', [])
                    for step in steps:
                        if step.get('conclusion') == 'failure':
                            print(f"    ❌ 失敗步驟: {step['name']}")
                            
        else:
            print(f"⚠️ 無法獲取 jobs 詳情: {response.status_code}")
            
    except Exception as e:
        print(f"⚠️ 獲取失敗詳情時出錯: {e}")

def get_status_icon(status, conclusion):
    """根據狀態和結論返回圖標"""
    if status == 'completed':
        if conclusion == 'success':
            return '✅'
        elif conclusion == 'failure':
            return '❌'
        elif conclusion == 'cancelled':
            return '⏹️'
        else:
            return '⚠️'
    elif status == 'in_progress':
        return '🔄'
    elif status == 'queued':
        return '⏳'
    else:
        return '❓'

def check_repository_status(token, owner="p8552015", repo="lineMCP"):
    """檢查 Repository 基本狀態"""
    print(f"\n🏠 檢查 Repository 狀態...")
    
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    try:
        repo_url = f"https://api.github.com/repos/{owner}/{repo}"
        response = requests.get(repo_url, headers=headers)
        
        if response.status_code == 200:
            repo_data = response.json()
            print(f"✅ Repository: {repo_data['full_name']}")
            print(f"  描述: {repo_data.get('description', 'N/A')}")
            print(f"  預設分支: {repo_data['default_branch']}")
            print(f"  最後推送: {repo_data.get('pushed_at', 'N/A')}")
            print(f"  私有: {'是' if repo_data['private'] else '否'}")
            
            return True
        else:
            print(f"❌ 無法存取 Repository: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 檢查 Repository 時出錯: {e}")
        return False

def generate_status_report(results, output_file="github_actions_status_report.md"):
    """生成狀態報告"""
    try:
        report_content = f"""# GitHub Actions 狀態報告

## 檢查資訊
- **檢查時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Repository**: p8552015/lineMCP
- **Branch**: stable/m001-query-fix-working

## 狀態摘要
"""
        
        if results.get('success'):
            latest_run = results['latest_run']
            status_icon = get_status_icon(latest_run['status'], latest_run.get('conclusion'))
            
            report_content += f"""
### {status_icon} 最新 Workflow Run
- **ID**: {latest_run['id']}
- **狀態**: {latest_run['status']}
- **結論**: {latest_run.get('conclusion', 'N/A')}
- **工作流程**: {latest_run['name']}
- **觸發事件**: {latest_run['event']}
- **開始時間**: {latest_run['created_at']}
- **URL**: [查看詳情]({latest_run['html_url']})

### 📊 最近的 Workflow Runs
| 工作流程 | 狀態 | 結論 | 時間 |
|----------|------|------|------|
"""
            
            for run in results.get('all_runs', []):
                status_icon = get_status_icon(run['status'], run.get('conclusion'))
                report_content += f"| {status_icon} {run['name']} | {run['status']} | {run.get('conclusion', 'N/A')} | {run['created_at'][:10]} |\n"
                
        else:
            report_content += f"""
### ❌ 檢查失敗
- **錯誤**: {results.get('error', '未知錯誤')}
"""
        
        report_content += f"""

---
**報告生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        # 寫入報告
        output_path = Path(output_file)
        output_path.write_text(report_content, encoding='utf-8')
        print(f"\n📁 狀態報告已生成: {output_path.absolute()}")
        
        return str(output_path.absolute())
        
    except Exception as e:
        print(f"❌ 生成報告時出錯: {e}")
        return None

def main():
    """主函數"""
    # GitHub token (從 CLAUDE.md 中獲取)
    token = "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"
    
    print("🚀 GitHub Actions 狀態檢測器")
    print("=" * 60)
    
    # 檢查 Repository 狀態
    repo_ok = check_repository_status(token)
    
    if repo_ok:
        # 檢查 GitHub Actions 狀態
        results = check_github_actions_status(token)
        
        # 生成報告
        report_file = generate_status_report(results, "CICD/tests/CICD_report/github_actions_status_report.md")
        
        if results.get('success'):
            latest_run = results['latest_run']
            if latest_run['status'] == 'completed':
                if latest_run.get('conclusion') == 'success':
                    print(f"\n🎉 總結: GitHub Actions 檢測完成，CI 測試成功！")
                    return 0
                else:
                    print(f"\n⚠️ 總結: GitHub Actions 檢測完成，但 CI 測試有問題")
                    return 1
            else:
                print(f"\n🔄 總結: GitHub Actions 檢測完成，CI 測試進行中")
                return 0
        else:
            print(f"\n❌ 總結: GitHub Actions 檢測失敗")
            return 1
    else:
        print(f"\n❌ 總結: 無法存取 Repository")
        return 1

if __name__ == "__main__":
    exit(main())