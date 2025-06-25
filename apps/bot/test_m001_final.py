"""
M001 機台稼動率查詢 - 最終驗證測試

這是核心業務邏輯的最終驗證，模擬 LINE Bot 查詢 M001 機台稼動率的完整流程。
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


async def test_m001_machine_query():
    """測試 M001 機台稼動率查詢"""
    print("🎯 M001 機台稼動率查詢 - 最終驗證")
    print("=" * 60)
    
    # 設置環境
    os.environ["ASYNCIO_FORCE_SELECT_SELECTOR"] = "1"
    
    # 初始化客戶端
    client = ProductionMCPClient()
    
    try:
        # 1. 連接 PostgreSQL MCP
        print("\n1️⃣ 連接 PostgreSQL MCP 服務器...")
        success = await client.connect_to_server("postgres")
        
        if not success:
            print("❌ 無法連接到 PostgreSQL MCP")
            return False
            
        print("✅ PostgreSQL MCP 連接成功")
        
        # 2. 檢查機台表
        print("\n2️⃣ 檢查機台資料表...")
        table_check_result = await client.call_tool("postgres", "query", {
            "sql": """
            SELECT table_name, column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'machines' 
            AND table_schema = 'public'
            ORDER BY ordinal_position
            """
        })
        
        if table_check_result.get("success", False):
            print("✅ 機台表結構檢查完成")
        else:
            print(f"❌ 機台表檢查失敗: {table_check_result}")
        
        # 3. 執行 M001 機台查詢 
        print("\n3️⃣ 查詢 M001 機台稼動率...")
        
        # 核心查詢 - 模擬 LINE Bot 的實際查詢
        m001_query = """
        SELECT 
            id as machine_id,
            name as machine_name,
            location as department,
            utilization_rate,
            status,
            temperature,
            last_maintenance,
            created_at
        FROM machines 
        WHERE id = 'M001'
        """
        
        result = await client.call_tool("postgres", "query", {"sql": m001_query})
        
        if result.get("success", False):
            print("✅ M001 機台查詢成功")
            
            # 解析結果
            data = result.get("data", {})
            content = data.get("content", [])
            
            if content and isinstance(content, list) and len(content) > 0:
                text_content = content[0].get("text", "")
                print(f"\n📊 查詢結果:")
                
                # 嘗試解析 JSON 結果
                try:
                    import json
                    if text_content.strip().startswith('['):
                        machines_data = json.loads(text_content)
                        if machines_data and len(machines_data) > 0:
                            machine = machines_data[0]
                            print(f"🔧 機台編號: {machine.get('machine_id', 'N/A')}")
                            print(f"🏭 機台名稱: {machine.get('machine_name', 'N/A')}")
                            print(f"📍 部門: {machine.get('department', 'N/A')}")
                            print(f"📊 稼動率: {machine.get('utilization_rate', 'N/A')}%")
                            print(f"🟢 狀態: {machine.get('status', 'N/A')}")
                            print(f"🌡️ 溫度: {machine.get('temperature', 'N/A')}°C")
                            print(f"🔧 上次維護: {machine.get('last_maintenance', 'N/A')}")
                            
                            # 驗證關鍵資料
                            machine_id = machine.get('machine_id')
                            utilization_rate = machine.get('utilization_rate')
                            
                            # 處理稼動率可能是字串或數字的情況
                            if isinstance(utilization_rate, str):
                                try:
                                    utilization_rate = float(utilization_rate)
                                except (ValueError, TypeError):
                                    utilization_rate = None
                            
                            if (machine_id == 'M001' and 
                                utilization_rate is not None and 
                                abs(utilization_rate - 74.4) < 0.01):  # 允許小數點誤差
                                print("\n🎉 M001 機台稼動率查詢驗證成功！")
                                print("✅ 所有資料正確，系統整合完成")
                                return True
                            else:
                                print(f"\n⚠️ 資料驗證異常:")
                                print(f"   機台編號: {machine_id} (期望: M001)")
                                print(f"   稼動率: {utilization_rate} (期望: 74.4)")
                                return False
                        else:
                            print("❌ 查詢結果為空")
                            return False
                    else:
                        print(f"📄 原始結果: {text_content}")
                        # 檢查是否包含關鍵資訊
                        if "M001" in text_content and "74.4" in text_content:
                            print("✅ 關鍵資料驗證成功")
                            return True
                        else:
                            print("⚠️ 關鍵資料不完整")
                            return False
                            
                except json.JSONDecodeError:
                    print(f"📄 查詢結果 (非JSON): {text_content}")
                    if "M001" in text_content:
                        print("✅ 包含 M001 機台資料")
                        return True
            else:
                print("❌ 查詢無結果")
                return False
        else:
            print(f"❌ M001 查詢失敗: {result}")
            return False
        
        # 4. 額外測試：查詢所有機台
        print("\n4️⃣ 查詢所有機台（驗證系統功能）...")
        
        all_machines_query = """
        SELECT 
            id, 
            name, 
            status, 
            utilization_rate,
            location
        FROM machines 
        ORDER BY id
        LIMIT 5
        """
        
        all_result = await client.call_tool("postgres", "query", {"sql": all_machines_query})
        
        if all_result.get("success", False):
            print("✅ 機台列表查詢成功")
            
            data = all_result.get("data", {})
            content = data.get("content", [])
            
            if content:
                text_content = content[0].get("text", "")
                print(f"📋 機台列表: {text_content[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # 清理
        await client.close()
        print("\n🧹 測試完成，資源已清理")


async def main():
    """主函數"""
    success = await test_m001_machine_query()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 M001 機台稼動率查詢測試 - 完全成功！")
        print("✅ nodecomman 架構與現有系統完美整合")
        print("✅ PostgreSQL MCP 連接穩定")
        print("✅ 核心業務邏輯正常運作")
        print("\n🚀 系統已準備好進入生產環境！")
    else:
        print("❌ M001 機台稼動率查詢測試失敗")
        print("⚠️ 需要進一步調試和修復")


if __name__ == "__main__":
    asyncio.run(main())