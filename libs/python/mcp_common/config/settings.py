"""
MCP 客戶端設定管理

提供設定載入、驗證和預設值管理功能。
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError, validator


class ServerConfig(BaseModel):
    """單一 MCP 伺服器配置"""
    
    name: str = Field(..., description="伺服器名稱")
    adapter_type: str = Field("http", description="適配器類型")
    url: Optional[str] = Field(None, description="伺服器 URL")
    timeout: float = Field(30.0, description="請求超時時間")
    retry_attempts: int = Field(3, description="重試次數")
    retry_delay: float = Field(1.0, description="重試延遲")
    enabled: bool = Field(True, description="是否啟用")
    
    # 協定特定設定
    protocol_config: Dict[str, Any] = Field(default_factory=dict, description="協定特定設定")
    
    @validator('adapter_type')
    def validate_adapter_type(cls, v):
        allowed_types = ['http', 'websocket', 'stdio', 'simple', 'legacy', 'mock']
        if v not in allowed_types:
            raise ValueError(f'adapter_type 必須是 {allowed_types} 中的一個')
        return v


class ConnectionConfig(BaseModel):
    """連接配置"""
    
    pool_min_size: int = Field(2, description="連接池最小大小")
    pool_max_size: int = Field(20, description="連接池最大大小")
    pool_timeout: float = Field(30.0, description="連接池超時")
    idle_timeout: float = Field(300.0, description="空閒連接超時")
    
    # 斷路器設定
    circuit_failure_threshold: int = Field(5, description="斷路器失敗閾值")
    circuit_recovery_timeout: float = Field(60.0, description="斷路器恢復超時")
    circuit_half_open_max_calls: int = Field(3, description="半開狀態最大呼叫數")


class ObservabilityConfig(BaseModel):
    """可觀測性配置"""
    
    metrics_enabled: bool = Field(True, description="啟用指標收集")
    tracing_enabled: bool = Field(True, description="啟用分散式追蹤")
    logging_level: str = Field("INFO", description="日誌等級")
    
    # Prometheus 設定
    prometheus_host: str = Field("localhost", description="Prometheus 主機")
    prometheus_port: int = Field(8000, description="Prometheus 埠號")
    
    # OpenTelemetry 設定
    otlp_endpoint: Optional[str] = Field(None, description="OTLP 端點")
    service_name: str = Field("mcp-client", description="服務名稱")


class MCPClientConfig(BaseModel):
    """MCP 客戶端完整配置"""
    
    # 基本設定
    environment: str = Field("development", description="執行環境")
    debug: bool = Field(False, description="除錯模式")
    
    # 伺服器設定
    servers: Dict[str, ServerConfig] = Field(default_factory=dict, description="MCP 伺服器配置")
    
    # 連接設定
    connection: ConnectionConfig = Field(default_factory=ConnectionConfig, description="連接配置")
    
    # 可觀測性設定
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig, description="可觀測性配置")
    
    # 進階設定
    default_timeout: float = Field(30.0, description="預設超時時間")
    max_concurrent_calls: int = Field(100, description="最大同時呼叫數")
    
    @validator('environment')
    def validate_environment(cls, v):
        allowed_envs = ['development', 'testing', 'staging', 'production']
        if v not in allowed_envs:
            raise ValueError(f'environment 必須是 {allowed_envs} 中的一個')
        return v
    
    class Config:
        extra = "allow"  # 允許額外欄位


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路徑
        """
        self.config_path = config_path or self._find_config_file()
        self._config: Optional[MCPClientConfig] = None
    
    def _find_config_file(self) -> str:
        """尋找配置文件"""
        possible_paths = [
            "mcp_client.yaml",
            "config/mcp_client.yaml", 
            os.path.expanduser("~/.mcp/config.yaml"),
            "/etc/mcp/config.yaml",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # 返回預設路徑
        return "config/mcp_client.yaml"
    
    def load_config(self) -> MCPClientConfig:
        """載入配置"""
        if self._config is not None:
            return self._config
        
        try:
            from .config_loader import ConfigLoader
            loader = ConfigLoader()
            config_data = loader.load_config(self.config_path)
            
            self._config = MCPClientConfig(**config_data)
            return self._config
            
        except FileNotFoundError:
            # 使用預設配置
            self._config = self._create_default_config()
            return self._config
        except ValidationError as e:
            raise ValueError(f"配置驗證失敗: {e}")
    
    def _create_default_config(self) -> MCPClientConfig:
        """創建預設配置"""
        return MCPClientConfig(
            environment="development",
            debug=True,
            servers={
                "sqlite": ServerConfig(
                    name="sqlite",
                    adapter_type="simple",
                    enabled=True,
                    protocol_config={
                        "database_path": "test.db"
                    }
                )
            }
        )
    
    def get_server_config(self, server_name: str) -> Optional[ServerConfig]:
        """獲取特定伺服器配置"""
        config = self.load_config()
        return config.servers.get(server_name)
    
    def reload_config(self) -> MCPClientConfig:
        """重新載入配置"""
        self._config = None
        return self.load_config()


# 全域配置管理器實例
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """獲取配置管理器實例"""
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    
    return _config_manager


def get_config() -> MCPClientConfig:
    """獲取當前配置"""
    manager = get_config_manager()
    return manager.load_config()


def get_server_config(server_name: str) -> Optional[ServerConfig]:
    """獲取特定伺服器配置"""
    manager = get_config_manager()
    return manager.get_server_config(server_name) 