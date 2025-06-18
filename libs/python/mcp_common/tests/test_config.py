"""
測試配置管理
"""

import pytest
import os
import tempfile
import yaml
from unittest.mock import patch, mock_open

from mcp_common.config.settings import (
    ServerConfig,
    ConnectionConfig,
    ObservabilityConfig,
    MCPClientConfig,
    ConfigManager,
    get_config_manager,
    get_config
)
from mcp_common.config.config_loader import load_config, get_client_config


class TestServerConfig:
    """測試伺服器配置"""
    
    def test_create_basic_server_config(self):
        """測試建立基本伺服器配置"""
        config = ServerConfig(
            name="test_server",
            adapter_type="http",
            url="http://localhost:8080"
        )
        
        assert config.name == "test_server"
        assert config.adapter_type == "http"
        assert config.url == "http://localhost:8080"
        assert config.timeout == 30.0  # 預設值
        assert config.retry_attempts == 3  # 預設值
        assert config.enabled is True  # 預設值
    
    def test_validate_adapter_type(self):
        """測試適配器類型驗證"""
        # 有效類型
        for adapter_type in ['http', 'websocket', 'stdio', 'simple', 'legacy', 'mock']:
            config = ServerConfig(name="test", adapter_type=adapter_type)
            assert config.adapter_type == adapter_type
        
        # 無效類型
        with pytest.raises(ValueError):
            ServerConfig(name="test", adapter_type="invalid")
    
    def test_protocol_config(self):
        """測試協定特定配置"""
        config = ServerConfig(
            name="websocket_server",
            adapter_type="websocket",
            url="ws://localhost:8080",
            protocol_config={
                "ping_interval": 30,
                "max_message_size": 1048576
            }
        )
        
        assert config.protocol_config["ping_interval"] == 30
        assert config.protocol_config["max_message_size"] == 1048576


class TestConnectionConfig:
    """測試連接配置"""
    
    def test_default_values(self):
        """測試預設值"""
        config = ConnectionConfig()
        
        assert config.pool_min_size == 2
        assert config.pool_max_size == 20
        assert config.pool_timeout == 30.0
        assert config.idle_timeout == 300.0
        assert config.circuit_failure_threshold == 5
        assert config.circuit_recovery_timeout == 60.0
        assert config.circuit_half_open_max_calls == 3
    
    def test_custom_values(self):
        """測試自訂值"""
        config = ConnectionConfig(
            pool_min_size=5,
            pool_max_size=50,
            circuit_failure_threshold=10
        )
        
        assert config.pool_min_size == 5
        assert config.pool_max_size == 50
        assert config.circuit_failure_threshold == 10


class TestObservabilityConfig:
    """測試可觀測性配置"""
    
    def test_default_values(self):
        """測試預設值"""
        config = ObservabilityConfig()
        
        assert config.metrics_enabled is True
        assert config.tracing_enabled is True
        assert config.logging_level == "INFO"
        assert config.prometheus_host == "localhost"
        assert config.prometheus_port == 8000
        assert config.service_name == "mcp-client"
    
    def test_otlp_endpoint(self):
        """測試 OTLP 端點配置"""
        config = ObservabilityConfig(
            otlp_endpoint="http://localhost:4317",
            service_name="my-service"
        )
        
        assert config.otlp_endpoint == "http://localhost:4317"
        assert config.service_name == "my-service"


class TestMCPClientConfig:
    """測試完整客戶端配置"""
    
    def test_default_config(self):
        """測試預設配置"""
        config = MCPClientConfig()
        
        assert config.environment == "development"
        assert config.debug is False
        assert config.default_timeout == 30.0
        assert config.max_concurrent_calls == 100
        assert isinstance(config.connection, ConnectionConfig)
        assert isinstance(config.observability, ObservabilityConfig)
    
    def test_environment_validation(self):
        """測試環境驗證"""
        # 有效環境
        for env in ['development', 'testing', 'staging', 'production']:
            config = MCPClientConfig(environment=env)
            assert config.environment == env
        
        # 無效環境
        with pytest.raises(ValueError):
            MCPClientConfig(environment="invalid")
    
    def test_server_configuration(self):
        """測試伺服器配置"""
        server1 = ServerConfig(name="server1", adapter_type="http")
        server2 = ServerConfig(name="server2", adapter_type="websocket")
        
        config = MCPClientConfig(
            servers={
                "server1": server1,
                "server2": server2
            }
        )
        
        assert len(config.servers) == 2
        assert config.servers["server1"].adapter_type == "http"
        assert config.servers["server2"].adapter_type == "websocket"
    
    def test_extra_fields_allowed(self):
        """測試允許額外欄位"""
        config = MCPClientConfig(
            custom_field="custom_value",
            another_field=123
        )
        
        # 不應該引發錯誤
        assert hasattr(config, 'custom_field')
        assert config.custom_field == "custom_value"


