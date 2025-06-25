"""
測試使用新的 nodecomman 架構連接 PostgreSQL MCP 服務器

這個測試驗證：
1. UniversalMCPServerFactory 能否正確創建 PostgreSQL MCP 服務器
2. NodeJSRuntimeManager 能否正確處理 npx 命令
3. 能否成功連接到 Docker 中的 PostgreSQL 資料庫
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.bot.src.nodecomman.implementations.universal_mcp_factory import UniversalMCPServerFactory
from apps.bot.src.nodecomman.interfaces.server_interfaces import MCPServerConfig, MCPServerType
from apps.bot.src.nodecomman.interfaces.runtime_interfaces import RuntimeType
from apps.bot.src.services.production_mcp_client import ProductionMCPClient
import structlog

# 設置日誌
logger = structlog.get_logger()


class PostgreSQLMCPTester:
    """PostgreSQL MCP 連接測試器"""
    
    def __init__(self):
        self.factory = UniversalMCPServerFactory()
        self.mcp_client = None
        self.server_info = None
        
    async def test_full_connection(self):
        """執行完整的 PostgreSQL MCP 連接測試"""
        print("🚀 開始 PostgreSQL MCP 連接測試（使用 nodecomman 架構）")
        print("=" * 70)
        
        try:
            # 步驟 1: 檢查 Docker PostgreSQL 狀態
            print("\n📋 步驟 1: 檢查 Docker PostgreSQL 狀態")
            await self.check_docker_postgres()
            
            # 步驟 2: 使用 UniversalMCPServerFactory 創建配置
            print("\n📋 步驟 2: 創建 PostgreSQL MCP 配置")
            await self.create_postgres_config()
            
            # 步驟 3: 創建並啟動 MCP 服務器
            print("\n📋 步驟 3: 啟動 PostgreSQL MCP 服務器")
            await self.start_mcp_server()
            
            # 步驟 4: 連接 MCP 客戶端
            print("\n📋 步驟 4: 連接 MCP 客戶端")
            await self.connect_mcp_client()
            
            # 步驟 5: 執行測試查詢
            print("\n📋 步驟 5: 執行測試查詢")
            await self.test_database_queries()
            
            # 步驟 6: 測試 M001 機台查詢
            print("\n📋 步驟 6: 測試 M001 機台查詢")
            await self.test_m001_query()
            
            print("\n" + "=" * 70)
            print("✅ PostgreSQL MCP 連接測試成功！")
            print("🎉 nodecomman 架構整合驗證完成")
            
        except Exception as e:
            print(f"\n❌ 測試失敗: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 清理資源
            await self.cleanup()
    
    async def check_docker_postgres(self):
        """檢查 Docker PostgreSQL 容器狀態"""
        try:
            # 檢查 Docker 容器
            process = await asyncio.create_subprocess_exec(
                "docker", "ps", "--filter", "name=manufacturing_postgres",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            
            if b"manufacturing_postgres" in stdout:
                print("✅ Docker PostgreSQL 容器運行中")
                
                # 測試直接連接
                test_process = await asyncio.create_subprocess_exec(
                    "docker", "exec", "manufacturing_postgres",
                    "psql", "-U", "postgres", "-d", "manufacturing_db",
                    "-c", "SELECT 1;",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await test_process.communicate()
                
                if test_process.returncode == 0:
                    print("✅ PostgreSQL 資料庫連接正常")
                else:
                    print(f"⚠️ 資料庫連接測試失敗: {stderr.decode()}")
            else:
                print("❌ Docker PostgreSQL 容器未運行")
                print("💡 請執行: docker-compose -f docker-compose.postgres.yml up -d")
                
        except Exception as e:
            print(f"⚠️ 無法檢查 Docker 狀態: {e}")
    
    async def create_postgres_config(self):
        """創建 PostgreSQL MCP 配置"""
        try:
            # 獲取預定義的 PostgreSQL 配置
            config = await self.factory.get_predefined_config("postgres")
            
            if config:
                print(f"✅ 使用預定義配置: {config.name}")
                print(f"   命令: {config.command} {' '.join(config.args)}")
                print(f"   環境變數: {list(config.env.keys())}")
                
                # 驗證配置
                issues = await self.factory.validate_config(config)
                if issues:
                    print("⚠️ 配置問題:")
                    for issue in issues:
                        print(f"   - {issue}")
                else:
                    print("✅ 配置驗證通過")
            else:
                print("❌ 無法獲取 PostgreSQL 預定義配置")
                
        except Exception as e:
            print(f"❌ 創建配置失敗: {e}")
            raise
    
    async def start_mcp_server(self):
        """啟動 MCP 服務器"""
        try:
            # 創建服務器
            self.server_info = await self.factory.create_from_predefined(
                "postgres",
                name="test_postgres_mcp"
            )
            
            print(f"✅ MCP 服務器創建成功: {self.server_info.config.name}")
            print(f"   狀態: {self.server_info.status}")
            
            # 啟動服務器
            success = await self.factory.start_server("test_postgres_mcp")
            
            if success:
                print(f"✅ MCP 服務器啟動成功")
                print(f"   PID: {self.server_info.process_id}")
                
                # 等待服務器啟動
                await asyncio.sleep(2)
                
                # 健康檢查
                is_healthy = await self.factory.health_check("test_postgres_mcp")
                print(f"   健康狀態: {'✅ 健康' if is_healthy else '❌ 不健康'}")
            else:
                print("❌ MCP 服務器啟動失敗")
                raise RuntimeError("無法啟動 MCP 服務器")
                
        except Exception as e:
            print(f"❌ 啟動 MCP 服務器失敗: {e}")
            raise
    
    async def connect_mcp_client(self):
        """連接 MCP 客戶端"""
        try:
            # 初始化 Production MCP Client
            self.mcp_client = ProductionMCPClient()
            
            # 連接到 PostgreSQL MCP 服務器
            success = await self.mcp_client.connect_to_server("postgres")
            
            if success:
                print("✅ MCP 客戶端連接成功")
                
                # 列出可用工具
                tools = await self.mcp_client.list_tools("postgres")
                print(f"   可用工具數量: {len(tools)}")
                for tool in tools[:3]:  # 只顯示前3個
                    print(f"   - {tool['name']}: {tool.get('description', '')[:50]}...")
            else:
                print("❌ MCP 客戶端連接失敗")
                raise RuntimeError("無法連接 MCP 客戶端")
                
        except Exception as e:
            print(f"❌ 連接 MCP 客戶端失敗: {e}")
            raise
    
    async def test_database_queries(self):
        """測試資料庫查詢"""
        try:
            # 測試 1: 列出資料表
            print("\n🔍 測試 1: 列出資料表")
            result = await self.mcp_client.call_tool(
                "postgres",
                "list_tables",
                {}
            )
            
            if result and "error" not in result:
                tables = result.get("tables", [])
                print(f"✅ 找到 {len(tables)} 個資料表")
                for table in tables[:5]:  # 只顯示前5個
                    print(f"   - {table}")
            else:
                print(f"❌ 查詢失敗: {result}")
            
            # 測試 2: 查詢機台資料
            print("\n🔍 測試 2: 查詢機台資料")
            query_result = await self.mcp_client.call_tool(
                "postgres",
                "query",
                {
                    "query": "SELECT machine_id, machine_name, department FROM machines LIMIT 5"
                }
            )
            
            if query_result and "error" not in query_result:
                rows = query_result.get("rows", [])
                print(f"✅ 查詢成功，返回 {len(rows)} 筆資料")
                for row in rows:
                    print(f"   - {row.get('machine_id')}: {row.get('machine_name')} ({row.get('department')})")
            else:
                print(f"❌ 查詢失敗: {query_result}")
                
        except Exception as e:
            print(f"❌ 資料庫查詢測試失敗: {e}")
            raise
    
    async def test_m001_query(self):
        """測試 M001 機台查詢（核心功能驗證）"""
        try:
            query = """
            SELECT 
                m.machine_id,
                m.machine_name,
                m.department,
                ms.utilization_rate,
                ms.efficiency_rate,
                ms.good_count,
                ms.defect_count,
                ms.status_date
            FROM machines m
            JOIN machine_status ms ON m.machine_id = ms.machine_id
            WHERE m.machine_id = 'M001'
            ORDER BY ms.status_date DESC
            LIMIT 1
            """
            
            result = await self.mcp_client.call_tool(
                "postgres",
                "query",
                {"query": query}
            )
            
            if result and "error" not in result:
                rows = result.get("rows", [])
                if rows:
                    data = rows[0]
                    print(f"✅ M001 機台查詢成功")
                    print(f"   機台名稱: {data.get('machine_name')}")
                    print(f"   部門: {data.get('department')}")
                    print(f"   稼動率: {data.get('utilization_rate')}%")
                    print(f"   效率: {data.get('efficiency_rate')}%")
                    print(f"   良品數: {data.get('good_count')}")
                    print(f"   不良品數: {data.get('defect_count')}")
                    print(f"   最後更新: {data.get('status_date')}")
                else:
                    print("⚠️ 查無 M001 機台資料")
            else:
                print(f"❌ M001 查詢失敗: {result}")
                
        except Exception as e:
            print(f"❌ M001 機台查詢測試失敗: {e}")
            raise
    
    async def cleanup(self):
        """清理資源"""
        print("\n🧹 清理測試資源")
        
        try:
            # 關閉 MCP 客戶端
            if self.mcp_client:
                await self.mcp_client.close()
                print("✅ MCP 客戶端已關閉")
            
            # 停止 MCP 服務器
            if self.factory and self.server_info:
                await self.factory.stop_server("test_postgres_mcp")
                print("✅ MCP 服務器已停止")
            
            # 清理所有服務器
            if self.factory:
                await self.factory.cleanup_all_servers()
                print("✅ 所有測試服務器已清理")
                
        except Exception as e:
            print(f"⚠️ 清理過程中出現錯誤: {e}")


async def main():
    """主測試函數"""
    tester = PostgreSQLMCPTester()
    await tester.test_full_connection()


if __name__ == "__main__":
    # 設置環境變數
    os.environ["ASYNCIO_FORCE_SELECT_SELECTOR"] = "1"  # macOS 修復
    
    # 執行測試
    asyncio.run(main())