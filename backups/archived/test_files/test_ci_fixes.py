#!/usr/bin/env python3
"""
CI修復驗證腳本
測試增強版AI模型服務是否能通過基本導入和初始化測試
"""

import os
import sys
from pathlib import Path

# 設定 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps', 'bot'))

# 載入環境變數
from dotenv import load_dotenv
env_path = Path(__file__).parent / 'apps' / 'bot' / '.env'
load_dotenv(env_path)

def test_enhanced_ai_service_import():
    """測試增強版AI模型服務導入"""
    print("🧪 測試1: 增強版AI模型服務導入")
    try:
        from src.services.ai_model_service_enhanced import EnhancedAIModelService
        print("✅ 增強版AI模型服務導入成功")
        return True
    except ImportError as e:
        print(f"❌ 導入失敗: {e}")
        return False

def test_service_factory_import():
    """測試服務工廠導入"""
    print("\n🧪 測試2: 服務工廠導入")
    try:
        from src.infrastructure.enhanced_service_factory import EnhancedServiceFactory
        print("✅ 增強版服務工廠導入成功")
        return True
    except ImportError as e:
        print(f"❌ 導入失敗: {e}")
        return False

def test_service_registration():
    """測試服務註冊"""
    print("\n🧪 測試3: 服務註冊測試")
    try:
        from src.infrastructure.enhanced_service_factory import EnhancedServiceFactory
        from src.services.ai_model_service_enhanced import EnhancedAIModelService
        
        factory = EnhancedServiceFactory()
        factory.initialize()
        
        ai_service = factory.get_service(EnhancedAIModelService)
        if ai_service is not None:
            print("✅ 增強版AI模型服務註冊和獲取成功")
            return True
        else:
            print("❌ 服務獲取失敗")
            return False
            
    except Exception as e:
        print(f"❌ 服務註冊測試失敗: {e}")
        return False

def test_basic_functionality():
    """測試基本功能"""
    print("\n🧪 測試4: 基本功能測試")
    try:
        from src.services.ai_model_service_enhanced import EnhancedAIModelService
        
        ai_service = EnhancedAIModelService()
        models = ai_service.get_available_models()
        health = ai_service.get_model_health_status()
        
        print(f"✅ 可用模型數量: {len(models)}")
        print(f"✅ 健康狀態跟蹤: {len(health)} 個模型")
        return True
        
    except Exception as e:
        print(f"❌ 基本功能測試失敗: {e}")
        return False

def test_compatibility():
    """測試向後兼容性"""
    print("\n🧪 測試5: 向後兼容性測試")
    try:
        from src.infrastructure.enhanced_service_factory import EnhancedServiceFactory
        
        factory = EnhancedServiceFactory()
        factory.initialize()
        
        # 測試舊的方法名稱仍然可用
        ai_service = factory.get_ai_model_service()
        assert ai_service is not None
        
        print("✅ 向後兼容性測試通過")
        return True
        
    except Exception as e:
        print(f"❌ 向後兼容性測試失敗: {e}")
        return False

def main():
    """運行所有測試"""
    print("=" * 60)
    print("🔧 LINE MCP Bot CI修復驗證")
    print("=" * 60)
    
    tests = [
        test_enhanced_ai_service_import,
        test_service_factory_import,
        test_service_registration,
        test_basic_functionality,
        test_compatibility
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 60)
    print("📊 測試結果總結")
    print("=" * 60)
    print(f"通過: {passed}/{total}")
    
    if passed == total:
        print("🎉 所有CI修復驗證測試通過！")
        print("✅ T-04任務相關修復完成")
        print("✅ 增強版AI模型服務整合成功")
        print("✅ GitHub Actions應該能正常運行")
        return True
    else:
        print("❌ 部分測試失敗，需要進一步修復")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)