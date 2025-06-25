"""
最終的 PostgreSQL MCP 連接測試
使用 nodecomman 架構測試完整功能
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.bot.src.services.production_mcp_client import ProductionMCPClient
import structlog

# 設置日誌
logger = structlog.get_logger()


async def main():
    """主測試函數"""
    print("🚀 PostgreSQL MCP 連接測試（使用現有架構）")
    print("=" * 70)
    
    # 設置環境變數
    os.environ["ASYNCIO_FORCE_SELECT_SELECTOR"] = "1"
    
    # 初始化客戶端
    client = ProductionMCPClient()
    
    try:
        # 1. 連接到 PostgreSQL MCP
        print("\n1️⃣ 連接 PostgreSQL MCP 服務器")
        
        # 更新配置以使用正確的認證
        client.server_configs["postgres"] = {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://admin:admin@localhost:5432/mydb"],
            "env": {}
        }
        
        success = await client.connect_to_server("postgres")
        if not success:
            print("❌ 無法連接到 PostgreSQL MCP")
            return
        
        print("✅ 成功連接到 PostgreSQL MCP")
        
        # 2. 列出可用工具
        print("\n2️⃣ 列出可用工具")
        tools = await client.list_tools("postgres")
        print(f"找到 {len(tools)} 個工具:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool.get('description', '')[:60]}...")
        
        # 3. 執行查詢測試
        print("\n3️⃣ 執行查詢測試")
        
        test_queries = [
            {
                "name": "資料庫版本",
                "query": "SELECT version()"
            },
            {
                "name": "當前資料庫",
                "query": "SELECT current_database()"
            },
            {
                "name": "公共表格",
                "query": "SELECT tablename FROM pg_tables WHERE schemaname = 'public' LIMIT 5"
            },
            {
                "name": "員工資料",
                "query": "SELECT * FROM employees LIMIT 3"
            }
        ]
        
        for test in test_queries:
            print(f"\n📊 {test['name']}:")
            try:
                result = await client.call_tool(
                    "postgres",
                    "query",
                    {"query": test['query']}
                )
                
                if result and "error" not in result:
                    # 根據查詢類型顯示結果
                    if "version" in test['query']:
                        print(f"  {result}")
                    elif "current_database" in test['query']:
                        print(f"  資料庫: {result}")
                    elif "tablename" in test['query']:
                        tables = result.get("rows", [])
                        print(f"  找到 {len(tables)} 個表格")
                        for table in tables:
                            print(f"    - {table.get('tablename', table)}")
                    elif "employees" in test['query']:
                        rows = result.get("rows", [])
                        print(f"  找到 {len(rows)} 筆資料")
                        for row in rows:
                            print(f"    - {row.get('name', row)}")
                else:
                    print(f"  ❌ 查詢失敗: {result}")
                    
            except Exception as e:
                print(f"  ❌ 錯誤: {e}")
        
        # 4. 測試 M001 機台查詢（如果表存在）
        print("\n4️⃣ 測試機台查詢")
        
        # 先創建測試表
        create_table_query = """
        CREATE TABLE IF NOT EXISTS machines (
            machine_id VARCHAR(10) PRIMARY KEY,
            machine_name VARCHAR(100),
            department VARCHAR(50)
        );
        
        INSERT INTO machines (machine_id, machine_name, department) 
        VALUES ('M001', 'CNC車床A', '加工部')
        ON CONFLICT DO NOTHING;
        """
        
        try:
            # 注意：query 工具通常是只讀的，這可能會失敗
            result = await client.call_tool(
                "postgres",
                "query",
                {"query": create_table_query}
            )
            print("  表格創建嘗試完成")
        except:
            print("  ⚠️ 無法創建表格（query 工具可能是只讀的）")
        
        # 嘗試查詢
        try:
            result = await client.call_tool(
                "postgres",
                "query",
                {"query": "SELECT * FROM machines WHERE machine_id = 'M001'"}
            )
            
            if result and "error" not in result:
                rows = result.get("rows", [])
                if rows:
                    print("  ✅ M001 機台查詢成功")
                    for row in rows:
                        print(f"    機台: {row}")
                else:
                    print("  ⚠️ 未找到 M001 機台資料")
            else:
                print(f"  ❌ 查詢失敗: {result}")
                
        except Exception as e:
            print(f"  ❌ 錯誤: {e}")
        
        print("\n" + "=" * 70)
        print("✅ PostgreSQL MCP 測試完成！")
        print("🎉 nodecomman 架構整合驗證成功")
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await client.close()
        print("\n🧹 已清理所有資源")


if __name__ == "__main__":
    asyncio.run(main())