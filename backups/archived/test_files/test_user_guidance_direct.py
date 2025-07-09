#!/usr/bin/env python3
"""
直接測試 generate_user_guidance 方法
驗證是否返回自然的用戶指導而非技術性描述
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent / "apps" / "bot"))

from dotenv import load_dotenv
from src.infrastructure.enhanced_service_factory import get_enhanced_service_factory


async def test_user_guidance_direct():
    """直接測試 generate_user_guidance 方法"""
    print("🧪 測試 generate_user_guidance 方法")
    print("=" * 50)
    
    try:
        # 獲取 AI 服務
        factory = get_enhanced_service_factory()
        factory.initialize()
        ai_service = factory.get_ai_model_service()
        
        print(f"✅ AI 服務類型: {type(ai_service).__name__}")
        print(f"✅ 預設模型: {ai_service.default_model}")
        
        # 測試查詢
        user_input = "CNC車床今天不良率"
        
        # 構建測試提示詞（模擬 _build_intelligent_prompt 的輸出）
        guidance_prompt = f"""
用戶詢問「{user_input}」，但系統目前不支援品質指標的直接查詢。

請協助解釋：
1. 為什麼無法直接查詢不良率數據
2. 建議替代的查詢方式（如機台狀態、產量統計等）
3. 提供2-3個相關的可查詢範例

語氣要專業友善，幫助用戶理解系統功能範圍。
"""
        
        print(f"\n🎯 測試查詢: '{user_input}'")
        print("🔄 調用 generate_user_guidance...")
        
        # 直接調用新方法
        result = await ai_service.generate_user_guidance(
            user_input=user_input,
            guidance_prompt=guidance_prompt
        )
        
        if isinstance(result, tuple):
            response, confidence = result
            print(f"✅ 成功獲得回應")
            print(f"📊 信心度: {confidence}")
            print(f"💬 回應內容:")
            print("-" * 40)
            print(response)
            print("-" * 40)
            
            # 檢查是否為自然指導
            is_natural = any(keyword in response for keyword in [
                "很抱歉", "目前", "建議", "可以", "您", "請", "幫助", "無法",
                "不支援", "功能", "範圍", "理解", "查詢", "資訊"
            ])
            
            is_technical = any(keyword in response for keyword in [
                "查詢CNC車床", "包含不良品", "總生產數量", "涉及的表格"
            ])
            
            if is_natural and not is_technical:
                print("✅ 回應為自然友善的用戶指導")
            elif is_technical:
                print("❌ 回應為技術性描述，需要修復")
            else:
                print("⚠️ 回應性質不明確")
                
        else:
            print(f"⚠️ 異常回應格式: {type(result)}")
            print(f"📝 內容: {result}")
    
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


async def test_old_method_comparison():
    """比較舊方法的輸出"""
    print("\n🔄 比較測試：舊方法 vs 新方法")
    print("=" * 50)
    
    try:
        factory = get_enhanced_service_factory()
        factory.initialize()
        ai_service = factory.get_ai_model_service()
        
        user_input = "CNC車床今天不良率"
        database_schema = {}
        
        print("📝 測試舊方法 enhance_natural_language_query:")
        old_result = await ai_service.enhance_natural_language_query(
            user_query=user_input,
            database_schema=database_schema
        )
        
        if isinstance(old_result, tuple):
            old_response, old_confidence = old_result
            print(f"舊方法回應: {old_response}")
            print(f"舊方法信心度: {old_confidence}")
        
        print("\n" + "="*30)
        print("📝 對比：新舊方法的差異")
        print("- 舊方法用於 SQL 增強（技術性）")
        print("- 新方法用於用戶指導（友善性）")
        print("- 預期：新方法應該更自然友善")
        
    except Exception as e:
        print(f"比較測試失敗: {e}")


if __name__ == "__main__":
    # 設置環境
    os.environ["ASYNCIO_FORCE_SELECT_SELECTOR"] = "1"
    os.chdir(Path(__file__).parent / "apps" / "bot")
    load_dotenv()
    
    print("🚀 啟動用戶指導直接測試")
    
    async def main():
        success1 = await test_user_guidance_direct()
        await test_old_method_comparison()
        
        if success1:
            print(f"\n🎉 直接測試完成！")
        else:
            print(f"\n❌ 測試失敗，需要進一步修復")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n⏹️ 測試中斷")
    except Exception as e:
        print(f"\n💥 測試執行錯誤: {e}")