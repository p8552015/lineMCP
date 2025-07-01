#!/usr/bin/env python3
"""
測試品質查詢分類
"""

import asyncio
import sys
import os

# 添加項目根目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps/bot'))

from src.services.nl_to_sql_service import NaturalLanguageToSQLService
from src.services.ai_model_service import AIModelService


async def test_quality_queries():
    """測試品質相關查詢是否正確觸發 LLM 指導"""
    print("🧪 測試品質查詢分類")
    print("=" * 50)
    
    # 創建服務
    ai_service = AIModelService()
    nl_service = NaturalLanguageToSQLService(ai_service)
    
    # 品質相關查詢測試
    quality_queries = [
        "品質部門M002銑床即時產量",
        "CNC車床今天不良率", 
        "品管部機台檢驗數據",
        "M003機台合格率統計",
        "品質指標分析報告"
    ]
    
    print("測試品質相關查詢（應該返回 UNKNOWN 並觸發 LLM 指導）:")
    
    for i, query in enumerate(quality_queries, 1):
        print(f"\n📝 測試 {i}: {query}")
        
        try:
            result = await nl_service.parse_natural_language(query)
            
            print(f"   查詢類型: {result.query_type.value}")
            print(f"   信心度: {result.confidence:.2f}")
            print(f"   有SQL: {'是' if result.sql_query.strip() else '否'}")
            print(f"   說明: {result.explanation[:100]}...")
            
            # 檢查是否正確分類為 UNKNOWN（應該觸發 LLM 指導）
            if result.query_type.value == "unknown":
                print("   ✅ 正確：返回 UNKNOWN，將觸發 LLM 指導")
            else:
                print(f"   ❌ 錯誤：應該返回 UNKNOWN，實際返回 {result.query_type.value}")
                
        except Exception as e:
            print(f"   ❌ 錯誤: {str(e)}")
    
    # 對比測試：有效的機台查詢
    print(f"\n{'='*50}")
    print("對比測試：有效機台查詢（應該返回具體類型並生成 SQL）:")
    
    valid_queries = [
        "M001機台稼動率",
        "M002機台狀態", 
        "加工部機台概覽"
    ]
    
    for i, query in enumerate(valid_queries, 1):
        print(f"\n📝 對比 {i}: {query}")
        
        try:
            result = await nl_service.parse_natural_language(query)
            
            print(f"   查詢類型: {result.query_type.value}")
            print(f"   信心度: {result.confidence:.2f}")
            print(f"   有SQL: {'是' if result.sql_query.strip() else '否'}")
            print(f"   SQL長度: {len(result.sql_query)} 字符")
            
            # 檢查是否正確分類為具體類型（不是 UNKNOWN）
            if result.query_type.value != "unknown" and result.sql_query.strip():
                print("   ✅ 正確：返回具體類型並生成 SQL")
            else:
                print(f"   ❌ 錯誤：應該返回具體類型，實際返回 {result.query_type.value}")
                
        except Exception as e:
            print(f"   ❌ 錯誤: {str(e)}")


if __name__ == "__main__":
    asyncio.run(test_quality_queries())