class TestConfigManager:
    """測試配置管理器"""
    
    @pytest.fixture
    def temp_config_file(self):
        """建立臨時配置檔案"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_data = {
                'environment': 'testing',
                'debug': True,
                'servers': {
                    'test_server': {
                        'name': 'test_server',
                        'adapter_type': 'mock',
                        'enabled': True
                    }
                }
            }
            yaml.dump(config_data, f)
            f.flush()
            yield f.name
        os.unlink(f.name)
    
    def test_load_config_from_file(self, temp_config_file):
        """測試從檔案載入配置"""
        manager = ConfigManager(config_path=temp_config_file)
        config = manager.load_config()
        
        assert config.environment == "testing"
        assert config.debug is True
        assert "test_server" in config.servers
    
    def test_load_default_config(self):
        """測試載入預設配置"""
        manager = ConfigManager(config_path="non_existent_file.yaml")
        config = manager.load_config()
        
        assert config.environment == "development"
        assert config.debug is True
        assert "sqlite" in config.servers
    
    def test_get_server_config(self, temp_config_file):
        """測試獲取特定伺服器配置"""
        manager = ConfigManager(config_path=temp_config_file)
        server_config = manager.get_server_config("test_server")
        
        assert server_config is not None
        assert server_config.name == "test_server"
        assert server_config.adapter_type == "mock"
    
    def test_reload_config(self, temp_config_file):
        """測試重新載入配置"""
        manager = ConfigManager(config_path=temp_config_file)
        
        # 第一次載入
        config1 = manager.load_config()
        assert config1.environment == "testing"
        
        # 修改檔案
        with open(temp_config_file, 'w') as f:
            yaml.dump({'environment': 'production'}, f)
        
        # 重新載入
        config2 = manager.reload_config()
        assert config2.environment == "production"
    
    def test_config_cache(self):
        """測試配置快取"""
        manager = ConfigManager()
        
        # 第一次載入
        config1 = manager.load_config()
        
        # 第二次載入應該返回快取
        config2 = manager.load_config()
        
        assert config1 is config2  # 同一個物件


class TestConfigLoader:
    """測試配置載入器"""
    
    def test_load_default_config(self):
        """測試載入預設配置"""
        config = load_config()
        
        assert "client_types" in config
        assert "simple" in config["client_types"]
        assert "mock" in config["client_types"]
        assert config["default_client"] == "simple"
    
    def test_get_client_config(self):
        """測試獲取客戶端配置"""
        # 測試 simple 客戶端
        simple_config = get_client_config("simple")
        assert simple_config["adapter"] == "simple_adapter"
        assert "connections" in simple_config
        assert "error_handling" in simple_config
        
        # 測試 mock 客戶端
        mock_config = get_client_config("mock")
        assert mock_config["adapter"] == "mock_adapter"
    
    @patch('builtins.open', mock_open(read_data="""
client_types:
  custom:
    adapter: custom_adapter
    description: Custom client
default_client: custom
    """))
    @patch('os.path.exists', return_value=True)
    def test_load_yaml_config(self, mock_exists):
        """測試載入 YAML 配置"""
        # 清除快取
        import mcp_common.config.config_loader
        mcp_common.config.config_loader._config_cache = None
        
        config = load_config()
        
        assert "custom" in config["client_types"]
        assert config["default_client"] == "custom"


class TestGlobalFunctions:
    """測試全域函數"""
    
    def test_get_config_manager(self):
        """測試獲取全域配置管理器"""
        manager1 = get_config_manager()
        manager2 = get_config_manager()
        
        assert manager1 is manager2  # 單例
    
    def test_get_config(self):
        """測試獲取當前配置"""
        config = get_config()
        
        assert isinstance(config, MCPClientConfig)
        assert config.environment in ["development", "testing", "staging", "production"]