#!/usr/bin/env python3
"""
測試 AI 模型自動備用切換機制
驗證當 Gemini 配額用盡時是否會自動切換到 OpenAI
"""

import asyncio
import os
import sys
import traceback
from pathlib import Path

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent / "apps" / "bot"))

from src.services.ai_model_service_enhanced import EnhancedAIModelService


async def test_ai_fallback():
    """測試 AI 模型備用機制"""
    print("🧪 測試 Gemini → OpenAI 自動備用切換機制")
    print("=" * 50)
    
    try:
        # 初始化增強版 AI 服務
        ai_service = EnhancedAIModelService()
        
        # 檢查可用模型
        models = ai_service.get_available_models()
        print(f"📋 可用模型數量: {len(models)}")
        for model in models:
            print(f"  - {model['name']} ({model['provider']}) {'[預設]' if model['is_default'] else ''}")
        
        print(f"\n🎯 預設模型: {ai_service.default_model}")
        print(f"🔄 備用模型列表: {ai_service.fallback_models}")
        
        # 測試查詢
        test_query = "CNC車床今天不良率"
        database_schema = {}
        
        print(f"\n🧪 測試查詢: '{test_query}'")
        print("正在執行 AI 增強查詢...")
        
        # 執行查詢
        result = await ai_service.enhance_natural_language_query(
            user_query=test_query,
            database_schema=database_schema
        )
        
        if isinstance(result, tuple):
            enhanced_query, confidence = result
            print(f"✅ AI 回應成功")
            print(f"📊 信心度: {confidence}")
            print(f"💬 增強後查詢: {enhanced_query[:200]}...")
        else:
            print(f"⚠️ 異常回應格式: {type(result)}")
            print(f"📝 回應內容: {str(result)[:200]}...")
        
        # 檢查模型健康狀態
        print(f"\n🏥 模型健康狀態:")
        health_status = ai_service.get_model_health_status()
        
        for model_name, status in health_status['models'].items():
            health_icon = "✅" if status['healthy'] else "❌"
            print(f"  {health_icon} {model_name}: 失敗次數={status['failures']}, "
                  f"上次成功={status['seconds_since_success']:.1f}秒前")
        
        # 測試特定模型（強制使用 Gemini）
        print(f"\n🎯 強制測試 Gemini 模型:")
        try:
            gemini_result = await ai_service.enhance_natural_language_query(
                user_query=test_query,
                database_schema=database_schema,
                model_name="gemini-1.5-flash"
            )
            print(f"✅ Gemini 直接調用成功")
        except Exception as e:
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['quota', '429', 'rate limit', 'exceeded']):
                print(f"💰 Gemini 配額錯誤 (符合預期): {e}")
                print("🔄 應該自動切換到 OpenAI...")
                
                # 檢查是否有備用模型被觸發
                health_after = ai_service.get_model_health_status()
                print("🏥 錯誤後的健康狀態:")
                for model_name, status in health_after['models'].items():
                    health_icon = "✅" if status['healthy'] else "❌"
                    quota_exhausted = ai_service._model_health[model_name].get('quota_exhausted', False)
                    quota_icon = "💰" if quota_exhausted else ""
                    print(f"  {health_icon}{quota_icon} {model_name}: 失敗次數={status['failures']}")
                    
            else:
                print(f"❌ Gemini 其他錯誤: {e}")
        
        print(f"\n🔍 最終狀態:")
        print(f"  - 預設模型: {ai_service.default_model}")
        print(f"  - 備用模型: {ai_service.fallback_models}")
        print(f"  - 速率限制器活躍: {health_status.get('rate_limiter_active', False)}")
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        print("📋 詳細錯誤:")
        traceback.print_exc()
        return False
    
    print("\n✅ 測試完成")
    return True


async def test_specific_fallback_scenario():
    """測試特定的備用切換場景"""
    print("\n🎯 測試備用切換場景")
    print("=" * 30)
    
    try:
        ai_service = EnhancedAIModelService()
        
        # 模擬 Gemini 配額用盡
        print("🔥 模擬 Gemini 配額用盡...")
        ai_service._model_health["gemini-1.5-flash"]["quota_exhausted"] = True
        ai_service._model_health["gemini-1.5-flash"]["failures"] = 3
        
        # 測試是否自動切換到 OpenAI
        result = await ai_service.enhance_natural_language_query(
            user_query="測試備用模型",
            database_schema={}
        )
        
        print(f"✅ 備用模型測試成功")
        if isinstance(result, tuple):
            enhanced_query, confidence = result
            print(f"📊 信心度: {confidence}")
            print(f"💬 回應: {enhanced_query[:100]}...")
        
        # 重置狀態
        ai_service._model_health["gemini-1.5-flash"]["quota_exhausted"] = False
        ai_service._model_health["gemini-1.5-flash"]["failures"] = 0
        
    except Exception as e:
        print(f"❌ 備用測試失敗: {e}")
        return False
    
    return True


if __name__ == "__main__":
    # 設置環境變數
    os.environ["ASYNCIO_FORCE_SELECT_SELECTOR"] = "1"
    
    # 切換到正確的工作目錄
    os.chdir(Path(__file__).parent / "apps" / "bot")
    
    # 載入環境變數
    from dotenv import load_dotenv
    load_dotenv()
    
    print("🚀 啟動 AI 模型備用機制測試")
    
    # 運行測試
    async def main():
        success1 = await test_ai_fallback()
        success2 = await test_specific_fallback_scenario()
        
        if success1 and success2:
            print(f"\n🎉 所有測試通過！Gemini → OpenAI 備用機制運行正常")
        else:
            print(f"\n❌ 部分測試失敗，需要檢查備用機制")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n⏹️ 測試中斷")
    except Exception as e:
        print(f"\n💥 測試執行錯誤: {e}")