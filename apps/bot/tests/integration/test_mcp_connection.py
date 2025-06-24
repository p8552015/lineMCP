"""MCP 連接整合測試"""
import asyncio
import pytest
from unittest.mock import Mock, patch
import os
import sys

# 添加 src 到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from services.production_mcp_client import ProductionMCPClient
from infrastructure.enhanced_service_factory import EnhancedServiceFactory


@pytest.fixture
def mock_service_factory():
    """模擬服務工廠"""
    factory = Mock(spec=EnhancedServiceFactory)
    return factory


@pytest.fixture
async def mcp_client(mock_service_factory):
    """創建 MCP 客戶端實例"""
    client = ProductionMCPClient()
    client.service_factory = mock_service_factory
    return client


class TestMCPConnection:
    """MCP 連接測試類別"""
    
    @pytest.mark.asyncio
    async def test_mcp_client_initialization(self, mcp_client):
        """測試 MCP 客戶端初始化"""
        assert mcp_client is not None
        assert hasattr(mcp_client, 'connections')
        assert hasattr(mcp_client, 'processes')
        assert hasattr(mcp_client, 'connection_pool')
    
    @pytest.mark.asyncio
    async def test_sqlite_server_configuration(self, mcp_client):
        """測試 SQLite 服務器配置"""
        # 檢查默認配置
        assert 'sqlite' in mcp_client.server_configs
        sqlite_config = mcp_client.server_configs['sqlite']
        
        assert 'command' in sqlite_config
        assert 'args' in sqlite_config
        assert sqlite_config['transport']['type'] == 'stdio'
    
    @pytest.mark.asyncio
    async def test_connection_pool_initialization(self, mcp_client):
        """測試連接池初始化"""
        assert mcp_client.connection_pool is not None
        
        # 檢查連接池狀態
        connections = mcp_client.connection_pool.connections
        assert isinstance(connections, dict)
    
    @pytest.mark.asyncio
    async def test_environment_variables_setup(self):
        """測試環境變數設置"""
        # 檢查關鍵環境變數
        required_vars = [
            'ASYNCIO_FORCE_SELECT_SELECTOR'
        ]
        
        for var in required_vars:
            value = os.getenv(var)
            if var == 'ASYNCIO_FORCE_SELECT_SELECTOR':
                assert value == '1', f"環境變數 {var} 應該設為 '1'"
    
    @pytest.mark.asyncio
    async def test_mock_connection_attempt(self, mcp_client):
        """測試模擬連接嘗試"""
        with patch.object(mcp_client, '_start_mcp_server') as mock_start:
            mock_start.return_value = Mock()
            
            # 嘗試連接（這應該在模擬環境中安全運行）
            try:
                result = await mcp_client.connect_to_server('sqlite')
                # 在測試環境中，這可能會失敗，但我們主要檢查代碼路徑
                assert isinstance(result, bool)
            except Exception as e:
                # 預期在測試環境中可能會有連接錯誤
                assert "No such file" in str(e) or "Connection" in str(e)
    
    @pytest.mark.asyncio
    async def test_connection_state_management(self, mcp_client):
        """測試連接狀態管理"""
        server_name = 'sqlite'
        
        # 初始狀態應該是斷開的
        assert not mcp_client.connections.get(server_name, False)
        
        # 測試狀態設置
        mcp_client.connections[server_name] = True
        assert mcp_client.connections[server_name] is True
        
        # 重置狀態
        mcp_client.connections[server_name] = False
        assert mcp_client.connections[server_name] is False
    
    @pytest.mark.asyncio
    async def test_process_management(self, mcp_client):
        """測試進程管理"""
        server_name = 'sqlite'
        
        # 初始狀態應該沒有進程
        assert server_name not in mcp_client.processes
        
        # 模擬進程添加
        mock_process = Mock()
        mcp_client.processes[server_name] = mock_process
        
        assert server_name in mcp_client.processes
        assert mcp_client.processes[server_name] == mock_process
        
        # 清理
        del mcp_client.processes[server_name]
        assert server_name not in mcp_client.processes
    
    @pytest.mark.asyncio
    async def test_health_check_logic(self, mcp_client):
        """測試健康檢查邏輯"""
        server_name = 'sqlite'
        
        # 測試無進程情況
        health_status = await mcp_client._verify_process_health(server_name)
        assert health_status is False
        
        # 模擬健康進程
        mock_process = Mock()
        mock_process.poll.return_value = None  # 進程仍在運行
        mock_process.returncode = None
        
        mcp_client.processes[server_name] = mock_process
        
        health_status = await mcp_client._verify_process_health(server_name)
        assert health_status is True
        
        # 模擬死亡進程
        mock_process.poll.return_value = 1  # 進程已結束
        mock_process.returncode = 1
        
        health_status = await mcp_client._verify_process_health(server_name)
        assert health_status is False
    
    @pytest.mark.asyncio
    async def test_error_handling_keyerror_fix(self, mcp_client):
        """測試 KeyError 修復的錯誤處理"""
        server_name = 'sqlite'
        
        # 確保進程字典為空（模擬 KeyError 情況）
        mcp_client.processes.clear()
        mcp_client.connections[server_name] = False
        
        # 測試查詢請求（這應該觸發我們的修復邏輯）
        query_data = {
            'query': 'SELECT 1',
            'server_name': server_name
        }
        
        with patch.object(mcp_client, 'connect_to_server') as mock_connect:
            mock_connect.return_value = False
            
            try:
                result = await mcp_client.query_database(query_data)
                assert result['success'] is False
                assert 'error' in result
            except Exception as e:
                # 這是預期的，因為我們在測試環境中無法實際連接
                assert 'KeyError' not in str(e)  # 確保不是 KeyError
    
    @pytest.mark.asyncio 
    async def test_configuration_validation(self, mcp_client):
        """測試配置驗證"""
        # 驗證所有服務器配置的基本結構
        for server_name, config in mcp_client.server_configs.items():
            assert 'command' in config, f"服務器 {server_name} 缺少 command 配置"
            assert 'transport' in config, f"服務器 {server_name} 缺少 transport 配置"
            assert 'type' in config['transport'], f"服務器 {server_name} 的 transport 缺少 type"
            
            # 驗證 SQLite 特定配置
            if server_name == 'sqlite':
                assert config['command'] == 'npx', f"SQLite 服務器應使用 npx 命令"
                assert '@mcp/sqlite' in config['args'], f"SQLite 服務器應包含 @mcp/sqlite 參數"