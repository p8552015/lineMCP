#!/usr/bin/env python3
"""
自動修復生成器
基於問題分析結果，生成智能修復方案並應用修復
"""

import os
import re
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from intelligent_problem_analyzer import ProblemDetail, ProblemCategory, Severity, AnalysisResult


@dataclass
class FixAction:
    """修復動作"""
    action_type: str  # 'file_edit', 'file_create', 'file_delete', 'command_run'
    target_path: str  # 目標文件路徑
    description: str  # 修復描述
    content: Optional[str] = None  # 新內容（用於創建或編輯）
    search_pattern: Optional[str] = None  # 搜索模式（用於編輯）
    replacement: Optional[str] = None  # 替換內容（用於編輯）
    command: Optional[str] = None  # 執行命令（用於命令類型）
    backup_required: bool = True  # 是否需要備份
    risk_level: str = "low"  # 風險等級: low, medium, high
    confidence: float = 0.0  # 修復信心度 (0.0-1.0)


@dataclass
class FixSolution:
    """修復解決方案"""
    problem_id: str
    problem_category: ProblemCategory
    solution_name: str
    description: str
    actions: List[FixAction]
    estimated_success_rate: float
    risk_assessment: str
    prerequisites: List[str]
    rollback_plan: str
    ai_generated: bool = False
    
    def __post_init__(self):
        if not self.prerequisites:
            self.prerequisites = []


