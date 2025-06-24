#!/usr/bin/env python3
"""
GitHub Actions 錯誤分析工具
自動從失敗的 workflow 中提取詳細錯誤信息
"""

import os
import re
import io
import gzip
import json
import zipfile
import requests
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import argparse
from pathlib import Path

class GitHubActionsErrorAnalyzer:
    """GitHub Actions 錯誤分析器"""
    
    def __init__(self, owner: str, repo: str, token: Optional[str] = None):
        self.owner = owner
        self.repo = repo
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        self.headers = {
            "Authorization": f"Bearer {self.token}" if self.token else "",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        self.base_url = "https://api.github.com"
        
    def get_failed_runs(self, limit: int = 10) -> List[Dict]:
        """獲取最近失敗的 workflow runs"""
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/actions/runs"
        params = {
            "status": "failure",
            "per_page": limit
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        return data.get("workflow_runs", [])
    
    def get_run_jobs(self, run_id: int) -> List[Dict]:
        """獲取指定 run 的所有 jobs"""
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/actions/runs/{run_id}/jobs"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        
        data = response.json()
        return data.get("jobs", [])
    
    def download_job_log(self, job_id: int) -> str:
        """下載指定 job 的日誌"""
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/actions/jobs/{job_id}/logs"
        
        # GitHub 會返回 302 重定向到實際的日誌 URL
        response = requests.get(url, headers=self.headers, allow_redirects=True)
        response.raise_for_status()
        
        # 檢查是否是 gzip 壓縮的內容
        if response.headers.get('content-encoding') == 'gzip' or response.content[:2] == b'\x1f\x8b':
            try:
                return gzip.decompress(response.content).decode('utf-8')
            except:
                return response.text
        else:
            return response.text
    
    def download_run_logs(self, run_id: int, output_dir: str = "./logs") -> Dict[str, str]:
        """下載整個 run 的所有日誌（zip 格式）"""
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/actions/runs/{run_id}/logs"
        
        response = requests.get(url, headers=self.headers, allow_redirects=True)
        response.raise_for_status()
        
        # 解壓 zip 文件
        logs = {}
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            for filename in zf.namelist():
                with zf.open(filename) as f:
                    content = f.read().decode('utf-8', errors='ignore')
                    logs[filename] = content
                    
                    # 可選：保存到本地
                    if output_dir:
                        Path(output_dir).mkdir(parents=True, exist_ok=True)
                        output_path = Path(output_dir) / filename
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        output_path.write_text(content)
        
        return logs
    
    def parse_pytest_errors(self, log_content: str) -> List[Dict]:
        """解析 pytest 相關錯誤"""
        errors = []
        
        # 定義各種錯誤模式
        patterns = {
            'pytest_error': re.compile(r'pytest: error: (.+)', re.I),
            'test_failed': re.compile(r'FAILED ([\w/]+\.py::\S+) - (.+)'),
            'assertion_error': re.compile(r'AssertionError: (.+)'),
            'import_error': re.compile(r'ImportError: (.+)'),
            'module_not_found': re.compile(r'ModuleNotFoundError: (.+)'),
            'syntax_error': re.compile(r'SyntaxError: (.+)'),
            'type_error': re.compile(r'TypeError: (.+)'),
            'value_error': re.compile(r'ValueError: (.+)'),
            'error_summary': re.compile(r'ERROR: (.+)'),
            'short_summary': re.compile(r'=+ (FAILURES|ERRORS|FAILED) =+'),
            'traceback_start': re.compile(r'_{10,} (\S+) _{10,}'),
            'exit_code': re.compile(r'Process completed with exit code (\d+)'),
        }
        
        lines = log_content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # 檢查每個錯誤模式
            for error_type, pattern in patterns.items():
                match = pattern.search(line)
                if match:
                    error_info = {
                        'type': error_type,
                        'line_number': i + 1,
                        'line': line,
                        'message': match.group(1) if match.groups() else match.group(0),
                        'context': []
                    }
                    
                    # 獲取上下文（前後各5行）
                    start = max(0, i - 5)
                    end = min(len(lines), i + 6)
                    error_info['context'] = lines[start:end]
                    
                    # 特殊處理：如果是 traceback，嘗試獲取完整的錯誤堆棧
                    if error_type in ['traceback_start', 'test_failed']:
                        j = i + 1
                        traceback_lines = []
                        while j < len(lines) and j < i + 50:  # 最多讀取50行
                            tb_line = lines[j]
                            if re.match(r'^(=+|_+)\s*$', tb_line):  # 遇到分隔線停止
                                break
                            traceback_lines.append(tb_line)
                            j += 1
                        error_info['traceback'] = traceback_lines
                    
                    errors.append(error_info)
                    break
            
            i += 1
        
        return errors
    
    def analyze_errors(self, errors: List[Dict]) -> Dict:
        """分析錯誤並生成統計"""
        analysis = {
            'total_errors': len(errors),
            'error_types': {},
            'common_messages': {},
            'recommendations': []
        }
        
        # 統計錯誤類型
        for error in errors:
            error_type = error['type']
            if error_type not in analysis['error_types']:
                analysis['error_types'][error_type] = 0
            analysis['error_types'][error_type] += 1
            
            # 統計常見錯誤消息
            msg = error['message']
            if msg not in analysis['common_messages']:
                analysis['common_messages'][msg] = 0
            analysis['common_messages'][msg] += 1
        
        # 生成建議
        if 'pytest_error' in analysis['error_types']:
            for error in errors:
                if error['type'] == 'pytest_error':
                    if 'unrecognized arguments' in error['message']:
                        arg_match = re.search(r'unrecognized arguments?: (.+)', error['message'])
                        if arg_match:
                            bad_args = arg_match.group(1)
                            analysis['recommendations'].append({
                                'issue': f'Pytest 不識別參數: {bad_args}',
                                'suggestion': '檢查 pytest 配置文件或命令行參數',
                                'fix': f'移除或修正參數 {bad_args}'
                            })
                    elif 'no tests ran' in error['message']:
                        analysis['recommendations'].append({
                            'issue': '沒有測試被執行',
                            'suggestion': '檢查測試文件路徑和測試發現配置',
                            'fix': '確認 tests/ 目錄存在且包含 test_*.py 文件'
                        })
        
        if 'import_error' in analysis['error_types'] or 'module_not_found' in analysis['error_types']:
            analysis['recommendations'].append({
                'issue': '模組導入錯誤',
                'suggestion': '檢查依賴是否正確安裝',
                'fix': '運行 poetry install 或 pip install -r requirements.txt'
            })
        
        return analysis
    
    def generate_report(self, run_id: int, output_file: str = "error_analysis_report.md") -> None:
        """生成詳細的錯誤分析報告"""
        print(f"🔍 分析 Run ID: {run_id}")
        
        # 獲取 run 信息
        run_url = f"{self.base_url}/repos/{self.owner}/{self.repo}/actions/runs/{run_id}"
        run_info = requests.get(run_url, headers=self.headers).json()
        
        # 獲取所有 jobs
        jobs = self.get_run_jobs(run_id)
        failed_jobs = [j for j in jobs if j['conclusion'] == 'failure']
        
        report_content = f"""# 🔍 GitHub Actions 錯誤分析報告

**生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**倉庫**: {self.owner}/{self.repo}  
**Run ID**: {run_id}  
**Workflow**: {run_info.get('name', 'Unknown')}  
**分支**: {run_info.get('head_branch', 'Unknown')}  
**提交**: {run_info.get('head_sha', 'Unknown')[:8]}  

## 📊 執行摘要

- **總 Jobs**: {len(jobs)}
- **失敗 Jobs**: {len(failed_jobs)}
- **觸發事件**: {run_info.get('event', 'Unknown')}
- **執行時間**: {run_info.get('run_started_at', 'Unknown')}

## ❌ 失敗的 Jobs

"""
        
        all_errors = []
        
        for job in failed_jobs:
            job_name = job['name']
            job_id = job['id']
            
            report_content += f"### 🔴 {job_name}\n\n"
            report_content += f"- **Job ID**: {job_id}\n"
            report_content += f"- **狀態**: {job['status']}\n"
            report_content += f"- **結論**: {job['conclusion']}\n"
            report_content += f"- **開始時間**: {job['started_at']}\n"
            report_content += f"- **完成時間**: {job['completed_at']}\n\n"
            
            # 下載並分析日誌
            try:
                print(f"  📥 下載 {job_name} 的日誌...")
                log_content = self.download_job_log(job_id)
                
                print(f"  🔍 分析錯誤...")
                errors = self.parse_pytest_errors(log_content)
                all_errors.extend(errors)
                
                if errors:
                    report_content += f"#### 🐛 發現的錯誤 ({len(errors)} 個)\n\n"
                    
                    for idx, error in enumerate(errors, 1):
                        report_content += f"**錯誤 {idx}**: {error['type']}\n"
                        report_content += f"- **行號**: {error['line_number']}\n"
                        report_content += f"- **訊息**: `{error['message']}`\n"
                        report_content += f"- **原始行**: `{error['line']}`\n"
                        
                        if 'traceback' in error and error['traceback']:
                            report_content += "\n<details>\n<summary>展開查看完整錯誤堆棧</summary>\n\n```\n"
                            report_content += '\n'.join(error['traceback'][:20])  # 最多顯示20行
                            report_content += "\n```\n</details>\n"
                        
                        report_content += "\n"
                else:
                    report_content += "未找到明確的錯誤訊息（可能需要檢查完整日誌）\n\n"
                    
            except Exception as e:
                report_content += f"⚠️ 無法分析此 job 的日誌: {str(e)}\n\n"
        
        # 錯誤分析
        if all_errors:
            analysis = self.analyze_errors(all_errors)
            
            report_content += "## 📈 錯誤分析\n\n"
            report_content += f"**總錯誤數**: {analysis['total_errors']}\n\n"
            
            report_content += "### 錯誤類型分布\n\n"
            report_content += "| 錯誤類型 | 數量 |\n"
            report_content += "|---------|------|\n"
            for error_type, count in sorted(analysis['error_types'].items(), key=lambda x: x[1], reverse=True):
                report_content += f"| {error_type} | {count} |\n"
            
            report_content += "\n### 常見錯誤訊息\n\n"
            for msg, count in sorted(analysis['common_messages'].items(), key=lambda x: x[1], reverse=True)[:10]:
                report_content += f"- **{count}次**: `{msg[:100]}{'...' if len(msg) > 100 else ''}`\n"
            
            if analysis['recommendations']:
                report_content += "\n## 🔧 修復建議\n\n"
                for idx, rec in enumerate(analysis['recommendations'], 1):
                    report_content += f"### 建議 {idx}: {rec['issue']}\n\n"
                    report_content += f"**問題描述**: {rec['suggestion']}\n\n"
                    report_content += f"**修復方法**: {rec['fix']}\n\n"
        
        # 快速修復腳本
        report_content += """## 🚀 快速修復

```bash
# 1. 修復 pytest 參數問題
cd apps/bot
# 檢查 pytest.ini 或 pyproject.toml 中的配置
grep -r "timeout" . --include="*.ini" --include="*.toml"

# 2. 更新依賴
poetry update
poetry install

# 3. 本地測試
poetry run pytest -v

# 4. 檢查 CI 配置
cat .github/workflows/ci-enhanced.yml | grep pytest
```

## 📝 備註

- 此報告基於自動分析生成，可能需要人工確認
- 完整日誌已下載到 `./logs` 目錄
- 建議查看原始日誌以獲取更多上下文

---

**生成工具**: GitHub Actions Error Analyzer v1.0
"""
        
        # 保存報告
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"✅ 報告已生成: {output_file}")
        
        # 同時下載完整日誌供離線分析
        try:
            print(f"📥 下載完整日誌...")
            self.download_run_logs(run_id)
            print(f"✅ 完整日誌已保存到 ./logs 目錄")
        except Exception as e:
            print(f"⚠️ 無法下載完整日誌: {e}")


def main():
    parser = argparse.ArgumentParser(description='GitHub Actions 錯誤分析工具')
    parser.add_argument('--owner', default='p8552015', help='GitHub 倉庫擁有者')
    parser.add_argument('--repo', default='lineMCP', help='GitHub 倉庫名稱')
    parser.add_argument('--run-id', type=int, help='指定要分析的 Run ID')
    parser.add_argument('--latest', action='store_true', help='分析最新的失敗 run')
    parser.add_argument('--token', help='GitHub Token (或使用環境變數 GITHUB_TOKEN)')
    parser.add_argument('--output', default='error_analysis_report.md', help='輸出報告文件名')
    
    args = parser.parse_args()
    
    # 初始化分析器
    analyzer = GitHubActionsErrorAnalyzer(
        owner=args.owner,
        repo=args.repo,
        token=args.token
    )
    
    # 確定要分析的 run ID
    if args.run_id:
        run_id = args.run_id
    elif args.latest:
        print("🔍 尋找最新的失敗 run...")
        failed_runs = analyzer.get_failed_runs(limit=1)
        if not failed_runs:
            print("❌ 沒有找到失敗的 runs")
            return
        run_id = failed_runs[0]['id']
        print(f"📍 找到 Run ID: {run_id} ({failed_runs[0]['name']})")
    else:
        print("❌ 請指定 --run-id 或使用 --latest")
        return
    
    # 生成報告
    analyzer.generate_report(run_id, args.output)


if __name__ == "__main__":
    main()