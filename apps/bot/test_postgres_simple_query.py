"""
簡單的 PostgreSQL MCP 查詢測試
測試基本的資料庫查詢功能
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.bot.src.nodecomman.implementations.universal_mcp_factory import UniversalMCPServerFactory
import structlog

# 設置日誌
logger = structlog.get_logger()


async def test_simple_postgres_query():
    """測試簡單的 PostgreSQL 查詢"""
    factory = UniversalMCPServerFactory()
    server_process = None
    
    try:
        print("🚀 PostgreSQL MCP 簡單查詢測試")
        print("=" * 70)
        
        # 1. 創建並啟動服務器
        print("\n1️⃣ 啟動 PostgreSQL MCP 服務器")
        server_info = await factory.create_from_predefined("postgres")
        success = await factory.start_server("postgres")
        
        if not success:
            raise RuntimeError("無法啟動服務器")
            
        print(f"✅ 服務器啟動成功 (PID: {server_info.process_id})")
        
        # 等待服務器初始化
        await asyncio.sleep(2)
        
        # 獲取進程
        server_process = factory._active_servers.get("postgres")
        
        # 2. 測試簡單查詢
        print("\n2️⃣ 執行簡單查詢測試")
        
        # 測試查詢列表
        test_queries = [
            ("SELECT version()", "PostgreSQL 版本"),
            ("SELECT current_database()", "當前資料庫"),
            ("SELECT tablename FROM pg_tables WHERE schemaname = 'public' LIMIT 5", "公共表格"),
            ("SELECT * FROM employees LIMIT 3", "員工資料"),
            ("SELECT COUNT(*) as total FROM products", "產品總數")
        ]
        
        # 準備請求
        requests = [
            {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "0.1.0",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0"}
                },
                "id": 0
            }
        ]
        
        # 添加查詢請求
        for i, (query, desc) in enumerate(test_queries, 1):
            requests.append({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "query",
                    "arguments": {"query": query}
                },
                "id": i
            })
        
        # 發送請求
        input_data = '\n'.join(json.dumps(req) for req in requests) + '\n'
        stdout, stderr = await server_process.communicate(input_data, timeout=10)
        
        if stderr:
            print(f"⚠️ 錯誤: {stderr}")
        
        # 解析結果
        if stdout:
            responses = []
            for line in stdout.strip().split('\n'):
                if line.strip():
                    try:
                        responses.append(json.loads(line))
                    except:
                        pass
            
            # 顯示結果
            for response in responses:
                resp_id = response.get("id", -1)
                
                if resp_id == 0 and "result" in response:
                    print("✅ 初始化成功")
                
                elif resp_id > 0 and resp_id <= len(test_queries):
                    query, desc = test_queries[resp_id - 1]
                    print(f"\n📊 {desc}:")
                    print(f"   查詢: {query}")
                    
                    if "result" in response:
                        result = response["result"]
                        if "content" in result:
                            content = result["content"]
                            if isinstance(content, list) and content:
                                text = content[0].get("text", "")
                                # 顯示前200字元
                                print(f"   結果: {text[:200]}{'...' if len(text) > 200 else ''}")
                    elif "error" in response:
                        print(f"   ❌ 錯誤: {response['error']}")
        
        print("\n" + "=" * 70)
        print("✅ PostgreSQL MCP 測試完成")
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 清理
        if factory:
            await factory.cleanup_all_servers()
            print("🧹 已清理所有資源")


if __name__ == "__main__":
    os.environ["ASYNCIO_FORCE_SELECT_SELECTOR"] = "1"
    asyncio.run(test_simple_postgres_query())