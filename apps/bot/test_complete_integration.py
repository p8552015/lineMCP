"""
完整的系統整合測試套件
包含 M001 機台查詢和所有核心功能驗證

測試範圍：
1. NodeJS Runtime Manager 功能測試
2. Universal MCP Factory 功能測試  
3. PostgreSQL MCP 連接和查詢測試
4. M001 機台稼動率查詢（核心業務邏輯）
5. 錯誤處理和恢復測試
6. 系統整合驗證
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
from apps.bot.src.nodecomman.implementations.nodejs_runtime_manager import NodeJSRuntimeManager
from apps.bot.src.services.production_mcp_client import ProductionMCPClient
import structlog

# 設置日誌
logger = structlog.get_logger()


class CompleteIntegrationTester:
    """完整的系統整合測試器"""
    
    def __init__(self):
        self.nodejs_manager = NodeJSRuntimeManager()
        self.mcp_factory = UniversalMCPServerFactory()
        self.mcp_client = ProductionMCPClient()
        
        self.test_results = {
            "nodejs_runtime": {"passed": 0, "total": 0, "details": []},
            "mcp_factory": {"passed": 0, "total": 0, "details": []},
            "postgres_connection": {"passed": 0, "total": 0, "details": []},
            "m001_machine_query": {"passed": 0, "total": 0, "details": []},
            "error_handling": {"passed": 0, "total": 0, "details": []},
            "system_integration": {"passed": 0, "total": 0, "details": []}
        }
    
    async def run_complete_test_suite(self):
        """執行完整測試套件"""
        print("🚀 開始完整系統整合測試")
        print("=" * 80)
        
        try:
            # 設置環境
            os.environ["ASYNCIO_FORCE_SELECT_SELECTOR"] = "1"
            
            # 測試階段 1: NodeJS Runtime Manager
            print("\n📋 階段 1: NodeJS Runtime Manager 測試")
            await self.test_nodejs_runtime_manager()
            
            # 測試階段 2: Universal MCP Factory
            print("\n📋 階段 2: Universal MCP Factory 測試")
            await self.test_universal_mcp_factory()
            
            # 測試階段 3: PostgreSQL 連接
            print("\n📋 階段 3: PostgreSQL MCP 連接測試")
            await self.test_postgres_connection()
            
            # 測試階段 4: M001 機台查詢
            print("\n📋 階段 4: M001 機台稼動率查詢測試")
            await self.test_m001_machine_query()
            
            # 測試階段 5: 錯誤處理
            print("\n📋 階段 5: 錯誤處理和恢復測試")
            await self.test_error_handling()
            
            # 測試階段 6: 系統整合
            print("\n📋 階段 6: 系統整合驗證")
            await self.test_system_integration()
            
            # 生成測試報告
            await self.generate_test_report()
            
        except Exception as e:
            print(f"\n❌ 測試套件執行失敗: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.cleanup_resources()
    
    async def test_nodejs_runtime_manager(self):
        """測試 NodeJS Runtime Manager"""
        category = "nodejs_runtime"
        
        # 測試 1: 可用性檢查
        test_name = "Node.js 環境可用性檢查"
        try:
            is_available = await self.nodejs_manager.check_availability()
            self._record_test_result(category, test_name, is_available, 
                                   "✅ Node.js 環境可用" if is_available else "❌ Node.js 環境不可用")
        except Exception as e:
            self._record_test_result(category, test_name, False, f"❌ 錯誤: {e}")
        
        # 測試 2: 運行時資訊獲取
        test_name = "運行時資訊獲取"
        try:
            runtime_info = await self.nodejs_manager.get_runtime_info()
            success = runtime_info.is_available and runtime_info.version
            self._record_test_result(category, test_name, success,
                                   f"✅ 版本: {runtime_info.version}" if success else "❌ 資訊獲取失敗")
        except Exception as e:
            self._record_test_result(category, test_name, False, f"❌ 錯誤: {e}")
        
        # 測試 3: 命令驗證
        test_name = "NPX 命令驗證"
        try:
            is_valid = await self.nodejs_manager.validate_command("npx", ["--version"])
            self._record_test_result(category, test_name, is_valid,
                                   "✅ NPX 命令有效" if is_valid else "❌ NPX 命令無效")
        except Exception as e:
            self._record_test_result(category, test_name, False, f"❌ 錯誤: {e}")
    
    async def test_universal_mcp_factory(self):
        """測試 Universal MCP Factory"""
        category = "mcp_factory"
        
        # 測試 1: 預定義配置
        test_name = "預定義配置獲取"
        try:
            config = await self.mcp_factory.get_predefined_config("postgres")
            success = config is not None and config.name == "postgres"
            self._record_test_result(category, test_name, success,
                                   "✅ PostgreSQL 配置正確" if success else "❌ 配置獲取失敗")
        except Exception as e:
            self._record_test_result(category, test_name, False, f"❌ 錯誤: {e}")
        
        # 測試 2: 配置驗證
        test_name = "配置驗證"
        try:
            config = await self.mcp_factory.get_predefined_config("postgres")
            issues = await self.mcp_factory.validate_config(config)
            success = len(issues) == 0
            self._record_test_result(category, test_name, success,
                                   "✅ 配置驗證通過" if success else f"❌ 配置問題: {issues}")
        except Exception as e:
            self._record_test_result(category, test_name, False, f"❌ 錯誤: {e}")
        
        # 測試 3: 服務器創建
        test_name = "MCP 服務器創建"
        try:
            server_info = await self.mcp_factory.create_from_predefined("postgres", name="test_integration")
            success = server_info is not None
            self._record_test_result(category, test_name, success,
                                   "✅ 服務器創建成功" if success else "❌ 服務器創建失敗")
        except Exception as e:
            self._record_test_result(category, test_name, False, f"❌ 錯誤: {e}")
    
    async def test_postgres_connection(self):
        """測試 PostgreSQL 連接"""
        category = "postgres_connection"
        
        # 測試 1: MCP 連接
        test_name = "PostgreSQL MCP 連接"
        try:
            success = await self.mcp_client.connect_to_server("postgres")
            self._record_test_result(category, test_name, success,
                                   "✅ MCP 連接成功" if success else "❌ MCP 連接失敗")
        except Exception as e:
            self._record_test_result(category, test_name, False, f"❌ 錯誤: {e}")
        
        # 測試 2: 工具列表
        test_name = "工具列表獲取"
        try:
            tools_response = await self.mcp_client.list_tools("postgres")
            if isinstance(tools_response, dict) and "tools" in tools_response:
                tools = tools_response["tools"]
            else:
                tools = tools_response if isinstance(tools_response, list) else []
            
            success = len(tools) > 0
            self._record_test_result(category, test_name, success,
                                   f"✅ 找到 {len(tools)} 個工具" if success else "❌ 無可用工具")
        except Exception as e:
            self._record_test_result(category, test_name, False, f"❌ 錯誤: {e}")
        
        # 測試 3: 基本查詢
        test_name = "基本資料庫查詢"
        try:
            result = await self.mcp_client.call_tool("postgres", "query", 
                                                   {"sql": "SELECT current_database(), version()"})
            success = result.get("success", False)
            self._record_test_result(category, test_name, success,
                                   "✅ 查詢執行成功" if success else f"❌ 查詢失敗: {result}")
        except Exception as e:
            self._record_test_result(category, test_name, False, f"❌ 錯誤: {e}")
    
    async def test_m001_machine_query(self):
        """測試 M001 機台查詢（核心業務邏輯）"""
        category = "m001_machine_query"
        
        # 測試 1: 檢查機台表是否存在
        test_name = "機台表結構檢查"
        try:
            result = await self.mcp_client.call_tool("postgres", "query", {
                "sql": """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('machines', 'machine_status')
                """
            })
            
            success = result.get("success", False)
            if success:
                data = result.get("data", {})
                content = data.get("content", [])
                tables_found = len(content) if content else 0
                self._record_test_result(category, test_name, tables_found > 0,
                                       f"✅ 找到 {tables_found} 個相關表格" if tables_found > 0 else "⚠️ 未找到機台表")
            else:
                self._record_test_result(category, test_name, False, f"❌ 查詢失敗: {result}")
        except Exception as e:
            self._record_test_result(category, test_name, False, f"❌ 錯誤: {e}")
        
        # 測試 2: 創建測試資料
        test_name = "創建機台測試資料"
        try:
            # 創建機台表（如果不存在）
            create_sql = """
            CREATE TABLE IF NOT EXISTS machines (
                machine_id VARCHAR(10) PRIMARY KEY,
                machine_name VARCHAR(100),
                department VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS machine_status (
                id SERIAL PRIMARY KEY,
                machine_id VARCHAR(10) REFERENCES machines(machine_id),
                utilization_rate DECIMAL(5,2),
                efficiency_rate DECIMAL(5,2),
                good_count INTEGER,
                defect_count INTEGER,
                status_date DATE DEFAULT CURRENT_DATE,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            INSERT INTO machines (machine_id, machine_name, department) 
            VALUES ('M001', 'CNC車床A', '加工部')
            ON CONFLICT (machine_id) DO UPDATE SET 
                machine_name = EXCLUDED.machine_name,
                department = EXCLUDED.department;
            
            INSERT INTO machine_status (machine_id, utilization_rate, efficiency_rate, good_count, defect_count)
            VALUES ('M001', 74.4, 91.2, 8952, 881);
            
            SELECT 'Tables created and data inserted' as result;
            """
            
            result = await self.mcp_client.call_tool("postgres", "query", {"sql": create_sql})
            success = result.get("success", False)
            self._record_test_result(category, test_name, success,
                                   "✅ 測試資料創建成功" if success else f"❌ 資料創建失敗: {result}")
        except Exception as e:
            self._record_test_result(category, test_name, False, f"❌ 錯誤: {e}")
        
        # 測試 3: M001 機台稼動率查詢
        test_name = "M001 機台稼動率查詢"
        try:
            m001_query = """
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
            LEFT JOIN machine_status ms ON m.machine_id = ms.machine_id
            WHERE m.machine_id = 'M001'
            ORDER BY ms.recorded_at DESC
            LIMIT 1
            """
            
            result = await self.mcp_client.call_tool("postgres", "query", {"sql": m001_query})
            success = result.get("success", False)
            
            if success:
                data = result.get("data", {})
                content = data.get("content", [])
                if content and isinstance(content, list) and len(content) > 0:
                    text_content = content[0].get("text", "")
                    if "M001" in text_content and "74.4" in text_content:
                        self._record_test_result(category, test_name, True,
                                               "✅ M001 機台稼動率查詢成功 (74.4%)")
                    else:
                        self._record_test_result(category, test_name, False,
                                               f"⚠️ 查詢結果格式異常: {text_content[:100]}...")
                else:
                    self._record_test_result(category, test_name, False, "❌ 查詢無結果")
            else:
                self._record_test_result(category, test_name, False, f"❌ 查詢失敗: {result}")
        except Exception as e:
            self._record_test_result(category, test_name, False, f"❌ 錯誤: {e}")
    
    async def test_error_handling(self):
        """測試錯誤處理和恢復"""
        category = "error_handling"
        
        # 測試 1: 無效 SQL 查詢
        test_name = "無效 SQL 查詢處理"
        try:
            result = await self.mcp_client.call_tool("postgres", "query", 
                                                   {"sql": "SELECT * FROM nonexistent_table"})
            success = not result.get("success", True)  # 期望失敗
            self._record_test_result(category, test_name, success,
                                   "✅ 正確處理無效查詢" if success else "❌ 錯誤處理異常")
        except Exception as e:
            self._record_test_result(category, test_name, True, f"✅ 正確拋出異常: {str(e)[:50]}...")
        
        # 測試 2: 連接恢復
        test_name = "連接恢復能力"
        try:
            # 重新連接測試
            success = await self.mcp_client.connect_to_server("postgres")
            self._record_test_result(category, test_name, success,
                                   "✅ 連接恢復成功" if success else "❌ 連接恢復失敗")
        except Exception as e:
            self._record_test_result(category, test_name, False, f"❌ 錯誤: {e}")
    
    async def test_system_integration(self):
        """測試系統整合"""
        category = "system_integration"
        
        # 測試 1: 端到端查詢流程
        test_name = "端到端查詢流程"
        try:
            # 模擬完整的查詢流程
            queries = [
                ("SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = 'public'", "表格統計"),
                ("SELECT machine_id, machine_name FROM machines LIMIT 3", "機台列表"),
                ("SELECT AVG(utilization_rate) as avg_utilization FROM machine_status", "平均稼動率")
            ]
            
            success_count = 0
            for sql, desc in queries:
                try:
                    result = await self.mcp_client.call_tool("postgres", "query", {"sql": sql})
                    if result.get("success", False):
                        success_count += 1
                except:
                    pass
            
            success = success_count == len(queries)
            self._record_test_result(category, test_name, success,
                                   f"✅ {success_count}/{len(queries)} 查詢成功" if success else 
                                   f"⚠️ 部分查詢失敗 {success_count}/{len(queries)}")
        except Exception as e:
            self._record_test_result(category, test_name, False, f"❌ 錯誤: {e}")
        
        # 測試 2: 系統性能
        test_name = "系統回應性能"
        try:
            import time
            start_time = time.time()
            
            result = await self.mcp_client.call_tool("postgres", "query", 
                                                   {"sql": "SELECT 1 as ping"})
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # 毫秒
            
            success = response_time < 1000  # 1秒內
            self._record_test_result(category, test_name, success,
                                   f"✅ 回應時間: {response_time:.1f}ms" if success else 
                                   f"⚠️ 回應較慢: {response_time:.1f}ms")
        except Exception as e:
            self._record_test_result(category, test_name, False, f"❌ 錯誤: {e}")
    
    def _record_test_result(self, category: str, test_name: str, success: bool, details: str):
        """記錄測試結果"""
        self.test_results[category]["total"] += 1
        if success:
            self.test_results[category]["passed"] += 1
        
        self.test_results[category]["details"].append({
            "test": test_name,
            "success": success,
            "details": details
        })
        
        # 實時顯示結果
        status = "✅" if success else "❌"
        print(f"  {status} {test_name}: {details}")
    
    async def generate_test_report(self):
        """生成測試報告"""
        print("\n" + "=" * 80)
        print("📊 完整系統整合測試報告")
        print("=" * 80)
        
        total_passed = 0
        total_tests = 0
        
        for category, results in self.test_results.items():
            passed = results["passed"]
            total = results["total"]
            percentage = (passed / total * 100) if total > 0 else 0
            
            total_passed += passed
            total_tests += total
            
            status = "✅" if passed == total else "⚠️" if passed > 0 else "❌"
            print(f"\n{status} {category.replace('_', ' ').title()}: {passed}/{total} ({percentage:.1f}%)")
            
            for detail in results["details"]:
                status_icon = "  ✅" if detail["success"] else "  ❌"
                print(f"{status_icon} {detail['test']}")
        
        overall_percentage = (total_passed / total_tests * 100) if total_tests > 0 else 0
        print(f"\n🎯 總體結果: {total_passed}/{total_tests} ({overall_percentage:.1f}%)")
        
        if overall_percentage >= 90:
            print("🎉 系統整合測試 - 優秀！所有核心功能正常運作")
        elif overall_percentage >= 75:
            print("✅ 系統整合測試 - 良好！大部分功能正常運作")
        elif overall_percentage >= 50:
            print("⚠️ 系統整合測試 - 需要改善！部分功能存在問題")
        else:
            print("❌ 系統整合測試 - 嚴重問題！需要立即修復")
    
    async def cleanup_resources(self):
        """清理測試資源"""
        print("\n🧹 清理測試資源")
        
        try:
            # 清理 MCP 工廠資源
            if hasattr(self, 'mcp_factory'):
                await self.mcp_factory.cleanup_all_servers()
                print("✅ MCP 工廠資源已清理")
            
            # 關閉 MCP 客戶端
            if hasattr(self, 'mcp_client'):
                await self.mcp_client.close()
                print("✅ MCP 客戶端已關閉")
                
        except Exception as e:
            print(f"⚠️ 清理過程中出現問題: {e}")


async def main():
    """主測試函數"""
    tester = CompleteIntegrationTester()
    await tester.run_complete_test_suite()


if __name__ == "__main__":
    asyncio.run(main())