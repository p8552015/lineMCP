"""
測試服務配置系統
"""
import pytest
import yaml
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import Mock, patch

from src.infrastructure.service_configuration import (
    ServiceConfig,
    ServicesConfiguration,
    ServiceConfigurator,
    ServiceConfigBuilder,
    create_default_configuration
)
from src.infrastructure.service_registry import ServiceRegistry, ServiceScope


class TestServiceConfig:
    """服務配置測試"""
    
    def test_service_config_creation(self):
        """測試服務配置創建"""
        config = ServiceConfig(
            service_type="test.Service",
            implementation="test.ServiceImpl",
            scope="singleton",
            tags=["test", "example"],
            metadata={"version": "1.0"}
        )
        
        assert config.service_type == "test.Service"
        assert config.implementation == "test.ServiceImpl"
        assert config.scope == "singleton"
        assert config.tags == ["test", "example"]
        assert config.metadata == {"version": "1.0"}
    
    def test_service_config_defaults(self):
        """測試服務配置預設值"""
        config = ServiceConfig(
            service_type="test.Service",
            implementation="test.ServiceImpl"
        )
        
        assert config.scope == "singleton"
        assert config.tags == []
        assert config.metadata == {}
        assert config.dependencies == {}
        assert config.factory is None


class TestServicesConfiguration:
    """服務配置集合測試"""
    
    def test_services_configuration_creation(self):
        """測試服務配置集合創建"""
        service1 = ServiceConfig("Service1", "ServiceImpl1")
        service2 = ServiceConfig("Service2", "ServiceImpl2")
        
        config = ServicesConfiguration(
            services=[service1, service2],
            imports=["module1", "module2"],
            settings={"key": "value"}
        )
        
        assert len(config.services) == 2
        assert config.imports == ["module1", "module2"]
        assert config.settings == {"key": "value"}
    
    def test_services_configuration_defaults(self):
        """測試服務配置集合預設值"""
        config = ServicesConfiguration(services=[])
        
        assert config.services == []
        assert config.imports == []
        assert config.settings == {}


class TestServiceConfigurator:
    """服務配置器測試"""
    
    @pytest.fixture
    def registry(self):
        """創建註冊表"""
        return ServiceRegistry()
    
    @pytest.fixture
    def configurator(self, registry):
        """創建配置器"""
        return ServiceConfigurator(registry)
    
    def test_configure_from_dict(self, configurator, registry):
        """測試從字典配置"""
        config_data = {
            "services": [
                {
                    "service_type": "builtins.str",
                    "implementation": "builtins.str",
                    "scope": "singleton",
                    "tags": ["test"]
                }
            ]
        }
        
        configurator.configure_from_dict(config_data)
        
        # 驗證服務已註冊
        assert registry.has_service(str)
        descriptor = registry.get_descriptor(str)
        assert descriptor.tags == ["test"]
    
    def test_configure_from_yaml_file(self, configurator, registry):
        """測試從 YAML 文件配置"""
        yaml_content = """
services:
  - service_type: builtins.list
    implementation: builtins.list
    scope: transient
    tags:
      - collection
    metadata:
      description: List service
"""
        
        with NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            try:
                configurator.configure_from_file(f.name)
                
                # 驗證服務已註冊
                assert registry.has_service(list)
                descriptor = registry.get_descriptor(list)
                assert descriptor.scope == ServiceScope.TRANSIENT
                assert "collection" in descriptor.tags
                assert descriptor.metadata["description"] == "List service"
            finally:
                Path(f.name).unlink()
    
    def test_configure_from_json_file(self, configurator, registry):
        """測試從 JSON 文件配置"""
        json_content = {
            "services": [
                {
                    "service_type": "builtins.dict",
                    "implementation": "builtins.dict",
                    "scope": "scoped"
                }
            ]
        }
        
        with NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(json_content, f)
            f.flush()
            
            try:
                configurator.configure_from_file(f.name)
                
                # 驗證服務已註冊
                assert registry.has_service(dict)
                descriptor = registry.get_descriptor(dict)
                assert descriptor.scope == ServiceScope.SCOPED
            finally:
                Path(f.name).unlink()
    
    def test_configure_with_factory(self, configurator, registry):
        """測試配置工廠函數"""
        def my_factory(provider):
            return "factory_result"
        
        # 模擬解析工廠函數
        with patch.object(configurator, '_resolve_callable', return_value=my_factory):
            config_data = {
                "services": [
                    {
                        "service_type": "builtins.str",
                        "implementation": "builtins.str",
                        "factory": "test.my_factory",
                        "scope": "transient"
                    }
                ]
            }
            
            configurator.configure_from_dict(config_data)
            
            # 驗證工廠已註冊
            assert str in registry._factories
    
    def test_configure_with_imports(self, configurator):
        """測試配置模組導入"""
        config_data = {
            "imports": ["json", "yaml"],  # 使用內建模組
            "services": []
        }
        
        configurator.configure_from_dict(config_data)
        
        # 驗證模組可以被導入（不會拋出異常）
        import json
        import yaml
    
    def test_configure_error_handling(self, configurator):
        """測試配置錯誤處理"""
        config_data = {
            "services": [
                {
                    "service_type": "nonexistent.Module",
                    "implementation": "nonexistent.Implementation"
                }
            ]
        }
        
        # 應該記錄錯誤但不拋出異常
        configurator.configure_from_dict(config_data)
    
    def test_resolve_type(self, configurator):
        """測試類型解析"""
        # 測試內建類型
        str_type = configurator._resolve_type("builtins.str")
        assert str_type is str
        
        # 測試緩存
        str_type2 = configurator._resolve_type("builtins.str")
        assert str_type2 is str_type
    
    def test_resolve_type_error(self, configurator):
        """測試類型解析錯誤"""
        with pytest.raises(ValueError, match="無法解析類型"):
            configurator._resolve_type("nonexistent.Type")


