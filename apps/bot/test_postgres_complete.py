"""
完整的 PostgreSQL MCP 測試
包含資料庫初始化和查詢測試
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


class PostgreSQLCompleteTester:
    """完整的 PostgreSQL MCP 測試"""
    
    def __init__(self):
        self.factory = UniversalMCPServerFactory()
        self.server_process = None
        self.server_info = None
        
    async def test_complete_flow(self):
        """執行完整測試流程"""
        print("🚀 開始完整的 PostgreSQL MCP 測試")
        print("=" * 70)
        
        try:
            # 步驟 1: 初始化資料庫
            print("\n📋 步驟 1: 初始化 manufacturing_db 資料庫")
            await self.initialize_database()
            
            # 步驟 2: 創建並啟動 MCP 服務器
            print("\n📋 步驟 2: 啟動 PostgreSQL MCP 服務器")
            await self.start_mcp_server()
            
            # 步驟 3: 測試 MCP 通信
            print("\n📋 步驟 3: 測試 MCP JSON-RPC 通信")
            await self.test_mcp_communication()
            
            print("\n" + "=" * 70)
            print("✅ PostgreSQL MCP 測試完成！")
            
        except Exception as e:
            print(f"\n❌ 測試失敗: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.cleanup()
    
    async def initialize_database(self):
        """初始化資料庫"""
        try:
            # 檢查並創建 manufacturing_db
            create_db_cmd = [
                "docker", "exec", "line_mcp_postgres",
                "psql", "-U", "postgres", "-c",
                "SELECT 'CREATE DATABASE manufacturing_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'manufacturing_db')\\gexec"
            ]
            
            process = await asyncio.create_subprocess_exec(
                *create_db_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                print("✅ 資料庫檢查/創建成功")
            else:
                print(f"⚠️ 資料庫操作警告: {stderr.decode()}")
            
            # 創建測試表結構
            create_tables_sql = """
            CREATE TABLE IF NOT EXISTS machines (
                machine_id VARCHAR(10) PRIMARY KEY,
                machine_name VARCHAR(100),
                department VARCHAR(50)
            );
            
            CREATE TABLE IF NOT EXISTS machine_status (
                id SERIAL PRIMARY KEY,
                machine_id VARCHAR(10) REFERENCES machines(machine_id),
                utilization_rate DECIMAL(5,2),
                efficiency_rate DECIMAL(5,2),
                good_count INTEGER,
                defect_count INTEGER,
                status_date DATE
            );
            
            -- 插入測試資料
            INSERT INTO machines (machine_id, machine_name, department) 
            VALUES ('M001', 'CNC車床A', '加工部')
            ON CONFLICT (machine_id) DO NOTHING;
            
            INSERT INTO machine_status (machine_id, utilization_rate, efficiency_rate, good_count, defect_count, status_date)
            VALUES ('M001', 74.4, 91.2, 8952, 881, CURRENT_DATE)
            ON CONFLICT DO NOTHING;
            """
            
            create_tables_cmd = [
                "docker", "exec", "line_mcp_postgres",
                "psql", "-U", "postgres", "-d", "manufacturing_db",
                "-c", create_tables_sql
            ]
            
            process = await asyncio.create_subprocess_exec(
                *create_tables_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                print("✅ 資料表結構初始化成功")
            else:
                print(f"⚠️ 資料表初始化警告: {stderr.decode()}")
                
        except Exception as e:
            print(f"❌ 資料庫初始化失敗: {e}")
            raise
    
    async def start_mcp_server(self):
        """啟動 MCP 服務器"""
        try:
            # 創建服務器
            self.server_info = await self.factory.create_from_predefined("postgres")
            
            print(f"✅ MCP 服務器創建成功")
            print(f"   配置: {self.server_info.config.command} {' '.join(self.server_info.config.args)}")
            
            # 啟動服務器
            success = await self.factory.start_server("postgres")
            
            if success:
                print(f"✅ MCP 服務器啟動成功")
                print(f"   PID: {self.server_info.process_id}")
                
                # 等待服務器完全啟動
                await asyncio.sleep(3)
                
                # 獲取進程
                self.server_process = self.factory._active_servers.get("postgres")
            else:
                raise RuntimeError("無法啟動 MCP 服務器")
                
        except Exception as e:
            print(f"❌ 啟動 MCP 服務器失敗: {e}")
            raise
    
    async def test_mcp_communication(self):
        """測試 MCP 通信"""
        try:
            if not self.server_process:
                raise RuntimeError("服務器進程不存在")
            
            print("\n🔍 測試 1: 發送 initialize 請求")
            
            # 準備 JSON-RPC 請求
            requests = [
                # 1. Initialize
                {
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
                },
                # 2. List tools
                {
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "params": {},
                    "id": 2
                },
                # 3. Execute query
                {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "query",
                        "arguments": {
                            "query": "SELECT machine_id, machine_name FROM machines WHERE machine_id = 'M001'"
                        }
                    },
                    "id": 3
                }
            ]
            
            # 發送請求（MCP 使用 newline-delimited JSON）
            input_data = '\n'.join(json.dumps(req) for req in requests) + '\n'
            
            # 發送並接收回應
            stdout, stderr = await self.server_process.communicate(
                input_data=input_data,
                timeout=10.0
            )
            
            if stderr:
                print(f"⚠️ 錯誤輸出: {stderr}")
            
            if stdout:
                print("✅ 收到回應")
                
                # 解析回應
                responses = []
                for line in stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            response = json.loads(line)
                            responses.append(response)
                        except json.JSONDecodeError:
                            print(f"⚠️ 無法解析: {line}")
                
                # 分析回應
                for response in responses:
                    if response.get("id") == 1:
                        if "result" in response:
                            print("✅ 初始化成功")
                            caps = response["result"].get("capabilities", {})
                            tools = caps.get("tools", {})
                            print(f"   支援的工具: {len(tools)} 個")
                    
                    elif response.get("id") == 2:
                        if "result" in response:
                            tools = response["result"].get("tools", [])
                            print(f"\n🔍 測試 2: 可用工具列表")
                            print(f"✅ 找到 {len(tools)} 個工具")
                            for tool in tools[:3]:
                                print(f"   - {tool.get('name')}: {tool.get('description', '')[:50]}...")
                    
                    elif response.get("id") == 3:
                        if "result" in response:
                            print(f"\n🔍 測試 3: 查詢 M001 機台")
                            result = response["result"]
                            if "content" in result:
                                content = result["content"]
                                if isinstance(content, list) and content:
                                    text = content[0].get("text", "")
                                    print(f"✅ 查詢成功")
                                    print(f"   結果: {text[:200]}...")
                                    
                                    # 嘗試解析結果
                                    if "M001" in text and "CNC車床A" in text:
                                        print("   ✅ M001 機台資料確認")
            else:
                print("❌ 無回應")
                
        except asyncio.TimeoutError:
            print("❌ 通信超時")
        except Exception as e:
            print(f"❌ MCP 通信測試失敗: {e}")
    
    async def cleanup(self):
        """清理資源"""
        print("\n🧹 清理測試資源")
        
        try:
            if self.factory:
                await self.factory.cleanup_all_servers()
                print("✅ 所有服務器已清理")
                
        except Exception as e:
            print(f"⚠️ 清理失敗: {e}")


async def main():
    """主測試函數"""
    # 設置環境變數
    os.environ["ASYNCIO_FORCE_SELECT_SELECTOR"] = "1"  # macOS 修復
    
    tester = PostgreSQLCompleteTester()
    await tester.test_complete_flow()


if __name__ == "__main__":
    asyncio.run(main())