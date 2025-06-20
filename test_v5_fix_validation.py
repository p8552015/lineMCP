#!/usr/bin/env python3
"""
v5 修復驗證腳本
測試空查詢問題和 AI 解析器修復
"""

import sys
import os
import asyncio
from pathlib import Path

# 添加專案路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "apps" / "bot" / "src"))
sys.path.insert(0, str(project_root / "apps" / "bot"))
os.chdir(project_root / "apps" / "bot")

async def test_ai_parser_fix():
    """測試 AI 解析器修復"""
    print("🔍 測試 AI 解析器修復...")
    
    try:
        from src.services.ai_model_service import AIModelService
        from src.services.nl_to_sql.parsers.ai_enhanced_parser import AIEnhancedParser
        from src.services.nl_to_sql.models.query_models import QueryType
        
        # 初始化服務
        ai_service = AIModelService()
        ai_parser = AIEnhancedParser(ai_service)
        
        print("✅ AI 解析器初始化成功")
        
        # 測試查詢
        test_queries = [
            "近期故障記錄",
            "所有機台狀態", 
            "M001機台狀況",
            "生產統計報告"
        ]
        
        for query in test_queries:
            try:
                print(f"\n🔧 測試查詢: {query}")
                
                # 測試解析
                result = await ai_parser.parse(query, {})
                
                print(f"   查詢類型: {result.query_type.value}")
                print(f"   信心度: {result.confidence}")
                print(f"   SQL 狀態: {'有' if result.sql_query else '無'}")
                print(f"   說明: {result.explanation}")
                
                # 驗證不是 UNKNOWN 類型
                if result.query_type == QueryType.UNKNOWN:
                    print(f"   ⚠️ 查詢類型仍為 UNKNOWN")
                else:
                    print(f"   ✅ 查詢類型識別成功")
                    
            except Exception as e:
                print(f"   ❌ 查詢失敗: {e}")
        
        print(f"\n🎉 AI 解析器測試完成")
        return True
        
    except Exception as e:
        print(f"❌ AI 解析器測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_full_nl_service():
    """測試完整 NL-to-SQL 服務"""
    print("\n🔍 測試完整 NL-to-SQL 服務...")
    
    try:
        from src.services.ai_model_service import AIModelService
        from src.services.nl_to_sql_service import NaturalLanguageToSQLService
        
        # 初始化服務
        ai_service = AIModelService()
        nl_service = NaturalLanguageToSQLService(ai_service)
        
        print("✅ NL-to-SQL 服務初始化成功")
        
        # 重點測試之前失敗的查詢
        test_queries = [
            "近期故障記錄",  # 這個之前失敗了
            "所有機台",
            "M001狀況",
            "生產報告"
        ]
        
        for query in test_queries:
            try:
                print(f"\n🔧 測試查詢: {query}")
                
                result = await nl_service.parse_natural_language(query)
                
                print(f"   查詢類型: {result.query_type.value}")
                print(f"   信心度: {result.confidence}")
                print(f"   SQL 長度: {len(result.sql_query) if result.sql_query else 0}")
                
                # 🔥 關鍵檢查：確保無空查詢
                if not result.sql_query or not result.sql_query.strip():
                    print(f"   ❌ 發現空查詢問題！")
                    return False
                else:
                    print(f"   ✅ SQL 建構成功")
                    print(f"   SQL 預覽: {result.sql_query[:100]}...")
                    
            except Exception as e:
                print(f"   ❌ 查詢失敗: {e}")
                return False
        
        print(f"\n🎉 完整服務測試通過！")
        return True
        
    except Exception as e:
        print(f"❌ 完整服務測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主測試函數"""
    print("🚀 開始 v5 修復驗證測試\n")
    
    # 測試 AI 解析器修復
    ai_test = await test_ai_parser_fix()
    
    # 測試完整服務
    full_test = await test_full_nl_service()
    
    print(f"\n{'='*50}")
    print("📊 v5 修復驗證結果")
    print('='*50)
    print(f"✅ AI 解析器修復: {'通過' if ai_test else '失敗'}")
    print(f"✅ 完整服務測試: {'通過' if full_test else '失敗'}")
    
    if ai_test and full_test:
        print("\n🎉 v5 修復驗證完全通過！")
        return 0
    else:
        print("\n💥 v5 修復驗證失敗，需要進一步調查")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))