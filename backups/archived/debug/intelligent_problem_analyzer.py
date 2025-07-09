#!/usr/bin/env python3
"""
智能問題分析器
解析 GitHub Actions 日誌，分類錯誤類型，提取關鍵資訊
"""

import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path


class ProblemCategory(Enum):
    """問題分類"""
    TEST_FAILURE = "test_failure"           # 測試失敗
    BUILD_ERROR = "build_error"             # 構建錯誤
    DEPENDENCY_ISSUE = "dependency_issue"   # 依賴問題
    ENVIRONMENT_ISSUE = "environment_issue" # 環境問題
    TIMEOUT_ERROR = "timeout_error"         # 超時錯誤
    PERMISSION_ERROR = "permission_error"   # 權限錯誤
    NETWORK_ERROR = "network_error"         # 網路錯誤
    CONFIGURATION_ERROR = "config_error"    # 配置錯誤
    UNKNOWN_ERROR = "unknown_error"         # 未知錯誤


class Severity(Enum):
    """問題嚴重程度"""
    CRITICAL = "critical"   # 嚴重：阻止所有功能
    HIGH = "high"          # 高：影響核心功能
    MEDIUM = "medium"      # 中：影響部分功能
    LOW = "low"           # 低：輕微影響


@dataclass
class ProblemDetail:
    """問題詳情"""
    category: ProblemCategory
    severity: Severity
    title: str
    description: str
    error_message: str
    stack_trace: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    suggested_actions: List[str] = None
    related_files: List[str] = None
    
    def __post_init__(self):
        if self.suggested_actions is None:
            self.suggested_actions = []
        if self.related_files is None:
            self.related_files = []


@dataclass
class AnalysisResult:
    """分析結果"""
    run_id: str
    job_name: str
    step_name: str
    problems: List[ProblemDetail]
    raw_logs: str
    analysis_time: str
    total_problems: int
    critical_problems: int
    high_problems: int
    
    def __post_init__(self):
        self.total_problems = len(self.problems)
        self.critical_problems = len([p for p in self.problems if p.severity == Severity.CRITICAL])
        self.high_problems = len([p for p in self.problems if p.severity == Severity.HIGH])


