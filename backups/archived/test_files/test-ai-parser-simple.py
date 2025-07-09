#!/usr/bin/env python3
"""
簡化版 AI 解析器測試腳本

專門測試「CNC車床今天不良率」查詢的處理流程
運行方式：cd apps/bot && python ../../test-ai-parser-simple.py
"""

import asyncio
import sys
import os

# 確保能夠導入專案模組
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps', 'bot', 'src'))

async def simple_test():
    """簡化的測試流程"""
    print("🔬 AI 解析器測試 - 「CNC車床今天不良率」")
    print("=" * 60)
    
    try:
        # 導入模組
        from infrastructure.enhanced_service_factory import EnhancedServiceFactory
        from services.nl_to_sql.parsers.ai_enhanced_parser import AIEnhancedParser
        from domain.entities.parsed_query import QueryType
        
        print("✅ 模組導入成功")
        
        # 初始化服務
        service_factory = EnhancedServiceFactory()
        ai_service = service_factory.get_ai_model_service()
        parser = AIEnhancedParser(ai_service)
        
        print("✅ 服務初始化完成")
        
        # 顯示系統提示詞的關鍵部分
        print("\n📝 系統提示詞關鍵部分:")
        prompt = parser._system_prompt
        if "不良率" in prompt:
            print("✅ 系統提示詞包含「不良率」處理指導")
        if "< 0.5" in prompt:
            print("✅ 系統提示詞包含低信心度指導")
        if "unknown" in prompt:
            print("✅ 系統提示詞包含 unknown 類型指導")
        
        # 測試查詢
        test_query = "CNC車床今天不良率"
        print(f"\n🔍 測試查詢: '{test_query}'")
        
        # 調用 AI 服務獲取原始回應
        print("\n1️⃣ AI 服務原始回應:")
        raw_response, raw_confidence = await ai_service.query_with_custom_prompt(
            test_query, prompt
        )
        print(f"回應內容: {raw_response}")
        print(f"原始信心度: {raw_confidence}")
        
        # 完整解析流程
        print("\n2️⃣ 完整解析結果:")
        result = await parser.parse(test_query)
        
        print(f"查詢類型: {result.query_type.value}")
        print(f"最終信心度: {result.confidence}")
        print(f"解釋: {result.explanation}")
        
        # 驗證結果
        print("\n3️⃣ 結果驗證:")
        if result.query_type == QueryType.UNKNOWN:
            print("✅ 正確識別為 UNKNOWN")
        else:
            print(f"❌ 意外的查詢類型: {result.query_type.value}")
        
        if result.confidence < 0.5:
            print(f"✅ 正確的低信心度: {result.confidence}")
        else:
            print(f"⚠️ 信心度較高: {result.confidence}")
        
        print("\n🎉 測試完成！")
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 檢查執行目錄
    if not os.getcwd().endswith('apps/bot'):
        print("❌ 請在 apps/bot 目錄下執行此腳本")
        print("正確方式: cd apps/bot && python ../../test-ai-parser-simple.py")
        sys.exit(1)
    
    asyncio.run(simple_test())