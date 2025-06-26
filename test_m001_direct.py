#!/usr/bin/env python3
"""
直接測試 M001 機台稼動率查詢
繞過 LINE webhook 驗證，直接測試核心功能
"""

import asyncio
import sys
import os

# 設置工作目錄到 apps/bot
bot_dir = os.path.join(os.path.dirname(__file__), 'apps', 'bot')
os.chdir(bot_dir)

# 添加 src 目錄到 Python 路徑
sys.path.insert(0, 'src')

from src.infrastructure.enhanced_service_factory import get_enhanced_service_factory
from src.services.message_handler_di import MessageHandlerDI


async def test_m001_query():
    """測試 M001 機台稼動率查詢"""
    print("🔧 初始化服務工廠...")
    
    try:
        # 初始化增強版服務工廠
        enhanced_factory = get_enhanced_service_factory()
        enhanced_factory.initialize()
        
        print("✅ 服務工廠初始化成功")
        
        # 創建訊息處理器
        message_handler: MessageHandlerDI = enhanced_factory.create_message_handler()
        print("✅ 訊息處理器創建成功")
        
        # 測試查詢
        test_query = "M001機台稼動率"
        print(f"\n🔍 測試查詢: {test_query}")
        
        # 處理訊息
        response = await message_handler.process_message("test-user-001", test_query, "test-reply-token")
        
        print(f"\n📊 查詢結果:\n{response}")
        
        # 驗證結果
        if "M001" in response and "稼動率" in response:
            if "0.0%" in response:
                print("\n❌ 警告：查詢結果顯示 0.0%，可能是空數據問題")
                return False
            else:
                print("\n✅ 查詢成功，返回了實際數據")
                return True
        else:
            print("\n❌ 查詢失敗，結果格式不正確")
            return False
            
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_m001_query())
    sys.exit(0 if success else 1) 