class AutoFixGenerator:
    """自動修復生成器"""
    
    def __init__(self, 
                 project_root: str = "/Users/yen/Desktop/lineMCP",
                 log_file: str = "auto_fix_generator.log"):
        """
        初始化修復生成器
        
        Args:
            project_root: 專案根目錄
            log_file: 日誌文件路徑
        """
        self.project_root = Path(project_root)
        self.setup_logging(log_file)
        self.setup_fix_templates()
        
        # AI模型配置（如果可用）
        self.ai_enabled = self._check_ai_availability()
        
        # 修復統計
        self.stats = {
            "total_fixes_generated": 0,
            "successful_fixes": 0,
            "failed_fixes": 0,
            "high_confidence_fixes": 0,
            "ai_generated_fixes": 0
        }
    
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
    
    def setup_fix_templates(self):
        """設置修復模板"""
        self.fix_templates = {
            ProblemCategory.TEST_FAILURE: {
                "assertion_error": {
                    "pattern": r"AssertionError.*assert (.*)",
                    "solution": self._generate_assertion_fix,
                    "confidence": 0.7
                },
                "import_error_in_test": {
                    "pattern": r"ImportError.*No module named '(.*)'",
                    "solution": self._generate_import_fix,
                    "confidence": 0.8
                },
                "test_timeout": {
                    "pattern": r"TimeoutError.*test.*timeout",
                    "solution": self._generate_test_timeout_fix,
                    "confidence": 0.6
                }
            },
            
            ProblemCategory.BUILD_ERROR: {
                "syntax_error": {
                    "pattern": r"SyntaxError.*invalid syntax",
                    "solution": self._generate_syntax_fix,
                    "confidence": 0.5
                },
                "import_error": {
                    "pattern": r"ImportError.*No module named '(.*)'",
                    "solution": self._generate_import_fix,
                    "confidence": 0.8
                },
                "module_not_found": {
                    "pattern": r"ModuleNotFoundError.*No module named '(.*)'",
                    "solution": self._generate_module_fix,
                    "confidence": 0.8
                }
            },
            
            ProblemCategory.DEPENDENCY_ISSUE: {
                "missing_package": {
                    "pattern": r"No module named '(.*)'",
                    "solution": self._generate_dependency_install_fix,
                    "confidence": 0.9
                },
                "version_conflict": {
                    "pattern": r"version.*conflict",
                    "solution": self._generate_version_fix,
                    "confidence": 0.6
                },
                "pip_install_failed": {
                    "pattern": r"pip.*failed",
                    "solution": self._generate_pip_fix,
                    "confidence": 0.7
                }
            },
            
            ProblemCategory.ENVIRONMENT_ISSUE: {
                "missing_env_var": {
                    "pattern": r"Environment variable.*not set",
                    "solution": self._generate_env_var_fix,
                    "confidence": 0.8
                },
                "file_not_found": {
                    "pattern": r"No such file or directory.*",
                    "solution": self._generate_file_creation_fix,
                    "confidence": 0.7
                },
                "permission_denied": {
                    "pattern": r"Permission denied.*",
                    "solution": self._generate_permission_fix,
                    "confidence": 0.6
                }
            },
            
            ProblemCategory.CONFIGURATION_ERROR: {
                "yaml_parse_error": {
                    "pattern": r"YAML.*parse.*error",
                    "solution": self._generate_yaml_fix,
                    "confidence": 0.7
                },
                "json_decode_error": {
                    "pattern": r"JSON.*decode.*error",
                    "solution": self._generate_json_fix,
                    "confidence": 0.7
                },
                "config_missing": {
                    "pattern": r"Missing.*required.*config",
                    "solution": self._generate_config_fix,
                    "confidence": 0.8
                }
            }
        }
    
    def _check_ai_availability(self) -> bool:
        """檢查AI模型是否可用"""
        try:
            # 檢查是否有可用的AI服務
            google_key = os.getenv("GOOGLE_API_KEY")
            openai_key = os.getenv("OPENAI_API_KEY")
            
            if google_key or openai_key:
                self.logger.info("✅ AI模型可用，將提供智能修復建議")
                return True
            else:
                self.logger.info("⚠️ 未檢測到AI API密鑰，將使用模板修復")
                return False
                
        except Exception as e:
            self.logger.warning(f"⚠️ AI可用性檢查失敗: {e}")
            return False
    
    async def generate_fixes(self, analysis_results: List[AnalysisResult]) -> List[FixSolution]:
        """
        生成修復方案
        
        Args:
            analysis_results: 問題分析結果列表
            
        Returns:
            修復方案列表
        """
        self.logger.info(f"🔧 開始生成修復方案，分析 {len(analysis_results)} 個結果...")
        
        all_solutions = []
        
        for result in analysis_results:
            self.logger.info(f"   處理 {result.job_name} - {result.step_name}")
            
            for problem in result.problems:
                solutions = await self._generate_problem_solutions(problem, result)
                all_solutions.extend(solutions)
        
        # 按信心度和風險排序
        all_solutions.sort(key=lambda s: (-s.estimated_success_rate, s.risk_assessment))
        
        self.logger.info(f"✅ 生成完成，共生成 {len(all_solutions)} 個修復方案")
        self.stats["total_fixes_generated"] += len(all_solutions)
        
        return all_solutions
    
    async def _generate_problem_solutions(self, 
                                        problem: ProblemDetail, 
                                        context: AnalysisResult) -> List[FixSolution]:
        """
        為特定問題生成解決方案
        
        Args:
            problem: 問題詳情
            context: 分析結果上下文
            
        Returns:
            解決方案列表
        """
        solutions = []
        
        # 1. 嘗試模板匹配修復
        template_solutions = self._generate_template_solutions(problem, context)
        solutions.extend(template_solutions)
        
        # 2. 如果AI可用，生成AI輔助修復
        if self.ai_enabled and len(template_solutions) == 0:
            ai_solutions = await self._generate_ai_solutions(problem, context)
            solutions.extend(ai_solutions)
        
        # 3. 生成通用修復建議
        if len(solutions) == 0:
            generic_solutions = self._generate_generic_solutions(problem, context)
            solutions.extend(generic_solutions)
        
        return solutions
    
    def _generate_template_solutions(self, 
                                   problem: ProblemDetail, 
                                   context: AnalysisResult) -> List[FixSolution]:
        """使用模板生成解決方案"""
        solutions = []
        
        category_templates = self.fix_templates.get(problem.category, {})
        
        for template_name, template_config in category_templates.items():
            pattern = template_config["pattern"]
            solution_func = template_config["solution"]
            confidence = template_config["confidence"]
            
            # 檢查模式是否匹配
            if re.search(pattern, problem.error_message, re.IGNORECASE):
                self.logger.info(f"   🎯 模板匹配: {template_name}")
                
                try:
                    solution = solution_func(problem, context, template_config)
                    if solution:
                        solution.estimated_success_rate = confidence
                        solutions.append(solution)
                        
                except Exception as e:
                    self.logger.error(f"❌ 模板解決方案生成失敗 {template_name}: {e}")
        
        return solutions
    
    async def _generate_ai_solutions(self, 
                                   problem: ProblemDetail, 
                                   context: AnalysisResult) -> List[FixSolution]:
        """使用AI生成解決方案"""
        try:
            self.logger.info("🤖 使用AI生成智能修復方案...")
            
            # 構建AI提示
            prompt = self._build_ai_prompt(problem, context)
            
            # 調用AI模型（這裡需要實際的AI服務集成）
            ai_response = await self._call_ai_service(prompt)
            
            if ai_response:
                solution = self._parse_ai_response(ai_response, problem, context)
                if solution:
                    solution.ai_generated = True
                    self.stats["ai_generated_fixes"] += 1
                    return [solution]
            
        except Exception as e:
            self.logger.error(f"❌ AI解決方案生成失敗: {e}")
        
        return []
    
    def _generate_generic_solutions(self, 
                                  problem: ProblemDetail, 
                                  context: AnalysisResult) -> List[FixSolution]:
        """生成通用解決方案"""
        
        actions = []
        
        # 根據問題類別生成通用動作
        if problem.category == ProblemCategory.TEST_FAILURE:
            actions.append(FixAction(
                action_type="command_run",
                target_path=".",
                description="重新運行特定測試以確認問題",
                command=f"cd apps/bot && poetry run pytest {problem.file_path or 'tests/'} -v",
                risk_level="low",
                confidence=0.3
            ))
        
        elif problem.category == ProblemCategory.DEPENDENCY_ISSUE:
            actions.append(FixAction(
                action_type="command_run",
                target_path="apps/bot",
                description="更新依賴並重新安裝",
                command="poetry install --no-cache",
                risk_level="medium",
                confidence=0.6
            ))
        
        elif problem.category == ProblemCategory.BUILD_ERROR:
            actions.append(FixAction(
                action_type="command_run",
                target_path="apps/bot",
                description="清理緩存並重新構建",
                command="poetry run black src/ && poetry run ruff check src/ --fix",
                risk_level="low",
                confidence=0.4
            ))
        
        if actions:
            solution = FixSolution(
                problem_id=f"generic_{problem.category.value}_{datetime.now().strftime('%H%M%S')}",
                problem_category=problem.category,
                solution_name=f"通用修復 - {problem.category.value}",
                description=f"針對 {problem.category.value} 的通用修復方案",
                actions=actions,
                estimated_success_rate=0.4,
                risk_assessment="low",
                rollback_plan="使用git revert回滾變更"
            )
            
            return [solution]
        
        return []
    
    # === 具體修復方案生成器 ===
    
    def _generate_assertion_fix(self, problem: ProblemDetail, context: AnalysisResult, config: Dict) -> Optional[FixSolution]:
        """生成斷言錯誤修復"""
        if not problem.file_path:
            return None
        
        actions = [
            FixAction(
                action_type="file_edit",
                target_path=problem.file_path,
                description="檢查並修正測試斷言邏輯",
                search_pattern=r"assert (.+)",
                replacement="# TODO: 檢查此斷言邏輯\n    assert \\1",
                risk_level="low",
                confidence=0.7
            )
        ]
        
        return FixSolution(
            problem_id=f"assertion_fix_{datetime.now().strftime('%H%M%S')}",
            problem_category=problem.category,
            solution_name="修復測試斷言錯誤",
            description="在斷言前添加檢查註釋，提醒開發者檢查邏輯",
            actions=actions,
            estimated_success_rate=0.7,
            risk_assessment="low",
            rollback_plan="移除添加的註釋",
            prerequisites=["確認測試檔案可寫"]
        )
    
    def _generate_import_fix(self, problem: ProblemDetail, context: AnalysisResult, config: Dict) -> Optional[FixSolution]:
        """生成導入錯誤修復"""
        
        # 提取缺失的模組名稱
        match = re.search(r"No module named '(.*)'", problem.error_message)
        if not match:
            return None
        
        module_name = match.group(1)
        
        actions = []
        
        # 常見的模組映射
        module_mapping = {
            "requests_mock": "requests-mock",
            "yaml": "PyYAML",
            "PIL": "Pillow",
            "cv2": "opencv-python"
        }
        
        package_name = module_mapping.get(module_name, module_name)
        
        # 添加依賴安裝動作
        actions.append(FixAction(
            action_type="command_run",
            target_path="apps/bot",
            description=f"安裝缺失的依賴 {package_name}",
            command=f"poetry add {package_name}",
            risk_level="medium",
            confidence=0.8
        ))
        
        return FixSolution(
            problem_id=f"import_fix_{module_name}_{datetime.now().strftime('%H%M%S')}",
            problem_category=problem.category,
            solution_name=f"修復 {module_name} 導入錯誤",
            description=f"安裝缺失的依賴包 {package_name}",
            actions=actions,
            estimated_success_rate=0.8,
            risk_assessment="medium",
            rollback_plan=f"使用 poetry remove {package_name} 移除依賴",
            prerequisites=["網路連接正常", "Poetry環境可用"]
        )
    
    def _generate_syntax_fix(self, problem: ProblemDetail, context: AnalysisResult, config: Dict) -> Optional[FixSolution]:
        """生成語法錯誤修復"""
        if not problem.file_path:
            return None
        
        actions = [
            FixAction(
                action_type="command_run",
                target_path="apps/bot",
                description="使用Black自動格式化修復語法問題",
                command=f"poetry run black {problem.file_path}",
                risk_level="low",
                confidence=0.5
            )
        ]
        
        return FixSolution(
            problem_id=f"syntax_fix_{datetime.now().strftime('%H%M%S')}",
            problem_category=problem.category,
            solution_name="自動修復語法錯誤",
            description="使用代碼格式化工具修復常見語法問題",
            actions=actions,
            estimated_success_rate=0.5,
            risk_assessment="low",
            rollback_plan="使用git checkout恢復文件",
            prerequisites=["Black格式化工具可用"]
        )
    
    def _generate_dependency_install_fix(self, problem: ProblemDetail, context: AnalysisResult, config: Dict) -> Optional[FixSolution]:
        """生成依賴安裝修復"""
        match = re.search(r"No module named '(.*)'", problem.error_message)
        if not match:
            return None
        
        module_name = match.group(1)
        
        actions = [
            FixAction(
                action_type="command_run",
                target_path="apps/bot",
                description=f"安裝缺失的依賴 {module_name}",
                command=f"poetry add {module_name}",
                risk_level="medium",
                confidence=0.9
            ),
            FixAction(
                action_type="command_run",
                target_path="apps/bot",
                description="重新安裝所有依賴",
                command="poetry install",
                risk_level="low",
                confidence=0.8
            )
        ]
        
        return FixSolution(
            problem_id=f"dep_install_{module_name}_{datetime.now().strftime('%H%M%S')}",
            problem_category=problem.category,
            solution_name=f"安裝依賴 {module_name}",
            description=f"安裝缺失的Python包 {module_name}",
            actions=actions,
            estimated_success_rate=0.9,
            risk_assessment="medium",
            rollback_plan="使用poetry.lock回滾依賴狀態"
        )
    
    def _generate_test_timeout_fix(self, problem: ProblemDetail, context: AnalysisResult, config: Dict) -> Optional[FixSolution]:
        """生成測試超時修復"""
        actions = [
            FixAction(
                action_type="file_edit",
                target_path="apps/bot/pyproject.toml",
                description="增加pytest超時時間設置",
                search_pattern=r"\[tool\.pytest\.ini_options\]",
                replacement="[tool.pytest.ini_options]\ntimeout = 300",
                risk_level="low",
                confidence=0.6
            )
        ]
        
        return FixSolution(
            problem_id=f"timeout_fix_{datetime.now().strftime('%H%M%S')}",
            problem_category=problem.category,
            solution_name="修復測試超時問題",
            description="增加pytest超時時間配置",
            actions=actions,
            estimated_success_rate=0.6,
            risk_assessment="low",
            rollback_plan="恢復原始pyproject.toml配置"
        )
    
    def _generate_module_fix(self, problem: ProblemDetail, context: AnalysisResult, config: Dict) -> Optional[FixSolution]:
        """生成模組修復"""
        return self._generate_import_fix(problem, context, config)
    
    def _generate_version_fix(self, problem: ProblemDetail, context: AnalysisResult, config: Dict) -> Optional[FixSolution]:
        """生成版本衝突修復"""
        actions = [
            FixAction(
                action_type="command_run",
                target_path="apps/bot",
                description="更新所有依賴到兼容版本",
                command="poetry update",
                risk_level="medium",
                confidence=0.6
            )
        ]
        
        return FixSolution(
            problem_id=f"version_fix_{datetime.now().strftime('%H%M%S')}",
            problem_category=problem.category,
            solution_name="修復版本衝突",
            description="更新依賴包到兼容版本",
            actions=actions,
            estimated_success_rate=0.6,
            risk_assessment="medium",
            rollback_plan="使用poetry.lock回滾版本"
        )
    
    def _generate_pip_fix(self, problem: ProblemDetail, context: AnalysisResult, config: Dict) -> Optional[FixSolution]:
        """生成pip修復"""
        actions = [
            FixAction(
                action_type="command_run",
                target_path="apps/bot",
                description="清理pip緩存並重新安裝",
                command="poetry cache clear --all pypi && poetry install",
                risk_level="medium",
                confidence=0.7
            )
        ]
        
        return FixSolution(
            problem_id=f"pip_fix_{datetime.now().strftime('%H%M%S')}",
            problem_category=problem.category,
            solution_name="修復pip安裝問題",
            description="清理緩存並重新安裝依賴",
            actions=actions,
            estimated_success_rate=0.7,
            risk_assessment="medium",
            rollback_plan="使用poetry.lock恢復依賴狀態"
        )
    
    def _generate_env_var_fix(self, problem: ProblemDetail, context: AnalysisResult, config: Dict) -> Optional[FixSolution]:
        """生成環境變數修復"""
        actions = [
            FixAction(
                action_type="file_edit",
                target_path="apps/bot/.env.example",
                description="添加缺失的環境變數範例",
                search_pattern=r"$",
                replacement="\n# 添加缺失的環境變數\nMISSING_VAR=your_value_here",
                risk_level="low",
                confidence=0.8
            )
        ]
        
        return FixSolution(
            problem_id=f"env_fix_{datetime.now().strftime('%H%M%S')}",
            problem_category=problem.category,
            solution_name="修復環境變數問題",
            description="在.env.example中添加缺失的環境變數",
            actions=actions,
            estimated_success_rate=0.8,
            risk_assessment="low",
            rollback_plan="移除添加的環境變數行"
        )
    
    def _generate_file_creation_fix(self, problem: ProblemDetail, context: AnalysisResult, config: Dict) -> Optional[FixSolution]:
        """生成文件創建修復"""
        # 提取缺失的文件路徑
        match = re.search(r"No such file or directory.*['\"]([^'\"]+)['\"]", problem.error_message)
        if not match:
            return None
        
        missing_file = match.group(1)
        
        actions = [
            FixAction(
                action_type="file_create",
                target_path=missing_file,
                description=f"創建缺失的文件 {missing_file}",
                content="# 自動創建的文件\n# 請根據需要添加內容\n",
                risk_level="medium",
                confidence=0.7
            )
        ]
        
        return FixSolution(
            problem_id=f"file_create_{datetime.now().strftime('%H%M%S')}",
            problem_category=problem.category,
            solution_name=f"創建缺失文件 {missing_file}",
            description=f"創建系統需要的缺失文件",
            actions=actions,
            estimated_success_rate=0.7,
            risk_assessment="medium",
            rollback_plan="刪除創建的文件"
        )
    
    def _generate_permission_fix(self, problem: ProblemDetail, context: AnalysisResult, config: Dict) -> Optional[FixSolution]:
        """生成權限修復"""
        actions = [
            FixAction(
                action_type="command_run",
                target_path=".",
                description="修復文件權限問題",
                command="chmod +x scripts/*.sh",
                risk_level="low",
                confidence=0.6
            )
        ]
        
        return FixSolution(
            problem_id=f"permission_fix_{datetime.now().strftime('%H%M%S')}",
            problem_category=problem.category,
            solution_name="修復權限問題",
            description="設置正確的文件執行權限",
            actions=actions,
            estimated_success_rate=0.6,
            risk_assessment="low",
            rollback_plan="恢復原始文件權限"
        )
    
    def _generate_yaml_fix(self, problem: ProblemDetail, context: AnalysisResult, config: Dict) -> Optional[FixSolution]:
        """生成YAML修復"""
        actions = [
            FixAction(
                action_type="command_run",
                target_path=".",
                description="檢查並修復YAML格式問題",
                command="python -c \"import yaml; yaml.safe_load(open('.github/workflows/ci-enhanced.yml'))\"",
                risk_level="low",
                confidence=0.7
            )
        ]
        
        return FixSolution(
            problem_id=f"yaml_fix_{datetime.now().strftime('%H%M%S')}",
            problem_category=problem.category,
            solution_name="修復YAML格式問題",
            description="驗證並修復YAML配置文件格式",
            actions=actions,
            estimated_success_rate=0.7,
            risk_assessment="low",
            rollback_plan="使用git checkout恢復YAML文件"
        )
    
    def _generate_json_fix(self, problem: ProblemDetail, context: AnalysisResult, config: Dict) -> Optional[FixSolution]:
        """生成JSON修復"""
        actions = [
            FixAction(
                action_type="command_run",
                target_path=".",
                description="檢查並修復JSON格式問題",
                command="python -c \"import json; json.load(open('package.json'))\"",
                risk_level="low",
                confidence=0.7
            )
        ]
        
        return FixSolution(
            problem_id=f"json_fix_{datetime.now().strftime('%H%M%S')}",
            problem_category=problem.category,
            solution_name="修復JSON格式問題",
            description="驗證並修復JSON配置文件格式",
            actions=actions,
            estimated_success_rate=0.7,
            risk_assessment="low",
            rollback_plan="使用git checkout恢復JSON文件"
        )
    
    def _generate_config_fix(self, problem: ProblemDetail, context: AnalysisResult, config: Dict) -> Optional[FixSolution]:
        """生成配置修復"""
        actions = [
            FixAction(
                action_type="file_edit",
                target_path="apps/bot/.env.example",
                description="添加缺失的配置項",
                search_pattern=r"$",
                replacement="\n# 缺失的配置項\nMISSING_CONFIG=default_value",
                risk_level="low",
                confidence=0.8
            )
        ]
        
        return FixSolution(
            problem_id=f"config_fix_{datetime.now().strftime('%H%M%S')}",
            problem_category=problem.category,
            solution_name="修復配置問題",
            description="添加缺失的配置項到環境變數範例",
            actions=actions,
            estimated_success_rate=0.8,
            risk_assessment="low",
            rollback_plan="移除添加的配置行"
        )
    
    # === AI相關方法 ===
    
    def _build_ai_prompt(self, problem: ProblemDetail, context: AnalysisResult) -> str:
        """構建AI提示"""
        prompt = f"""
請分析以下CI/CD錯誤並提供修復建議：

錯誤類型: {problem.category.value}
嚴重程度: {problem.severity.value}
錯誤訊息: {problem.error_message}
檔案路徑: {problem.file_path or '未知'}
專案根目錄: {self.project_root}

上下文資訊:
- Job名稱: {context.job_name}
- Step名稱: {context.step_name}
- 相關檔案: {', '.join(problem.related_files)}

請提供：
1. 問題的根本原因分析
2. 具體的修復步驟
3. 修復的信心度 (0.0-1.0)
4. 潛在的風險評估
5. 回滾計劃

請以JSON格式回應，包含fix_actions陣列。
        """
        return prompt.strip()
    
    async def _call_ai_service(self, prompt: str) -> Optional[str]:
        """調用AI服務"""
        try:
            # 這裡應該調用實際的AI服務
            # 暫時返回模擬回應
            await asyncio.sleep(0.1)  # 模擬API調用
            
            return """
{
    "root_cause": "缺失依賴包導致導入錯誤",
    "fix_actions": [
        {
            "action_type": "command_run",
            "target_path": "apps/bot",
            "description": "安裝缺失的依賴包",
            "command": "poetry add missing_package",
            "confidence": 0.9,
            "risk_level": "medium"
        }
    ],
    "confidence": 0.9,
    "risk_assessment": "medium",
    "rollback_plan": "使用poetry remove移除包"
}
            """
        except Exception as e:
            self.logger.error(f"❌ AI服務調用失敗: {e}")
            return None
    
    def _parse_ai_response(self, 
                          response: str, 
                          problem: ProblemDetail, 
                          context: AnalysisResult) -> Optional[FixSolution]:
        """解析AI回應"""
        try:
            data = json.loads(response)
            
            actions = []
            for action_data in data.get("fix_actions", []):
                action = FixAction(
                    action_type=action_data.get("action_type", "command_run"),
                    target_path=action_data.get("target_path", "."),
                    description=action_data.get("description", "AI生成的修復"),
                    command=action_data.get("command"),
                    content=action_data.get("content"),
                    search_pattern=action_data.get("search_pattern"),
                    replacement=action_data.get("replacement"),
                    risk_level=action_data.get("risk_level", "medium"),
                    confidence=action_data.get("confidence", 0.7)
                )
                actions.append(action)
            
            solution = FixSolution(
                problem_id=f"ai_fix_{datetime.now().strftime('%H%M%S')}",
                problem_category=problem.category,
                solution_name="AI智能修復方案",
                description=data.get("root_cause", "AI分析的修復方案"),
                actions=actions,
                estimated_success_rate=data.get("confidence", 0.7),
                risk_assessment=data.get("risk_assessment", "medium"),
                rollback_plan=data.get("rollback_plan", "使用git revert回滾"),
                ai_generated=True
            )
            
            return solution
            
        except Exception as e:
            self.logger.error(f"❌ AI回應解析失敗: {e}")
            return None
    
    def save_solutions(self, solutions: List[FixSolution], output_dir: str = "fix_solutions"):
        """保存修復方案"""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"fix_solutions_{timestamp}.json"
            
            file_path = output_path / filename
            
            # 轉換為可序列化的格式
            solutions_data = []
            for solution in solutions:
                solution_dict = asdict(solution)
                # 處理Enum值
                solution_dict["problem_category"] = solution_dict["problem_category"].value
                solutions_data.append(solution_dict)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(solutions_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"📄 修復方案已保存: {file_path}")
            
        except Exception as e:
            self.logger.error(f"❌ 保存修復方案失敗: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取統計資訊"""
        return self.stats.copy()


async def main():
    """測試主函數"""
    generator = AutoFixGenerator()
    
    # 創建測試問題
    from intelligent_problem_analyzer import ProblemDetail, AnalysisResult
    
    test_problem = ProblemDetail(
        category=ProblemCategory.DEPENDENCY_ISSUE,
        severity=Severity.HIGH,
        title="缺失依賴包",
        description="導入錯誤",
        error_message="ImportError: No module named 'requests_mock'",
        file_path="tests/test_api.py",
        line_number=5
    )
    
    test_result = AnalysisResult(
        run_id="12345",
        job_name="Python Tests",
        step_name="Run tests",
        problems=[test_problem],
        raw_logs="",
        analysis_time=datetime.now().isoformat()
    )
    
    print("🔧 開始測試自動修復生成器...")
    solutions = await generator.generate_fixes([test_result])
    
    print(f"\n📊 生成了 {len(solutions)} 個修復方案:")
    for i, solution in enumerate(solutions, 1):
        print(f"\n{i}. {solution.solution_name}")
        print(f"   成功率: {solution.estimated_success_rate:.1%}")
        print(f"   風險: {solution.risk_assessment}")
        print(f"   動作數: {len(solution.actions)}")
        if solution.actions:
            print(f"   第一個動作: {solution.actions[0].description}")
    
    # 保存結果
    generator.save_solutions(solutions)
    
    print(f"\n📈 統計資訊: {generator.get_stats()}")


if __name__ == "__main__":
    asyncio.run(main())