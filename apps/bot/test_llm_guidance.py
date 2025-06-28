#!/usr/bin/env python3
"""
直接測試 LLM 指導功能的腳本
"""

import asyncio
import sys
from src.infrastructure.enhanced_service_factory import get_enhanced_service_factory
from src.services.message_handler_di import MessageHandlerDI

async def test_llm_guidance():
    """測試 LLM 指導功能"""
    try:
        print("🚀 初始化服務工廠...")
        factory = get_enhanced_service_factory()
        factory.initialize()
        
        print("📝 獲取訊息處理器...")
        message_handler = factory.get_service(MessageHandlerDI)
        
        print("🤖 測試 LLM 指導功能...")
        test_inputs = [
            "機台",
            "你好 今天天氣如何",
            "查詢生產狀況",
            "M001",
            "故障分析"
        ]
        
        for user_input in test_inputs:
            print(f"\n📋 輸入：{user_input}")
            print("=" * 50)
            
            try:
                result = await message_handler.process_message(
                    user_id="test_user",
                    message_text=user_input,
                    reply_token="test_token"
                )
                
                if hasattr(result, 'text'):
                    print(f"✅ 回應：{result.text}")
                else:
                    print(f"✅ 回應類型：{type(result)}")
                    print(f"✅ 回應內容：{str(result)}")
                    
            except Exception as e:
                print(f"❌ 錯誤：{str(e)}")
                import traceback
                traceback.print_exc()
        
        print("\n🎯 LLM 指導測試完成！")
        
    except Exception as e:
        print(f"❌ 初始化失敗：{str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_llm_guidance())