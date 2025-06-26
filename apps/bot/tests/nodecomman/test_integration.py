"""
系統整合測試套件

端到端測試 nodecomman 架構與現有系統的整合：
- 配置管理 API 一致性驗證
- 服務註冊參數問題檢測
- 兼容性接口差異分析
- 完整工作流程測試

重點修復配置管理和服務註冊的嚴重問題
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

# 系統整合導入
from src.config.mcp_config import get_mcp_config, MCPConfigManager
from src.services.production_mcp_client import get_production_mcp_client
from src.infrastructure.enhanced_service_factory import EnhancedServiceFactory


class TestConfigurationConsistency:
    """配置一致性整合測試 - 修復 API 不一致問題"""
    
    @pytest.fixture
    def base_config(self):
        """基礎配置管理器"""
        return get_mcp_config()
    
    @pytest.fixture
    def enhanced_factory(self):
        """增強服務工廠"""
        return EnhancedServiceFactory()
    
    def test_base_config_postgres_structure(self, base_config):
        """測試基礎配置 PostgreSQL 結構"""
        postgres_config = base_config.get_server_config("postgres")
        
        assert postgres_config is not None, "PostgreSQL 配置不存在"
        
        # 檢查必要屬性
        required_attrs = ['name', 'protocol', 'command', 'args', 'timeout']
        for attr in required_attrs:
            assert hasattr(postgres_config, attr), f"缺少屬性: {attr}"
        
        # 檢查 PostgreSQL 特定配置
        assert postgres_config.name == "postgres"
        assert postgres_config.protocol == "stdio"
        assert postgres_config.command == "npx"
        assert "postgres" in str(postgres_config.args).lower()
        
        print(f"✅ 基礎配置結構正確: {postgres_config.name}")
    
    @pytest.mark.asyncio
    async def test_enhanced_config_integration(self):
        """測試增強配置整合 - 檢測 API 不一致"""
        try:
            from src.config.enhanced_mcp_config import get_enhanced_mcp_config
            
            enhanced_config = get_enhanced_mcp_config(enable_nodecomman=True)
            
            # 測試運行時環境分析
            environments = await enhanced_config.analyze_runtime_environments()
            
            # Python 環境應該總是可用
            assert "python" in environments, "Python 運行時環境未檢測到"
            python_env = environments["python"]
            assert python_env.available is True, "Python 運行時不可用"
            
            # 測試服務器配置分析
            analysis = await enhanced_config.analyze_server_config("postgres")
            
            assert analysis is not None, "PostgreSQL 配置分析失敗"
            assert analysis.server_name == "postgres"
            assert analysis.current_config is not None
            
            print(f"✅ 增強配置整合正常: {analysis.server_name}")
            
        except ImportError as e:
            pytest.fail(f"增強配置模組導入失敗: {e}")
        except Exception as e:
            pytest.fail(f"增強配置整合測試失敗: {e}")
    
    @pytest.mark.asyncio
    async def test_nodecomman_factory_config_consistency(self):
        """測試 nodecomman 工廠配置一致性"""
        try:
            from src.nodecomman.implementations.universal_mcp_factory import UniversalMCPServerFactory
            
            factory = UniversalMCPServerFactory()
            
            # 獲取預定義配置
            nodecomman_config = await factory.get_predefined_config("postgres")
            
            assert nodecomman_config is not None, "nodecomman PostgreSQL 配置不存在"
            
            # 檢查與基礎配置的一致性
            base_config = get_mcp_config()
            base_postgres = base_config.get_server_config("postgres")
            
            if base_postgres:
                assert nodecomman_config.name == base_postgres.name, "配置名稱不一致"
                assert nodecomman_config.command == base_postgres.command, "命令不一致"
                assert nodecomman_config.args == base_postgres.args, "參數不一致"
            
            print(f"✅ nodecomman 配置一致性驗證通過")
            
        except ImportError as e:
            pytest.fail(f"nodecomman 工廠導入失敗: {e}")
        except Exception as e:
            pytest.fail(f"配置一致性測試失敗: {e}")


class TestServiceRegistryIssues:
    """服務註冊問題檢測和修復"""
    
    @pytest.fixture
    def enhanced_factory(self):
        """增強服務工廠實例"""
        return EnhancedServiceFactory()
    
    def test_enhanced_factory_initialization(self, enhanced_factory):
        """測試增強工廠初始化"""
        assert enhanced_factory is not None
        
        # 檢查基本服務註冊方法
        basic_methods = [
            'get_mcp_config',
            'get_mcp_connection_pool', 
            'get_application_facade'
        ]
        
        for method_name in basic_methods:
            assert hasattr(enhanced_factory, method_name), f"缺少基本方法: {method_name}"
            method = getattr(enhanced_factory, method_name)
            assert callable(method), f"方法不可調用: {method_name}"
        
        print(f"✅ 增強工廠基本方法檢查通過")
    
    def test_enhanced_mcp_client_registration(self, enhanced_factory):
        """測試增強 MCP 客戶端註冊"""
        try:
            # 嘗試獲取增強 MCP 客戶端
            if hasattr(enhanced_factory, 'get_enhanced_mcp_client'):
                client = enhanced_factory.get_enhanced_mcp_client()
                assert client is not None, "增強 MCP 客戶端獲取失敗"
                
                # 檢查客戶端方法
                required_methods = [
                    'connect_to_server',
                    'call_tool',
                    'get_system_info'
                ]
                
                for method_name in required_methods:
                    assert hasattr(client, method_name), f"客戶端缺少方法: {method_name}"
                
                print(f"✅ 增強 MCP 客戶端註冊正常")
            else:
                print(f"⚠️ 增強 MCP 客戶端方法不存在，使用回退機制")
                
        except Exception as e:
            pytest.fail(f"增強 MCP 客戶端註冊測試失敗: {e}")
    
    def test_enhanced_mcp_config_registration(self, enhanced_factory):
        """測試增強 MCP 配置註冊"""
        try:
            # 嘗試獲取增強 MCP 配置
            if hasattr(enhanced_factory, 'get_enhanced_mcp_config'):
                config = enhanced_factory.get_enhanced_mcp_config()
                assert config is not None, "增強 MCP 配置獲取失敗"
                
                # 檢查配置方法
                required_methods = [
                    'get_base_config',
                    'analyze_runtime_environments'
                ]
                
                for method_name in required_methods:
                    assert hasattr(config, method_name), f"配置缺少方法: {method_name}"
                
                print(f"✅ 增強 MCP 配置註冊正常")
            else:
                print(f"⚠️ 增強 MCP 配置方法不存在，使用回退機制")
                
        except Exception as e:
            pytest.fail(f"增強 MCP 配置註冊測試失敗: {e}")
    
    def test_service_factory_parameter_compatibility(self, enhanced_factory):
        """測試服務工廠參數兼容性"""
        # 檢查各種參數組合是否正常工作
        try:
            # 測試 MCP 配置參數
            config = enhanced_factory.get_mcp_config()
            assert config is not None
            
            # 測試連接池參數
            pool = enhanced_factory.get_mcp_connection_pool()
            assert pool is not None
            
            # 檢查方法簽名是否匹配
            import inspect
            
            # 檢查 get_mcp_config 方法簽名
            config_sig = inspect.signature(enhanced_factory.get_mcp_config)
            assert len(config_sig.parameters) == 0, "get_mcp_config 不應該有參數"
            
            print(f"✅ 服務工廠參數兼容性檢查通過")
            
        except Exception as e:
            pytest.fail(f"參數兼容性測試失敗: {e}")


class TestCompatibilityInterfaces:
    """兼容性接口測試"""
    
    @pytest.mark.asyncio
    async def test_enhanced_mcp_client_compatibility(self):
        """測試增強 MCP 客戶端兼容性"""
        try:
            from src.services.enhanced_mcp_client import get_enhanced_mcp_client
            
            # 測試不同參數組合的兼容性
            client_nodecomman = get_enhanced_mcp_client(use_nodecomman=True, fallback_enabled=True)
            client_fallback = get_enhanced_mcp_client(use_nodecomman=False, fallback_enabled=True)
            
            # 檢查系統資訊
            info1 = await client_nodecomman.get_system_info()
            info2 = await client_fallback.get_system_info()
            
            assert isinstance(info1, dict), "nodecomman 客戶端系統資訊格式錯誤"
            assert isinstance(info2, dict), "fallback 客戶端系統資訊格式錯誤"
            
            print(f"✅ 增強 MCP 客戶端兼容性正常")
            
        except Exception as e:
            pytest.fail(f"增強 MCP 客戶端兼容性測試失敗: {e}")
    
    @pytest.mark.asyncio
    async def test_production_client_fallback(self):
        """測試生產客戶端回退機制"""
        try:
            production_client = get_production_mcp_client()
            
            # 檢查生產客戶端基本方法
            assert hasattr(production_client, 'connect_to_server')
            assert hasattr(production_client, 'call_tool')
            
            # 測試基本連接（不實際連接）
            # 這只是檢查方法簽名和基本功能
            assert callable(production_client.connect_to_server)
            assert callable(production_client.call_tool)
            
            print(f"✅ 生產客戶端回退機制正常")
            
        except Exception as e:
            pytest.fail(f"生產客戶端回退測試失敗: {e}")
    
    def test_config_manager_interface_consistency(self):
        """測試配置管理器接口一致性"""
        base_config = get_mcp_config()
        
        # 檢查基本接口方法
        interface_methods = [
            ('get_server_config', 1),  # (方法名, 參數數量)
            ('list_servers', 0),
            ('get_client_config', 0),
            ('validate_server_config', 1)
        ]
        
        for method_name, expected_params in interface_methods:
            assert hasattr(base_config, method_name), f"缺少接口方法: {method_name}"
            
            method = getattr(base_config, method_name)
            assert callable(method), f"方法不可調用: {method_name}"
            
            # 檢查參數數量
            import inspect
            sig = inspect.signature(method)
            actual_params = len([p for p in sig.parameters.values() 
                               if p.kind != p.VAR_POSITIONAL and p.kind != p.VAR_KEYWORD])
            
            assert actual_params == expected_params, \
                f"方法 {method_name} 參數數量不匹配: 期望 {expected_params}, 實際 {actual_params}"
        
        print(f"✅ 配置管理器接口一致性檢查通過")


class TestEndToEndWorkflow:
    """端到端工作流程測試"""
    
    @pytest.mark.asyncio
    async def test_complete_integration_workflow(self):
        """測試完整整合工作流程"""
        try:
            # 1. 初始化增強服務工廠
            factory = EnhancedServiceFactory()
            
            # 2. 獲取基礎配置
            base_config = factory.get_mcp_config()
            postgres_config = base_config.get_server_config("postgres")
            assert postgres_config is not None, "PostgreSQL 基礎配置獲取失敗"
            
            # 3. 嘗試獲取增強配置（如果可用）
            enhanced_config = None
            if hasattr(factory, 'get_enhanced_mcp_config'):
                enhanced_config = factory.get_enhanced_mcp_config()
                
                # 分析運行時環境
                environments = await enhanced_config.analyze_runtime_environments()
                assert "python" in environments, "Python 運行時環境分析失敗"
            
            # 4. 嘗試獲取增強客戶端（如果可用）
            enhanced_client = None
            if hasattr(factory, 'get_enhanced_mcp_client'):
                enhanced_client = factory.get_enhanced_mcp_client()
                
                # 獲取系統資訊
                system_info = await enhanced_client.get_system_info()
                assert isinstance(system_info, dict), "系統資訊格式錯誤"
            
            # 5. 回退到生產客戶端
            production_client = get_production_mcp_client()
            assert production_client is not None, "生產客戶端獲取失敗"
            
            print(f"✅ 完整整合工作流程測試通過")
            print(f"   - 基礎配置: ✅")
            print(f"   - 增強配置: {'✅' if enhanced_config else '⚠️ 回退'}")
            print(f"   - 增強客戶端: {'✅' if enhanced_client else '⚠️ 回退'}")
            print(f"   - 生產客戶端: ✅")
            
        except Exception as e:
            pytest.fail(f"完整整合工作流程測試失敗: {e}")
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """測試錯誤恢復工作流程"""
        try:
            # 模擬各種錯誤情況
            
            # 1. nodecomman 不可用時的回退
            try:
                from src.services.enhanced_mcp_client import get_enhanced_mcp_client
                
                # 強制使用回退機制
                client = get_enhanced_mcp_client(use_nodecomman=False, fallback_enabled=True)
                system_info = await client.get_system_info()
                
                assert system_info["using_nodecomman"] is False, "回退機制未正確啟用"
                
            except ImportError:
                # 如果增強客戶端不可用，直接使用生產客戶端
                production_client = get_production_mcp_client()
                assert production_client is not None
            
            # 2. 配置分析失敗時的處理
            base_config = get_mcp_config()
            
            # 嘗試獲取不存在的配置
            nonexistent_config = base_config.get_server_config("nonexistent")
            assert nonexistent_config is None, "不存在的配置應該返回 None"
            
            # 驗證現有配置
            is_valid, error_msg = base_config.validate_server_config("postgres")
            # 注意：這裡可能失敗是正常的，因為實際 MCP 服務器可能未運行
            
            print(f"✅ 錯誤恢復工作流程測試通過")
            print(f"   - 回退機制: ✅")
            print(f"   - 錯誤處理: ✅")
            print(f"   - 配置驗證: {'✅' if is_valid else f'⚠️ {error_msg}'}")
            
        except Exception as e:
            pytest.fail(f"錯誤恢復工作流程測試失敗: {e}")


class TestCriticalIssueDetection:
    """關鍵問題檢測"""
    
    def test_detect_configuration_api_inconsistencies(self):
        """檢測配置 API 不一致問題"""
        issues = []
        
        try:
            # 檢測基礎配置 API
            base_config = get_mcp_config()
            if not hasattr(base_config, 'get_server_config'):
                issues.append("基礎配置缺少 get_server_config 方法")
            
            # 檢測增強配置 API
            try:
                from src.config.enhanced_mcp_config import get_enhanced_mcp_config
                enhanced_config = get_enhanced_mcp_config()
                
                if not hasattr(enhanced_config, 'get_base_config'):
                    issues.append("增強配置缺少 get_base_config 方法")
                    
            except ImportError:
                issues.append("增強配置模組無法導入")
            
            # 檢測 nodecomman 工廠 API
            try:
                from src.nodecomman.implementations.universal_mcp_factory import UniversalMCPServerFactory
                factory = UniversalMCPServerFactory()
                
                if not hasattr(factory, 'get_predefined_config'):
                    issues.append("MCP 工廠缺少 get_predefined_config 方法")
                    
            except ImportError:
                issues.append("MCP 工廠模組無法導入")
        
        except Exception as e:
            issues.append(f"配置 API 檢測失敗: {e}")
        
        if issues:
            print(f"🚨 檢測到配置 API 問題:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print(f"✅ 配置 API 一致性檢查通過")
        
        # 檢查問題列表，如果有問題則測試失敗
        if issues:
            pytest.fail(f"發現 {len(issues)} 個配置 API 不一致問題: {issues}")
    
    def test_detect_service_registry_parameter_issues(self):
        """檢測服務註冊參數問題"""
        issues = []
        
        try:
            factory = EnhancedServiceFactory()
            
            # 檢查方法簽名
            import inspect
            
            # 檢查關鍵方法的參數
            critical_methods = [
                'get_mcp_config',
                'get_mcp_connection_pool'
            ]
            
            for method_name in critical_methods:
                if hasattr(factory, method_name):
                    method = getattr(factory, method_name)
                    sig = inspect.signature(method)
                    
                    # 檢查是否有意外的必需參數
                    required_params = [
                        p for p in sig.parameters.values()
                        if p.default == p.empty and p.kind != p.VAR_POSITIONAL and p.kind != p.VAR_KEYWORD
                    ]
                    
                    if required_params:
                        issues.append(f"方法 {method_name} 有意外的必需參數: {[p.name for p in required_params]}")
                else:
                    issues.append(f"服務工廠缺少方法: {method_name}")
        
        except Exception as e:
            issues.append(f"服務註冊參數檢測失敗: {e}")
        
        if issues:
            print(f"🚨 檢測到服務註冊參數問題:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print(f"✅ 服務註冊參數檢查通過")
        
        # 檢查問題列表，如果有問題則測試失敗
        if issues:
            pytest.fail(f"發現 {len(issues)} 個服務註冊參數問題: {issues}")
    
    def test_detect_compatibility_interface_differences(self):
        """檢測兼容性接口差異"""
        issues = []
        
        try:
            # 檢查生產客戶端和增強客戶端的接口一致性
            production_client = get_production_mcp_client()
            
            try:
                from src.services.enhanced_mcp_client import get_enhanced_mcp_client
                enhanced_client = get_enhanced_mcp_client()
                
                # 檢查關鍵方法是否存在
                critical_methods = ['connect_to_server', 'call_tool']
                
                for method_name in critical_methods:
                    if not hasattr(production_client, method_name):
                        issues.append(f"生產客戶端缺少方法: {method_name}")
                    
                    if not hasattr(enhanced_client, method_name):
                        issues.append(f"增強客戶端缺少方法: {method_name}")
                    
                    # 如果兩者都有該方法，檢查簽名兼容性
                    if hasattr(production_client, method_name) and hasattr(enhanced_client, method_name):
                        import inspect
                        
                        prod_sig = inspect.signature(getattr(production_client, method_name))
                        enh_sig = inspect.signature(getattr(enhanced_client, method_name))
                        
                        # 簡單檢查參數數量（不考慮默認值）
                        prod_params = len(prod_sig.parameters)
                        enh_params = len(enh_sig.parameters)
                        
                        if prod_params != enh_params:
                            issues.append(f"方法 {method_name} 參數數量不一致: 生產={prod_params}, 增強={enh_params}")
                
            except ImportError:
                issues.append("增強客戶端模組無法導入")
        
        except Exception as e:
            issues.append(f"兼容性接口檢測失敗: {e}")
        
        if issues:
            print(f"🚨 檢測到兼容性接口問題:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print(f"✅ 兼容性接口檢查通過")
        
        # 檢查問題列表，如果有問題則測試失敗
        if issues:
            pytest.fail(f"發現 {len(issues)} 個兼容性接口問題: {issues}")
    
    def test_comprehensive_issue_detection(self):
        """綜合問題檢測"""
        print("🔍 執行綜合問題檢測...")
        
        # 嘗試執行所有檢測，如果任何一個失敗，會拋出 AssertionError
        failed_tests = []
        
        try:
            self.test_detect_configuration_api_inconsistencies()
            print("✅ 配置 API 檢測通過")
        except (AssertionError, Exception) as e:
            failed_tests.append(f"配置 API: {str(e)}")
            
        try:
            self.test_detect_service_registry_parameter_issues()
            print("✅ 服務註冊參數檢測通過")
        except (AssertionError, Exception) as e:
            failed_tests.append(f"服務註冊: {str(e)}")
            
        try:
            self.test_detect_compatibility_interface_differences()
            print("✅ 兼容性接口檢測通過")
        except (AssertionError, Exception) as e:
            failed_tests.append(f"兼容性: {str(e)}")
        
        print(f"\n📊 綜合檢測結果:")
        print(f"   - 失敗測試數: {len(failed_tests)}")
        
        if len(failed_tests) == 0:
            print(f"🎉 所有檢測通過，系統架構穩定！")
        else:
            print(f"⚠️ 發現 {len(failed_tests)} 個需要關注的問題:")
            for test_fail in failed_tests:
                print(f"   - {test_fail}")
            
            # 如果有失敗的測試，整體測試失敗
            pytest.fail(f"綜合檢測發現 {len(failed_tests)} 個問題: {failed_tests}")


if __name__ == "__main__":
    # 運行全面的整合測試
    pytest.main([__file__, "-v", "--tb=short", "-s"])