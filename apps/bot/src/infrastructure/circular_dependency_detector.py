"""
循環依賴檢測和預防機制
實現依賴圖分析、檢測和預防循環依賴的完整方案
"""

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class DependencyType(Enum):
    """依賴類型"""

    CONSTRUCTOR = "constructor"  # 構造函數依賴
    PROPERTY = "property"  # 屬性依賴
    METHOD = "method"  # 方法依賴
    FACTORY = "factory"  # 工廠方法依賴
    LAZY = "lazy"  # 延遲依賴


class CycleDetectionResult(Enum):
    """循環檢測結果"""

    NO_CYCLE = "no_cycle"
    CYCLE_DETECTED = "cycle_detected"
    POTENTIAL_CYCLE = "potential_cycle"


@dataclass
class DependencyEdge:
    """依賴邊"""

    from_service: str
    to_service: str
    dependency_type: DependencyType
    created_at: float = field(default_factory=time.time)
    stack_trace: str | None = None


@dataclass
class CycleDetectionReport:
    """循環檢測報告"""

    result: CycleDetectionResult
    cycle_path: list[str] = field(default_factory=list)
    cycle_edges: list[DependencyEdge] = field(default_factory=list)
    detection_time: float = field(default_factory=time.time)
    suggestions: list[str] = field(default_factory=list)


