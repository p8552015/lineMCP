"""
自然語言轉 SQL 服務模型定義模組

定義了 NL-to-SQL 服務使用的所有資料模型和枚舉類型
"""

from .query_models import ParsedQuery, QueryType

__all__ = [
    "ParsedQuery",
    "QueryType",
]