#!/usr/bin/env python3
"""
T-04 & T-05 測試腳本：驗證統計服務類型安全修復

測試項目：
1. 驗證字串與數值混合輸入的處理
2. 測試所有數值比較操作的類型安全
3. 驗證 _grade_performance 方法的錯誤處理
4. 測試 _analyze_trend_direction 的數值比較
5. 確保所有輸入驗證機制正常工作
"""

import sys
import os
from pathlib import Path

# 添加專案路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "apps" / "bot" / "src"))
sys.path.insert(0, str(project_root / "apps" / "bot"))

# 修正工作目錄
os.chdir(project_root / "apps" / "bot")

def test_type_safety_with_mixed_inputs():
    """測試混合類型輸入的安全處理"""
    print("🔍 測試混合類型輸入處理...")
    
    try:
        from src.services.nl_to_sql.services.query_statistics_service import QueryStatisticsService
        
        # 初始化統計服務
        stats_service = QueryStatisticsService()
        
        print("✅ 統計服務初始化成功")
        
        # 測試各種類型的混合輸入
        test_cases = [
            # (operation_type, duration, metadata)
            ("test_operation", "1.5", {"confidence": "0.9", "parser_type": "rule"}),  # 字串數值
            ("test_operation", 2.0, {"confidence": 0.8, "parser_type": "ai"}),       # 正常數值
            ("test_operation", "invalid", {"confidence": "invalid"}),                 # 無效字串
            ("test_operation", None, {"confidence": None}),                          # None 值
            ("test_operation", "", {"confidence": ""}),                              # 空字串
            ("test_operation", [], {"confidence": []}),                              # 錯誤類型
            ("test_operation", 3, {"confidence": 1}),                               # 整數
        ]
        
        success_count = 0
        for i, (op_type, duration, metadata) in enumerate(test_cases):
            try:
                print(f"\n🔧 測試案例 {i+1}: duration={duration} ({type(duration).__name__})")
                
                # 記錄成功操作
                stats_service.record_success(op_type, duration, metadata)
                
                print(f"✅ 案例 {i+1} 處理成功")
                success_count += 1
                
            except Exception as e:
                print(f"❌ 案例 {i+1} 失敗: {str(e)}")
        
        print(f"\n📊 混合輸入測試結果: {success_count}/{len(test_cases)} 成功")
        
        # 測試獲取統計資料（這會觸發數值比較）
        try:
            stats = stats_service.get_stats()
            print("✅ 統計資料獲取成功")
            print(f"   總請求數: {stats['summary']['total_requests']}")
            print(f"   成功率: {stats['summary']['success_rate']}")
            return True
        except Exception as e:
            print(f"❌ 統計資料獲取失敗: {str(e)}")
            return False
            
    except Exception as e:
        print(f"❌ 混合輸入測試失敗: {str(e)}")
        return False

def test_grade_performance_type_safety():
    """測試 _grade_performance 方法的類型安全"""
    print("\n🔍 測試效能評級類型安全...")
    
    try:
        from src.services.nl_to_sql.services.query_statistics_service import QueryStatisticsService
        
        stats_service = QueryStatisticsService()
        
        # 測試各種可能導致類型錯誤的輸入
        test_cases = [
            [],                                    # 空列表
            [1.0, 2.0, 3.0],                      # 正常浮點數
            ["1.5", "2.0", "3.5"],                # 字串數值
            [1, 2, 3],                            # 整數
            ["invalid", "data"],                  # 無效字串
            [None, 1.0, None],                    # 含 None 值
            ["", 1.0, ""],                        # 含空字串
            [float('inf'), 1.0, float('-inf')],   # 無限值
        ]
        
        success_count = 0
        for i, parse_times in enumerate(test_cases):
            try:
                print(f"\n🔧 測試效能評級案例 {i+1}: {parse_times}")
                
                # 直接測試 _grade_performance 方法
                grade = stats_service._grade_performance(parse_times)
                
                print(f"✅ 案例 {i+1} 評級: {grade}")
                success_count += 1
                
            except Exception as e:
                print(f"❌ 案例 {i+1} 失敗: {str(e)}")
        
        print(f"\n📊 效能評級測試結果: {success_count}/{len(test_cases)} 成功")
        return success_count == len(test_cases)
        
    except Exception as e:
        print(f"❌ 效能評級測試失敗: {str(e)}")
        return False

