"""
直接測試 nodecomman 架構的 PostgreSQL MCP 連接

這個測試繞過現有的 production_mcp_client，
直接使用 UniversalMCPServerFactory 創建和管理 MCP 服務器。
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
from apps.bot.src.nodecomman.interfaces.server_interfaces import MCPServerConfig, MCPServerType
from apps.bot.src.nodecomman.interfaces.runtime_interfaces import RuntimeType
import structlog

# 設置日誌
logger = structlog.get_logger()


class DirectNodecommanTester:
    """直接使用 nodecomman 架構測試 PostgreSQL MCP"""
    
    def __init__(self):
        self.factory = UniversalMCPServerFactory()
        self.server_process = None
        
    async def test_postgres_mcp(self):
        """執行 PostgreSQL MCP 測試"""
        print("🚀 開始 nodecomman 直接測試 PostgreSQL MCP")
        print("=" * 70)
        
        try:
            # 步驟 1: 檢查 PostgreSQL 容器
            print("\n📋 步驟 1: 檢查 Docker PostgreSQL")
            await self.check_postgres_container()
            
            # 步驟 2: 創建並啟動 MCP 服務器進程
            print("\n📋 步驟 2: 使用 nodecomman 創建 MCP 服務器進程")
            await self.create_mcp_server_process()
            
            # 步驟 3: 透過 stdio 通信測試
            print("\n📋 步驟 3: 測試 stdio 通信")
            await self.test_stdio_communication()
            
            # 步驟 4: 執行資料庫查詢
            print("\n📋 步驟 4: 執行資料庫查詢")
            await self.test_database_operations()
            
            print("\n" + "=" * 70)
            print("✅ nodecomman PostgreSQL MCP 測試成功！")
            
        except Exception as e:
            print(f"\n❌ 測試失敗: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.cleanup()
    
    async def check_postgres_container(self):
        """檢查 PostgreSQL 容器狀態"""
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "ps", "--filter", "name=postgres", "--format", "{{.Names}}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            
            containers = stdout.decode().strip().split('\n')
            postgres_containers = [c for c in containers if 'postgres' in c]
            
            if postgres_containers:
                print(f"✅ 找到 PostgreSQL 容器: {postgres_containers}")
                
                # 測試連接
                for container in postgres_containers:
                    test_cmd = await asyncio.create_subprocess_exec(
                        "docker", "exec", container,
                        "psql", "-U", "postgres", "-c", "SELECT version();",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await test_cmd.communicate()
                    
                    if test_cmd.returncode == 0:
                        print(f"✅ 容器 {container} PostgreSQL 運行正常")
                        version = stdout.decode().strip().split('\n')[2] if stdout else "Unknown"
                        print(f"   版本: {version[:50]}...")
                        break
            else:
                print("❌ 未找到運行中的 PostgreSQL 容器")
                
        except Exception as e:
            print(f"⚠️ 檢查容器失敗: {e}")
    
    async def create_mcp_server_process(self):
        """創建 MCP 服務器進程"""
        try:
            # 獲取預定義配置
            config = await self.factory.get_predefined_config("postgres")
            
            # 更新連接字串以匹配 Docker 容器
            config.env["POSTGRES_CONNECTION_STRING"] = (
                "postgresql://postgres:postgres@localhost:5432/postgres"
            )
            
            print(f"📝 配置資訊:")
            print(f"   命令: {config.command} {' '.join(config.args)}")
            print(f"   連接字串: {config.env['POSTGRES_CONNECTION_STRING']}")
            
            # 獲取 runtime manager
            runtime_manager = self.factory._runtime_managers.get(RuntimeType.NODEJS)
            
            if not runtime_manager:
                raise RuntimeError("Node.js runtime manager 不可用")
            
            # 創建進程
            self.server_process = await runtime_manager.create_process(
                command=config.command,
                args=config.args,
                env=config.env
            )
            
            # 啟動進程
            if await self.server_process.start():
                print(f"✅ MCP 服務器進程啟動成功")
                print(f"   PID: {self.server_process.info.pid}")
                
                # 等待服務器初始化
                await asyncio.sleep(2)
            else:
                raise RuntimeError("無法啟動 MCP 服務器進程")
                
        except Exception as e:
            print(f"❌ 創建 MCP 服務器失敗: {e}")
            raise
    
    async def test_stdio_communication(self):
        """測試 stdio 通信"""
        try:
            if not self.server_process:
                raise RuntimeError("服務器進程未創建")
            
            # 發送初始化請求
            init_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "0.1.0",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "nodecomman-test",
                        "version": "1.0.0"
                    }
                },
                "id": 1
            }
            
            # 發送請求並等待回應
            request_str = json.dumps(init_request) + "\n"
            response_str, error = await self.server_process.communicate(
                input_data=request_str,
                timeout=5.0
            )
            
            if response_str:
                print("✅ 收到 MCP 服務器回應")
                
                # 嘗試解析回應
                try:
                    # MCP 使用 JSON-RPC over stdio，可能有多行
                    for line in response_str.strip().split('\n'):
                        if line.strip():
                            response = json.loads(line)
                            if "result" in response:
                                print(f"   ✅ 初始化成功")
                                capabilities = response.get("result", {}).get("capabilities", {})
                                print(f"   工具數量: {len(capabilities.get('tools', []))}")
                                break
                            elif "error" in response:
                                print(f"   ❌ 錯誤: {response['error']}")
                except json.JSONDecodeError:
                    print(f"   ⚠️ 無法解析回應: {response_str[:100]}...")
            else:
                print(f"❌ 無回應，錯誤: {error}")
                
        except Exception as e:
            print(f"❌ stdio 通信測試失敗: {e}")
            # 不拋出異常，繼續其他測試
    
    async def test_database_operations(self):
        """測試資料庫操作"""
        try:
            print("\n🔍 測試直接資料庫連接")
            
            # 使用 psycopg2 直接測試連接
            try:
                import psycopg2
                conn = psycopg2.connect(
                    host="localhost",
                    port=5432,
                    database="postgres",
                    user="postgres",
                    password="postgres"
                )
                
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
                if result and result[0] == 1:
                    print("✅ 直接資料庫連接成功")
                    
                    # 檢查是否有 manufacturing_db
                    cursor.execute("""
                        SELECT datname FROM pg_database 
                        WHERE datname = 'manufacturing_db'
                    """)
                    
                    if cursor.fetchone():
                        print("✅ manufacturing_db 資料庫存在")
                    else:
                        print("⚠️ manufacturing_db 資料庫不存在")
                        print("💡 需要初始化資料庫結構")
                
                cursor.close()
                conn.close()
                
            except ImportError:
                print("⚠️ psycopg2 未安裝，跳過直接連接測試")
            except Exception as db_error:
                print(f"⚠️ 直接資料庫連接失敗: {db_error}")
                
        except Exception as e:
            print(f"❌ 資料庫操作測試失敗: {e}")
    
    async def cleanup(self):
        """清理資源"""
        print("\n🧹 清理測試資源")
        
        try:
            if self.server_process:
                if await self.server_process.stop():
                    print("✅ MCP 服務器進程已停止")
                else:
                    print("⚠️ 停止服務器進程時出現問題")
                    
        except Exception as e:
            print(f"⚠️ 清理失敗: {e}")


async def main():
    """主測試函數"""
    # 設置環境變數
    os.environ["ASYNCIO_FORCE_SELECT_SELECTOR"] = "1"  # macOS 修復
    
    tester = DirectNodecommanTester()
    await tester.test_postgres_mcp()


if __name__ == "__main__":
    asyncio.run(main())