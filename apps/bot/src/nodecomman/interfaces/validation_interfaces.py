"""
環境驗證介面模組

定義符合 SOLID 原則的環境驗證相關抽象介面：
- IEnvironmentValidator: 環境驗證介面
- IDependencyManager: 依賴管理介面
- IInstallationGuide: 安裝指南介面

遵循設計原則：
- SRP: 每個介面專注單一職責
- ISP: 介面隔離，細粒度設計
- DIP: 依賴抽象而非具體實現
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .runtime_interfaces import RuntimeType


class ValidationLevel(Enum):
    """驗證級別"""
    BASIC = "basic"          # 基本檢查：命令是否存在
    STANDARD = "standard"    # 標準檢查：版本、依賴等
    COMPREHENSIVE = "comprehensive"  # 全面檢查：效能、相容性等


class IssueType(Enum):
    """問題類型"""
    MISSING_RUNTIME = "missing_runtime"
    WRONG_VERSION = "wrong_version"
    MISSING_DEPENDENCY = "missing_dependency"
    PERMISSION_ERROR = "permission_error"
    PATH_ERROR = "path_error"
    CONFIGURATION_ERROR = "configuration_error"
    NETWORK_ERROR = "network_error"


class IssueSeverity(Enum):
    """問題嚴重程度"""
    CRITICAL = "critical"    # 阻止運行
    HIGH = "high"           # 影響功能
    MEDIUM = "medium"       # 影響效能
    LOW = "low"             # 輕微影響
    INFO = "info"           # 僅供參考


class AutoFixStrategy(Enum):
    """自動修復策略"""
    INSTALL = "install"      # 安裝缺失組件
    UPDATE = "update"        # 更新版本
    CONFIGURE = "configure"  # 修改配置
    REPAIR = "repair"        # 修復損壞
    SKIP = "skip"           # 跳過問題


@dataclass
class ValidationIssue:
    """驗證問題"""
    type: IssueType
    severity: IssueSeverity
    message: str
    component: str
    details: Dict[str, Any] = field(default_factory=dict)
    auto_fix_available: bool = False
    auto_fix_strategy: Optional[AutoFixStrategy] = None
    suggestion: Optional[str] = None
    
    @property
    def is_blocking(self) -> bool:
        """檢查問題是否會阻止運行"""
        return self.severity in [IssueSeverity.CRITICAL, IssueSeverity.HIGH]
    
    @property
    def can_auto_fix(self) -> bool:
        """檢查是否可以自動修復"""
        return self.auto_fix_available and self.auto_fix_strategy is not None


@dataclass
class ValidationResult:
    """驗證結果"""
    runtime_type: RuntimeType
    is_valid: bool
    validation_level: ValidationLevel
    issues: List[ValidationIssue] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def critical_issues(self) -> List[ValidationIssue]:
        """獲取關鍵問題"""
        return [issue for issue in self.issues if issue.severity == IssueSeverity.CRITICAL]
    
    @property
    def auto_fixable_issues(self) -> List[ValidationIssue]:
        """獲取可自動修復的問題"""
        return [issue for issue in self.issues if issue.can_auto_fix]
    
    @property
    def blocking_issues(self) -> List[ValidationIssue]:
        """獲取阻塞問題"""
        return [issue for issue in self.issues if issue.is_blocking]
    
    def has_issues(self, severity: Optional[IssueSeverity] = None) -> bool:
        """檢查是否有指定嚴重程度的問題"""
        if severity is None:
            return len(self.issues) > 0
        return any(issue.severity == severity for issue in self.issues)


@dataclass
class DependencyInfo:
    """依賴資訊"""
    name: str
    version: Optional[str] = None
    required: bool = True
    installed: bool = False
    available_versions: List[str] = field(default_factory=list)
    install_command: Optional[str] = None
    description: Optional[str] = None
    
    @property
    def is_satisfied(self) -> bool:
        """檢查依賴是否滿足"""
        return self.installed or not self.required


@dataclass
class InstallationStep:
    """安裝步驟"""
    step_number: int
    title: str
    description: str
    command: Optional[str] = None
    verification_command: Optional[str] = None
    expected_output: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "step": self.step_number,
            "title": self.title,
            "description": self.description,
            "command": self.command,
            "verification": self.verification_command,
            "expected_output": self.expected_output,
            "notes": self.notes
        }


@dataclass
class InstallationGuide:
    """安裝指南"""
    runtime_type: RuntimeType
    platform: str
    steps: List[InstallationStep] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    troubleshooting: Dict[str, str] = field(default_factory=dict)
    references: List[str] = field(default_factory=list)
    
    def add_step(self, step: InstallationStep) -> None:
        """添加安裝步驟"""
        self.steps.append(step)
        # 自動排序
        self.steps.sort(key=lambda s: s.step_number)
    
    def to_markdown(self) -> str:
        """轉換為 Markdown 格式"""
        lines = [
            f"# {self.runtime_type.value.title()} 安裝指南",
            f"平台：{self.platform}",
            ""
        ]
        
        if self.prerequisites:
            lines.extend([
                "## 前置需求",
                ""
            ])
            for req in self.prerequisites:
                lines.append(f"- {req}")
            lines.append("")
        
        lines.extend([
            "## 安裝步驟",
            ""
        ])
        
        for step in self.steps:
            lines.extend([
                f"### {step.step_number}. {step.title}",
                step.description,
                ""
            ])
            
            if step.command:
                lines.extend([
                    "```bash",
                    step.command,
                    "```",
                    ""
                ])
            
            if step.verification_command:
                lines.extend([
                    "驗證：",
                    "```bash",
                    step.verification_command,
                    "```",
                    ""
                ])
                
                if step.expected_output:
                    lines.extend([
                        f"預期輸出：`{step.expected_output}`",
                        ""
                    ])
            
            if step.notes:
                lines.append("注意事項：")
                for note in step.notes:
                    lines.append(f"- {note}")
                lines.append("")
        
        if self.troubleshooting:
            lines.extend([
                "## 疑難排解",
                ""
            ])
            for problem, solution in self.troubleshooting.items():
                lines.extend([
                    f"**問題：{problem}**",
                    f"解決方案：{solution}",
                    ""
                ])
        
        if self.references:
            lines.extend([
                "## 參考資料",
                ""
            ])
            for ref in self.references:
                lines.append(f"- {ref}")
        
        return "\n".join(lines)


class IEnvironmentValidator(ABC):
    """
    環境驗證介面
    
    遵循 SRP 原則：專注於環境驗證功能
    遵循 ISP 原則：只定義驗證相關的方法
    """
    
    @abstractmethod
    async def validate_runtime(
        self, 
        runtime_type: RuntimeType,
        level: ValidationLevel = ValidationLevel.STANDARD
    ) -> ValidationResult:
        """
        驗證指定運行時環境
        
        Args:
            runtime_type: 運行時類型
            level: 驗證級別
            
        Returns:
            ValidationResult: 驗證結果
        """
        pass
    
    @abstractmethod
    async def validate_all_runtimes(
        self,
        level: ValidationLevel = ValidationLevel.STANDARD
    ) -> Dict[RuntimeType, ValidationResult]:
        """
        驗證所有運行時環境
        
        Args:
            level: 驗證級別
            
        Returns:
            Dict[RuntimeType, ValidationResult]: 運行時類型到驗證結果的映射
        """
        pass
    
    @abstractmethod
    async def auto_fix_issues(
        self, 
        runtime_type: RuntimeType,
        issues: Optional[List[ValidationIssue]] = None
    ) -> Dict[ValidationIssue, bool]:
        """
        自動修復環境問題
        
        Args:
            runtime_type: 運行時類型
            issues: 要修復的問題列表，None 表示修復所有可修復的問題
            
        Returns:
            Dict[ValidationIssue, bool]: 問題到修復結果的映射
        """
        pass
    
    @abstractmethod
    async def get_installation_guide(
        self, 
        runtime_type: RuntimeType,
        platform: Optional[str] = None
    ) -> InstallationGuide:
        """
        獲取安裝指南
        
        Args:
            runtime_type: 運行時類型
            platform: 目標平台，None 表示當前平台
            
        Returns:
            InstallationGuide: 安裝指南
        """
        pass
    
    @abstractmethod
    async def check_dependencies(
        self, 
        runtime_type: RuntimeType,
        packages: Optional[List[str]] = None
    ) -> List[DependencyInfo]:
        """
        檢查依賴套件
        
        Args:
            runtime_type: 運行時類型
            packages: 要檢查的套件列表，None 表示檢查所有必要套件
            
        Returns:
            List[DependencyInfo]: 依賴資訊列表
        """
        pass
    
    @abstractmethod
    async def suggest_alternatives(
        self, 
        runtime_type: RuntimeType
    ) -> List[RuntimeType]:
        """
        建議替代運行時
        
        Args:
            runtime_type: 當前運行時類型
            
        Returns:
            List[RuntimeType]: 建議的替代運行時類型列表
        """
        pass


class IDependencyManager(ABC):
    """
    依賴管理介面
    
    遵循 SRP 原則：專注於依賴套件的管理
    """
    
    @abstractmethod
    async def install_package(
        self, 
        runtime_type: RuntimeType,
        package_name: str,
        version: Optional[str] = None
    ) -> bool:
        """
        安裝套件
        
        Args:
            runtime_type: 運行時類型
            package_name: 套件名稱
            version: 套件版本，None 表示最新版本
            
        Returns:
            bool: 安裝是否成功
        """
        pass
    
    @abstractmethod
    async def uninstall_package(
        self, 
        runtime_type: RuntimeType,
        package_name: str
    ) -> bool:
        """
        卸載套件
        
        Args:
            runtime_type: 運行時類型
            package_name: 套件名稱
            
        Returns:
            bool: 卸載是否成功
        """
        pass
    
    @abstractmethod
    async def update_package(
        self, 
        runtime_type: RuntimeType,
        package_name: str,
        version: Optional[str] = None
    ) -> bool:
        """
        更新套件
        
        Args:
            runtime_type: 運行時類型
            package_name: 套件名稱
            version: 目標版本，None 表示最新版本
            
        Returns:
            bool: 更新是否成功
        """
        pass
    
    @abstractmethod
    async def list_installed_packages(
        self, 
        runtime_type: RuntimeType
    ) -> List[DependencyInfo]:
        """
        列出已安裝的套件
        
        Args:
            runtime_type: 運行時類型
            
        Returns:
            List[DependencyInfo]: 已安裝套件列表
        """
        pass
    
    @abstractmethod
    async def search_packages(
        self, 
        runtime_type: RuntimeType,
        query: str
    ) -> List[DependencyInfo]:
        """
        搜尋套件
        
        Args:
            runtime_type: 運行時類型
            query: 搜尋關鍵字
            
        Returns:
            List[DependencyInfo]: 搜尋結果列表
        """
        pass
    
    @abstractmethod
    async def get_package_info(
        self, 
        runtime_type: RuntimeType,
        package_name: str
    ) -> Optional[DependencyInfo]:
        """
        獲取套件資訊
        
        Args:
            runtime_type: 運行時類型
            package_name: 套件名稱
            
        Returns:
            Optional[DependencyInfo]: 套件資訊，不存在返回 None
        """
        pass


class IInstallationGuideProvider(ABC):
    """
    安裝指南提供者介面
    
    遵循 SRP 原則：專注於安裝指南的生成和管理
    """
    
    @abstractmethod
    async def generate_guide(
        self, 
        runtime_type: RuntimeType,
        platform: str,
        validation_result: Optional[ValidationResult] = None
    ) -> InstallationGuide:
        """
        生成安裝指南
        
        Args:
            runtime_type: 運行時類型
            platform: 目標平台
            validation_result: 驗證結果，用於客製化指南
            
        Returns:
            InstallationGuide: 安裝指南
        """
        pass
    
    @abstractmethod
    async def get_supported_platforms(
        self, 
        runtime_type: RuntimeType
    ) -> List[str]:
        """
        獲取支援的平台列表
        
        Args:
            runtime_type: 運行時類型
            
        Returns:
            List[str]: 支援的平台列表
        """
        pass
    
    @abstractmethod
    async def update_guide_templates(self) -> bool:
        """
        更新指南模板
        
        Returns:
            bool: 更新是否成功
        """
        pass