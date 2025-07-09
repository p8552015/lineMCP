#!/usr/bin/env python3
"""
調試「CNC車床今天不良率」查詢處理流程
追蹤每個階段的處理結果
"""
import asyncio
import json
import sys
import os

# 添加項目路徑
sys.path.append('/Users/yen/Desktop/lineMCP/apps/bot/src')

# 設置環境變數
os.environ['ASYNCIO_FORCE_SELECT_SELECTOR'] = '1'

# 設置必要的環境變數（最小配置）
os.environ['LINE_CHANNEL_ACCESS_TOKEN'] = 'test_token'
os.environ['LINE_CHANNEL_SECRET'] = 'test_secret'
os.environ['OPENAI_API_KEY'] = 'test_openai_key'
os.environ['GOOGLE_API_KEY'] = 'test_google_key' 
os.environ['JWT_SECRET_KEY'] = 'test_jwt_secret'
os.environ['AI_MODEL_PROVIDER'] = 'google'

async def debug_query():
    try:
        from infrastructure.enhanced_service_factory import get_enhanced_service_factory
        
        # 獲取服務工廠
        factory = get_enhanced_service_factory()
        factory.initialize()
        
        # 要調試的查詢
        test_query = "CNC車床今天不良率"
        print(f"🔍 調試查詢: '{test_query}'")
        print("=" * 50)
        
        # 1. 測試 AI 解析器
        print("1️⃣ 測試 AI 解析器...")
        try:
            ai_parser = factory.get_service('AIEnhancedParser')
            ai_result = await ai_parser.parse(test_query, {})
            print(f"   查詢類型: {ai_result.query_type}")
            print(f"   信心度: {ai_result.confidence}")
            print(f"   說明: {ai_result.explanation}")
            print(f"   參數: {ai_result.parameters}")
            print(f"   SQL: '{ai_result.sql_query}'")
        except Exception as e:
            print(f"   ❌ AI 解析器錯誤: {e}")
        
        print()
        
        # 2. 測試組合解析器
        print("2️⃣ 測試組合解析器...")
        try:
            composite_parser = factory.get_parser()
            composite_result = await composite_parser.parse(test_query, {})
            print(f"   查詢類型: {composite_result.query_type}")
            print(f"   信心度: {composite_result.confidence}")
            print(f"   說明: {composite_result.explanation}")
            print(f"   參數: {composite_result.parameters}")
            print(f"   SQL: '{composite_result.sql_query}'")
        except Exception as e:
            print(f"   ❌ 組合解析器錯誤: {e}")
        
        print()
        
        # 3. 測試 NL-to-SQL 服務
        print("3️⃣ 測試 NL-to-SQL 服務...")
        try:
            nl_service = factory.get_nl_service()
            nl_result = await nl_service.parse_natural_language(test_query, {})
            print(f"   查詢類型: {nl_result.query_type}")
            print(f"   信心度: {nl_result.confidence}")
            print(f"   說明: {nl_result.explanation}")
            print(f"   參數: {nl_result.parameters}")
            print(f"   SQL: '{nl_result.sql_query}'")
        except Exception as e:
            print(f"   ❌ NL-to-SQL 服務錯誤: {e}")
        
        print()
        
        # 4. 測試訊息處理器
        print("4️⃣ 測試訊息處理器...")
        try:
            message_handler = factory.create_message_handler()
            result = await message_handler.process_message(
                user_id="debug_user", 
                message_text=test_query, 
                reply_token="debug_token"
            )
            print(f"   最終回覆類型: {type(result)}")
            if hasattr(result, 'text'):
                response_text = result.text
                print(f"   回覆長度: {len(response_text)} 字符")
                print(f"   回覆預覽: {response_text[:200]}...")
                
                # 檢查是否包含 LLM 指導關鍵字
                llm_keywords = ["建議", "範例", "分析", "提示", "請"]
                has_llm_guidance = any(keyword in response_text for keyword in llm_keywords)
                print(f"   是否為 LLM 指導: {has_llm_guidance}")
                
                # 檢查是否包含原始數據關鍵字
                data_keywords = ["machine_id", "稼動率", "效率", "良品", "不良品"]
                has_raw_data = any(keyword in response_text for keyword in data_keywords)
                print(f"   是否包含原始數據: {has_raw_data}")
            
        except Exception as e:
            print(f"   ❌ 訊息處理器錯誤: {e}")
            
        print()
        print("🏁 調試完成")
        
    except Exception as e:
        print(f"❌ 調試腳本錯誤: {e}")

if __name__ == "__main__":
    asyncio.run(debug_query())