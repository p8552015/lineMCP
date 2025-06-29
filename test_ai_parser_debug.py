#!/usr/bin/env python3
"""
測試 AI 解析器對品質查詢的處理
"""
import asyncio
import sys
import os

# 添加路徑
sys.path.append(os.path.join(os.path.dirname(__file__), 'apps', 'bot', 'src'))

from infrastructure.enhanced_service_factory import get_enhanced_service_factory
from services.nl_to_sql.parsers.ai_enhanced_parser import AIEnhancedParser
from services.ai_model_service import AIModelService

async def test_ai_parser_directly():
    """直接測試 AI 解析器"""
    print("🔍 直接測試 AI 解析器行為")
    print("=" * 50)
    
    try:
        # 獲取服務工廠
        factory = get_enhanced_service_factory()
        factory.initialize()
        
        # 獲取 AI 模型服務
        ai_service = factory.get_ai_model_service()
        
        # 直接創建 AI 解析器
        ai_parser = AIEnhancedParser(ai_service)
        
        # 測試查詢
        test_queries = [
            "M001機台稼動率",
            "CNC車床今天不良率", 
            "品質部門檢驗數據",
            "所有機台狀況"
        ]
        
        for query in test_queries:
            print(f"\n📝 測試：{query}")
            print("-" * 30)
            
            try:
                result = await ai_parser.parse(query, None)
                print(f"查詢類型: {result.query_type.value}")
                print(f"信心度: {result.confidence}")
                print(f"說明: {result.explanation}")
                print(f"參數: {result.parameters}")
                
                # 檢查是否符合我們的期望
                if query == "CNC車床今天不良率":
                    if result.query_type.value == "unknown":
                        print("✅ 正確識別為 UNKNOWN 類型")
                    else:
                        print(f"❌ 應該是 UNKNOWN，但識別為 {result.query_type.value}")
                        
            except Exception as e:
                print(f"❌ 解析失敗: {str(e)}")
        
    except Exception as e:
        print(f"❌ 初始化失敗: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ai_parser_directly())