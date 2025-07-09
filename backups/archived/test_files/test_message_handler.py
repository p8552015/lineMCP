#!/usr/bin/env python3
"""
測試 MessageHandlerDI 的完整流程
"""
import asyncio
import sys
import os

# 設置環境變數
os.environ['ASYNCIO_FORCE_SELECT_SELECTOR'] = '1'
os.environ['LINE_CHANNEL_ACCESS_TOKEN'] = 'test_token'
os.environ['LINE_CHANNEL_SECRET'] = 'test_secret'
os.environ['OPENAI_API_KEY'] = 'test_openai_key'
os.environ['JWT_SECRET_KEY'] = 'test_jwt_secret'
os.environ['AI_MODEL_PROVIDER'] = 'google'
os.environ['AI_ENABLE_ENHANCED_NL'] = 'true'
os.environ['NL_FALLBACK_TO_RULES'] = 'true'

# 讀取實際的 Google API key
try:
    with open('/Users/yen/Desktop/lineMCP/apps/bot/.env', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and 'GOOGLE_API_KEY=' in line:
                key, value = line.split('=', 1)
                value = value.split('#')[0].strip().strip('\'"')
                os.environ['GOOGLE_API_KEY'] = value
                break
except Exception:
    pass

# 添加項目路徑
sys.path.append('/Users/yen/Desktop/lineMCP/apps/bot/src')

async def test_message_handler():
    try:
        from infrastructure.enhanced_service_factory import get_enhanced_service_factory
        
        print("🔍 測試 MessageHandlerDI 完整流程")
        print("=" * 40)
        
        # 獲取服務工廠和訊息處理器
        factory = get_enhanced_service_factory()
        factory.initialize()
        message_handler = factory.create_message_handler()
        
        # 測試查詢
        test_query = "CNC車床今天不良率"
        print(f"測試查詢: '{test_query}'")
        print()
        
        try:
            # 調用完整的處理流程
            print("🔄 調用 process_message...")
            result = await message_handler.process_message(
                user_id="test_user",
                message_text=test_query,
                reply_token="test_token"
            )
            
            print("✅ 處理完成")
            print(f"結果類型: {type(result)}")
            
            if hasattr(result, 'text'):
                response_text = result.text
                print(f"回覆長度: {len(response_text)} 字符")
                print()
                print("回覆內容:")
                print("-" * 40)
                print(response_text)
                print("-" * 40)
                
                # 檢查回覆類型
                if "machine_id" in response_text.lower():
                    print("\n❌ 這是原始數據庫記錄！")
                elif any(word in response_text for word in ["建議", "請", "提供", "指定"]):
                    print("\n✅ 這是 LLM 指導回覆！")
                else:
                    print("\n❓ 無法確定回覆類型")
                    
            else:
                print(f"無法獲取回覆文字，結果: {result}")
                
        except Exception as e:
            print(f"❌ 處理失敗: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_message_handler())