def test_trend_analysis_type_safety():
    """測試趨勢分析的類型安全"""
    print("\n🔍 測試趨勢分析類型安全...")
    
    try:
        from src.services.nl_to_sql.services.query_statistics_service import QueryStatisticsService
        import time
        
        stats_service = QueryStatisticsService()
        
        # 創建測試記錄
        records = []
        current_time = time.time()
        
        # 添加一些成功和失敗記錄
        for i in range(20):
            record = {
                "timestamp": current_time - (i * 3600),  # 每小時一個記錄
                "result": "success" if i % 2 == 0 else "failure"
            }
            records.append(record)
        
        try:
            # 測試趨勢分析
            trend = stats_service._analyze_trend_direction(records)
            print(f"✅ 趨勢分析成功: {trend}")
            
            # 測試邊緣情況
            empty_records = []
            trend_empty = stats_service._analyze_trend_direction(empty_records)
            print(f"✅ 空記錄趨勢分析: {trend_empty}")
            
            # 測試少量記錄
            few_records = records[:5]
            trend_few = stats_service._analyze_trend_direction(few_records)
            print(f"✅ 少量記錄趨勢分析: {trend_few}")
            
            return True
            
        except Exception as e:
            print(f"❌ 趨勢分析失敗: {str(e)}")
            return False
            
    except Exception as e:
        print(f"❌ 趨勢分析測試失敗: {str(e)}")
        return False

def test_comprehensive_statistics():
    """測試完整統計功能的類型安全"""
    print("\n🔍 測試完整統計功能...")
    
    try:
        from src.services.nl_to_sql.services.query_statistics_service import QueryStatisticsService
        
        stats_service = QueryStatisticsService()
        
        # 添加多種類型的記錄
        test_data = [
            ("rule_parser", "1.5", {"confidence": "0.9"}),
            ("ai_parser", 2.0, {"confidence": 0.8}),
            ("composite_parser", "invalid", {"confidence": "invalid"}),  # 無效數據
        ]
        
        for parser, duration, metadata in test_data:
            try:
                stats_service.record_success(parser, duration, metadata)
            except:
                pass  # 忽略個別記錄的錯誤
        
        # 添加一些失敗記錄
        for i in range(3):
            try:
                stats_service.record_failure(
                    "test_parser", 
                    "type_error", 
                    f"測試錯誤 {i}",
                    {"duration": str(i * 0.5)}  # 字串 duration
                )
            except:
                pass
        
        # 測試所有統計方法
        tests = [
            ("get_stats", lambda: stats_service.get_stats()),
            ("get_parser_performance", lambda: stats_service.get_parser_performance("rule_parser")),
            ("get_recent_activity", lambda: stats_service.get_recent_activity(24)),
            ("export_statistics", lambda: stats_service.export_statistics("dict")),
        ]
        
        success_count = 0
        for test_name, test_func in tests:
            try:
                result = test_func()
                print(f"✅ {test_name} 成功")
                success_count += 1
            except Exception as e:
                print(f"❌ {test_name} 失敗: {str(e)}")
        
        print(f"\n📊 完整統計測試結果: {success_count}/{len(tests)} 成功")
        return success_count == len(tests)
        
    except Exception as e:
        print(f"❌ 完整統計測試失敗: {str(e)}")
        return False

def main():
    """主測試函數"""
    print("🚀 開始 T-04 & T-05 統計服務類型安全測試\n")
    
    tests = [
        ("混合類型輸入處理", test_type_safety_with_mixed_inputs),
        ("效能評級類型安全", test_grade_performance_type_safety),
        ("趨勢分析類型安全", test_trend_analysis_type_safety),
        ("完整統計功能", test_comprehensive_statistics),
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
    print("📊 T-04 & T-05 測試結果總結")
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
        print("🎉 所有測試通過！T-04 & T-05 修復成功！")
        return 0
    else:
        print("💥 部分測試失敗，需要進一步修復")
        return 1

if __name__ == "__main__":
    exit(main())