class CircularDependencyDetector:
    """
    循環依賴檢測器

    功能：
    - 即時檢測循環依賴
    - 依賴圖分析和可視化
    - 提供修復建議
    - 預防性檢查
    """

    def __init__(self):
        self._dependency_graph: dict[str, set[str]] = defaultdict(set)
        self._dependency_edges: list[DependencyEdge] = []
        self._service_types: dict[str, type] = {}
        self._resolution_stack: list[str] = []
        self._lock = threading.RLock()

        # 已知的安全模式
        self._safe_patterns = {
            "lazy_initialization",
            "factory_method",
            "interface_segregation",
            "dependency_inversion",
        }

        # 高風險服務名稱模式
        self._risky_patterns = {
            "facade",
            "factory",
            "service_factory",
            "application_facade",
            "command_executor",
        }

    def register_service_type(self, service_name: str, service_type: type) -> None:
        """註冊服務類型"""
        with self._lock:
            self._service_types[service_name] = service_type
            logger.debug(f"註冊服務類型: {service_name} -> {service_type.__name__}")

    def add_dependency(
        self,
        from_service: str,
        to_service: str,
        dependency_type: DependencyType = DependencyType.CONSTRUCTOR,
        stack_trace: str | None = None,
    ) -> CycleDetectionReport:
        """
        添加依賴關係並檢測循環

        Args:
            from_service: 依賴源服務
            to_service: 依賴目標服務
            dependency_type: 依賴類型
            stack_trace: 調用堆疊

        Returns:
            循環檢測報告
        """
        with self._lock:
            # 創建依賴邊
            edge = DependencyEdge(
                from_service=from_service,
                to_service=to_service,
                dependency_type=dependency_type,
                stack_trace=stack_trace,
            )

            # 檢查是否會創建循環
            temp_graph = self._dependency_graph.copy()
            temp_graph[from_service].add(to_service)

            cycle_report = self._detect_cycles_in_graph(temp_graph)

            # 如果沒有循環，添加依賴
            if cycle_report.result == CycleDetectionResult.NO_CYCLE:
                self._dependency_graph[from_service].add(to_service)
                self._dependency_edges.append(edge)
                logger.debug(
                    f"添加依賴: {from_service} -> {to_service} "
                    f"({dependency_type.value})"
                )
            else:
                logger.warning(f"檢測到循環依賴: {from_service} -> {to_service}")
                cycle_report.suggestions = self._generate_cycle_resolution_suggestions(
                    cycle_report
                )

            return cycle_report

    def begin_resolution(self, service_name: str) -> bool:
        """
        開始服務解析

        Args:
            service_name: 服務名稱

        Returns:
            是否可以安全解析（無循環）
        """
        with self._lock:
            if service_name in self._resolution_stack:
                # 檢測到正在解析中的服務，可能是循環
                cycle_path = self._resolution_stack[
                    self._resolution_stack.index(service_name) :
                ]
                cycle_path.append(service_name)

                logger.error(f"檢測到解析時循環: {' -> '.join(cycle_path)}")
                return False

            self._resolution_stack.append(service_name)
            logger.debug(f"開始解析服務: {service_name}, 堆疊深度: {len(self._resolution_stack)}")
            return True

    def end_resolution(self, service_name: str) -> None:
        """結束服務解析"""
        with self._lock:
            if self._resolution_stack and self._resolution_stack[-1] == service_name:
                self._resolution_stack.pop()
                logger.debug(
                    f"完成解析服務: {service_name}, " f"剩餘深度: {len(self._resolution_stack)}"
                )

    def _detect_cycles_in_graph(
        self, graph: dict[str, set[str]]
    ) -> CycleDetectionReport:
        """檢測圖中的循環"""
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: list[str]) -> list[str] | None:
            if node in rec_stack:
                # 找到循環，返回循環路徑
                cycle_start_idx = path.index(node)
                return path[cycle_start_idx:] + [node]

            if node in visited:
                return None

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, set()):
                cycle = dfs(neighbor, path.copy())
                if cycle:
                    return cycle

            rec_stack.remove(node)
            return None

        # 檢查所有節點
        for node in graph:
            if node not in visited:
                cycle = dfs(node, [])
                if cycle:
                    # 找到循環，創建報告
                    cycle_edges = self._get_edges_for_cycle(cycle)
                    return CycleDetectionReport(
                        result=CycleDetectionResult.CYCLE_DETECTED,
                        cycle_path=cycle,
                        cycle_edges=cycle_edges,
                    )

        return CycleDetectionReport(result=CycleDetectionResult.NO_CYCLE)

    def _get_edges_for_cycle(self, cycle_path: list[str]) -> list[DependencyEdge]:
        """獲取循環路徑中的邊"""
        cycle_edges = []
        for i in range(len(cycle_path) - 1):
            from_service = cycle_path[i]
            to_service = cycle_path[i + 1]

            # 查找對應的邊
            for edge in self._dependency_edges:
                if edge.from_service == from_service and edge.to_service == to_service:
                    cycle_edges.append(edge)
                    break

        return cycle_edges

    def _generate_cycle_resolution_suggestions(
        self, report: CycleDetectionReport
    ) -> list[str]:
        """生成循環解析建議"""
        suggestions = []

        if not report.cycle_path:
            return suggestions

        # 分析循環類型
        cycle_services = set(report.cycle_path)

        # 檢查是否有工廠類服務
        factory_services = [
            s
            for s in cycle_services
            if any(pattern in s.lower() for pattern in self._risky_patterns)
        ]

        if factory_services:
            suggestions.append(f"💡 工廠模式解決：在 {', '.join(factory_services)} 中使用延遲初始化")
            suggestions.append("🔧 實現方式：設置 service_factory=None，在需要時才創建服務")

        # 檢查依賴類型
        constructor_deps = [
            e
            for e in report.cycle_edges
            if e.dependency_type == DependencyType.CONSTRUCTOR
        ]
        if constructor_deps:
            suggestions.append("🏗️ 構造函數依賴問題：考慮將部分依賴改為屬性注入或方法注入")

        # 通用解決方案
        suggestions.extend(
            [
                "🔄 介面隔離：通過抽象介面打破直接依賴",
                "📦 依賴倒置：讓高層模組依賴抽象而非具體實現",
                "⏰ 延遲載入：將非關鍵依賴改為延遲載入",
                "🎭 代理模式：使用代理對象延遲實際服務創建",
            ]
        )

        return suggestions

    def analyze_dependency_risks(self) -> dict[str, Any]:
        """分析依賴風險"""
        with self._lock:
            # 收集所有服務名稱
            all_services = set(self._service_types.keys())
            for edge in self._dependency_edges:
                all_services.add(edge.from_service)
                all_services.add(edge.to_service)

            analysis = {
                "total_services": len(all_services),
                "total_dependencies": len(self._dependency_edges),
                "high_risk_services": [],
                "complex_dependencies": [],
                "potential_bottlenecks": [],
                "recommendations": [],
            }

            # 計算每個服務的依賴度
            in_degree = defaultdict(int)
            out_degree = defaultdict(int)

            for edge in self._dependency_edges:
                out_degree[edge.from_service] += 1
                in_degree[edge.to_service] += 1

            # 識別高風險服務
            for service in all_services:
                risk_score = 0

                # 高出度（依賴太多服務）
                if out_degree[service] > 2:  # 降低閾值
                    risk_score += out_degree[service] * 2

                # 高入度（被太多服務依賴）
                if in_degree[service] > 1:  # 降低閾值
                    risk_score += in_degree[service] * 3

                # 名稱模式匹配
                if any(pattern in service.lower() for pattern in self._risky_patterns):
                    risk_score += 10

                if risk_score > 5:  # 降低閾值
                    analysis["high_risk_services"].append(
                        {
                            "service": service,
                            "risk_score": risk_score,
                            "out_degree": out_degree[service],
                            "in_degree": in_degree[service],
                        }
                    )

            # 生成建議
            if analysis["high_risk_services"]:
                analysis["recommendations"].extend(
                    [
                        "🎯 重構高風險服務，減少依賴複雜度",
                        "🔧 考慮拆分職責過重的服務",
                        "💉 使用依賴注入容器管理生命週期",
                    ]
                )

            return analysis

    def get_dependency_graph_summary(self) -> dict[str, Any]:
        """獲取依賴圖摘要"""
        with self._lock:
            return {
                "services_count": len(self._service_types),
                "dependencies_count": len(self._dependency_edges),
                "graph_depth": self._calculate_max_depth(),
                "cycles_detected": len(
                    [
                        r
                        for r in [self._detect_cycles_in_graph(self._dependency_graph)]
                        if r.result == CycleDetectionResult.CYCLE_DETECTED
                    ]
                ),
                "timestamp": time.time(),
            }

    def _calculate_max_depth(self) -> int:
        """計算依賴圖的最大深度"""
        if not self._dependency_graph:
            return 0

        def dfs_depth(node: str, visited: set[str]) -> int:
            if node in visited:
                return 0

            visited.add(node)
            max_child_depth = 0

            for child in self._dependency_graph.get(node, set()):
                child_depth = dfs_depth(child, visited.copy())
                max_child_depth = max(max_child_depth, child_depth)

            return max_child_depth + 1

        max_depth = 0
        for root in self._dependency_graph:
            depth = dfs_depth(root, set())
            max_depth = max(max_depth, depth)

        return max_depth

    def clear_graph(self) -> None:
        """清空依賴圖（用於測試）"""
        with self._lock:
            self._dependency_graph.clear()
            self._dependency_edges.clear()
            self._resolution_stack.clear()
            logger.info("依賴圖已清空")


# 全局檢測器實例
_global_detector: CircularDependencyDetector | None = None
_detector_lock = threading.Lock()


def get_circular_dependency_detector() -> CircularDependencyDetector:
    """獲取全局循環依賴檢測器"""
    global _global_detector

    if _global_detector is None:
        with _detector_lock:
            if _global_detector is None:
                _global_detector = CircularDependencyDetector()
                logger.info("創建全局循環依賴檢測器")

    return _global_detector


def reset_detector() -> None:
    """重置檢測器（用於測試）"""
    global _global_detector
    with _detector_lock:
        if _global_detector:
            _global_detector.clear_graph()
