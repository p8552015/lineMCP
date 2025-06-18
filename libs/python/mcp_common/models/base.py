"""
MCP 基礎資料模型

定義 MCP 通訊的核心資料結構。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field

try:
    from pydantic import ConfigDict, validator
    PYDANTIC_V2 = True
except ImportError:
    # Pydantic v1 相容性
    from pydantic import validator
    PYDANTIC_V2 = False
    
    class ConfigDict:
        def __init__(self, **kwargs):
            pass


class MCPStatusCode(str, Enum):
    """MCP 狀態碼枚舉"""
    SUCCESS = "success"
    ERROR = "error" 
    TIMEOUT = "timeout"
    PARTIAL = "partial"


class HealthStatusLevel(str, Enum):
    """健康狀態等級"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CallOptions(BaseModel):
    """呼叫選項配置"""
    if PYDANTIC_V2:
        model_config = ConfigDict(
            extra="forbid",
            validate_assignment=True,
            str_strip_whitespace=True,
        )
    else:
        class Config:
            extra = "forbid"
            validate_assignment = True
    
    timeout: float = Field(
        default=30.0,
        ge=0.1,
        le=300.0,
        description="請求超時時間（秒）"
    )
    
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="最大重試次數"
    )
    
    retry_delay: float = Field(
        default=1.0,
        ge=0.1,
        le=60.0,
        description="重試延遲時間（秒）"
    )
    
    enable_circuit_breaker: bool = Field(
        default=True,
        description="是否啟用熔斷器"
    )
    
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="自訂 HTTP 標頭"
    )
    
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="附加中繼資料"
    )


class MCPCall(BaseModel):
    """MCP 呼叫請求"""
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )
    
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="呼叫唯一識別碼"
    )
    
    server: str = Field(
        min_length=1,
        max_length=255,
        description="目標伺服器名稱或 URL"
    )
    
    tool: str = Field(
        min_length=1,
        max_length=255,
        description="工具名稱"
    )
    
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="工具參數"
    )
    
    options: Optional[CallOptions] = Field(
        default=None,
        description="呼叫選項"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="呼叫時間戳"
    )


class MCPResponse(BaseModel):
    """MCP 回應結果"""
    model_config = ConfigDict(
        extra="allow",  # 允許額外欄位以支援不同伺服器的客製化回應
        validate_assignment=True,
    )
    
    call_id: str = Field(
        description="對應的呼叫 ID"
    )
    
    status: MCPStatusCode = Field(
        description="回應狀態"
    )
    
    data: Optional[Any] = Field(
        default=None,
        description="回應資料"
    )
    
    error: Optional[str] = Field(
        default=None,
        description="錯誤訊息"
    )
    
    error_code: Optional[str] = Field(
        default=None,
        description="錯誤代碼"
    )
    
    duration_ms: Optional[float] = Field(
        default=None,
        ge=0,
        description="執行時間（毫秒）"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="回應時間戳"
    )
    
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="回應中繼資料"
    )
    
    @validator('error')
    def validate_error(cls, v, values):
        """驗證錯誤狀態與錯誤訊息的一致性"""
        status = values.get('status')
        if status == MCPStatusCode.ERROR and not v:
            raise ValueError("錯誤狀態必須包含錯誤訊息")
        if status != MCPStatusCode.ERROR and v:
            raise ValueError("非錯誤狀態不應包含錯誤訊息")
        return v


class ServerInfo(BaseModel):
    """伺服器資訊"""
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )
    
    name: str = Field(
        min_length=1,
        max_length=255,
        description="伺服器名稱"
    )
    
    url: str = Field(
        min_length=1,
        max_length=2048,
        description="伺服器 URL"
    )
    
    protocol: str = Field(
        default="http",
        pattern=r"^(http|https|ws|wss|stdio)$",
        description="通訊協議"
    )
    
    version: Optional[str] = Field(
        default=None,
        description="伺服器版本"
    )
    
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="伺服器描述"
    )


class HealthStatus(BaseModel):
    """健康狀態資訊"""
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )
    
    overall: HealthStatusLevel = Field(
        description="整體健康狀態"
    )
    
    servers: dict[str, HealthStatusLevel] = Field(
        default_factory=dict,
        description="各伺服器健康狀態"
    )
    
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="詳細狀態資訊"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="檢查時間戳"
    )
    
    response_time_ms: Optional[float] = Field(
        default=None,
        ge=0,
        description="回應時間（毫秒）"
    )


class ToolInfo(BaseModel):
    """工具資訊"""
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )
    
    name: str = Field(
        min_length=1,
        max_length=255,
        description="工具名稱"
    )
    
    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="工具描述"
    )
    
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="工具參數規格"
    )
    
    examples: list[dict[str, Any]] = Field(
        default_factory=list,
        description="使用範例"
    )
    
    tags: list[str] = Field(
        default_factory=list,
        description="工具標籤"
    )


class BatchResult(BaseModel):
    """批次執行結果"""
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )
    
    total: int = Field(
        ge=0,
        description="總請求數"
    )
    
    succeeded: int = Field(
        ge=0,
        description="成功請求數"
    )
    
    failed: int = Field(
        ge=0,
        description="失敗請求數"
    )
    
    responses: list[MCPResponse] = Field(
        description="所有回應結果"
    )
    
    duration_ms: float = Field(
        ge=0,
        description="總執行時間（毫秒）"
    )
    
    @validator('failed')
    def validate_counts(cls, v, values):
        """驗證計數一致性"""
        total = values.get('total', 0)
        succeeded = values.get('succeeded', 0)
        if total != succeeded + v:
            raise ValueError("總數必須等於成功數加失敗數")
        return v