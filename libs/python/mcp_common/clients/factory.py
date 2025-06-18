"""
MCP 客戶端工廠

提供統一的客戶端建立介面。
"""

import os
from typing import Any, Dict, Optional
import logging

try:
    import yaml
except ImportError:
    yaml = None

from ..models.error import ConfigurationError
from .interface import MCPClientInterface
from .http_client import MCPHttpClient
from .mock_client import MockMCPClient

logger = logging.getLogger(__name__)


class MCPClientFactory:
    """MCP 客戶端工廠類別"""
    
    def __init__(self):
        self._config_cache: Optional[Dict[str, Any]] = None
        self._client_cache: Dict[str, MCPClientInterface] = {}

    def _load_config(self) -> Dict[str, Any]:
        """載入配置文件"""
        if self._config_cache is not None:
            return self._config_cache
        
        config = {}
        
        # 1. 從環境變數載入
        env_config = self._load_from_env()
        if env_config:
            config.update(env_config)
        
        # 2. 從 YAML 檔案載入
        yaml_config = self._load_from_yaml()
        if yaml_config:
            config.update(yaml_config)
        
        # 3. 設定預設值
        config = self._apply_defaults(config)
        
        self._config_cache = config
        logger.info(f"載入 MCP 客戶端配置: {len(config.get('servers', {}))} 個伺服器")
        
        return config

    def _load_from_env(self) -> Dict[str, Any]:
        """從環境變數載入配置"""
        config = {}
        
        # 基本配置
        if os.getenv("MCP_CLIENT_TYPE"):
            config["client_type"] = os.getenv("MCP_CLIENT_TYPE")
        
        if os.getenv("MCP_DEFAULT_TIMEOUT"):
            try:
                config["default_timeout"] = float(os.getenv("MCP_DEFAULT_TIMEOUT"))
            except ValueError:
                logger.warning("無效的 MCP_DEFAULT_TIMEOUT 值")
        
        # 伺服器配置
        servers = {}
        for key, value in os.environ.items():
            if key.startswith("MCP_SERVER_"):
                server_name = key[11:].lower()  # 移除 "MCP_SERVER_" 前綴
                servers[server_name] = value
        
        if servers:
            config["servers"] = servers
        
        return config

    def _load_from_yaml(self) -> Dict[str, Any]:
        """從 YAML 檔案載入配置"""
        if yaml is None:
            logger.warning("YAML 模組未安裝，跳過配置檔案載入")
            return {}
        
        # 嘗試多個可能的配置檔案位置
        config_paths = [
            "mcp_client.yaml",
            "config/mcp_client.yaml",
            os.path.expanduser("~/.mcp/client.yaml"),
            "/etc/mcp/client.yaml",
        ]
        
        for config_path in config_paths:
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                    
                    logger.info(f"從 {config_path} 載入配置")
                    return config.get("mcp_client", config)
                    
                except Exception as e:
                    logger.warning(f"載入配置檔案 {config_path} 失敗: {e}")
        
        return {}

    def _apply_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """應用預設配置"""
        defaults = {
            "client_type": "http",
            "servers": {},
            "default_options": {
                "timeout": 30.0,
                "max_retries": 3,
                "retry_delay": 1.0,
                "enable_circuit_breaker": True,
            },
            "http_client": {
                "max_keepalive": 20,
                "max_connections": 100,
                "keepalive_expiry": 5,
                "connect_timeout": 10.0,
                "read_timeout": 30.0,
                "write_timeout": 10.0,
                "pool_timeout": 5.0,
            },
            "circuit_breaker": {
                "failure_threshold": 5,
                "success_threshold": 3,
                "timeout": 60,
            },
            "connection_pool": {
                "min_size": 2,
                "max_size": 20,
                "timeout": 30.0,
                "idle_timeout": 300.0,
            },
        }
        
        # 深度合併配置
        def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
            result = base.copy()
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        return deep_merge(defaults, config)

    def create_client(
        self,
        client_type: Optional[str] = None,
        servers: Optional[Dict[str, str]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> MCPClientInterface:
        """
        建立 MCP 客戶端
        
        Args:
            client_type: 客戶端類型 ("http", "mock")
            servers: 伺服器配置
            config: 客戶端配置
            
        Returns:
            MCP 客戶端實例
            
        Raises:
            ConfigurationError: 配置錯誤
        """
        # 載入基礎配置
        base_config = self._load_config()
        
        # 合併配置
        if config:
            base_config.update(config)
        
        if servers:
            base_config["servers"] = {**base_config.get("servers", {}), **servers}
        
        if client_type:
            base_config["client_type"] = client_type
        
        # 驗證配置
        self._validate_config(base_config)
        
        # 建立客戶端
        client_type = base_config["client_type"]
        
        if client_type == "http":
            return MCPHttpClient(
                servers=base_config["servers"],
                config=base_config,
            )
        elif client_type == "mock":
            return MockMCPClient(
                config=base_config,
            )
        elif client_type == "legacy":
            from ..adapters.legacy_adapter import LegacyMCPAdapter
            return LegacyMCPAdapter(config=base_config)
        elif client_type == "simple":
            from ..adapters.simple_adapter import SimpleMCPAdapter
            return SimpleMCPAdapter(config=base_config)
        else:
            raise ConfigurationError(
                f"不支援的客戶端類型: {client_type}",
                config_key="client_type",
            )

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """驗證配置"""
        if "client_type" not in config:
            raise ConfigurationError("缺少 client_type 配置", config_key="client_type")
        
        valid_types = {"http", "mock", "legacy", "simple"}
        if config["client_type"] not in valid_types:
            raise ConfigurationError(
                f"client_type 必須是 {valid_types} 之一",
                config_key="client_type",
            )
        
        # 驗證伺服器配置
        servers = config.get("servers", {})
        if not isinstance(servers, dict):
            raise ConfigurationError("servers 必須是字典格式", config_key="servers")
        
        for name, url in servers.items():
            if not isinstance(name, str) or not isinstance(url, str):
                raise ConfigurationError(
                    f"伺服器 {name} 的配置格式錯誤",
                    config_key=f"servers.{name}",
                )

    def get_cached_client(self, cache_key: str = "default") -> Optional[MCPClientInterface]:
        """獲取快取的客戶端"""
        return self._client_cache.get(cache_key)

    def cache_client(self, client: MCPClientInterface, cache_key: str = "default") -> None:
        """快取客戶端"""
        self._client_cache[cache_key] = client

    def clear_cache(self) -> None:
        """清除快取"""
        self._client_cache.clear()
        self._config_cache = None


# 全域工廠實例
_factory = MCPClientFactory()


def get_mcp_client(
    server_name: Optional[str] = None,
    client_type: Optional[str] = None,
    servers: Optional[Dict[str, str]] = None,
    config: Optional[Dict[str, Any]] = None,
    use_cache: bool = True,
) -> MCPClientInterface:
    """
    獲取 MCP 客戶端實例（主要入口點）
    
    Args:
        server_name: 特定伺服器名稱（用於快取鍵）
        client_type: 客戶端類型
        servers: 伺服器配置
        config: 客戶端配置
        use_cache: 是否使用快取
        
    Returns:
        MCP 客戶端實例
        
    Example:
        >>> # 使用預設配置
        >>> client = get_mcp_client()
        
        >>> # 指定伺服器
        >>> client = get_mcp_client(
        ...     servers={"sqlite": "http://localhost:3003"}
        ... )
        
        >>> # 使用模擬客戶端
        >>> client = get_mcp_client(client_type="mock")
    """
    cache_key = f"{client_type or 'default'}_{server_name or 'default'}"
    
    # 檢查快取
    if use_cache:
        cached_client = _factory.get_cached_client(cache_key)
        if cached_client:
            return cached_client
    
    # 建立新客戶端
    client = _factory.create_client(
        client_type=client_type,
        servers=servers,
        config=config,
    )
    
    # 快取客戶端
    if use_cache:
        _factory.cache_client(client, cache_key)
    
    return client


def clear_client_cache() -> None:
    """清除客戶端快取"""
    _factory.clear_cache()


def configure_mcp_client(config: Dict[str, Any]) -> None:
    """
    配置 MCP 客戶端全域設定
    
    Args:
        config: 配置字典
    """
    _factory._config_cache = config
    _factory.clear_cache()  # 清除快取以強制重新載入