class TestServiceConfigBuilder:
    """服務配置建構器測試"""
    
    def test_builder_add_service(self):
        """測試建構器添加服務"""
        builder = ServiceConfigBuilder()
        
        builder.add_service(
            "test.Service",
            "test.ServiceImpl",
            tags=["test"]
        )
        
        config = builder.build()
        assert len(config.services) == 1
        assert config.services[0].service_type == "test.Service"
        assert config.services[0].tags == ["test"]
    
    def test_builder_add_singleton(self):
        """測試建構器添加單例"""
        builder = ServiceConfigBuilder()
        builder.add_singleton("test.Service")
        
        config = builder.build()
        assert config.services[0].scope == "singleton"
    
    def test_builder_add_transient(self):
        """測試建構器添加瞬態"""
        builder = ServiceConfigBuilder()
        builder.add_transient("test.Service")
        
        config = builder.build()
        assert config.services[0].scope == "transient"
    
    def test_builder_add_scoped(self):
        """測試建構器添加作用域"""
        builder = ServiceConfigBuilder()
        builder.add_scoped("test.Service")
        
        config = builder.build()
        assert config.services[0].scope == "scoped"
    
    def test_builder_add_import(self):
        """測試建構器添加導入"""
        builder = ServiceConfigBuilder()
        builder.add_import("test.module")
        
        config = builder.build()
        assert "test.module" in config.imports
    
    def test_builder_with_setting(self):
        """測試建構器添加設定"""
        builder = ServiceConfigBuilder()
        builder.with_setting("key", "value")
        
        config = builder.build()
        assert config.settings["key"] == "value"
    
    def test_builder_chain_calls(self):
        """測試建構器鏈式調用"""
        builder = ServiceConfigBuilder()
        
        result = (builder
                 .add_singleton("Service1")
                 .add_transient("Service2")
                 .add_import("module1")
                 .with_setting("debug", True))
        
        assert result is builder  # 返回自身
        
        config = builder.build()
        assert len(config.services) == 2
        assert len(config.imports) == 1
        assert config.settings["debug"] is True
    
    def test_builder_to_dict(self):
        """測試建構器轉換為字典"""
        builder = ServiceConfigBuilder()
        builder.add_singleton("test.Service", tags=["test"])
        
        data = builder.to_dict()
        
        assert "services" in data
        assert len(data["services"]) == 1
        assert data["services"][0]["service_type"] == "test.Service"
        assert data["services"][0]["tags"] == ["test"]
    
    def test_builder_to_yaml(self):
        """測試建構器轉換為 YAML"""
        builder = ServiceConfigBuilder()
        builder.add_singleton("test.Service")
        
        yaml_str = builder.to_yaml()
        
        # 解析 YAML 驗證
        data = yaml.safe_load(yaml_str)
        assert data["services"][0]["service_type"] == "test.Service"
    
    def test_builder_to_json(self):
        """測試建構器轉換為 JSON"""
        builder = ServiceConfigBuilder()
        builder.add_singleton("test.Service")
        
        json_str = builder.to_json()
        
        # 解析 JSON 驗證
        data = json.loads(json_str)
        assert data["services"][0]["service_type"] == "test.Service"


class TestDefaultConfiguration:
    """預設配置測試"""
    
    def test_create_default_configuration(self):
        """測試創建預設配置"""
        config = create_default_configuration()
        
        assert isinstance(config, ServicesConfiguration)
        assert len(config.services) > 0
        assert len(config.imports) > 0
        
        # 檢查是否包含核心服務
        service_types = [s.service_type for s in config.services]
        assert "src.services.ai_model_service.AIModelService" in service_types
        assert "src.services.message_formatter.MessageFormatter" in service_types
        
        # 檢查標籤
        ai_services = [s for s in config.services if "ai" in s.tags]
        assert len(ai_services) > 0


class TestIntegration:
    """集成測試"""
    
    def test_full_configuration_flow(self):
        """測試完整的配置流程"""
        # 創建配置
        builder = ServiceConfigBuilder()
        builder.add_singleton(
            "builtins.str",
            tags=["test", "integration"]
        ).add_transient(
            "builtins.list",
            metadata={"test": True}
        ).add_import("json")
        
        # 轉換為 YAML
        yaml_str = builder.to_yaml()
        
        # 創建新的配置器和註冊表
        registry = ServiceRegistry()
        configurator = ServiceConfigurator(registry)
        
        # 從 YAML 配置
        with NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_str)
            f.flush()
            
            try:
                configurator.configure_from_file(f.name)
                
                # 驗證配置已應用
                assert registry.has_service(str)
                assert registry.has_service(list)
                
                str_desc = registry.get_descriptor(str)
                assert str_desc.scope == ServiceScope.SINGLETON
                assert "test" in str_desc.tags
                
                list_desc = registry.get_descriptor(list)
                assert list_desc.scope == ServiceScope.TRANSIENT
                assert list_desc.metadata["test"] is True
                
            finally:
                Path(f.name).unlink()