class IntelligentProblemAnalyzer:
    """智能問題分析器"""
    
    def __init__(self, log_file: str = "problem_analyzer.log"):
        """
        初始化分析器
        
        Args:
            log_file: 日誌文件路徑
        """
        self.setup_logging(log_file)
        self.setup_patterns()
        
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
    
    def setup_patterns(self):
        """設置錯誤模式匹配規則"""
        self.error_patterns = {
            # 測試失敗模式
            ProblemCategory.TEST_FAILURE: [
                r"FAILED.*::(.*)",
                r"AssertionError: (.*)",
                r"Test.*failed.*: (.*)",
                r"pytest.*FAILED.*",
                r"(\d+) failed.*(\d+) passed",
                r"E\s+assert (.*)",
                r"Failed: (.*)"
            ],
            
            # 構建錯誤模式
            ProblemCategory.BUILD_ERROR: [
                r"error: (.*)",
                r"Error: (.*)",
                r"ERROR: (.*)",
                r"Build failed.*: (.*)",
                r"Compilation failed.*: (.*)",
                r"SyntaxError: (.*)",
                r"ImportError: (.*)",
                r"ModuleNotFoundError: (.*)"
            ],
            
            # 依賴問題模式
            ProblemCategory.DEPENDENCY_ISSUE: [
                r"No module named '(.*)'",
                r"Package .* not found",
                r"Could not find a version.*",
                r"dependency.*not found",
                r"pip.*failed.*",
                r"poetry.*failed.*",
                r"npm.*failed.*",
                r"Requirements.*not satisfied"
            ],
            
            # 環境問題模式
            ProblemCategory.ENVIRONMENT_ISSUE: [
                r"Command '(.*)' not found",
                r"Permission denied.*",
                r"No such file or directory.*",
                r"Environment variable.*not set",
                r"Path.*not found",
                r"ENOENT.*no such file"
            ],
            
            # 超時錯誤模式
            ProblemCategory.TIMEOUT_ERROR: [
                r"TimeoutError.*",
                r"Timeout.*exceeded",
                r"Operation timed out.*",
                r"Command timed out.*",
                r"Process.*killed.*timeout"
            ],
            
            # 權限錯誤模式
            ProblemCategory.PERMISSION_ERROR: [
                r"Permission denied.*",
                r"Access denied.*",
                r"Forbidden.*",
                r"Authentication.*failed",
                r"401.*Unauthorized",
                r"403.*Forbidden"
            ],
            
            # 網路錯誤模式
            ProblemCategory.NETWORK_ERROR: [
                r"Connection.*failed",
                r"Network.*unreachable",
                r"DNS.*resolution.*failed",
                r"ConnectionError.*",
                r"HTTPSConnectionPool.*",
                r"Failed to establish.*connection"
            ],
            
            # 配置錯誤模式
            ProblemCategory.CONFIGURATION_ERROR: [
                r"Configuration.*invalid",
                r"Config.*error",
                r"Invalid.*configuration",
                r"Missing.*required.*config",
                r"YAML.*parse.*error",
                r"JSON.*decode.*error"
            ]
        }
        
        # 檔案路徑提取模式
        self.file_path_patterns = [
            r"File \"([^\"]+)\"",
            r"in file ([^\s]+)",
            r"at ([^\s]+):\d+",
            r"([^\s]+\.py):\d+",
            r"([^\s]+\.js):\d+",
            r"([^\s]+\.ts):\d+",
            r"([^\s]+\.yaml):\d+",
            r"([^\s]+\.yml):\d+"
        ]
        
        # 行號提取模式
        self.line_number_patterns = [
            r"line (\d+)",
            r":(\d+):",
            r"at line (\d+)",
            r"on line (\d+)"
        ]
    
    def analyze_ci_failure(self, ci_report: Dict[str, Any]) -> List[AnalysisResult]:
        """
        分析 CI 失敗報告
        
        Args:
            ci_report: CI 失敗報告
            
        Returns:
            分析結果列表
        """
        self.logger.info(f"🔍 開始分析 CI 失敗報告: Run {ci_report.get('run_id')}")
        
        results = []
        failed_jobs = [job for job in ci_report.get("jobs", []) if job.get("conclusion") == "failure"]
        
        for job in failed_jobs:
            job_name = job.get("name", "unknown")
            self.logger.info(f"   分析失敗的 Job: {job_name}")
            
            # 獲取 job 日誌（這裡需要實際的日誌獲取邏輯）
            job_logs = self._get_job_logs(ci_report.get("run_id"), job.get("id", ""))
            
            # 分析失敗的步驟
            failed_steps = [step for step in job.get("steps", []) if step.get("conclusion") == "failure"]
            
            for step in failed_steps:
                step_name = step.get("name", "unknown")
                self.logger.info(f"     分析失敗的步驟: {step_name}")
                
                # 分析步驟日誌
                step_logs = job_logs  # 簡化處理，實際應該獲取具體步驟日誌
                problems = self.analyze_logs(step_logs)
                
                result = AnalysisResult(
                    run_id=str(ci_report.get("run_id", "")),
                    job_name=job_name,
                    step_name=step_name,
                    problems=problems,
                    raw_logs=step_logs,
                    analysis_time=datetime.now().isoformat()
                )
                
                results.append(result)
        
        self.logger.info(f"✅ 分析完成，共發現 {len(results)} 個問題區域")
        return results
    
    def analyze_logs(self, logs: str) -> List[ProblemDetail]:
        """
        分析日誌內容
        
        Args:
            logs: 日誌內容
            
        Returns:
            問題詳情列表
        """
        if not logs:
            return []
        
        problems = []
        log_lines = logs.split('\n')
        
        for category, patterns in self.error_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, logs, re.MULTILINE | re.IGNORECASE)
                
                for match in matches:
                    problem = self._create_problem_from_match(
                        category, pattern, match, log_lines
                    )
                    if problem:
                        problems.append(problem)
        
        # 去重和排序
        problems = self._deduplicate_problems(problems)
        problems = sorted(problems, key=lambda p: (p.severity.value, p.category.value))
        
        return problems
    
    def _create_problem_from_match(self, 
                                   category: ProblemCategory, 
                                   pattern: str, 
                                   match: re.Match, 
                                   log_lines: List[str]) -> Optional[ProblemDetail]:
        """
        根據匹配結果創建問題詳情
        
        Args:
            category: 問題分類
            pattern: 匹配模式
            match: 正則匹配結果
            log_lines: 日誌行列表
            
        Returns:
            問題詳情或None
        """
        try:
            error_message = match.group(1) if match.groups() else match.group(0)
            
            # 提取文件路徑
            file_path = self._extract_file_path(match.string)
            
            # 提取行號
            line_number = self._extract_line_number(match.string)
            
            # 提取堆棧跟蹤
            stack_trace = self._extract_stack_trace(match.string, log_lines)
            
            # 確定嚴重程度
            severity = self._determine_severity(category, error_message)
            
            # 生成標題和描述
            title = self._generate_title(category, error_message)
            description = self._generate_description(category, error_message, file_path)
            
            # 生成建議動作
            suggested_actions = self._generate_suggested_actions(category, error_message)
            
            # 提取相關文件
            related_files = self._extract_related_files(match.string)
            
            return ProblemDetail(
                category=category,
                severity=severity,
                title=title,
                description=description,
                error_message=error_message,
                stack_trace=stack_trace,
                file_path=file_path,
                line_number=line_number,
                suggested_actions=suggested_actions,
                related_files=related_files
            )
            
        except Exception as e:
            self.logger.error(f"❌ 創建問題詳情失敗: {e}")
            return None
    
    def _extract_file_path(self, text: str) -> Optional[str]:
        """提取文件路徑"""
        for pattern in self.file_path_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None
    
    def _extract_line_number(self, text: str) -> Optional[int]:
        """提取行號"""
        for pattern in self.line_number_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        return None
    
    def _extract_stack_trace(self, text: str, log_lines: List[str]) -> Optional[str]:
        """提取堆棧跟蹤"""
        # 簡化實現，實際可能需要更複雜的邏輯
        traceback_patterns = [
            r"Traceback \(most recent call last\):",
            r"Stack trace:",
            r"Call stack:"
        ]
        
        for pattern in traceback_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                # 找到堆棧跟蹤的開始
                for i, line in enumerate(log_lines):
                    if re.search(pattern, line, re.IGNORECASE):
                        # 提取堆棧跟蹤部分
                        stack_lines = []
                        for j in range(i, min(i + 20, len(log_lines))):
                            stack_lines.append(log_lines[j])
                            if not log_lines[j].strip():
                                break
                        return '\n'.join(stack_lines)
        
        return None
    
    def _determine_severity(self, category: ProblemCategory, error_message: str) -> Severity:
        """確定問題嚴重程度"""
        error_lower = error_message.lower()
        
        # 嚴重級別關鍵字
        critical_keywords = ["critical", "fatal", "emergency", "panic", "crash"]
        high_keywords = ["error", "failed", "failure", "exception", "broken"]
        medium_keywords = ["warning", "warn", "deprecated", "issue"]
        
        for keyword in critical_keywords:
            if keyword in error_lower:
                return Severity.CRITICAL
        
        for keyword in high_keywords:
            if keyword in error_lower:
                return Severity.HIGH
        
        for keyword in medium_keywords:
            if keyword in error_lower:
                return Severity.MEDIUM
        
        # 根據分類確定默認嚴重程度
        if category in [ProblemCategory.TEST_FAILURE, ProblemCategory.BUILD_ERROR]:
            return Severity.HIGH
        elif category in [ProblemCategory.DEPENDENCY_ISSUE, ProblemCategory.ENVIRONMENT_ISSUE]:
            return Severity.MEDIUM
        else:
            return Severity.LOW
    
    def _generate_title(self, category: ProblemCategory, error_message: str) -> str:
        """生成問題標題"""
        category_titles = {
            ProblemCategory.TEST_FAILURE: "測試失敗",
            ProblemCategory.BUILD_ERROR: "構建錯誤",
            ProblemCategory.DEPENDENCY_ISSUE: "依賴問題",
            ProblemCategory.ENVIRONMENT_ISSUE: "環境問題",
            ProblemCategory.TIMEOUT_ERROR: "超時錯誤",
            ProblemCategory.PERMISSION_ERROR: "權限錯誤",
            ProblemCategory.NETWORK_ERROR: "網路錯誤",
            ProblemCategory.CONFIGURATION_ERROR: "配置錯誤",
            ProblemCategory.UNKNOWN_ERROR: "未知錯誤"
        }
        
        base_title = category_titles.get(category, "未知問題")
        
        # 截取錯誤訊息的前50個字符作為詳細標題
        if len(error_message) > 50:
            detail = error_message[:50] + "..."
        else:
            detail = error_message
        
        return f"{base_title}: {detail}"
    
    def _generate_description(self, 
                            category: ProblemCategory, 
                            error_message: str, 
                            file_path: Optional[str]) -> str:
        """生成問題描述"""
        description = f"檢測到 {category.value} 類型的問題。\n\n"
        description += f"錯誤訊息: {error_message}\n"
        
        if file_path:
            description += f"相關文件: {file_path}\n"
        
        return description
    
    def _generate_suggested_actions(self, 
                                  category: ProblemCategory, 
                                  error_message: str) -> List[str]:
        """生成建議動作"""
        suggestions = {
            ProblemCategory.TEST_FAILURE: [
                "檢查測試代碼邏輯",
                "確認測試數據是否正確",
                "檢查模擬(mock)設置",
                "運行單個測試以排除干擾"
            ],
            ProblemCategory.BUILD_ERROR: [
                "檢查語法錯誤",
                "確認依賴是否正確安裝",
                "檢查導入路徑",
                "清理構建緩存後重試"
            ],
            ProblemCategory.DEPENDENCY_ISSUE: [
                "更新依賴版本",
                "檢查包管理器配置",
                "確認依賴在requirements中",
                "清理並重新安裝依賴"
            ],
            ProblemCategory.ENVIRONMENT_ISSUE: [
                "檢查環境變數設置",
                "確認文件路徑存在",
                "檢查權限設置",
                "驗證運行環境配置"
            ],
            ProblemCategory.TIMEOUT_ERROR: [
                "增加超時時間設置",
                "優化執行效率",
                "檢查網路連接",
                "分解大型操作"
            ],
            ProblemCategory.PERMISSION_ERROR: [
                "檢查文件權限",
                "確認API權限",
                "檢查用戶授權",
                "更新訪問令牌"
            ],
            ProblemCategory.NETWORK_ERROR: [
                "檢查網路連接",
                "確認服務可用性",
                "檢查防火牆設置",
                "嘗試使用代理"
            ],
            ProblemCategory.CONFIGURATION_ERROR: [
                "檢查配置文件格式",
                "確認配置項完整性",
                "驗證配置值正確性",
                "參考文檔修正配置"
            ]
        }
        
        return suggestions.get(category, ["檢查錯誤日誌", "聯繫技術支援"])
    
    def _extract_related_files(self, text: str) -> List[str]:
        """提取相關文件"""
        files = []
        for pattern in self.file_path_patterns:
            matches = re.findall(pattern, text)
            files.extend(matches)
        
        # 去重
        return list(set(files))
    
    def _deduplicate_problems(self, problems: List[ProblemDetail]) -> List[ProblemDetail]:
        """去除重複問題"""
        seen = set()
        unique_problems = []
        
        for problem in problems:
            # 使用錯誤訊息和分類作為去重鍵
            key = f"{problem.category.value}:{problem.error_message[:100]}"
            if key not in seen:
                seen.add(key)
                unique_problems.append(problem)
        
        return unique_problems
    
    def _get_job_logs(self, run_id: str, job_id: str) -> str:
        """
        獲取 job 日誌
        
        Args:
            run_id: Workflow run ID
            job_id: Job ID
            
        Returns:
            日誌內容
        """
        # 這裡應該調用 GitHub API 獲取實際日誌
        # 暫時返回模擬日誌用於測試
        return f"""
FAILED tests/test_example.py::test_function - AssertionError: Expected 5, got 3
E   assert 3 == 5
E    +  where 3 = function_call()

tests/test_example.py:25: AssertionError

ImportError: No module named 'missing_package'
File "/home/runner/work/app/src/main.py", line 10, in <module>
    import missing_package

SyntaxError: invalid syntax
File "/home/runner/work/app/src/parser.py", line 42
    if condition
             ^
SyntaxError: invalid syntax
        """
    
    def save_analysis_result(self, result: AnalysisResult, output_dir: str = "analysis_results"):
        """保存分析結果"""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"analysis_{result.run_id}_{result.job_name}_{timestamp}.json"
            
            file_path = output_path / filename
            
            # 轉換為可序列化的格式
            result_dict = asdict(result)
            
            # 處理Enum值
            for problem in result_dict["problems"]:
                problem["category"] = problem["category"].value if hasattr(problem["category"], 'value') else str(problem["category"])
                problem["severity"] = problem["severity"].value if hasattr(problem["severity"], 'value') else str(problem["severity"])
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(result_dict, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"📄 分析結果已保存: {file_path}")
            
        except Exception as e:
            self.logger.error(f"❌ 保存分析結果失敗: {e}")


