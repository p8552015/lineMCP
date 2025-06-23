"""
統計追蹤和配置管理抽象介面定義

實現 ISP (介面隔離原則)：
- 分離統計追蹤和配置管理職責
- 細粒度介面設計，避免客戶端依賴不需要的方法

實現 DIP (依賴倒置原則)：
- 服務依賴抽象統計和配置介面
- 支援不同的統計和配置實現策略
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum


class StatisticsEventType(Enum):
    """統計事件類型枚舉"""
    PARSE_SUCCESS = "parse_success"
    PARSE_FAILURE = "parse_failure"
    QUERY_BUILD_SUCCESS = "query_build_success"
    QUERY_BUILD_FAILURE = "query_build_failure"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"


class IStatistics(ABC):
    """
    統計追蹤抽象介面
    
    職責：
    - 記錄和追蹤系統運行統計
    - 提供效能指標和使用分析
    - 支援統計資料的查詢和匯出
    
    設計原則：
    - SRP: 專門負責統計追蹤
    - Observer Pattern: 事件驅動的統計收集
    """
    
    @abstractmethod
    def record_event(
        self, 
        event_type: StatisticsEventType, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        記錄統計事件
        
        Args:
            event_type: 事件類型
            metadata: 可選的事件元數據
            
        契約要求：
        - 方法不應拋出異常（統計失敗不應影響主流程）
        - 執行時間應 < 1ms
        - 支援高併發調用
        """
        pass
    
    @abstractmethod
    def record_success(
        self, 
        operation_type: str, 
        duration: float, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        記錄成功操作
        
        Args:
            operation_type: 操作類型（如 "rule_parsing", "ai_parsing"）
            duration: 操作耗時（秒）
            metadata: 操作元數據
        """
        pass
    
    @abstractmethod
    def record_failure(
        self, 
        operation_type: str, 
        error_type: str, 
        error_message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        記錄失敗操作
        
        Args:
            operation_type: 操作類型
            error_type: 錯誤類型
            error_message: 錯誤訊息
            metadata: 錯誤元數據
        """
        pass
    
    @abstractmethod
    def get_summary_stats(self) -> Dict[str, Any]:
        """
        獲取統計摘要
        
        Returns:
            Dict[str, Any]: 統計摘要
                - total_requests: 總請求數
                - success_rate: 成功率
                - average_response_time: 平均回應時間
                - error_distribution: 錯誤分布
        """
        pass
    
    @abstractmethod
    def get_detailed_stats(
        self, 
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        operation_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        獲取詳細統計資料
        
        Args:
            start_time: 開始時間（ISO 格式）
            end_time: 結束時間（ISO 格式）
            operation_type: 過濾的操作類型
            
        Returns:
            Dict[str, Any]: 詳細統計資料
        """
        pass
    
    @abstractmethod
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        獲取效能指標
        
        Returns:
            Dict[str, Any]: 效能指標
                - response_time_percentiles: 回應時間百分位
                - throughput: 吞吐量
                - error_rate: 錯誤率
                - resource_usage: 資源使用情況
        """
        pass
    
    @abstractmethod
    def reset_stats(self) -> None:
        """
        重置統計資料
        
        注意：此操作會清除所有統計資料，請謹慎使用
        """
        pass
    
    @abstractmethod
    def export_stats(self, format_type: str = "json") -> str:
        """
        匯出統計資料
        
        Args:
            format_type: 匯出格式（"json", "csv", "xml"）
            
        Returns:
            str: 格式化的統計資料
        """
        pass


class IConfiguration(ABC):
    """
    配置管理抽象介面
    
    職責：
    - 管理系統配置參數
    - 支援配置的動態載入和更新
    - 提供配置驗證和預設值
    
    設計原則：
    - SRP: 專門負責配置管理
    - Strategy Pattern: 支援不同配置來源
    """
    
    @abstractmethod
    def get_config_value(
        self, 
        key: str, 
        default: Any = None,
        config_section: Optional[str] = None
    ) -> Any:
        """
        獲取配置值
        
        Args:
            key: 配置鍵名
            default: 預設值
            config_section: 可選的配置段落
            
        Returns:
            Any: 配置值
        """
        pass
    
    @abstractmethod
    def set_config_value(
        self, 
        key: str, 
        value: Any,
        config_section: Optional[str] = None
    ) -> None:
        """
        設置配置值
        
        Args:
            key: 配置鍵名
            value: 配置值
            config_section: 可選的配置段落
        """
        pass
    
    @abstractmethod
    def get_query_patterns(self) -> Dict[str, Any]:
        """
        獲取查詢模式配置
        
        Returns:
            Dict[str, Any]: 查詢模式字典
        """
        pass
    
    @abstractmethod
    def get_sql_templates(self) -> Dict[str, str]:
        """
        獲取 SQL 模板配置
        
        Returns:
            Dict[str, str]: SQL 模板字典
        """
        pass
    
    @abstractmethod
    def get_parser_settings(self) -> Dict[str, Any]:
        """
        獲取解析器設定
        
        Returns:
            Dict[str, Any]: 解析器設定字典
        """
        pass
    
    @abstractmethod
    def reload_config(self) -> None:
        """
        重新載入配置
        
        用於支援配置熱更新
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> Dict[str, Any]:
        """
        驗證配置的有效性
        
        Returns:
            Dict[str, Any]: 驗證結果
                - is_valid: 配置是否有效
                - errors: 錯誤列表
                - warnings: 警告列表
        """
        pass
    
    @abstractmethod
    def get_config_metadata(self) -> Dict[str, Any]:
        """
        獲取配置元數據
        
        Returns:
            Dict[str, Any]: 配置元數據
                - version: 配置版本
                - last_updated: 最後更新時間
                - source: 配置來源
        """
        pass


class IMetricsCollector(ABC):
    """
    指標收集器抽象介面
    
    職責：
    - 收集系統運行指標
    - 支援自定義指標定義
    - 與監控系統整合
    
    設計原則：
    - SRP: 專門負責指標收集
    - Observer Pattern: 事件驅動的指標收集
    """
    
    @abstractmethod
    def increment_counter(
        self, 
        metric_name: str, 
        value: int = 1,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """
        增加計數器指標
        
        Args:
            metric_name: 指標名稱
            value: 增加的值
            tags: 指標標籤
        """
        pass
    
    @abstractmethod
    def record_gauge(
        self, 
        metric_name: str, 
        value: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """
        記錄量表指標
        
        Args:
            metric_name: 指標名稱
            value: 指標值
            tags: 指標標籤
        """
        pass
    
    @abstractmethod
    def record_histogram(
        self, 
        metric_name: str, 
        value: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """
        記錄直方圖指標
        
        Args:
            metric_name: 指標名稱
            value: 指標值
            tags: 指標標籤
        """
        pass
    
    @abstractmethod
    def start_timer(self, metric_name: str) -> str:
        """
        開始計時器
        
        Args:
            metric_name: 計時器指標名稱
            
        Returns:
            str: 計時器 ID
        """
        pass
    
    @abstractmethod
    def stop_timer(self, timer_id: str) -> float:
        """
        停止計時器並記錄耗時
        
        Args:
            timer_id: 計時器 ID
            
        Returns:
            float: 耗時（秒）
        """
        pass
    
    @abstractmethod
    def get_metric_summary(self) -> Dict[str, Any]:
        """
        獲取指標摘要
        
        Returns:
            Dict[str, Any]: 指標摘要
        """
        pass


class ILogger(ABC):
    """
    日誌記錄抽象介面
    
    職責：
    - 記錄系統運行日誌
    - 支援不同日誌級別
    - 提供結構化日誌功能
    
    設計原則：
    - SRP: 專門負責日誌記錄
    - Strategy Pattern: 支援不同日誌後端
    """
    
    @abstractmethod
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """記錄調試日誌"""
        pass
    
    @abstractmethod
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """記錄資訊日誌"""
        pass
    
    @abstractmethod
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """記錄警告日誌"""
        pass
    
    @abstractmethod
    def error(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """記錄錯誤日誌"""
        pass
    
    @abstractmethod
    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """記錄嚴重錯誤日誌"""
        pass