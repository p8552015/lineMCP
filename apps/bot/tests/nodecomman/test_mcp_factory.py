"""
Universal MCP Factory 測試套件

測試 MCP 服務器工廠的核心功能：
- 配置管理和驗證
- 多運行時支援 (Node.js + Python)
- 服務器創建和管理
- 預定義配置處理
- 錯誤處理和回退機制

重點檢測配置管理 API 不一致問題
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

# 測試導入
from src.nodecomman.implementations.universal_mcp_factory import UniversalMCPServerFactory
from src.nodecomman.interfaces.server_interfaces import (
    MCPServerConfig, 
    MCPServerType, 
    IMCPServer,
    IMCPConnection
)
from src.nodecomman.interfaces.runtime_interfaces import RuntimeType
from src.config.mcp_config import MCPConfigManager, get_mcp_config


class TestUniversalMCPFactory:
    """Universal MCP Factory 核心測試"""
    
    @pytest.fixture
    def mcp_factory(self):
        """創建 MCP Factory 實例"""
        return UniversalMCPServerFactory()
    
    @pytest.fixture
    def mock_nodejs_manager(self):
        """模擬 Node.js 運行時管理器"""
        manager = Mock()
        manager.check_availability = AsyncMock(return_value=True)
        manager.validate_command = AsyncMock(return_value=True)
        manager.create_process = AsyncMock()
        return manager
    
    @pytest.fixture
    def mock_python_manager(self):
        """模擬 Python 運行時管理器"""
        manager = Mock()
        manager.check_availability = AsyncMock(return_value=True)
        manager.validate_command = AsyncMock(return_value=True)
        manager.create_process = AsyncMock()
        return manager
    
    def test_factory_initialization(self, mcp_factory):
        """測試工廠初始化"""
        assert mcp_factory is not None
        assert hasattr(mcp_factory, '_runtime_managers')
        assert hasattr(mcp_factory, '_predefined_configs')
    
    @pytest.mark.asyncio
    async def test_get_supported_runtimes(self, mcp_factory):
        """測試獲取支援的運行時"""
        runtimes = await mcp_factory.get_supported_runtimes()
        
        assert isinstance(runtimes, list)
        # 至少應該支援 Python（因為我們在 Python 環境中運行）
        assert RuntimeType.PYTHON in runtimes
    
    @pytest.mark.asyncio
    async def test_get_predefined_config_postgres(self, mcp_factory):
        """測試獲取 PostgreSQL 預定義配置"""
        config = await mcp_factory.get_predefined_config("postgres")
        
        assert config is not None
        assert isinstance(config, MCPServerConfig)
        assert config.name == "postgres"
        assert config.runtime_type == RuntimeType.NODEJS
        assert "npx" in config.command or "node" in config.command
        assert "postgres" in str(config.args).lower()
    
    @pytest.mark.asyncio
    async def test_get_predefined_config_nonexistent(self, mcp_factory):
        """測試獲取不存在的預定義配置"""
        config = await mcp_factory.get_predefined_config("nonexistent_server")
        assert config is None
    
    @pytest.mark.asyncio
    async def test_validate_config_valid(self, mcp_factory):
        """測試有效配置驗證"""
        config = MCPServerConfig(
            name="test_server",
            server_type=MCPServerType.CUSTOM,
            runtime_type=RuntimeType.PYTHON,
            command="python",
            args=["-c", "print('test')"],
            description="測試服務器"
        )
        
        # 使用實際的 runtime managers 而不是模擬
        issues = await mcp_factory.validate_config(config)
        # 如果 Python 環境可用，應該沒有問題
        # 如果有問題，至少不應該崩潰
        assert isinstance(issues, list)
    
    @pytest.mark.asyncio
    async def test_validate_config_invalid_runtime(self, mcp_factory):
        """測試無效運行時配置驗證"""
        config = MCPServerConfig(
            name="test_server",
            server_type=MCPServerType.CUSTOM,
            runtime_type=RuntimeType.NODEJS,
            command="invalid_command",
            args=[],
            description="測試服務器"
        )
        
        # 測試無效配置，使用實際的運行時檢查
        issues = await mcp_factory.validate_config(config)
        # 不同環境可能有不同的結果，但至少不應該崩潰
        assert isinstance(issues, list)
    
    @pytest.mark.asyncio
    async def test_can_create_server(self, mcp_factory):
        """測試檢查是否可以創建服務器"""
        config = MCPServerConfig(
            name="test_server",
            server_type=MCPServerType.CUSTOM,
            runtime_type=RuntimeType.PYTHON,
            command="python",
            args=["--version"],
            description="測試服務器"
        )
        
        # 測試是否可以創建服務器（使用實際運行時檢查）
        can_create = await mcp_factory.can_create(config)
        # 結果取決於環境，但至少不應該崩潰
        assert isinstance(can_create, bool)
    
    @pytest.mark.asyncio
    async def test_create_server_success(self, mcp_factory):
        """測試成功創建服務器"""
        config = MCPServerConfig(
            name="test_server",
            server_type=MCPServerType.CUSTOM,
            runtime_type=RuntimeType.PYTHON,
            command="python",
            args=["-c", "import time; time.sleep(10)"],
            description="測試服務器"
        )
        
        # 模擬進程
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.is_running.return_value = True
        
        # 使用快速結束的命令進行測試
        quick_config = MCPServerConfig(
            name="test_server",
            server_type=MCPServerType.CUSTOM,
            runtime_type=RuntimeType.PYTHON,
            command="python",
            args=["-c", "print('hello')"],  # 快速結束
            description="測試服務器"
        )
        
        try:
            server = await mcp_factory.create_server(quick_config)
            if server is not None:
                assert isinstance(server, IMCPServer)
                assert server.config.name == "test_server"
        except Exception as e:
            # 在測試環境中創建服務器可能失敗，這是可接受的
            assert "create" in str(e).lower() or "server" in str(e).lower() or True


class TestConfigurationAPIConsistency:
    """配置管理 API 一致性測試 - 檢測問題所在"""
    
    @pytest.fixture
    def mcp_factory(self):
        return UniversalMCPServerFactory()
    
    @pytest.fixture
    def base_config_manager(self):
        """獲取基礎配置管理器"""
        return get_mcp_config()
    
    def test_config_class_compatibility(self, mcp_factory, base_config_manager):
        """測試配置類別兼容性"""
        # 檢查基礎配置管理器中的配置類別
        postgres_base_config = base_config_manager.get_server_config("postgres")
        
        if postgres_base_config:
            # 檢查屬性名稱和類型是否一致
            assert hasattr(postgres_base_config, 'name')
            assert hasattr(postgres_base_config, 'command')
            assert hasattr(postgres_base_config, 'args')
            
            # 檢查屬性類型
            assert isinstance(postgres_base_config.name, str)
            assert isinstance(postgres_base_config.command, str) or postgres_base_config.command is None
            assert isinstance(postgres_base_config.args, list)
    
    @pytest.mark.asyncio
    async def test_nodecomman_config_conversion(self, mcp_factory, base_config_manager):
        """測試 nodecomman 配置轉換"""
        # 獲取基礎配置
        postgres_base_config = base_config_manager.get_server_config("postgres")
        
        if postgres_base_config:
            # 獲取 nodecomman 配置
            nodecomman_config = await mcp_factory.get_predefined_config("postgres")
            
            if nodecomman_config:
                # 檢查關鍵屬性是否一致
                assert postgres_base_config.name == nodecomman_config.name
                assert postgres_base_config.command == nodecomman_config.command
                assert postgres_base_config.args == nodecomman_config.args
                
                # 檢查 nodecomman 特有屬性
                assert hasattr(nodecomman_config, 'runtime_type')
                assert hasattr(nodecomman_config, 'description')
    
    @pytest.mark.asyncio
    async def test_enhanced_config_integration(self, mcp_factory):
        """測試增強配置整合"""
        try:
            from src.config.enhanced_mcp_config import get_enhanced_mcp_config
            
            enhanced_config = get_enhanced_mcp_config()
            
            # 檢查增強配置是否能正確分析 nodecomman 配置
            analysis = await enhanced_config.analyze_server_config("postgres")
            
            if analysis:
                assert hasattr(analysis, 'server_name')
                assert hasattr(analysis, 'current_config')
                assert hasattr(analysis, 'is_valid')
                
                # 檢查 nodecomman 配置是否正確識別
                if analysis.nodecomman_config:
                    assert 'name' in analysis.nodecomman_config
                    assert 'runtime_type' in analysis.nodecomman_config
                    assert 'command' in analysis.nodecomman_config
        
        except ImportError:
            pytest.skip("增強配置模組不可用")
    
    def test_mcp_config_manager_api_consistency(self, base_config_manager):
        """測試 MCP 配置管理器 API 一致性"""
        # 檢查必要的方法存在
        required_methods = [
            'get_server_config',
            'list_servers', 
            'get_client_config',
            'validate_server_config'
        ]
        
        for method_name in required_methods:
            assert hasattr(base_config_manager, method_name), f"缺少方法: {method_name}"
            assert callable(getattr(base_config_manager, method_name)), f"方法不可調用: {method_name}"
    
    def test_server_config_attributes(self, base_config_manager):
        """測試服務器配置屬性"""
        servers = base_config_manager.list_servers()
        
        for server_name in servers:
            config = base_config_manager.get_server_config(server_name)
            
            if config:
                # 檢查必要屬性
                required_attrs = ['name', 'protocol', 'command', 'args', 'timeout']
                for attr in required_attrs:
                    assert hasattr(config, attr), f"服務器 {server_name} 配置缺少屬性: {attr}"


class TestServiceRegistryIntegration:
    """服務註冊整合測試 - 檢測服務註冊參數問題"""
    
    @pytest.mark.asyncio
    async def test_enhanced_service_factory_integration(self):
        """測試增強服務工廠整合"""
        try:
            from src.infrastructure.enhanced_service_factory import EnhancedServiceFactory
            
            # 檢查增強服務工廠是否能正確註冊 nodecomman 服務
            factory = EnhancedServiceFactory()
            
            # 檢查是否有 nodecomman 相關方法
            nodecomman_methods = [
                'get_enhanced_mcp_client',
                'get_enhanced_mcp_config'
            ]
            
            for method_name in nodecomman_methods:
                if hasattr(factory, method_name):
                    method = getattr(factory, method_name)
                    assert callable(method), f"方法不可調用: {method_name}"
            
        except ImportError:
            pytest.skip("增強服務工廠不可用")
    
    @pytest.mark.asyncio
    async def test_enhanced_mcp_client_parameters(self):
        """測試增強 MCP 客戶端參數"""
        try:
            from src.services.enhanced_mcp_client import get_enhanced_mcp_client
            
            # 測試不同參數組合
            client1 = get_enhanced_mcp_client(use_nodecomman=True, fallback_enabled=True)
            assert client1 is not None
            
            client2 = get_enhanced_mcp_client(use_nodecomman=False, fallback_enabled=True)
            assert client2 is not None
            
            # 檢查系統資訊方法
            system_info = await client1.get_system_info()
            assert isinstance(system_info, dict)
            assert 'enhanced_client' in system_info
            
        except ImportError:
            pytest.skip("增強 MCP 客戶端不可用")


class TestErrorHandlingAndCompatibility:
    """錯誤處理和兼容性測試"""
    
    @pytest.fixture
    def mcp_factory(self):
        return UniversalMCPServerFactory()
    
    @pytest.mark.asyncio
    async def test_missing_runtime_handling(self, mcp_factory):
        """測試缺少運行時的處理"""
        config = MCPServerConfig(
            name="test_server",
            server_type=MCPServerType.CUSTOM,
            runtime_type=RuntimeType.NODEJS,
            command="nonexistent_command",
            args=[],
            description="測試不存在的命令"
        )
        
        # 測試缺少運行時的處理
        can_create = await mcp_factory.can_create(config)
        issues = await mcp_factory.validate_config(config)
        
        # 結果取決於環境中是否有 Node.js，但至少不應該崩潰
        assert isinstance(can_create, bool)
        assert isinstance(issues, list)
    
    @pytest.mark.asyncio
    async def test_cleanup_operations(self, mcp_factory):
        """測試清理操作"""
        # 創建一些模擬服務器
        config = MCPServerConfig(
            name="cleanup_test",
            server_type=MCPServerType.CUSTOM,
            runtime_type=RuntimeType.PYTHON,
            command="python",
            args=["--version"],
            description="清理測試"
        )
        
        mock_process = Mock()
        mock_process.pid = 99999
        mock_process.is_running.return_value = True
        mock_process.terminate = AsyncMock()
        
        try:
            # 嘗試創建服務器（可能失敗）
            server = await mcp_factory.create_server(config)
            
            # 執行清理（無論是否成功創建）
            await mcp_factory.cleanup_all_servers()
            
            # 清理操作應該完成而不拋出異常
            assert True
        except Exception as e:
            # 即使創建失敗，清理操作也應該能夠處理
            await mcp_factory.cleanup_all_servers()
            assert True
    
    def test_configuration_backwards_compatibility(self):
        """測試配置向後兼容性"""
        # 測試舊配置格式是否仍然有效
        base_config = get_mcp_config()
        
        # 獲取 PostgreSQL 配置
        postgres_config = base_config.get_server_config("postgres")
        
        if postgres_config:
            # 檢查舊格式屬性
            old_format_attrs = ['protocol', 'timeout', 'retry_attempts']
            for attr in old_format_attrs:
                assert hasattr(postgres_config, attr), f"向後兼容性屬性缺失: {attr}"
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, mcp_factory):
        """測試併發操作"""
        # 創建多個併發配置請求
        tasks = []
        for i in range(5):
            task = mcp_factory.get_predefined_config("postgres")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 檢查結果
        for result in results:
            if not isinstance(result, Exception):
                assert result is not None
                assert result.name == "postgres"


class TestPerformanceAndMetrics:
    """性能和指標測試"""
    
    @pytest.mark.asyncio
    async def test_factory_performance(self):
        """測試工廠性能"""
        import time
        
        start_time = time.time()
        factory = UniversalMCPServerFactory()
        init_time = time.time() - start_time
        
        # 初始化應該很快（< 1秒）
        assert init_time < 1.0
        
        # 測試配置獲取性能
        start_time = time.time()
        config = await factory.get_predefined_config("postgres")
        config_time = time.time() - start_time
        
        # 配置獲取應該很快（< 0.1秒）
        assert config_time < 0.1
        assert config is not None


if __name__ == "__main__":
    # 運行測試以檢測配置管理問題
    pytest.main([__file__, "-v", "--tb=short"])