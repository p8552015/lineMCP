"""
工具類別模組

提供支援功能的工具類別：
- 依賴自動安裝
- 進程健康監控
- 執行環境檢測

遵循 SRP (單一職責原則)，每個工具專注特定功能。
"""

from .dependency_installer import DependencyInstaller, InstallationResult
from .health_monitor import HealthMonitor, HealthStatus
from .runtime_detector import DetectionResult, RuntimeDetector

__all__ = [
    "DependencyInstaller",
    "InstallationResult",
    "HealthMonitor",
    "HealthStatus",
    "RuntimeDetector",
    "DetectionResult",
]
