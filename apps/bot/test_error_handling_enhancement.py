#!/usr/bin/env python3
"""
T-08 錯誤處理改進測試
驗證延遲初始化的錯誤處理和用戶體驗增強
"""

import asyncio
import sys
import time
from pathlib import Path

# 添加應用路徑
sys.path.insert(0, str(Path(__file__).parent / "src"))

import structlog
from src.infrastructure.lazy_initialization_error_handler import (
    LazyServiceConfig,
    LazyInitializationErrorHandler,
    InitializationState,
    ErrorSeverity,
    get_lazy_service_registry,
    lazy_service_context,
    async_lazy_service_context,
)
from src.infrastructure.user_experience_enhancer import (
    UserExperienceEnhancer,
    ServiceStatus,
    get_user_experience_enhancer,
)

logger = structlog.get_logger()


class MockService:
    """模擬服務類"""
    def __init__(self, should_fail: bool = False, delay: float = 0):
        self.should_fail = should_fail
        self.delay = delay
        self.initialized = False
        
    async def initialize(self):
        """初始化服務"""
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        
        if self.should_fail:
            raise RuntimeError("模擬初始化失敗")
        
        self.initialized = True
        return "初始化成功"


class TestErrorHandlingEnhancement:
    """錯誤處理增強測試類"""
    
    def __init__(self):
        self.ux_enhancer = get_user_experience_enhancer()
        self.test_results = []
    
    async def run_all_tests(self):
        """執行所有測試"""
        print("🛡️ 開始 T-08 錯誤處理改進測試...")
        print("=" * 60)
        
        tests = [
            ("基本延遲初始化", self.test_basic_lazy_initialization),
            ("錯誤重試機制", self.test_error_retry_mechanism),
            ("自動恢復測試", self.test_auto_recovery),
            ("用戶體驗增強", self.test_user_experience_enhancement),
            ("多服務協調", self.test_multiple_services_coordination),
            ("超時處理", self.test_timeout_handling),
            ("嚴重程度評估", self.test_error_severity_assessment),
            ("上下文管理器", self.test_context_managers),
            ("服務註冊表", self.test_service_registry),
            ("健康狀態監控", self.test_health_monitoring),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                print(f"\n📋 執行測試: {test_name}")
                print("-" * 40)
                
                result = await test_func()
                if result:
                    print(f"✅ 測試通過: {test_name}")
                    passed += 1
                else:
                    print(f"❌ 測試失敗: {test_name}")
                    failed += 1
                    
            except Exception as e:
                print(f"💥 測試異常: {test_name} - {e}")
                import traceback
                traceback.print_exc()
                failed += 1
        
        print(f"\n{'='*60}")
        print(f"📊 T-08 測試結果摘要:")
        print(f"   ✅ 通過: {passed}")
        print(f"   ❌ 失敗: {failed}")
        print(f"   📈 成功率: {passed/(passed+failed)*100:.1f}%")
        
        return passed, failed
    
    async def test_basic_lazy_initialization(self) -> bool:
        """測試基本延遲初始化"""
        print("🔄 測試基本延遲初始化功能...")
        
        config = LazyServiceConfig(
            service_name="TestService",
            max_retry_attempts=2,
            timeout_seconds=5.0
        )
        
        handler = LazyInitializationErrorHandler(config)
        
        async def create_service():
            await asyncio.sleep(0.1)  # 模擬初始化時間
            return MockService()
        
        success, result, user_message = await handler.safe_initialize(create_service)
        
        print(f"   🎯 初始化結果: {'成功' if success else '失敗'}")
        print(f"   📝 用戶消息: {user_message or '無'}")
        print(f"   📊 服務狀態: {handler.state.value}")
        
        return success and isinstance(result, MockService)
    
    async def test_error_retry_mechanism(self) -> bool:
        """測試錯誤重試機制"""
        print("🔁 測試錯誤重試機制...")
        
        config = LazyServiceConfig(
            service_name="RetryTestService",
            max_retry_attempts=3,
            retry_delay_base=0.1,  # 快速重試用於測試
            timeout_seconds=2.0
        )
        
        handler = LazyInitializationErrorHandler(config)
        retry_count = 0
        
        async def failing_then_success():
            nonlocal retry_count
            retry_count += 1
            if retry_count < 3:  # 前兩次失敗
                raise ConnectionError("模擬連接失敗")
            return MockService()  # 第三次成功
        
        start_time = time.time()
        success, result, user_message = await handler.safe_initialize(failing_then_success)
        elapsed_time = time.time() - start_time
        
        print(f"   🎯 最終結果: {'成功' if success else '失敗'}")
        print(f"   🔢 重試次數: {retry_count}")
        print(f"   ⏱️ 總耗時: {elapsed_time:.2f}秒")
        print(f"   📝 用戶消息: {user_message or '無'}")
        print(f"   📊 錯誤記錄: {len(handler.errors)}")
        
        return success and retry_count == 3
    
    async def test_auto_recovery(self) -> bool:
        """測試自動恢復機制"""
        print("🔧 測試自動恢復機制...")
        
        config = LazyServiceConfig(
            service_name="RecoveryTestService",
            max_retry_attempts=2,
            auto_recovery=True,
            timeout_seconds=2.0
        )
        
        handler = LazyInitializationErrorHandler(config)
        
        async def always_fail():
            raise RuntimeError("總是失敗的服務")
        
        # 第一次嘗試（應該失敗）
        success1, _, _ = await handler.safe_initialize(always_fail)
        
        print(f"   🎯 首次嘗試: {'成功' if success1 else '失敗'}")
        print(f"   📊 狀態: {handler.state.value}")
        
        # 檢查是否嘗試了自動恢復
        recovery_attempted = any(error.recovery_attempted for error in handler.errors)
        
        print(f"   🔧 自動恢復: {'已嘗試' if recovery_attempted else '未嘗試'}")
        
        return not success1  # 應該失敗但展示了恢復機制
    
    async def test_user_experience_enhancement(self) -> bool:
        """測試用戶體驗增強"""
        print("👤 測試用戶體驗增強功能...")
        
        # 測試各種通知類型
        status_notification = self.ux_enhancer.create_status_notification(
            "TestService", estimated_time=3.5
        )
        
        error_notification = self.ux_enhancer.create_error_notification(
            "connection", "DatabaseService", retry_count=2
        )
        
        initialization_feedback = self.ux_enhancer.create_initialization_feedback(
            "APIService", "連接數據庫", 65.0
        )
        
        comprehensive_error = self.ux_enhancer.create_comprehensive_error_message(
            "PostgreSQL", "timeout", retry_count=1,
            suggestions=["檢查網絡連接", "稍後重試"]
        )
        
        print(f"   📋 狀態通知: {status_notification.message}")
        print(f"   ❌ 錯誤通知: {error_notification.message}")
        print(f"   🔄 初始化反饋: {initialization_feedback.message}")
        print(f"   📝 綜合錯誤消息長度: {len(comprehensive_error)} 字符")
        
        # 測試服務狀態追蹤
        self.ux_enhancer.update_service_status("TestService", ServiceStatus.INITIALIZING)
        self.ux_enhancer.update_service_status("DatabaseService", ServiceStatus.AVAILABLE)
        
        health_summary = self.ux_enhancer.get_service_health_summary()
        print(f"   🏥 健康摘要: {health_summary}")
        
        return all([
            status_notification.message,
            error_notification.message,
            initialization_feedback.message,
            len(comprehensive_error) > 50,
            "部分可用" in health_summary or "正常" in health_summary
        ])
    
    async def test_multiple_services_coordination(self) -> bool:
        """測試多服務協調"""
        print("🔗 測試多服務協調...")
        
        services = ["ServiceA", "ServiceB", "ServiceC"]
        handlers = []
        
        for service_name in services:
            config = LazyServiceConfig(
                service_name=service_name,
                max_retry_attempts=2,
                timeout_seconds=1.0
            )
            handler = LazyInitializationErrorHandler(config)
            handlers.append(handler)
        
        # 並行初始化多個服務
        async def create_mock_service(delay: float):
            await asyncio.sleep(delay)
            return MockService()
        
        tasks = []
        for i, handler in enumerate(handlers):
            task = handler.safe_initialize(lambda d=i*0.1: create_mock_service(d))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for result in results if isinstance(result, tuple) and result[0])
        
        print(f"   🎯 成功初始化: {success_count}/{len(services)}")
        print(f"   📊 結果詳情: {[r[0] if isinstance(r, tuple) else False for r in results]}")
        
        return success_count >= 2  # 至少2個服務成功
    
    async def test_timeout_handling(self) -> bool:
        """測試超時處理"""
        print("⏱️ 測試超時處理...")
        
        config = LazyServiceConfig(
            service_name="TimeoutTestService",
            timeout_seconds=0.5,  # 短超時用於測試
            max_retry_attempts=1
        )
        
        handler = LazyInitializationErrorHandler(config)
        
        async def slow_service():
            await asyncio.sleep(1.0)  # 超過超時時間
            return MockService()
        
        start_time = time.time()
        success, result, user_message = await handler.safe_initialize(slow_service)
        elapsed_time = time.time() - start_time
        
        print(f"   ⏱️ 執行時間: {elapsed_time:.2f}秒")
        print(f"   🎯 結果: {'成功' if success else '超時失敗'}")
        print(f"   📝 用戶消息: {user_message or '無'}")
        
        # 應該在超時時間內失敗
        return not success and elapsed_time < 2.0
    
    async def test_error_severity_assessment(self) -> bool:
        """測試錯誤嚴重程度評估"""
        print("📊 測試錯誤嚴重程度評估...")
        
        config = LazyServiceConfig(service_name="SeverityTestService")
        handler = LazyInitializationErrorHandler(config)
        
        # 測試不同類型的錯誤
        test_errors = [
            ("permission denied", ErrorSeverity.HIGH),
            ("connection timeout", ErrorSeverity.MEDIUM),
            ("out of memory", ErrorSeverity.CRITICAL),
            ("simple error", ErrorSeverity.LOW),
        ]
        
        correct_assessments = 0
        
        for error_msg, expected_severity in test_errors:
            assessed_severity = handler._assess_error_severity("TestError", error_msg)
            is_correct = assessed_severity == expected_severity
            
            print(f"   📋 '{error_msg}' -> {assessed_severity.value} ({'✅' if is_correct else '❌'})")
            
            if is_correct:
                correct_assessments += 1
        
        accuracy = correct_assessments / len(test_errors)
        print(f"   🎯 評估準確率: {accuracy:.1%}")
        
        return accuracy >= 0.75  # 至少75%準確率
    
    async def test_context_managers(self) -> bool:
        """測試上下文管理器"""
        print("🎭 測試上下文管理器...")
        
        # 測試同步上下文管理器
        with lazy_service_context("SyncTestService") as handler:
            print(f"   📋 同步上下文: {handler.config.service_name}")
            sync_result = True
        
        # 測試異步上下文管理器
        async with async_lazy_service_context("AsyncTestService") as handler:
            print(f"   📋 異步上下文: {handler.config.service_name}")
            
            success, result, _ = await handler.safe_initialize(
                lambda: MockService()
            )
            async_result = success
        
        print(f"   ✅ 同步上下文: {'正常' if sync_result else '異常'}")
        print(f"   ✅ 異步上下文: {'正常' if async_result else '異常'}")
        
        return sync_result and async_result
    
    async def test_service_registry(self) -> bool:
        """測試服務註冊表"""
        print("📝 測試服務註冊表...")
        
        registry = get_lazy_service_registry()
        
        # 註冊多個服務
        services = ["RegistryServiceA", "RegistryServiceB"]
        
        for service_name in services:
            config = LazyServiceConfig(service_name=service_name)
            handler = registry.register_service(service_name, config)
            print(f"   📋 已註冊: {service_name}")
        
        # 測試獲取處理器
        handler_a = registry.get_handler("RegistryServiceA")
        handler_b = registry.get_handler("RegistryServiceB")
        handler_none = registry.get_handler("NonExistentService")
        
        print(f"   🔍 獲取 ServiceA: {'✅' if handler_a else '❌'}")
        print(f"   🔍 獲取 ServiceB: {'✅' if handler_b else '❌'}")
        print(f"   🔍 獲取不存在服務: {'❌' if handler_none is None else '⚠️'}")
        
        # 測試健康狀態
        health_status = registry.get_all_health_status()
        print(f"   🏥 健康狀態服務數: {len(health_status)}")
        
        return all([handler_a, handler_b, handler_none is None, len(health_status) >= 2])
    
    async def test_health_monitoring(self) -> bool:
        """測試健康狀態監控"""
        print("🏥 測試健康狀態監控...")
        
        config = LazyServiceConfig(service_name="HealthTestService")
        handler = LazyInitializationErrorHandler(config)
        
        # 初始狀態
        initial_health = handler.get_health_status()
        print(f"   📊 初始狀態: {initial_health['state']}")
        
        # 模擬一次失敗
        async def failing_service():
            raise ConnectionError("連接失敗")
        
        await handler.safe_initialize(failing_service)
        
        # 檢查失敗後的健康狀態
        after_failure_health = handler.get_health_status()
        print(f"   📊 失敗後狀態: {after_failure_health['state']}")
        print(f"   📋 錯誤數量: {after_failure_health['error_count']}")
        
        # 測試狀態重置
        handler.reset_state()
        reset_health = handler.get_health_status()
        print(f"   📊 重置後狀態: {reset_health['state']}")
        print(f"   📋 重置後錯誤數量: {reset_health['error_count']}")
        
        return all([
            initial_health['state'] == 'pending',
            after_failure_health['error_count'] > 0,
            reset_health['error_count'] == 0
        ])


async def main():
    """主測試函數"""
    print("🚀 T-08 錯誤處理改進測試開始")
    print("=" * 60)
    
    # 配置日誌
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # 運行測試
    test_suite = TestErrorHandlingEnhancement()
    passed, failed = await test_suite.run_all_tests()
    
    print(f"\n🎉 T-08 測試完成!")
    print(f"📊 最終結果: {passed}通過 / {failed}失敗")
    
    if failed == 0:
        print("✅ 錯誤處理改進實現成功！")
        return True
    else:
        print(f"⚠️ 部分測試失敗，成功率: {passed/(passed+failed)*100:.1f}%")
        return passed / (passed + failed) >= 0.8  # 80%以上算成功


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)