#!/usr/bin/env python3
"""
調試腳本：測試 AI 解析器對「CNC車床今天不良率」查詢的實際處理過程

此腳本用於調試和分析 AI 解析器的行為，特別是：
1. 系統提示詞是否正確發揮作用
2. AI 服務的原始回應內容
3. 解析後的 ParsedQuery 對象詳細信息
4. 信心度計算和 UNKNOWN 判斷邏輯

運行方式：
cd apps/bot && python ../../debug_ai_parser.py
"""

import asyncio
import json
import sys
import os
from typing import Any, Dict

# 確保能夠導入專案模組
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps', 'bot', 'src'))

def print_separator(title: str):
    """打印分隔線"""
    print("=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)

def print_subsection(title: str):
    """打印子節標題"""
    print(f"\n{'─' * 40}")
    print(f"🔍 {title}")
    print('─' * 40)

async def test_ai_parser_debug():
    """測試 AI 解析器的完整調試流程"""
    
    try:
        # 1. 導入必要的模組
        print_separator("步驟 1: 導入系統模組")
        
        from infrastructure.enhanced_service_factory import EnhancedServiceFactory
        from services.nl_to_sql.parsers.ai_enhanced_parser import AIEnhancedParser
        from domain.entities.parsed_query import ParsedQuery, QueryType
        
        print("✅ 成功導入核心模組")
        
        # 2. 初始化服務工廠和 AI 解析器
        print_separator("步驟 2: 初始化服務")
        
        service_factory = EnhancedServiceFactory()
        ai_model_service = service_factory.get_ai_model_service()
        
        if not ai_model_service:
            print("❌ 無法獲取 AI 模型服務，請檢查配置")
            return
        
        parser = AIEnhancedParser(ai_model_service)
        print("✅ AI 解析器初始化完成")
        
        # 3. 顯示系統提示詞
        print_separator("步驟 3: 系統提示詞分析")
        
        system_prompt = parser._system_prompt
        print("📝 系統提示詞內容：")
        print(system_prompt)
        
        # 檢查關鍵字是否存在
        print_subsection("關鍵字檢查")
        keywords_to_check = ["不良率", "品質指標", "< 0.5", "unknown"]
        for keyword in keywords_to_check:
            if keyword in system_prompt:
                print(f"✅ 找到關鍵字: '{keyword}'")
            else:
                print(f"❌ 未找到關鍵字: '{keyword}'")
        
        # 4. 測試查詢
        print_separator("步驟 4: 執行查詢測試")
        
        test_query = "CNC車床今天不良率"
        print(f"🔍 測試查詢: '{test_query}'")
        
        # 4.1 調用 AI 服務查看原始回應
        print_subsection("AI 服務原始回應")
        
        try:
            # 直接調用 AI 服務來查看原始回應
            raw_response, raw_confidence = await ai_model_service.query_with_custom_prompt(
                test_query, system_prompt
            )
            
            print(f"🤖 AI 原始回應:")
            print(f"內容: {raw_response}")
            print(f"原始信心度: {raw_confidence}")
            
            # 嘗試解析為 JSON
            if raw_response.strip().startswith('{') and raw_response.strip().endswith('}'):
                try:
                    parsed_json = json.loads(raw_response)
                    print(f"📊 解析後的 JSON 結構:")
                    for key, value in parsed_json.items():
                        print(f"  {key}: {value}")
                except json.JSONDecodeError as e:
                    print(f"❌ JSON 解析失敗: {e}")
            
        except Exception as e:
            print(f"❌ AI 服務調用失敗: {e}")
            return
        
        # 4.2 完整解析流程
        print_subsection("完整解析流程")
        
        try:
            parsed_result = await parser.parse(test_query)
            
            print(f"📋 解析結果詳細信息:")
            print(f"  查詢類型: {parsed_result.query_type}")
            print(f"  查詢類型值: {parsed_result.query_type.value}")
            print(f"  SQL 查詢: {parsed_result.sql_query}")
            print(f"  參數: {parsed_result.parameters}")
            print(f"  信心度: {parsed_result.confidence}")
            print(f"  解釋: {parsed_result.explanation}")
            
            # 驗證結果是否符合預期
            print_subsection("結果驗證")
            
            if parsed_result.query_type == QueryType.UNKNOWN:
                print("✅ 正確識別為 UNKNOWN 查詢類型")
            else:
                print(f"⚠️  查詢類型不是 UNKNOWN，而是: {parsed_result.query_type.value}")
            
            if parsed_result.confidence < 0.5:
                print(f"✅ 信心度正確 (< 0.5): {parsed_result.confidence}")
            else:
                print(f"⚠️  信心度過高 (>= 0.5): {parsed_result.confidence}")
            
            if "不良率" in parsed_result.explanation or "品質" in parsed_result.explanation:
                print("✅ 解釋中正確提到品質相關概念")
            else:
                print("⚠️  解釋中未明確提及品質相關概念")
            
        except Exception as e:
            print(f"❌ 解析過程出錯: {e}")
            import traceback
            traceback.print_exc()
        
        # 5. 能力評估測試
        print_separator("步驟 5: 解析器能力評估")
        
        try:
            capability_score = parser.can_handle(test_query)
            print(f"🎯 解析器能力評估分數: {capability_score}")
            
            if capability_score > 0.5:
                print("✅ 解析器認為可以處理此查詢")
            else:
                print("❌ 解析器認為無法有效處理此查詢")
            
        except Exception as e:
            print(f"❌ 能力評估失敗: {e}")
        
        # 6. 額外測試其他相關查詢
        print_separator("步驟 6: 對比測試")
        
        comparison_queries = [
            "M001稼動率",  # 應該可以正常處理
            "CNC車床合格率",  # 也是品質指標，應該返回 UNKNOWN
            "M002今天生產統計",  # 正常的生產查詢
            "品質檢驗報告"  # 品質相關，應該 UNKNOWN
        ]
        
        for i, query in enumerate(comparison_queries, 1):
            print_subsection(f"對比測試 {i}: '{query}'")
            
            try:
                result = await parser.parse(query)
                print(f"  查詢類型: {result.query_type.value}")
                print(f"  信心度: {result.confidence}")
                print(f"  是否為 UNKNOWN: {'✅' if result.query_type == QueryType.UNKNOWN else '❌'}")
            except Exception as e:
                print(f"  ❌ 解析失敗: {e}")
        
        print_separator("調試完成")
        print("🎉 AI 解析器調試測試完成！")
        print("💡 請檢查上述輸出以診斷 AI 解析器的行為")
        
    except ImportError as e:
        print(f"❌ 模組導入失敗: {e}")
        print("💡 請確保在正確的目錄下運行此腳本：cd apps/bot && python ../../debug_ai_parser.py")
    except Exception as e:
        print(f"❌ 未預期的錯誤: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函數"""
    print_separator("AI 解析器調試腳本")
    print("🎯 目標：測試 AI 解析器對「CNC車床今天不良率」的處理")
    print("📍 測試範圍：系統提示詞、AI 原始回應、解析結果、信心度計算")
    print("")
    print("⚠️  注意：此腳本需要在 apps/bot 目錄下運行")
    print("   正確運行方式：cd apps/bot && python ../../debug_ai_parser.py")
    
    # 檢查運行目錄
    current_dir = os.getcwd()
    if not current_dir.endswith('apps/bot'):
        print(f"\n❌ 當前目錄不正確: {current_dir}")
        print("請先切換到正確目錄：cd apps/bot")
        sys.exit(1)
    
    try:
        asyncio.run(test_ai_parser_debug())
    except KeyboardInterrupt:
        print("\n\n⛔ 用戶中斷執行")
    except Exception as e:
        print(f"\n❌ 執行失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()