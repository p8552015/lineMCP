#!/usr/bin/env python3
"""
製造業詞彙庫智能解譯系統測試腳本
演示如何從「M001機台稼動率」等查詢中提取多個欄位資料
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加專案路徑
project_root = Path(__file__).parent
sys.path.append(str(project_root / "apps" / "bot" / "src"))

try:
    from services.nl_to_sql.services.intelligent_vocabulary_interpreter import (
        IntelligentVocabularyInterpreter,
        VocabularyEntry
    )
except ImportError as e:
    print(f"❌ 導入錯誤：{e}")
    print("請確認您在專案根目錄下執行此腳本")
    sys.exit(1)


class VocabularyTestSuite:
    """詞彙庫測試套件"""
    
    def __init__(self):
        config_path = project_root / "apps" / "bot" / "src" / "services" / "nl_to_sql" / "config" / "manufacturing_vocabulary_database.yaml"
        if not config_path.exists():
            print(f"❌ 配置檔案不存在：{config_path}")
            print("請先確認詞彙庫檔案已正確建立")
            sys.exit(1)
            
        self.interpreter = IntelligentVocabularyInterpreter(str(config_path))
        self.test_results = []
    
    async def run_comprehensive_tests(self):
        """執行綜合測試"""
        print("🔍 製造業詞彙庫智能解譯系統測試")
        print("=" * 60)
        
        # 1. 系統狀態檢查
        await self.test_system_status()
        
        # 2. 單欄位提取測試
        await self.test_single_field_extraction()
        
        # 3. 多欄位提取測試
        await self.test_multi_field_extraction()
        
        # 4. 複雜查詢測試
        await self.test_complex_queries()
        
        # 5. 邊界情況測試
        await self.test_edge_cases()
        
        # 6. 效能測試
        await self.test_performance()
        
        # 顯示測試總結
        self.display_test_summary()
    
    async def test_system_status(self):
        """測試系統狀態"""
        print("\n📊 系統狀態檢查")
        print("-" * 30)
        
        try:
            stats = self.interpreter.get_interpretation_statistics()
            print(f"✅ 詞彙庫載入成功")
            print(f"   總詞彙數：{stats['total_vocabulary_entries']}")
            print(f"   模式數量：{stats['pattern_count']}")
            print(f"   資料庫版本：{stats['database_version']}")
            
            for category, count in stats['entries_by_type'].items():
                print(f"   {category}: {count} 個詞彙")
                
            self.test_results.append(("系統狀態", True, "系統正常載入"))
            
        except Exception as e:
            print(f"❌ 系統狀態檢查失敗：{e}")
            self.test_results.append(("系統狀態", False, str(e)))
    
    async def test_single_field_extraction(self):
        """測試單一欄位提取"""
        print("\n🎯 單一欄位提取測試")
        print("-" * 30)
        
        test_cases = [
            {
                "query": "M001",
                "expected_field": "machine_id",
                "expected_value": "M001",
                "description": "機台編號識別"
            },
            {
                "query": "稼動率",
                "expected_field": "metric_type",
                "expected_value": "utilization_rate",
                "description": "指標類型識別"
            },
            {
                "query": "今天",
                "expected_field": "time_period",
                "expected_value": "today",
                "description": "時間範圍識別"
            },
            {
                "query": "生產部門",
                "expected_field": "department",
                "expected_value": "production",
                "description": "部門識別"
            }
        ]
        
        for case in test_cases:
            try:
                result = await self.interpreter.interpret_query(case["query"])
                extracted_value = getattr(result.extracted_fields, case["expected_field"])
                
                if extracted_value == case["expected_value"]:
                    print(f"✅ {case['description']}：{case['query']} → {extracted_value}")
                    self.test_results.append((case["description"], True, f"正確識別：{extracted_value}"))
                else:
                    print(f"❌ {case['description']}：{case['query']} → {extracted_value} (期望：{case['expected_value']})")
                    self.test_results.append((case["description"], False, f"識別錯誤：{extracted_value}"))
                    
            except Exception as e:
                print(f"❌ {case['description']} 測試失敗：{e}")
                self.test_results.append((case["description"], False, str(e)))
    
    async def test_multi_field_extraction(self):
        """測試多欄位提取（核心功能）"""
        print("\n🎯 多欄位提取測試（核心功能）")
        print("-" * 30)
        
        test_cases = [
            {
                "query": "M001機台稼動率",
                "expected": {
                    "machine_id": "M001",
                    "metric_type": "utilization_rate"
                },
                "description": "機台+指標組合"
            },
            {
                "query": "生產部門本週的OEE指標",
                "expected": {
                    "department": "production",
                    "time_period": "weekly",
                    "metric_type": "oee"
                },
                "description": "部門+時間+指標組合"
            },
            {
                "query": "CNC車床今天不良率",
                "expected": {
                    "machine_type": "CNC_LATHE",
                    "time_period": "today",
                    "metric_type": "defect_rate"
                },
                "description": "機台類型+時間+指標組合"
            },
            {
                "query": "M002銑床即時產量數據",
                "expected": {
                    "machine_id": "M002",
                    "machine_type": "MILLING_MACHINE",
                    "time_period": "real_time",
                    "metric_type": "throughput"
                },
                "description": "複合多欄位查詢"
            }
        ]
        
        for case in test_cases:
            try:
                result = await self.interpreter.interpret_query(case["query"])
                
                print(f"\n查詢：「{case['query']}」")
                print(f"描述：{case['description']}")
                
                success_count = 0
                total_fields = len(case["expected"])
                
                for field_name, expected_value in case["expected"].items():
                    extracted_value = getattr(result.extracted_fields, field_name)
                    
                    if extracted_value == expected_value:
                        print(f"  ✅ {field_name}: {extracted_value}")
                        success_count += 1
                    else:
                        print(f"  ❌ {field_name}: {extracted_value} (期望: {expected_value})")
                
                # 額外顯示的欄位
                additional_fields = ['time_period', 'department', 'shift_type']
                for field in additional_fields:
                    if field not in case["expected"]:
                        value = getattr(result.extracted_fields, field)
                        if value:
                            print(f"  📋 {field}: {value}")
                
                accuracy = success_count / total_fields
                print(f"  信心度: {result.confidence:.2f}")
                print(f"  準確率: {accuracy:.2f} ({success_count}/{total_fields})")
                print(f"  解譯方法: {result.interpretation_method}")
                print(f"  處理時間: {result.processing_time_ms:.1f}ms")
                
                if accuracy >= 0.8:
                    self.test_results.append((case["description"], True, f"準確率 {accuracy:.2f}"))
                else:
                    self.test_results.append((case["description"], False, f"準確率過低 {accuracy:.2f}"))
                    
            except Exception as e:
                print(f"❌ {case['description']} 測試失敗：{e}")
                self.test_results.append((case["description"], False, str(e)))
    
    async def test_complex_queries(self):
        """測試複雜查詢"""
        print("\n🧠 複雜查詢測試")
        print("-" * 30)
        
        complex_queries = [
            "請查詢M001機台在早班的稼動率數據",
            "我想看生產線A今天的整體設備效率",
            "品質部門負責的所有設備本月不良率統計",
            "晚班時段CNC車床的產量表現如何",
            "M002銑床上週的維修記錄和稼動率關聯分析"
        ]
        
        for query in complex_queries:
            try:
                result = await self.interpreter.interpret_query(query)
                
                print(f"\n查詢：「{query}」")
                print(f"  機台: {result.extracted_fields.machine_id or '未識別'}")
                print(f"  指標: {result.extracted_fields.metric_type or '未識別'}")
                print(f"  時間: {result.extracted_fields.time_period or '未識別'}")
                print(f"  部門: {result.extracted_fields.department or '未識別'}")
                print(f"  班次: {result.extracted_fields.shift_type or '未識別'}")
                print(f"  信心度: {result.confidence:.2f}")
                
                if result.confidence >= 0.6:
                    print(f"  狀態: ✅ 解譯成功")
                    self.test_results.append((f"複雜查詢: {query[:20]}...", True, f"信心度 {result.confidence:.2f}"))
                else:
                    print(f"  狀態: ⚠️ 解譯準確度待改善")
                    self.test_results.append((f"複雜查詢: {query[:20]}...", False, f"信心度過低 {result.confidence:.2f}"))
                    
            except Exception as e:
                print(f"❌ 複雜查詢測試失敗：{e}")
                self.test_results.append(("複雜查詢", False, str(e)))
    
    async def test_edge_cases(self):
        """測試邊界情況"""
        print("\n⚠️ 邊界情況測試")
        print("-" * 30)
        
        edge_cases = [
            "",  # 空查詢
            "abcdefg",  # 無意義查詢
            "M999機台",  # 不存在的機台
            "稼動率M001",  # 順序顛倒
            "M001 M002 稼動率",  # 多機台
            "今天昨天明天",  # 多時間
        ]
        
        for query in edge_cases:
            try:
                result = await self.interpreter.interpret_query(query)
                
                print(f"查詢：「{query}」→ 信心度: {result.confidence:.2f}")
                
                # 邊界情況應該有低信心度或適當的錯誤處理
                if result.confidence < 0.5 or result.error_message:
                    print(f"  ✅ 正確處理邊界情況")
                    self.test_results.append((f"邊界情況: {query}", True, "正確處理"))
                else:
                    print(f"  ⚠️ 可能誤判")
                    self.test_results.append((f"邊界情況: {query}", False, "可能誤判"))
                    
            except Exception as e:
                print(f"查詢：「{query}」→ 錯誤: {e}")
                # 對於邊界情況，適當的錯誤處理也是正確的
                self.test_results.append((f"邊界情況: {query}", True, "適當錯誤處理"))
    
    async def test_performance(self):
        """測試效能"""
        print("\n⚡ 效能測試")
        print("-" * 30)
        
        test_query = "M001機台稼動率"
        iteration_count = 10
        
        try:
            total_time = 0
            
            for i in range(iteration_count):
                result = await self.interpreter.interpret_query(test_query)
                total_time += result.processing_time_ms
            
            average_time = total_time / iteration_count
            
            print(f"測試查詢: {test_query}")
            print(f"測試次數: {iteration_count}")
            print(f"平均處理時間: {average_time:.1f}ms")
            print(f"總處理時間: {total_time:.1f}ms")
            
            if average_time < 1000:  # 1秒內
                print("✅ 效能表現良好")
                self.test_results.append(("效能測試", True, f"平均 {average_time:.1f}ms"))
            else:
                print("⚠️ 效能可能需要優化")
                self.test_results.append(("效能測試", False, f"平均 {average_time:.1f}ms 過慢"))
                
        except Exception as e:
            print(f"❌ 效能測試失敗：{e}")
            self.test_results.append(("效能測試", False, str(e)))
    
    def display_test_summary(self):
        """顯示測試總結"""
        print("\n" + "=" * 60)
        print("📋 測試結果總結")
        print("=" * 60)
        
        passed = sum(1 for _, success, _ in self.test_results if success)
        total = len(self.test_results)
        success_rate = (passed / total) * 100 if total > 0 else 0
        
        print(f"總測試數: {total}")
        print(f"通過測試: {passed}")
        print(f"失敗測試: {total - passed}")
        print(f"成功率: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("🎉 系統表現優秀！")
        elif success_rate >= 60:
            print("👍 系統表現良好，有改善空間")
        else:
            print("⚠️ 系統需要重大改善")
        
        print("\n詳細結果:")
        for test_name, success, message in self.test_results:
            status = "✅" if success else "❌"
            print(f"  {status} {test_name}: {message}")
        
        print("\n💡 改善建議:")
        if success_rate < 100:
            print("1. 檢查失敗的測試案例，調整詞彙庫配置")
            print("2. 增加更多同義詞和提取模式")
            print("3. 調整信心度權重設定")
            print("4. 優化複雜查詢的解譯邏輯")


async def main():
    """主函數"""
    print("🚀 啟動製造業詞彙庫智能解譯系統測試")
    
    try:
        test_suite = VocabularyTestSuite()
        await test_suite.run_comprehensive_tests()
        
    except KeyboardInterrupt:
        print("\n\n⛔ 測試被使用者中斷")
    except Exception as e:
        print(f"\n\n❌ 測試執行失敗：{e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())