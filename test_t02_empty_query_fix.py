#!/usr/bin/env python3
"""
T-02 測試腳本：驗證空查詢問題修復

測試項目：
1. 確保所有查詢類型都能成功建構 SQL
2. 驗證建構的 SQL 不為空
3. 測試模板載入失敗時的錯誤處理
4. 驗證預設模板載入機制
"""

import sys
import os
import logging
from pathlib import Path

# 添加專案路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "apps" / "bot" / "src"))
sys.path.insert(0, str(project_root / "apps" / "bot"))

# 修正工作目錄
os.chdir(project_root / "apps" / "bot")

# 設置詳細日誌
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_query_construction():
    """測試查詢建構功能"""
    print("🔍 測試查詢建構功能...")
    
    try:
        from services.nl_to_sql.builders.sql_query_builder import SQLQueryBuilder
        from services.nl_to_sql.builders.query_template_manager import QueryTemplateManager
        from services.nl_to_sql.services.configuration_service import ConfigurationService
        from services.nl_to_sql.models.query_models import QueryType
        
        # 初始化配置服務
        config_service = ConfigurationService()
        
        # 初始化模板管理器
        template_manager = QueryTemplateManager(config_service)
        
        # 初始化查詢建構器
        query_builder = SQLQueryBuilder(template_manager)
        
        print("✅ 服務初始化成功")
        
        # 測試所有查詢類型
        test_cases = [
            (QueryType.ALL_MACHINES, {}),
            (QueryType.SPECIFIC_MACHINE, {"machine_id": "M001"}),
            (QueryType.DEPARTMENT_STATUS, {"department": "加工部"}),
            (QueryType.FAULT_ANALYSIS, {"days": 30}),
            (QueryType.PRODUCTION_STATS, {}),
            (QueryType.MACHINE_STATUS, {}),
        ]
        
        successful_queries = 0
        failed_queries = []
        
        for query_type, parameters in test_cases:
            try:
                print(f"\n🔧 測試查詢類型: {query_type.value}")
                print(f"   參數: {parameters}")
                
                # 建構查詢
                sql_query = query_builder.build_query(query_type, parameters)
                
                # 驗證查詢不為空
                if not sql_query or not sql_query.strip():
                    raise ValueError("建構的 SQL 查詢為空")
                
                # 驗證查詢內容
                if len(sql_query.strip()) < 10:
                    raise ValueError("建構的 SQL 查詢過短，疑似無效")
                
                if not sql_query.upper().strip().startswith("SELECT"):
                    raise ValueError("建構的 SQL 查詢不是以 SELECT 開始")
                
                print(f"✅ 查詢建構成功")
                print(f"   SQL 長度: {len(sql_query)}")
                print(f"   SQL 預覽: {sql_query[:100]}...")
                
                successful_queries += 1
                
            except Exception as e:
                print(f"❌ 查詢建構失敗: {str(e)}")
                failed_queries.append((query_type.value, str(e)))
        
        # 結果統計
        print(f"\n📊 測試結果統計:")
        print(f"   總測試數: {len(test_cases)}")
        print(f"   成功數: {successful_queries}")
        print(f"   失敗數: {len(failed_queries)}")
        
        if failed_queries:
            print(f"\n❌ 失敗的查詢:")
            for query_type, error in failed_queries:
                print(f"   - {query_type}: {error}")
            return False
        else:
            print(f"\n✅ 所有查詢測試通過！")
            return True
            
    except Exception as e:
        print(f"❌ 測試過程中發生嚴重錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_template_validation():
    """測試模板驗證功能"""
    print("\n🔍 測試模板驗證功能...")
    
    try:
        from services.nl_to_sql.builders.query_template_manager import QueryTemplateManager
        from services.nl_to_sql.services.configuration_service import ConfigurationService
        
        # 初始化
        config_service = ConfigurationService()
        template_manager = QueryTemplateManager(config_service)
        
        # 驗證所有模板
        validation_result = template_manager.validate_all_templates()
        
        print(f"📋 模板驗證結果:")
        print(f"   總模板數: {validation_result['summary']['total_templates']}")
        print(f"   有效模板數: {validation_result['summary']['valid_count']}")
        print(f"   無效模板數: {validation_result['summary']['invalid_count']}")
        print(f"   MCP 相容模板數: {validation_result['summary']['mcp_compatible_count']}")
        print(f"   整體有效: {validation_result['summary']['overall_valid']}")
        print(f"   MCP 就緒: {validation_result['summary']['mcp_ready']}")
        
        if validation_result['summary']['overall_valid'] and validation_result['summary']['mcp_ready']:
            print("✅ 所有模板驗證通過！")
            return True
        else:
            print("❌ 模板驗證發現問題")
            if validation_result['errors']:
                print("錯誤:")
                for error in validation_result['errors'][:5]:  # 顯示前5個錯誤
                    print(f"   - {error}")
            return False
            
    except Exception as e:
        print(f"❌ 模板驗證測試失敗: {str(e)}")
        return False

def test_empty_query_prevention():
    """測試空查詢防護機制"""
    print("\n🔍 測試空查詢防護機制...")
    
    try:
        from services.nl_to_sql.builders.query_template_manager import QueryTemplateManager
        from services.nl_to_sql.services.configuration_service import ConfigurationService
        from services.nl_to_sql.models.query_models import QueryType
        
        # 初始化
        config_service = ConfigurationService()
        template_manager = QueryTemplateManager(config_service)
        
        # 測試無效模板處理
        try:
            # 嘗試設置空模板
            template_manager.set_template(QueryType.ALL_MACHINES, "")
            print("❌ 空模板設置應該失敗但成功了")
            return False
        except ValueError:
            print("✅ 空模板正確被拒絕")
        
        # 測試無效模板處理
        try:
            # 嘗試設置無效模板
            template_manager.set_template(QueryType.ALL_MACHINES, "DROP TABLE users;")
            print("❌ 危險模板設置應該失敗但成功了")
            return False
        except ValueError:
            print("✅ 危險模板正確被拒絕")
        
        print("✅ 空查詢防護機制測試通過！")
        return True
        
    except Exception as e:
        print(f"❌ 空查詢防護測試失敗: {str(e)}")
        return False

def main():
    """主測試函數"""
    print("🚀 開始 T-02 空查詢修復測試\n")
    
    tests = [
        ("查詢建構功能", test_query_construction),
        ("模板驗證功能", test_template_validation),
        ("空查詢防護機制", test_empty_query_prevention),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"執行測試: {test_name}")
        print('='*50)
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ 測試 {test_name} 發生異常: {str(e)}")
            results.append((test_name, False))
    
    # 總結
    print(f"\n{'='*50}")
    print("📊 T-02 測試結果總結")
    print('='*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n總計: {passed}/{total} 測試通過")
    
    if passed == total:
        print("🎉 所有測試通過！T-02 修復成功！")
        return 0
    else:
        print("💥 部分測試失敗，需要進一步修復")
        return 1

if __name__ == "__main__":
    exit(main())