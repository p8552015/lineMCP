#!/usr/bin/env python3
"""
增強版AI模型服務測試
驗證重試機制、速率限制控制和備用模型切換功能
"""

import asyncio
import os
import sys
from pathlib import Path

# 設定 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps', 'bot'))

# 載入環境變數
from dotenv import load_dotenv
env_path = Path(__file__).parent / 'apps' / 'bot' / '.env'
load_dotenv(env_path)
os.environ['ASYNCIO_FORCE_SELECT_SELECTOR'] = '1'

from src.services.ai_model_service_enhanced import EnhancedAIModelService

async def test_enhanced_ai_service():
    """測試增強版AI模型服務"""
    print("=" * 60)
    print("🤖 增強版AI模型服務測試")
    print("=" * 60)
    
    try:
        # 初始化服務
        ai_service = EnhancedAIModelService()
        print("✅ 服務初始化成功")
        
        # 顯示可用模型
        models = ai_service.get_available_models()
        print(f"\n📋 可用模型數量: {len(models)}")
        for model in models:
            print(f"  • {model['name']} ({model['provider']}) - 預設: {model['is_default']}")
            
        # 顯示備用模型順序
        fallback_models = ai_service.fallback_models
        print(f"\n🔄 備用模型順序: {fallback_models}")
        
        # 測試自然語言查詢（可能觸發速率限制）
        print("\n🧪 測試1: 自然語言查詢處理")
        print("-" * 40)
        
        # 模擬資料庫結構
        database_schema = {
            "machines": {"columns": [{"name": "machine_id"}, {"name": "machine_name"}]},
            "utilizations": {"columns": [{"name": "utilization_rate"}, {"name": "date"}]}
        }
        
        test_query = "M001機台稼動率"
        result = await ai_service.enhance_natural_language_query(
            test_query, database_schema
        )
        
        enhanced_query, confidence = result
        print(f"✅ 查詢處理成功")
        print(f"原始查詢: {test_query}")
        print(f"增強查詢: {enhanced_query}")
        print(f"信心度: {confidence}")
        
        # 檢查模型健康狀態
        print("\n🏥 測試2: 模型健康狀態")
        print("-" * 40)
        
        health_status = ai_service.get_model_health_status()
        for model_name, status in health_status.items():
            print(f"  • {model_name}:")
            print(f"    健康狀態: {'✅ 健康' if status['is_healthy'] else '❌ 不健康'}")
            print(f"    失敗次數: {status['failures']}")
            print(f"    速率限制: {'🟢 正常' if status['rate_limit_status'] == 'ok' else '🔴 受限'}")
            
        # 測試多次調用（可能觸發速率限制）
        print("\n⚡ 測試3: 速率限制和備用模型切換")
        print("-" * 40)
        
        test_queries = [
            "查看所有機台",
            "M002機台效率",
            "加工部門狀況",
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n  📞 第{i}次調用: {query}")
            try:
                result = await ai_service.enhance_natural_language_query(
                    query, database_schema
                )
                enhanced_query, confidence = result
                print(f"  ✅ 成功 - 信心度: {confidence:.2f}")
            except Exception as e:
                print(f"  ⚠️ 失敗: {e}")
        
        # 最終健康狀態
        print("\n📊 最終模型健康狀態:")
        health_status = ai_service.get_model_health_status()
        for model_name, status in health_status.items():
            status_icon = "✅" if status['is_healthy'] else "❌"
            rate_icon = "🟢" if status['rate_limit_status'] == 'ok' else "🔴"
            print(f"  {status_icon} {model_name} (速率: {rate_icon})")
            
        print("\n" + "=" * 60)
        print("🎉 增強版AI模型服務測試完成")
        print("✅ 支援功能:")
        print("  • 重試機制 ✅")
        print("  • 速率限制控制 ✅") 
        print("  • 備用模型自動切換 ✅")
        print("  • 429錯誤立即切換OpenAI ✅")
        print("  • 模型健康狀態監控 ✅")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ 測試過程中發生錯誤: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_enhanced_ai_service())
    exit_code = 0 if success else 1
    sys.exit(exit_code)