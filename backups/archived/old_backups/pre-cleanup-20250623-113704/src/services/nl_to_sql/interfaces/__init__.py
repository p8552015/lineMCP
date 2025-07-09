"""
自然語言轉 SQL 服務抽象介面模組

這個模組定義了 NL-to-SQL 服務的所有抽象介面，實現了：
- ISP (介面隔離原則): 細粒度的介面設計
- DIP (依賴倒置原則): 高層模組依賴抽象介面

模組結構：
- parsing_interfaces.py: 解析相關抽象介面
- query_builder_interfaces.py: 查詢建構相關抽象介面
- statistics_interfaces.py: 統計追蹤相關抽象介面
"""

from .parsing_interfaces import IParser, IParsingStrategy
from .query_builder_interfaces import IQueryBuilder, ITemplateManager
from .statistics_interfaces import IStatistics, IConfiguration

__all__ = [
    # 解析介面
    "IParser",
    "IParsingStrategy", 
    
    # 查詢建構介面
    "IQueryBuilder",
    "ITemplateManager",
    
    # 統計和配置介面
    "IStatistics",
    "IConfiguration",
]