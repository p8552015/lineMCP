#!/usr/bin/env python
"""
MCP Common 函式庫驗證腳本

驗證所有模組是否可以正確導入和使用。
"""

import sys
import asyncio
import traceback
from pathlib import Path

# 添加專案路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 驗證結果
validation_results = []


def test_import(module_name, description):
    """測試模組導入"""
    try:
        __import__(module_name)
        validation_results.append(("✅", description, "成功"))
        return True
    except Exception as e:
        validation_results.append(("❌", description, f"失敗: {e}"))
        return False


def test_function(func, description, *args, **kwargs):
    """測試函數執行"""
    try:
        result = func(*args, **kwargs)
        validation_results.append(("✅", description, "成功"))
        return result
    except Exception as e:
        validation_results.append(("❌", description, f"失敗: {e}"))
        return None


async def test_async_function(func, description, *args, **kwargs):
    """測試異步函數執行"""
    try:
        result = await func(*args, **kwargs)
        validation_results.append(("✅", description, "成功"))
        return result
    except Exception as e:
        validation_results.append(("❌", description, f"失敗: {e}"))
        return None


def print_results():
    """打印驗證結果"""
    print("\n" + "="*60)
    print("MCP Common 函式庫驗證結果")
    print("="*60)
    
    for status, description, result in validation_results:
        print(f"{status} {description}: {result}")
    
    # 統計
    success_count = sum(1 for r in validation_results if r[0] == "✅")
    total_count = len(validation_results)
    
    print("\n" + "-"*60)
    print(f"總計: {success_count}/{total_count} 通過")
    
    if success_count == total_count:
        print("🎉 所有驗證項目都通過！")
        return True
    else:
        print(f"⚠️  有 {total_count - success_count} 項驗證失敗")
        return False


