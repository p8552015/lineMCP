#!/usr/bin/env python3
"""
空查詢防護機制測試腳本
驗證 T-04 空查詢防護機制的實施效果
"""

import asyncio
import sys
import os

# 添加路徑
bot_src_path = os.path.join(os.path.dirname(__file__), 'apps/bot/src')
sys.path.insert(0, bot_src_path)
os.chdir(os.path.join(os.path.dirname(__file__), 'apps/bot'))

async def test_empty_query_protection():
    """測試空查詢防護機制"""
    print("🛡️ 空查詢防護機制測試開始...")
    
    try:
        # 導入必要的模組
        from services.nl_to_sql_service import NaturalLanguageToSQLService
        from services.ai_model_service import AIModelService
        from infrastructure.enhanced_service_factory import get_enhanced_service_factory
        
        # 初始化服務
        factory = get_enhanced_service_factory()
        factory.initialize()
        
        ai_service = factory.get_ai_service()
        nl_service = NaturalLanguageToSQLService(ai_service)
        
        # 測試案例
        test_cases = [
            ("", "空字串"),
            ("   ", "只有空白"),
            ("a", "過短輸入"),
            ("DROP TABLE users", "惡意輸入"),
            ("M001機台", "正常查詢"),
            ("查看所有機台", "正常查詢"),
            ("機台狀況如何？", "正常查詢"),
        ]
        
        print("\n📋 測試案例執行:")
        results = []
        
        for i, (query, description) in enumerate(test_cases, 1):
            print(f"\n{i}. 測試: {description}")
            print(f"   輸入: '{query}'")
            
            try:
                result = await nl_service.parse_natural_language(query)
                
                # 檢查結果
                is_safe = True
                if result.query_type.value != "UNKNOWN" and (not result.sql_query or not result.sql_query.strip()):
                    is_safe = False
                    print(f"   ❌ 防護失敗: 返回了空 SQL！")
                else:
                    print(f"   ✅ 防護成功")
                
                print(f"   結果: type={result.query_type.value}, confidence={result.confidence:.2f}")
                print(f"   SQL長度: {len(result.sql_query) if result.sql_query else 0}")
                
                if result.explanation:
                    print(f"   說明: {result.explanation[:100]}...")
                
                results.append({
                    "query": query,
                    "description": description,
                    "safe": is_safe,
                    "query_type": result.query_type.value,
                    "sql_length": len(result.sql_query) if result.sql_query else 0,
                    "confidence": result.confidence
                })
                
            except Exception as e:
                print(f"   ❌ 測試異常: {e}")
                results.append({
                    "query": query,
                    "description": description,
                    "safe": False,
                    "error": str(e)
                })
        
        # 統計結果
        print(f"\n📊 測試結果統計:")
        total_tests = len(results)
        safe_tests = sum(1 for r in results if r.get("safe", False))
        
        print(f"   總測試數: {total_tests}")
        print(f"   安全通過: {safe_tests}")
        print(f"   成功率: {safe_tests/total_tests*100:.1f}%")
        
        # 驗證關鍵指標
        critical_passed = True
        
        # 檢查空輸入防護
        empty_tests = [r for r in results if r["query"] in ["", "   ", "a"]]
        for test in empty_tests:
            if test.get("query_type") != "UNKNOWN":
                print(f"   ⚠️ 警告: 空輸入 '{test['query']}' 未被正確攔截")
                critical_passed = False
        
        # 檢查惡意輸入防護
        malicious_tests = [r for r in results if "DROP TABLE" in r["query"]]
        for test in malicious_tests:
            if test.get("query_type") != "UNKNOWN":
                print(f"   🚨 嚴重: 惡意輸入 '{test['query']}' 未被攔截！")
                critical_passed = False
        
        # 檢查正常輸入處理
        normal_tests = [r for r in results if r["description"] == "正常查詢"]
        normal_processed = sum(1 for t in normal_tests if t.get("query_type") != "UNKNOWN")
        
        print(f"\n🎯 關鍵指標:")
        print(f"   空輸入防護: {'✅ 通過' if all(r.get('query_type') == 'UNKNOWN' for r in empty_tests) else '❌ 失敗'}")
        print(f"   惡意輸入防護: {'✅ 通過' if all(r.get('query_type') == 'UNKNOWN' for r in malicious_tests) else '❌ 失敗'}")
        print(f"   正常查詢處理: {normal_processed}/{len(normal_tests)} 個處理成功")
        print(f"   整體評估: {'✅ 防護機制有效' if critical_passed else '❌ 防護機制需要改進'}")
        
        return critical_passed
        
    except Exception as e:
        print(f"❌ 測試初始化失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_empty_query_protection())
    sys.exit(0 if success else 1)