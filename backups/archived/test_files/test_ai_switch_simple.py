#!/usr/bin/env python3
"""
簡單測試 AI 模型切換機制
不需要完整的服務工廠，直接測試 AI 服務
"""

import asyncio
import os
import sys
from pathlib import Path

# 設置工作目錄和環境
os.chdir(Path(__file__).parent / "apps" / "bot")
sys.path.insert(0, '.')

# 載入環境變數
from dotenv import load_dotenv
load_dotenv()

try:
    from src.services.ai_model_service_enhanced import EnhancedAIModelService
    
    async def test_ai_models():
        print("🧪 測試 AI 模型切換機制")
        print("=" * 40)
        
        # 創建 AI 服務
        ai_service = EnhancedAIModelService()
        
        print(f"✅ 預設模型: {ai_service.default_model}")
        print(f"✅ 備用模型: {ai_service.fallback_models}")
        print(f"✅ 可用模型: {list(ai_service.models.keys())}")
        
        # 測試查詢
        test_query = "CNC車床今天不良率"
        print(f"\n🎯 測試查詢: '{test_query}'")
        
        # 方法1：測試新的用戶指導方法
        print("\n📋 方法1：generate_user_guidance")
        try:
            guidance_prompt = """
用戶詢問「CNC車床今天不良率」，但系統目前不支援品質指標的直接查詢。

請協助解釋：
1. 為什麼無法直接查詢不良率數據
2. 建議替代的查詢方式（如機台狀態、產量統計等）
3. 提供2-3個相關的可查詢範例

語氣要專業友善，幫助用戶理解系統功能範圍。
"""
            
            result1 = await ai_service.generate_user_guidance(
                user_input=test_query,
                guidance_prompt=guidance_prompt
            )
            
            if isinstance(result1, tuple):
                response1, confidence1 = result1
                print(f"✅ 用戶指導回應: {response1[:100]}...")
                print(f"📊 信心度: {confidence1}")
            else:
                print(f"⚠️ 異常回應: {result1}")
                
        except Exception as e:
            print(f"❌ generate_user_guidance 失敗: {e}")
            
        # 方法2：測試舊的增強查詢方法
        print("\n📋 方法2：enhance_natural_language_query")
        try:
            result2 = await ai_service.enhance_natural_language_query(
                user_query=test_query,
                database_schema={}
            )
            
            if isinstance(result2, tuple):
                response2, confidence2 = result2
                print(f"✅ 增強查詢回應: {response2[:100]}...")
                print(f"📊 信心度: {confidence2}")
            else:
                print(f"⚠️ 異常回應: {result2}")
                
        except Exception as e:
            print(f"❌ enhance_natural_language_query 失敗: {e}")
            
        # 檢查模型健康狀態
        print("\n🏥 模型健康狀態:")
        health = ai_service.get_model_health_status()
        for model_name, status in health['models'].items():
            health_icon = "✅" if status['healthy'] else "❌"
            failures = status['failures']
            print(f"  {health_icon} {model_name}: 失敗次數={failures}")
            
        print("\n🔍 結論:")
        print("- 如果兩個方法都返回相似的技術性回應，問題在於 AI 提示詞")
        print("- 如果 generate_user_guidance 返回友善回應，說明方法正確")
        print("- 檢查模型是否正常切換（失敗次數）")
        
    asyncio.run(test_ai_models())
    
except Exception as e:
    print(f"❌ 模組載入或執行失敗: {e}")
    import traceback
    traceback.print_exc()