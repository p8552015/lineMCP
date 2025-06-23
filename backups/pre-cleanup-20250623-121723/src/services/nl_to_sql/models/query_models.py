"""
查詢相關模型定義

包含自然語言轉 SQL 服務使用的所有資料模型
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict


class QueryType(Enum):
    """查詢類型枚舉"""
    
    MACHINE_STATUS = "machine_status"
    FAULT_ANALYSIS = "fault_analysis"
    PRODUCTION_STATS = "production_stats"
    ALL_MACHINES = "all_machines"
    SPECIFIC_MACHINE = "specific_machine"
    DEPARTMENT_STATUS = "department_status"
    UNKNOWN = "unknown"


@dataclass
class ParsedQuery:
    """解析後的查詢物件"""
    
    query_type: QueryType
    sql_query: str
    parameters: Dict[str, Any]
    confidence: float  # 0-1，查詢解析的信心度
    explanation: str  # 查詢說明
    
    def __post_init__(self):
        """資料驗證"""
        # 🔥 關鍵修復：確保 confidence 為數值類型，防止字串比較錯誤
        try:
            if isinstance(self.confidence, str):
                # 如果是字串，嘗試轉換為浮點數
                if self.confidence.strip() == '':
                    self.confidence = 0.0
                else:
                    self.confidence = float(self.confidence.strip())
            elif self.confidence is None:
                self.confidence = 0.0
            else:
                # 確保是數值類型
                self.confidence = float(self.confidence)
        except (ValueError, TypeError):
            # 轉換失敗時使用預設值
            self.confidence = 0.0
        
        # 🔥 確保信心度在有效範圍內
        self.confidence = max(0.0, min(1.0, self.confidence))
        
        if not isinstance(self.parameters, dict):
            raise TypeError("參數必須是字典類型")
            
        if not isinstance(self.explanation, str):
            raise TypeError("說明必須是字串類型")
    
    def is_successful(self) -> bool:
        """判斷解析是否成功"""
        return self.query_type != QueryType.UNKNOWN and self.confidence > 0.5
    
    def has_sql_query(self) -> bool:
        """判斷是否包含有效的 SQL 查詢"""
        return bool(self.sql_query and self.sql_query.strip())
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "query_type": self.query_type.value,
            "sql_query": self.sql_query,
            "parameters": self.parameters,
            "confidence": self.confidence,
            "explanation": self.explanation,
        }