def main():
    """測試主函數"""
    analyzer = IntelligentProblemAnalyzer()
    
    # 測試分析功能
    sample_logs = """
FAILED tests/integration/test_api.py::test_user_login - AssertionError: Status code should be 200
E   assert 401 == 200
E    +  where 401 = <Response [401]>.status_code

ImportError: No module named 'requests_mock'
File "/home/runner/work/lineMCP/src/services/api_client.py", line 5, in <module>
    import requests_mock

SyntaxError: invalid syntax
File "/home/runner/work/lineMCP/src/utils/parser.py", line 42
    if user_data
             ^
SyntaxError: invalid syntax

TimeoutError: Command 'pytest tests/' timed out after 300 seconds
    """
    
    print("🔍 開始測試問題分析器...")
    problems = analyzer.analyze_logs(sample_logs)
    
    print(f"\n📊 分析結果: 發現 {len(problems)} 個問題")
    for i, problem in enumerate(problems, 1):
        print(f"\n{i}. {problem.title}")
        print(f"   分類: {problem.category.value}")
        print(f"   嚴重程度: {problem.severity.value}")
        print(f"   錯誤訊息: {problem.error_message}")
        if problem.file_path:
            print(f"   文件: {problem.file_path}")
        if problem.suggested_actions:
            print(f"   建議: {', '.join(problem.suggested_actions[:2])}")


if __name__ == "__main__":
    main()