async def main():
    """主驗證流程"""
    print("🔍 開始驗證 MCP Common 函式庫...")
    
    # 1. 核心模組導入測試
    print("\n📦 測試核心模組導入...")
    test_import("mcp_common", "主模組")
    test_import("mcp_common.models.base", "基礎資料模型")
    test_import("mcp_common.models.error", "錯誤模型")
    test_import("mcp_common.models.query", "查詢模型")
    
    # 2. 客戶端模組測試
    print("\n👥 測試客戶端模組...")
    test_import("mcp_common.clients.interface", "客戶端介面")
    test_import("mcp_common.clients.mock_client", "Mock 客戶端")
    test_import("mcp_common.clients.factory", "客戶端工廠")
    
    # 3. 適配器模組測試
    print("\n🔌 測試適配器模組...")
    test_import("mcp_common.adapters.base", "基礎適配器")
    test_import("mcp_common.adapters.http", "HTTP 適配器")
    test_import("mcp_common.adapters.websocket", "WebSocket 適配器")
    test_import("mcp_common.adapters.stdio", "STDIO 適配器")
    test_import("mcp_common.adapters.simple_adapter", "Simple 適配器")
    test_import("mcp_common.adapters.legacy_adapter", "Legacy 適配器")
    
    # 4. 連接管理模組測試
    print("\n🔗 測試連接管理模組...")
    test_import("mcp_common.connection.pool", "連接池")
    test_import("mcp_common.connection.circuit", "斷路器")
    test_import("mcp_common.connection.health", "健康檢查")
    test_import("mcp_common.connection.retry", "重試機制")
    
    # 5. 配置系統測試
    print("\n⚙️  測試配置系統...")
    test_import("mcp_common.config.settings", "配置設定")
    test_import("mcp_common.config.config_loader", "配置載入器")
    
    # 6. 可觀測性模組測試
    print("\n📊 測試可觀測性模組...")
    test_import("mcp_common.observability.metrics", "指標收集")
    test_import("mcp_common.observability.tracing", "分散式追蹤")
    
    # 7. 統一客戶端測試
    print("\n🎯 測試統一客戶端...")
    test_import("mcp_common.unified_client", "統一客戶端")
    
    # 8. 功能性測試
    print("\n🧪 執行功能性測試...")
    
    # 測試工廠函數
    try:
        from mcp_common import get_mcp_client
        client = test_function(get_mcp_client, "建立 Mock 客戶端", "mock")
        
        if client:
            # 測試基本操作
            response = await test_async_function(
                client.call_tool,
                "Mock 客戶端工具呼叫",
                "test_server", "test_tool", {"key": "value"}
            )
            
            # 測試健康檢查
            health = await test_async_function(
                client.health_check,
                "Mock 客戶端健康檢查"
            )
            
            # 測試批次呼叫
            from mcp_common.models.base import MCPCall
            calls = [
                MCPCall(server="server1", tool="tool1", params={}),
                MCPCall(server="server2", tool="tool2", params={}),
            ]
            batch_response = await test_async_function(
                client.batch_call,
                "Mock 客戶端批次呼叫",
                calls
            )
            
            # 測試串流呼叫
            try:
                chunks = []
                async for chunk in client.stream_call("test", "stream_tool", {"count": 2}):
                    chunks.append(chunk)
                test_function(lambda: len(chunks) >= 2, "Mock 客戶端串流呼叫")
            except Exception as e:
                validation_results.append(("❌", "Mock 客戶端串流呼叫", f"失敗: {e}"))
            
            # 關閉客戶端
            await test_async_function(client.close, "關閉 Mock 客戶端")
    
    except Exception as e:
        validation_results.append(("❌", "Mock 客戶端功能測試", f"失敗: {e}"))
    
    # 9. 配置系統功能測試
    print("\n⚙️  測試配置功能...")
    try:
        from mcp_common.config.settings import ServerConfig, MCPClientConfig
        
        # 測試伺服器配置
        server_config = test_function(
            ServerConfig,
            "建立伺服器配置",
            name="test_server",
            adapter_type="http",
            url="http://localhost:8080"
        )
        
        # 測試客戶端配置
        client_config = test_function(
            MCPClientConfig,
            "建立客戶端配置",
            environment="testing",
            servers={"test": server_config} if server_config else {}
        )
        
    except Exception as e:
        validation_results.append(("❌", "配置系統功能測試", f"失敗: {e}"))
    
    # 10. 指標系統測試
    print("\n📈 測試指標系統...")
    try:
        from mcp_common.observability.metrics import MCPMetrics
        
        metrics = test_function(MCPMetrics, "建立指標收集器", enabled=True)
        
        if metrics:
            test_function(
                metrics.record_request,
                "記錄請求指標",
                "server", "tool", "http", "success", 0.1
            )
            
            test_function(
                metrics.get_metrics,
                "獲取 Prometheus 指標"
            )
    
    except Exception as e:
        validation_results.append(("❌", "指標系統測試", f"失敗: {e}"))
    
    # 11. 追蹤系統測試
    print("\n🔍 測試追蹤系統...")
    try:
        from mcp_common.observability.tracing import MCPTracing
        
        tracing = test_function(MCPTracing, "建立追蹤配置器", enabled=True)
        
        if tracing:
            # 測試 span 建立
            try:
                with tracing.start_span("test_operation") as span:
                    test_function(lambda: span is not None, "建立追蹤 span")
            except Exception as e:
                validation_results.append(("❌", "建立追蹤 span", f"失敗: {e}"))
    
    except Exception as e:
        validation_results.append(("❌", "追蹤系統測試", f"失敗: {e}"))
    
    # 12. 統一客戶端高級功能測試
    print("\n🎯 測試統一客戶端高級功能...")
    try:
        from mcp_common.unified_client import get_unified_mcp_client
        
        # 測試不同類型的客戶端
        mock_client = test_function(get_unified_mcp_client, "建立統一 Mock 客戶端", "mock")
        
        if mock_client:
            # 測試向後相容介面
            legacy_result = await test_async_function(
                mock_client.call_tool_legacy,
                "統一客戶端 Legacy API",
                "test_server", "test_tool", {}
            )
            
            # 測試工具列表
            tools = await test_async_function(
                mock_client.list_tools,
                "統一客戶端工具列表",
                "test_server"
            )
            
            # 測試伺服器連接
            connected = await test_async_function(
                mock_client.connect_to_server,
                "統一客戶端伺服器連接",
                "test_server"
            )
            
            # 測試上下文管理器
            try:
                async with mock_client as client:
                    test_function(lambda: client is not None, "統一客戶端上下文管理器")
            except Exception as e:
                validation_results.append(("❌", "統一客戶端上下文管理器", f"失敗: {e}"))
    
    except Exception as e:
        validation_results.append(("❌", "統一客戶端高級功能測試", f"失敗: {e}"))
    
    # 打印結果
    return print_results()


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n💥 驗證過程中發生嚴重錯誤: {e}")
        traceback.print_exc()
        sys.exit(1)