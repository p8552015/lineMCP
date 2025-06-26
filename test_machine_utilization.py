#!/usr/bin/env python3
"""
測試機台稼動率查詢問題
模擬用戶查詢並診斷為什麼會卡住
"""

import asyncio
import sys
import os
import time
from datetime import datetime

# 添加應用程式路徑
sys.path.append(os.path.join(os.path.dirname(__file__), 'apps', 'bot', 'src'))

async def test_machine_utilization_query():
    """測試機台稼動率查詢是否會卡住"""
    print("🔍 測試機台稼動率查詢問題...")
    print("=" * 60)
    
    try:
        # 1. 測試基本服務初始化
        print("📋 步驟 1: 測試服務初始化...")
        from src.infrastructure.enhanced_service_factory import get_enhanced_service_factory
        
        start_time = time.time()
        factory = get_enhanced_service_factory()
        factory.initialize()
        init_time = time.time() - start_time
        print(f"✅ 服務工廠初始化完成 ({init_time:.2f}s)")
        
        # 2. 測試訊息處理器創建
        print("\n📋 步驟 2: 測試訊息處理器創建...")
        start_time = time.time()
        message_handler = factory.create_message_handler()
        handler_time = time.time() - start_time
        print(f"✅ 訊息處理器創建完成 ({handler_time:.2f}s)")
        
        # 3. 測試自然語言查詢
        print("\n📋 步驟 3: 測試機台稼動率查詢...")
        test_queries = [
            "機台稼動率",
            "M001 機台稼動率",
            "查看機台稼動率",
            "謝東興「跑起來，別用走的」 機台稼動率"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n🧪 測試查詢 {i}: '{query}'")
            start_time = time.time()
            
            try:
                # 設定較短的超時來避免卡住
                result = await asyncio.wait_for(
                    message_handler.process_message("test-user", query, "test-token"),
                    timeout=10.0  # 10秒超時
                )
                
                elapsed = time.time() - start_time
                print(f"✅ 查詢完成 ({elapsed:.2f}s)")
                print(f"📝 回應: {result.text[:100]}...")
                
            except asyncio.TimeoutError:
                elapsed = time.time() - start_time
                print(f"⏰ 查詢超時 ({elapsed:.2f}s)")
                print("❌ 這可能是導致用戶看到「正在處理...」的原因")
                
                # 分析可能的原因
                print("\n🔍 超時原因分析:")
                print("  1. AI 模型 API 呼叫超時")
                print("  2. MCP PostgreSQL 連線問題")
                print("  3. 資料庫查詢複雜度過高")
                print("  4. 網路連線問題")
                
            except Exception as e:
                elapsed = time.time() - start_time
                print(f"❌ 查詢失敗 ({elapsed:.2f}s): {e}")
        
        # 4. 測試直接 SQL 查詢作為對比
        print("\n📋 步驟 4: 測試直接 SQL 查詢...")
        sql_queries = [
            "/sql SELECT machine_id, status FROM machines LIMIT 5",
            "/sql SELECT * FROM machines WHERE machine_id = 'M001'",
        ]
        
        for query in sql_queries:
            print(f"\n🧪 測試 SQL: '{query}'")
            start_time = time.time()
            
            try:
                result = await asyncio.wait_for(
                    message_handler.process_message("test-user", query, "test-token"),
                    timeout=5.0
                )
                elapsed = time.time() - start_time
                print(f"✅ SQL 查詢完成 ({elapsed:.2f}s)")
                
            except asyncio.TimeoutError:
                elapsed = time.time() - start_time
                print(f"⏰ SQL 查詢也超時 ({elapsed:.2f}s)")
                print("❌ 這表明 MCP 或資料庫連線有問題")
                
            except Exception as e:
                elapsed = time.time() - start_time
                print(f"❌ SQL 查詢失敗 ({elapsed:.2f}s): {e}")
        
        # 5. 測試系統狀態查詢
        print("\n📋 步驟 5: 測試系統狀態...")
        try:
            result = await message_handler.process_message("test-user", "/status", "test-token")
            print(f"✅ 系統狀態: {result.text[:100]}...")
        except Exception as e:
            print(f"❌ 系統狀態查詢失敗: {e}")
            
    except Exception as e:
        print(f"❌ 測試過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()

async def diagnose_stuck_issue():
    """診斷卡住問題的具體原因"""
    print("\n" + "=" * 60)
    print("🔬 診斷「正在處理...」卡住問題")
    print("=" * 60)
    
    # 1. 檢查環境變數
    print("📋 檢查 AI 配置...")
    import os
    
    openai_key = os.getenv('OPENAI_API_KEY')
    google_key = os.getenv('GOOGLE_API_KEY')
    
    print(f"  OPENAI_API_KEY: {'已設定' if openai_key else '❌ 未設定'}")
    print(f"  GOOGLE_API_KEY: {'已設定' if google_key else '❌ 未設定'}")
    
    if not openai_key and not google_key:
        print("⚠️  沒有設定 AI API 金鑰，這可能導致自然語言處理卡住")
    
    # 2. 檢查 MCP 配置
    print("\n📋 檢查 MCP 服務配置...")
    try:
        from src.config import get_settings
        settings = get_settings()
        
        print(f"  MCP 配置存在: {'✅' if hasattr(settings, 'mcp_config') else '❌'}")
        
    except Exception as e:
        print(f"❌ 無法載入配置: {e}")
    
    # 3. 建議解決方案
    print("\n💡 建議的解決方案:")
    print("  1. 設定 AI API 金鑰 (OPENAI_API_KEY 或 GOOGLE_API_KEY)")
    print("  2. 檢查 MCP PostgreSQL 服務是否啟動")
    print("  3. 在自然語言處理中添加更短的超時")
    print("  4. 提供降級回答機制")
    print("  5. 添加更詳細的錯誤處理和日誌")

async def create_fallback_solution():
    """創建降級回答機制"""
    print("\n" + "=" * 60)
    print("🛠️  建議的降級回答機制")
    print("=" * 60)
    
    fallback_responses = {
        "機台稼動率": """
📊 機台稼動率查詢

目前系統正在處理中，您可以嘗試：

🔍 **直接查詢:**
• /sql SELECT machine_id, efficiency_rate FROM machines WHERE efficiency_rate IS NOT NULL
• /sql SELECT AVG(efficiency_rate) as avg_utilization FROM machines

📈 **建議查詢:**
• M001 機台狀態
• 查看所有機台
• 生產效率統計

💡 如果查詢時間過長，請使用 /help 查看更多選項
        """,
        
        "M001 機台稼動率": """
🏭 M001 機台稼動率

**快速查詢:**
/sql SELECT * FROM machines WHERE machine_id = 'M001'

**詳細分析:**
/sql SELECT machine_id, efficiency_rate, status, last_updated FROM machines WHERE machine_id = 'M001'
        """
    }
    
    print("建議在 MessageHandlerDI 中添加以下降級機制:")
    print("""
def _get_fallback_response(self, query: str) -> Message:
    \"\"\"當自然語言處理超時時的降級回答\"\"\"
    # 檢查是否為機台稼動率查詢
    if '稼動率' in query or 'utilization' in query.lower():
        return TextMessage(text=fallback_responses.get(query, default_response))
    
    return TextMessage(text="查詢處理中，請稍後再試或使用 /help 查看可用指令")
    """)

if __name__ == "__main__":
    async def main():
        await test_machine_utilization_query()
        await diagnose_stuck_issue()
        await create_fallback_solution()
        
        print("\n🎯 總結:")
        print("系統「正在處理...」卡住的主要原因可能是:")
        print("1. AI 模型 API 呼叫超時（最可能）")
        print("2. MCP PostgreSQL 連線問題")
        print("3. 缺乏適當的超時和降級機制")
        print("\n建議立即實施超時控制和降級回答機制。")
    
    asyncio.run(main()) 