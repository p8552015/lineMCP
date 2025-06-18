"""
MCP 查詢相關資料模型

定義 MCP 查詢操作的資料結構。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field

try:
    from pydantic import ConfigDict
    PYDANTIC_V2 = True
except ImportError:
    # Pydantic v1 相容性
    PYDANTIC_V2 = False
    
    class ConfigDict:
        def __init__(self, **kwargs):
            pass


class QueryType(str, Enum):
    """查詢類型枚舉"""
    SINGLE = "single"
    BATCH = "batch"
    STREAM = "stream"
    HEALTH_CHECK = "health_check"
    LIST_TOOLS = "list_tools"


class QueryPriority(str, Enum):
    """查詢優先級"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class QueryFilter(BaseModel):
    """查詢篩選條件"""
    if PYDANTIC_V2:
        model_config = ConfigDict(
            extra="forbid",
            validate_assignment=True,
        )
    else:
        class Config:
            extra = "forbid"
            validate_assignment = True
    
    server: Optional[str] = Field(
        default=None,
        description="指定伺服器名稱"
    )
    
    tool: Optional[str] = Field(
        default=None,
        description="指定工具名稱"
    )
    
    status: Optional[str] = Field(
        default=None,
        description="指定狀態"
    )
    
    since: Optional[datetime] = Field(
        default=None,
        description="起始時間"
    )
    
    until: Optional[datetime] = Field(
        default=None,
        description="結束時間"
    )
    
    tags: list[str] = Field(
        default_factory=list,
        description="標籤篩選"
    )


class QueryOptions(BaseModel):
    """查詢選項配置"""
    if PYDANTIC_V2:
        model_config = ConfigDict(
            extra="forbid",
            validate_assignment=True,
        )
    else:
        class Config:
            extra = "forbid"
            validate_assignment = True
    
    limit: Optional[int] = Field(
        default=100,
        ge=1,
        le=10000,
        description="結果數量限制"
    )
    
    offset: Optional[int] = Field(
        default=0,
        ge=0,
        description="結果偏移量"
    )
    
    sort_by: Optional[str] = Field(
        default="timestamp",
        description="排序欄位"
    )
    
    sort_order: Optional[str] = Field(
        default="desc",
        pattern=r"^(asc|desc)$",
        description="排序順序"
    )
    
    include_metadata: bool = Field(
        default=True,
        description="是否包含中繼資料"
    )


class QueryRequest(BaseModel):
    """查詢請求"""
    if PYDANTIC_V2:
        model_config = ConfigDict(
            extra="forbid",
            validate_assignment=True,
        )
    else:
        class Config:
            extra = "forbid"
            validate_assignment = True
    
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="查詢唯一識別碼"
    )
    
    type: QueryType = Field(
        description="查詢類型"
    )
    
    priority: QueryPriority = Field(
        default=QueryPriority.NORMAL,
        description="查詢優先級"
    )
    
    filter: Optional[QueryFilter] = Field(
        default=None,
        description="篩選條件"
    )
    
    options: Optional[QueryOptions] = Field(
        default=None,
        description="查詢選項"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="查詢時間戳"
    )


class QueryResult(BaseModel):
    """查詢結果"""
    if PYDANTIC_V2:
        model_config = ConfigDict(
            extra="allow",
            validate_assignment=True,
        )
    else:
        class Config:
            extra = "allow"
            validate_assignment = True
    
    query_id: str = Field(
        description="對應的查詢 ID"
    )
    
    total_count: int = Field(
        ge=0,
        description="符合條件的總數量"
    )
    
    returned_count: int = Field(
        ge=0,
        description="實際回傳數量"
    )
    
    data: list[Any] = Field(
        default_factory=list,
        description="查詢結果資料"
    )
    
    has_more: bool = Field(
        default=False,
        description="是否還有更多結果"
    )
    
    next_offset: Optional[int] = Field(
        default=None,
        description="下一頁偏移量"
    )
    
    execution_time_ms: float = Field(
        ge=0,
        description="執行時間（毫秒）"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="結果時間戳"
    )


class StreamQueryChunk(BaseModel):
    """串流查詢資料塊"""
    if PYDANTIC_V2:
        model_config = ConfigDict(
            extra="forbid",
            validate_assignment=True,
        )
    else:
        class Config:
            extra = "forbid"
            validate_assignment = True
    
    query_id: str = Field(
        description="對應的查詢 ID"
    )
    
    chunk_index: int = Field(
        ge=0,
        description="資料塊索引"
    )
    
    data: Any = Field(
        description="資料塊內容"
    )
    
    is_final: bool = Field(
        default=False,
        description="是否為最後一個資料塊"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="資料塊時間戳"
    )


class QueryStats(BaseModel):
    """查詢統計資訊"""
    if PYDANTIC_V2:
        model_config = ConfigDict(
            extra="forbid",
            validate_assignment=True,
        )
    else:
        class Config:
            extra = "forbid"
            validate_assignment = True
    
    total_queries: int = Field(
        ge=0,
        description="總查詢數"
    )
    
    successful_queries: int = Field(
        ge=0,
        description="成功查詢數"
    )
    
    failed_queries: int = Field(
        ge=0,
        description="失敗查詢數"
    )
    
    average_execution_time_ms: float = Field(
        ge=0,
        description="平均執行時間（毫秒）"
    )
    
    peak_execution_time_ms: float = Field(
        ge=0,
        description="峰值執行時間（毫秒）"
    )
    
    queries_per_second: float = Field(
        ge=0,
        description="每秒查詢數"
    )
    
    period_start: datetime = Field(
        description="統計期間開始時間"
    )
    
    period_end: datetime = Field(
        description="統計期間結束時間"
    ) 