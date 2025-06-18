"""
配置載入器
"""

import os
from typing import Dict, Any, Optional

# 配置快取
_config_cache: Optional[Dict[str, Any]] = None

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    載入配置
    
    Args:
        config_path: 配置檔案路徑（可選）
        
    Returns:
        配置字典
    """
    global _config_cache
    
    if _config_cache is not None:
        return _config_cache
    
    # 預設配置
    default_config = {
        "client_types": {
            "simple": {
                "adapter": "simple_adapter",
                "description": "Simple MCP 客戶端適配器",
                "protocols": ["sqlite"]
            },
            "mock": {
                "adapter": "mock_adapter", 
                "description": "Mock 客戶端（用於測試）",
                "protocols": ["any"]
            }
        },
        "default_client": "simple",
        "connections": {
            "sqlite": {
                "protocol": "stdio",
                "timeout": 30,
                "retry_attempts": 3,
                "retry_delay": 1
            }
        },
        "error_handling": {
            "max_retries": 3,
            "timeout_seconds": 30,
            "fallback_enabled": True
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s [%(levelname)s] %(message)s"
        },
        "performance": {
            "connection_pool_size": 5,
            "connection_timeout": 10,
            "request_timeout": 30
        },
        "security": {
            "validate_responses": True,
            "sanitize_errors": True
        }
    }
    
    try:
        # 嘗試載入 YAML 配置
        import yaml
        
        # 如果沒有提供路徑，使用預設路徑
        if config_path is None:
            config_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(config_dir, "default_config.yaml")
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                yaml_config = yaml.safe_load(f)
                
            # 合併配置
            _config_cache = _merge_configs(default_config, yaml_config)
        else:
            _config_cache = default_config
            
    except ImportError:
        # YAML 模組未安裝，使用預設配置
        _config_cache = default_config
    except Exception:
        # 載入失敗，使用預設配置
        _config_cache = default_config
    
    return _config_cache

def get_client_config(client_type: str = "simple") -> Dict[str, Any]:
    """
    獲取特定客戶端類型的配置
    
    Args:
        client_type: 客戶端類型
        
    Returns:
        客戶端配置
    """
    config = load_config()
    
    # 獲取客戶端配置
    client_config = config.get("client_types", {}).get(client_type, {})
    
    # 添加通用配置
    client_config["connections"] = config.get("connections", {})
    client_config["error_handling"] = config.get("error_handling", {})
    client_config["performance"] = config.get("performance", {})
    client_config["security"] = config.get("security", {})
    
    return client_config

def _merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    合併配置字典
    
    Args:
        base: 基礎配置
        override: 覆蓋配置
        
    Returns:
        合併後的配置
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_configs(result[key], value)
        else:
            result[key] = value
    
    return result