#!/usr/bin/env python3
"""
測試查詢分類修復
"""

import asyncio
import sys
import os

# 添加項目根目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps/bot'))

from src.services.nl_to_sql.parsers.ai_enhanced_parser import AIEnhancedParser


class MockAIService:
    """模擬 AI 服務"""
    
    async def query_with_custom_prompt(self, text: str, prompt: str):
        """模擬 AI 查詢"""
        text_lower = text.lower()
        
        if "m001" in text_lower and "稼動率" in text_lower:
            # M001機台稼動率 - 應該返回 specific_machine
            return (
                '{"query_type": "specific_machine", "entities": ["M001", "稼動率"], '
                '"parameters": {"machine_id": "M001", "metric": "utilization_rate"}, "confidence": 0.9}',
                0.9
            )
        elif "品質部門" in text_lower and "m002" in text_lower:
            # 品質部門M002銑床即時產量 - 應該返回 unknown
            return (
                '{"query_type": "unknown", "entities": ["品質部門", "M002", "產量"], '
                '"parameters": {}, "confidence": 0.3}',
                0.3
            )
        else:
            return (
                '{"query_type": "unknown", "entities": [], "parameters": {}, "confidence": 0.1}',
                0.1
            )


async def test_query_classification():
    """測試查詢分類修復"""
    print("🧪 測試查詢分類修復")
    print("=" * 50)
    
    # 創建解析器
    ai_service = MockAIService()
    parser = AIEnhancedParser(ai_service)
    
    # 測試案例
    test_cases = [
        {
            "query": "M001機台稼動率",
            "expected": "SPECIFIC_MACHINE",
            "description": "應該返回機台資料"
        },
        {
            "query": "品質部門M002銑床即時產量", 
            "expected": "UNKNOWN",
            "description": "應該觸發 LLM 指導"
        },
        {
            "query": "CNC車床今天不良率",
            "expected": "UNKNOWN", 
            "description": "品質指標，應該觸發 LLM 指導"
        },
        {
            "query": "M003機台狀態",
            "expected": "SPECIFIC_MACHINE",
            "description": "有效機台查詢"
        }
    ]
    
    results = []
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n📝 測試 {i}: {case['query']}")
        print(f"   預期: {case['expected']} - {case['description']}")
        
        try:
            # 執行解析
            result = await parser.parse(case["query"])
            
            actual_type = result.query_type.value.upper()
            expected_type = case["expected"]
            
            is_correct = actual_type == expected_type
            status = "✅ 通過" if is_correct else "❌ 失敗"
            
            print(f"   實際: {actual_type}")
            print(f"   信心度: {result.confidence:.2f}")
            print(f"   結果: {status}")
            
            results.append({
                "query": case["query"],
                "expected": expected_type,
                "actual": actual_type,
                "correct": is_correct,
                "confidence": result.confidence
            })
            
        except Exception as e:
            print(f"   ❌ 錯誤: {str(e)}")
            results.append({
                "query": case["query"],
                "expected": case["expected"],
                "actual": "ERROR",
                "correct": False,
                "confidence": 0.0
            })
    
    # 總結
    print("\n" + "=" * 50)
    print("📊 測試總結")
    print("=" * 50)
    
    correct_count = sum(1 for r in results if r["correct"])
    total_count = len(results)
    success_rate = correct_count / total_count * 100
    
    print(f"總測試數: {total_count}")
    print(f"通過數: {correct_count}")
    print(f"成功率: {success_rate:.1f}%")
    
    if success_rate == 100:
        print("🎉 所有測試通過！查詢分類邏輯修復成功")
    else:
        print("⚠️ 部分測試失敗，需要進一步調整")
        
        # 顯示失敗的測試
        print("\n❌ 失敗的測試:")
        for r in results:
            if not r["correct"]:
                print(f"  - {r['query']}: 預期 {r['expected']}, 實際 {r['actual']}")
    
    return success_rate == 100


if __name__ == "__main__":
    asyncio.run(test_query_classification())