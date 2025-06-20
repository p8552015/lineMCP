#!/usr/bin/env python3
"""
測試當前修復狀態
驗證空查詢問題是否已解決
"""

import sys
import os
from pathlib import Path

# 添加專案路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "apps" / "bot" / "src"))
sys.path.insert(0, str(project_root / "apps" / "bot"))
os.chdir(project_root / "apps" / "bot")

async def test_nl_to_sql_service():
    """測試 NL-to-SQL 服務是否正常工作"""
    print("🔍 測試 NL-to-SQL 服務...")
    
    try:
        from src.services.ai_model_service import AIModelService
        from src.services.nl_to_sql_service import NaturalLanguageToSQLService
        from src.services.nl_to_sql.models.query_models import QueryType
        
        # 初始化服務
        ai_service = AIModelService()
        nl_sql_service = NaturalLanguageToSQLService(ai_service)
        
        print("✅ 服務初始化成功")
        
        # 測試自然語言查詢
        test_queries = [
            "顯示所有機台狀態",
            "查詢加工部的機台",
            "M001機台的效能資料",
        ]
        
        for i, query in enumerate(test_queries):
            try:
                print(f"\n🔧 測試查詢 {i+1}: {query}")
                
                # 解析自然語言
                result = await nl_sql_service.parse_natural_language(query)
                
                print(f"   查詢類型: {result.query_type.value}")
                print(f"   SQL 長度: {len(result.sql_query)}")
                print(f"   信心度: {result.confidence}")
                
                # 檢查是否為空查詢
                if not result.sql_query or not result.sql_query.strip():
                    print(f"❌ 空查詢問題仍然存在！")
                    return False
                else:
                    print(f"✅ SQL 建構成功: {result.sql_query[:50]}...")
                    
            except Exception as e:
                print(f"❌ 查詢 {i+1} 失敗: {str(e)}")
                return False
        
        print(f"\n🎉 所有測試通過！空查詢問題已解決！")
        return True
        
    except Exception as e:
        print(f"❌ 服務測試失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_direct_components():
    """測試直接組件是否工作正常"""
    print("\n🔍 測試直接組件...")
    
    try:
        from src.services.nl_to_sql.builders.sql_query_builder import SQLQueryBuilder
        from src.services.nl_to_sql.builders.query_template_manager import QueryTemplateManager
        from src.services.nl_to_sql.services.configuration_service import ConfigurationService
        from src.services.nl_to_sql.models.query_models import QueryType
        
        # 初始化組件
        config_service = ConfigurationService()
        template_manager = QueryTemplateManager(config_service)
        query_builder = SQLQueryBuilder(template_manager)
        
        print("✅ 組件初始化成功")
        
        # 測試查詢建構
        test_case = (QueryType.ALL_MACHINES, {})
        query_type, parameters = test_case
        
        sql_query = query_builder.build_query(query_type, parameters)
        
        print(f"   查詢類型: {query_type.value}")
        print(f"   參數: {parameters}")
        print(f"   SQL 長度: {len(sql_query)}")
        print(f"   SQL 預覽: {sql_query[:100]}...")
        
        if not sql_query or not sql_query.strip():
            print("❌ 直接組件仍產生空查詢！")
            return False
        else:
            print("✅ 直接組件工作正常！")
            return True
            
    except Exception as e:
        print(f"❌ 直接組件測試失敗: {str(e)}")
        return False

async def main():
    """主測試函數"""
    print("🚀 開始測試當前修復狀態\n")
    
    # 測試直接組件
    direct_test = test_direct_components()
    
    # 測試完整服務
    service_test = await test_nl_to_sql_service()
    
    print(f"\n{'='*50}")
    print("📊 修復狀態測試結果")
    print('='*50)
    print(f"✅ 直接組件: {'正常' if direct_test else '異常'}")
    print(f"✅ 完整服務: {'正常' if service_test else '異常'}")
    
    if direct_test and service_test:
        print("\n🎉 所有修復已生效！空查詢問題已解決！")
        return 0
    else:
        print("\n💥 修復未完全生效，需要進一步調查")
        return 1

if __name__ == "__main__":
    import asyncio
    exit(asyncio.run(main()))