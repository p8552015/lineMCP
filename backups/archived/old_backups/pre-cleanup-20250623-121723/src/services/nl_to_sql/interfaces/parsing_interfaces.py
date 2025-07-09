"""
自然語言解析抽象介面定義

實現 ISP (介面隔離原則)：
- 細粒度介面設計，避免龐大的綜合介面
- 客戶端只依賴需要使用的方法

實現 DIP (依賴倒置原則)：
- 高層模組依賴抽象介面，不依賴具體實現
- 具體實現實現抽象介面
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..models.query_models import ParsedQuery


class IParser(ABC):
    """
    自然語言解析器抽象介面
    
    職責：
    - 將自然語言文字解析為結構化查詢
    - 提供解析能力評估
    - 支援上下文資訊傳遞
    
    設計原則：
    - SRP: 專門負責解析功能
    - LSP: 所有實現必須可互換
    """
    
    @abstractmethod
    async def parse(
        self, 
        text: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> ParsedQuery:
        """
        解析自然語言文字為結構化查詢
        
        Args:
            text: 使用者輸入的自然語言文字
            context: 可選的上下文資訊，如資料庫結構
            
        Returns:
            ParsedQuery: 解析後的結構化查詢物件
            
        Raises:
            ParseError: 解析失敗時拋出
            
        契約要求：
        - 輸入的 text 不能為空
        - 返回的 ParsedQuery 必須包含有效的 query_type
        - confidence 值必須在 0-1 範圍內
        """
        pass
    
    @abstractmethod
    def can_handle(self, text: str) -> float:
        """
        評估解析器處理給定文字的能力
        
        Args:
            text: 要評估的自然語言文字
            
        Returns:
            float: 處理能力信心度 (0-1)
                  0: 完全無法處理
                  1: 完全確信可以處理
                  
        契約要求：
        - 返回值必須在 0-1 範圍內
        - 不應拋出異常
        - 執行時間應 < 10ms
        """
        pass
    
    @abstractmethod
    def get_parser_info(self) -> Dict[str, Any]:
        """
        獲取解析器資訊和元數據
        
        Returns:
            Dict[str, Any]: 解析器資訊
                - name: 解析器名稱
                - version: 版本號
                - capabilities: 支援的功能列表
                - performance_stats: 效能統計
                
        契約要求：
        - 必須包含 'name' 和 'version' 鍵
        - 不應拋出異常
        """
        pass


class IParsingStrategy(ABC):
    """
    解析策略抽象介面
    
    用於實現策略模式，支援不同的解析算法：
    - 規則解析策略
    - AI 增強解析策略
    - 混合解析策略
    
    設計原則：
    - OCP: 新增策略無需修改現有代碼
    - Strategy Pattern: 算法族可互換
    """
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """
        獲取策略名稱
        
        Returns:
            str: 策略的唯一名稱
        """
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        """
        獲取策略優先級
        
        Returns:
            int: 優先級數值，數值越大優先級越高
        """
        pass
    
    @abstractmethod
    async def execute_strategy(
        self, 
        text: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> ParsedQuery:
        """
        執行解析策略
        
        Args:
            text: 要解析的自然語言文字
            context: 解析上下文
            
        Returns:
            ParsedQuery: 解析結果
        """
        pass
    
    @abstractmethod
    def is_applicable(self, text: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        判斷策略是否適用於給定的輸入
        
        Args:
            text: 要判斷的文字
            context: 判斷上下文
            
        Returns:
            bool: 是否適用
        """
        pass


class IParserFactory(ABC):
    """
    解析器工廠抽象介面
    
    職責：
    - 創建和管理解析器實例
    - 支援解析器的動態註冊和發現
    
    設計原則：
    - Factory Pattern: 封裝對象創建邏輯
    - OCP: 支援新解析器類型的擴展
    """
    
    @abstractmethod
    def create_parser(self, parser_type: str, **kwargs) -> IParser:
        """
        創建指定類型的解析器
        
        Args:
            parser_type: 解析器類型標識
            **kwargs: 創建參數
            
        Returns:
            IParser: 解析器實例
            
        Raises:
            UnknownParserTypeError: 不支援的解析器類型
        """
        pass
    
    @abstractmethod
    def register_parser_type(
        self, 
        parser_type: str, 
        parser_class: type, 
        is_default: bool = False
    ) -> None:
        """
        註冊新的解析器類型
        
        Args:
            parser_type: 解析器類型標識
            parser_class: 解析器類別
            is_default: 是否設為預設解析器
        """
        pass
    
    @abstractmethod
    def get_available_parser_types(self) -> List[str]:
        """
        獲取所有可用的解析器類型
        
        Returns:
            List[str]: 解析器類型列表
        """
        pass
    
    @abstractmethod
    def get_default_parser(self) -> IParser:
        """
        獲取預設解析器實例
        
        Returns:
            IParser: 預設解析器
        """
        pass