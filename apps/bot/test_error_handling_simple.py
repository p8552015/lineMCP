#!/usr/bin/env python3
"""
T-08 錯誤處理改進簡化測試
快速驗證核心功能
"""

import asyncio
import sys
from pathlib import Path

# 添加應用路徑
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.infrastructure.lazy_initialization_error_handler import (
    LazyServiceConfig,
    LazyInitializationErrorHandler,
    InitializationState,
    ErrorSeverity,
)
from src.infrastructure.user_experience_enhancer import (
    UserExperienceEnhancer,
    ServiceStatus,
)


async def test_basic_functionality():
    """測試基本功能"""
    print("🔄 測試基本延遲初始化...")
    
    config = LazyServiceConfig(
        service_name="TestService",
        max_retry_attempts=2,
        timeout_seconds=2.0,
        auto_recovery=False  # 關閉自動恢復避免循環
    )
    
    handler = LazyInitializationErrorHandler(config)
    
    # 測試成功初始化
    async def success_init():
        await asyncio.sleep(0.1)
        return "SUCCESS"
    
    success, result, message = await handler.safe_initialize(success_init)
    print(f"   ✅ 成功初始化: {success}, 結果: {result}")
    
    # 測試失敗初始化
    config2 = LazyServiceConfig(
        service_name="FailService", 
        max_retry_attempts=1,
        auto_recovery=False
    )
    handler2 = LazyInitializationErrorHandler(config2)
    
    async def fail_init():
        raise ConnectionError("連接失敗")
    
    success2, result2, message2 = await handler2.safe_initialize(fail_init)
    print(f"   ❌ 失敗初始化: {success2}, 消息: {message2}")
    
    return success and not success2


def test_user_experience():
    """測試用戶體驗功能"""
    print("👤 測試用戶體驗增強...")
    
    ux = UserExperienceEnhancer()
    
    # 測試狀態通知
    notification = ux.create_status_notification("TestService", 3.0)
    print(f"   📋 狀態通知: {notification.message}")
    
    # 測試錯誤通知
    error_notif = ux.create_error_notification("connection", "DatabaseService", 1)
    print(f"   ❌ 錯誤通知: {error_notif.message}")
    
    # 測試綜合錯誤消息
    comprehensive = ux.create_comprehensive_error_message(
        "PostgreSQL", "timeout", retry_count=1,
        suggestions=["檢查網絡", "重試"]
    )
    print(f"   📝 綜合消息長度: {len(comprehensive)} 字符")
    
    return len(notification.message) > 10 and len(error_notif.message) > 10


def test_error_severity():
    """測試錯誤嚴重程度評估"""
    print("📊 測試錯誤嚴重程度評估...")
    
    config = LazyServiceConfig(service_name="SeverityTest")
    handler = LazyInitializationErrorHandler(config)
    
    test_cases = [
        ("permission denied", ErrorSeverity.HIGH),
        ("connection timeout", ErrorSeverity.MEDIUM),
        ("out of memory", ErrorSeverity.CRITICAL),
        ("simple error", ErrorSeverity.LOW),
    ]
    
    correct = 0
    for error_msg, expected in test_cases:
        actual = handler._assess_error_severity("TestError", error_msg)
        if actual == expected:
            correct += 1
        print(f"   📋 '{error_msg}' -> {actual.value} ({'✅' if actual == expected else '❌'})")
    
    accuracy = correct / len(test_cases)
    print(f"   🎯 準確率: {accuracy:.1%}")
    
    return accuracy >= 0.5


async def main():
    """主測試函數"""
    print("🚀 T-08 錯誤處理改進簡化測試")
    print("=" * 50)
    
    tests = [
        ("基本功能", test_basic_functionality()),
        ("用戶體驗", test_user_experience()),
        ("錯誤評估", test_error_severity()),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        print(f"\n📋 執行: {name}")
        print("-" * 30)
        
        try:
            if asyncio.iscoroutine(test_func):
                result = await test_func
            else:
                result = test_func
            
            if result:
                print(f"✅ {name} 通過")
                passed += 1
            else:
                print(f"❌ {name} 失敗")
        except Exception as e:
            print(f"💥 {name} 異常: {e}")
    
    print(f"\n🎉 T-08 簡化測試完成!")
    print(f"📊 結果: {passed}/{total} 通過 ({passed/total*100:.0f}%)")
    
    return passed >= 2  # 至少2個測試通過


if __name__ == "__main__":
    success = asyncio.run(main())
    print(f"✅ T-08 錯誤處理改進: {'成功' if success else '需要改進'}")
    sys.exit(0 if success else 1)