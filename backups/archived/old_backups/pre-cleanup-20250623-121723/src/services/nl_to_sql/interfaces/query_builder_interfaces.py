"""
SQL 查詢建構抽象介面定義

實現 ISP (介面隔離原則)：
- 分離查詢建構和模板管理職責
- 客戶端只依賴需要的介面方法

實現 DIP (依賴倒置原則)：
- 查詢建構依賴抽象介面
- 支援多種建構策略實現
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..models.query_models import QueryType


class IQueryBuilder(ABC):
    """
    SQL 查詢建構器抽象介面
    
    職責：
    - 根據查詢類型和參數建構 SQL 查詢
    - 驗證查詢參數的有效性
    - 提供查詢優化建議
    
    設計原則：
    - SRP: 專門負責 SQL 建構
    - LSP: 所有實現必須可互換
    """
    
    @abstractmethod
    def build_query(
        self, 
        query_type: QueryType, 
        parameters: Dict[str, Any]
    ) -> str:
        """
        建構 SQL 查詢語句
        
        Args:
            query_type: 查詢類型枚舉
            parameters: 查詢參數字典
            
        Returns:
            str: 完整的 SQL 查詢語句
            
        Raises:
            InvalidQueryTypeError: 不支援的查詢類型
            InvalidParametersError: 參數驗證失敗
            QueryBuildError: 查詢建構失敗
            
        契約要求：
        - 返回的 SQL 必須是有效的語法
        - 必須正確處理 SQL 注入防護
        - 參數必須正確轉義和格式化
        """
        pass
    
    @abstractmethod
    def validate_parameters(
        self, 
        query_type: QueryType, 
        parameters: Dict[str, Any]
    ) -> bool:
        """
        驗證查詢參數的有效性
        
        Args:
            query_type: 查詢類型
            parameters: 要驗證的參數
            
        Returns:
            bool: 參數是否有效
            
        契約要求：
        - 必須檢查必要參數是否存在
        - 必須驗證參數值的格式和範圍
        - 不應拋出異常，返回 false 即可
        """
        pass
    
    @abstractmethod
    def get_required_parameters(self, query_type: QueryType) -> List[str]:
        """
        獲取指定查詢類型所需的參數列表
        
        Args:
            query_type: 查詢類型
            
        Returns:
            List[str]: 必要參數名稱列表
            
        Raises:
            InvalidQueryTypeError: 不支援的查詢類型
        """
        pass
    
    @abstractmethod
    def get_supported_query_types(self) -> List[QueryType]:
        """
        獲取支援的查詢類型列表
        
        Returns:
            List[QueryType]: 支援的查詢類型
        """
        pass
    
    @abstractmethod
    def get_query_metadata(self, query_type: QueryType) -> Dict[str, Any]:
        """
        獲取查詢類型的元數據資訊
        
        Args:
            query_type: 查詢類型
            
        Returns:
            Dict[str, Any]: 查詢元數據
                - description: 查詢描述
                - estimated_complexity: 預估複雜度
                - performance_hint: 效能提示
                
        Raises:
            InvalidQueryTypeError: 不支援的查詢類型
        """
        pass


class ITemplateManager(ABC):
    """
    SQL 模板管理器抽象介面
    
    職責：
    - 管理 SQL 查詢模板
    - 支援模板的動態載入和更新
    - 提供模板驗證和優化
    
    設計原則：
    - SRP: 專門負責模板管理
    - OCP: 支援新模板類型擴展
    """
    
    @abstractmethod
    def get_template(self, query_type: QueryType) -> str:
        """
        獲取指定查詢類型的 SQL 模板
        
        Args:
            query_type: 查詢類型
            
        Returns:
            str: SQL 模板字串，包含參數佔位符
            
        Raises:
            TemplateNotFoundError: 模板不存在
        """
        pass
    
    @abstractmethod
    def set_template(self, query_type: QueryType, template: str) -> None:
        """
        設置查詢類型的 SQL 模板
        
        Args:
            query_type: 查詢類型
            template: SQL 模板字串
            
        Raises:
            InvalidTemplateError: 模板格式不正確
        """
        pass
    
    @abstractmethod
    def validate_template(self, template: str) -> bool:
        """
        驗證 SQL 模板的有效性
        
        Args:
            template: 要驗證的模板
            
        Returns:
            bool: 模板是否有效
        """
        pass
    
    @abstractmethod
    def get_template_parameters(self, query_type: QueryType) -> List[str]:
        """
        獲取模板中的參數列表
        
        Args:
            query_type: 查詢類型
            
        Returns:
            List[str]: 參數名稱列表
        """
        pass
    
    @abstractmethod
    def load_templates_from_file(self, file_path: str) -> None:
        """
        從檔案載入模板配置
        
        Args:
            file_path: 模板配置檔案路徑
            
        Raises:
            TemplateLoadError: 載入失敗
        """
        pass
    
    @abstractmethod
    def reload_templates(self) -> None:
        """
        重新載入所有模板
        
        用於支援熱更新功能
        """
        pass


class IQueryOptimizer(ABC):
    """
    查詢優化器抽象介面
    
    職責：
    - 分析和優化 SQL 查詢
    - 提供效能改進建議
    - 檢測潛在的效能問題
    
    設計原則：
    - SRP: 專門負責查詢優化
    - Strategy Pattern: 支援不同優化策略
    """
    
    @abstractmethod
    def optimize_query(self, sql_query: str) -> str:
        """
        優化 SQL 查詢語句
        
        Args:
            sql_query: 原始 SQL 查詢
            
        Returns:
            str: 優化後的 SQL 查詢
        """
        pass
    
    @abstractmethod
    def analyze_query(self, sql_query: str) -> Dict[str, Any]:
        """
        分析 SQL 查詢的效能特徵
        
        Args:
            sql_query: 要分析的 SQL 查詢
            
        Returns:
            Dict[str, Any]: 分析結果
                - estimated_cost: 預估執行成本
                - complexity_score: 複雜度評分
                - optimization_suggestions: 優化建議列表
        """
        pass
    
    @abstractmethod
    def validate_query_security(self, sql_query: str) -> Dict[str, Any]:
        """
        驗證 SQL 查詢的安全性
        
        Args:
            sql_query: 要驗證的 SQL 查詢
            
        Returns:
            Dict[str, Any]: 安全性檢查結果
                - is_safe: 是否安全
                - security_issues: 安全問題列表
                - risk_level: 風險等級
        """
        pass


class IQueryCache(ABC):
    """
    查詢快取抽象介面
    
    職責：
    - 快取查詢結果以提升效能
    - 管理快取的生命週期
    - 提供快取統計資訊
    
    設計原則：
    - SRP: 專門負責快取管理
    - Strategy Pattern: 支援不同快取策略
    """
    
    @abstractmethod
    def get_cached_result(self, cache_key: str) -> Optional[Any]:
        """
        獲取快取的查詢結果
        
        Args:
            cache_key: 快取鍵值
            
        Returns:
            Optional[Any]: 快取的結果，若無則返回 None
        """
        pass
    
    @abstractmethod
    def set_cached_result(
        self, 
        cache_key: str, 
        result: Any, 
        ttl: Optional[int] = None
    ) -> None:
        """
        設置查詢結果快取
        
        Args:
            cache_key: 快取鍵值
            result: 要快取的結果
            ttl: 快取存活時間（秒），None 表示永不過期
        """
        pass
    
    @abstractmethod
    def invalidate_cache(self, pattern: Optional[str] = None) -> None:
        """
        使快取失效
        
        Args:
            pattern: 可選的快取鍵模式，None 表示清除所有快取
        """
        pass
    
    @abstractmethod
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        獲取快取統計資訊
        
        Returns:
            Dict[str, Any]: 快取統計
                - hit_rate: 命中率
                - total_requests: 總請求數
                - cache_size: 快取大小
        """
        pass