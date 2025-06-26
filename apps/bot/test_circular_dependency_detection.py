#!/usr/bin/env python3
"""
循環依賴檢測系統測試
驗證 T-07 任務：循環依賴預防機制的實現
"""

import asyncio
import sys
import traceback
from pathlib import Path

# 添加應用路徑
sys.path.insert(0, str(Path(__file__).parent / "src"))

import structlog
from src.infrastructure.circular_dependency_detector import (
    CircularDependencyDetector,
    DependencyType,
    CycleDetectionResult,
    get_circular_dependency_detector,
    reset_detector,
)
from src.infrastructure.dependency_injection_guard import (
    DependencyInjectionGuard,
    CircularDependencyError,
    get_dependency_guard,
    dependency_guard,
    dependency_resolution_context,
)
from src.infrastructure.enhanced_service_factory import EnhancedServiceFactory
from src.infrastructure.service_registry import get_service_registry

logger = structlog.get_logger()


class TestServiceA:
    """測試服務 A"""
    def __init__(self, service_b=None):
        self.service_b = service_b
        self.name = "ServiceA"


class TestServiceB:
    """測試服務 B"""  
    def __init__(self, service_c=None):
        self.service_c = service_c
        self.name = "ServiceB"


class TestServiceC:
    """測試服務 C"""
    def __init__(self, service_a=None):
        self.service_a = service_a
        self.name = "ServiceC"


class TestCircularDependencyDetection:
    """循環依賴檢測測試類"""
    
    def __init__(self):
        self.detector = CircularDependencyDetector()
        self.guard = DependencyInjectionGuard()
        self.test_results = []
    
    def run_all_tests(self):
        """執行所有測試"""
        print("🔍 開始循環依賴檢測系統測試...")
        print("=" * 60)
        
        tests = [
            ("基本循環檢測", self.test_basic_cycle_detection),
            ("無循環依賴檢測", self.test_no_cycle_detection), 
            ("解析堆疊檢測", self.test_resolution_stack_detection),
            ("依賴防護測試", self.test_dependency_guard),
            ("上下文管理器測試", self.test_context_manager),
            ("風險分析測試", self.test_risk_analysis),
            ("服務工廠整合測試", self.test_service_factory_integration),
            ("健康檢查測試", self.test_health_check),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                print(f"\n📋 執行測試: {test_name}")
                print("-" * 40)
                
                # 重置檢測器狀態
                self.detector.clear_graph()
                
                result = test_func()
                if result:
                    print(f"✅ 測試通過: {test_name}")
                    passed += 1
                else:
                    print(f"❌ 測試失敗: {test_name}")
                    failed += 1
                    
            except Exception as e:
                print(f"💥 測試異常: {test_name} - {e}")
                traceback.print_exc()
                failed += 1
        
        print(f"\n{'='*60}")
        print(f"📊 測試結果摘要:")
        print(f"   ✅ 通過: {passed}")
        print(f"   ❌ 失敗: {failed}")
        print(f"   📈 成功率: {passed/(passed+failed)*100:.1f}%")
        
        return passed, failed
    
    def test_basic_cycle_detection(self) -> bool:
        """測試基本循環檢測"""
        print("🔄 測試三個服務之間的循環依賴...")
        
        # 添加依賴：A -> B -> C -> A (循環)
        report1 = self.detector.add_dependency("ServiceA", "ServiceB", DependencyType.CONSTRUCTOR)
        report2 = self.detector.add_dependency("ServiceB", "ServiceC", DependencyType.CONSTRUCTOR)
        report3 = self.detector.add_dependency("ServiceC", "ServiceA", DependencyType.CONSTRUCTOR)
        
        print(f"   A->B: {report1.result.value}")
        print(f"   B->C: {report2.result.value}")
        print(f"   C->A: {report3.result.value}")
        
        # 第三個依賴應該檢測到循環
        if report3.result == CycleDetectionResult.CYCLE_DETECTED:
            print(f"   🎯 檢測到循環路徑: {' -> '.join(report3.cycle_path)}")
            print(f"   💡 建議數量: {len(report3.suggestions)}")
            return True
        else:
            print("   ❌ 未能檢測到預期的循環依賴")
            return False
    
    def test_no_cycle_detection(self) -> bool:
        """測試無循環的正常依賴"""
        print("➡️ 測試正常的線性依賴...")
        
        # 添加線性依賴：A -> B -> C (無循環)
        report1 = self.detector.add_dependency("ServiceA", "ServiceB", DependencyType.CONSTRUCTOR)
        report2 = self.detector.add_dependency("ServiceB", "ServiceC", DependencyType.CONSTRUCTOR)
        
        print(f"   A->B: {report1.result.value}")
        print(f"   B->C: {report2.result.value}")
        
        # 都應該是無循環
        if (report1.result == CycleDetectionResult.NO_CYCLE and 
            report2.result == CycleDetectionResult.NO_CYCLE):
            print("   ✅ 正確識別無循環依賴")
            return True
        else:
            print("   ❌ 錯誤地檢測到循環依賴")
            return False
    
    def test_resolution_stack_detection(self) -> bool:
        """測試解析堆疊檢測"""
        print("📚 測試解析堆疊的循環檢測...")
        
        # 開始解析 ServiceA
        if not self.detector.begin_resolution("ServiceA"):
            print("   ❌ 首次解析失敗")
            return False
        
        print("   📍 開始解析 ServiceA")
        
        # 嘗試再次解析 ServiceA（應該檢測到循環）
        if self.detector.begin_resolution("ServiceA"):
            print("   ❌ 未檢測到解析中的循環")
            self.detector.end_resolution("ServiceA")
            self.detector.end_resolution("ServiceA") 
            return False
        
        print("   🎯 成功檢測到解析堆疊中的循環")
        self.detector.end_resolution("ServiceA")
        return True
    
    def test_dependency_guard(self) -> bool:
        """測試依賴防護"""
        print("🛡️ 測試依賴注入防護...")
        
        @dependency_guard("TestService")
        def create_service():
            return TestServiceA()
        
        try:
            service = create_service()
            print(f"   ✅ 成功創建服務: {service.name}")
            
            # 註冊服務類型
            self.detector.register_service_type("TestService", TestServiceA)
            print("   📝 成功註冊服務類型")
            
            return True
        except Exception as e:
            print(f"   ❌ 服務創建失敗: {e}")
            return False
    
    def test_context_manager(self) -> bool:
        """測試上下文管理器"""
        print("🎭 測試依賴解析上下文管理器...")
        
        try:
            with dependency_resolution_context("ContextTestService"):
                print("   📍 進入依賴解析上下文")
                
                # 嘗試再次進入同一服務的上下文（應該失敗）
                try:
                    with dependency_resolution_context("ContextTestService"):
                        print("   ❌ 不應該能再次進入相同服務的上下文")
                        return False
                except CircularDependencyError:
                    print("   🎯 正確檢測到上下文循環")
            
            print("   ✅ 上下文管理器正常退出")
            return True
            
        except CircularDependencyError as e:
            print(f"   ❌ 上下文管理器異常: {e}")
            return False
    
    def test_risk_analysis(self) -> bool:
        """測試風險分析"""
        print("📊 測試依賴風險分析...")
        
        # 創建複雜的依賴結構
        services = ["ServiceFactory", "ApplicationFacade", "DatabaseService", "AIService"]
        
        # ServiceFactory 依賴很多服務（高出度）
        for service in services[1:]:
            self.detector.add_dependency("ServiceFactory", service, DependencyType.CONSTRUCTOR)
        
        # ApplicationFacade 被很多服務依賴（高入度）
        for service in services[2:]:
            self.detector.add_dependency(service, "ApplicationFacade", DependencyType.PROPERTY)
        
        # 執行風險分析
        risk_analysis = self.detector.analyze_dependency_risks()
        
        print(f"   📈 總服務數: {risk_analysis['total_services']}")
        print(f"   📊 總依賴數: {risk_analysis['total_dependencies']}")
        print(f"   ⚠️ 高風險服務: {len(risk_analysis['high_risk_services'])}")
        print(f"   💡 建議數量: {len(risk_analysis['recommendations'])}")
        
        # 應該識別出高風險服務
        if risk_analysis['high_risk_services']:
            for risk_service in risk_analysis['high_risk_services']:
                print(f"   🔴 高風險: {risk_service['service']} (評分: {risk_service['risk_score']})")
            return True
        else:
            print("   ❌ 未識別出預期的高風險服務")
            return False
    
    def test_service_factory_integration(self) -> bool:
        """測試服務工廠整合"""
        print("🏭 測試增強版服務工廠的循環依賴檢測整合...")
        
        try:
            # 創建增強版服務工廠
            registry = get_service_registry()
            factory = EnhancedServiceFactory(registry)
            
            print("   🔧 服務工廠創建成功")
            
            # 初始化工廠
            factory.initialize()
            print("   ⚙️ 服務工廠初始化完成")
            
            # 獲取依賴健康報告
            health_report = factory.get_dependency_health_report()
            
            print(f"   📋 健康狀態: {health_report['overall_status']}")
            print(f"   🎯 風險等級: {health_report['risk_level']}")
            print(f"   📊 註冊服務數: {health_report['factory_info']['registry_services']}")
            
            return health_report['overall_status'] in ['healthy', 'warning']
            
        except Exception as e:
            print(f"   ❌ 服務工廠整合測試失敗: {e}")
            return False
    
    def test_health_check(self) -> bool:
        """測試健康檢查"""
        print("🏥 測試系統健康檢查...")
        
        try:
            health_status = self.guard.check_system_health()
            
            print(f"   🎯 系統狀態: {health_status['status']}")
            print(f"   📊 風險等級: {health_status['risk_level']}")
            print(f"   📋 問題數量: {len(health_status['issues'])}")
            print(f"   💡 建議數量: {len(health_status['recommendations'])}")
            
            # 打印具體資訊
            if health_status['issues']:
                for issue in health_status['issues']:
                    print(f"      ⚠️ 問題: {issue}")
            
            if health_status['recommendations']:
                for rec in health_status['recommendations'][:3]:  # 顯示前3個建議
                    print(f"      💡 建議: {rec}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ 健康檢查失敗: {e}")
            return False


async def main():
    """主測試函數"""
    print("🚀 T-07 循環依賴預防機制測試開始")
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
    
    # 重置全局檢測器
    reset_detector()
    
    # 運行測試
    test_suite = TestCircularDependencyDetection()
    passed, failed = test_suite.run_all_tests()
    
    print(f"\n🎉 T-07 測試完成!")
    print(f"📊 最終結果: {passed}通過 / {failed}失敗")
    
    if failed == 0:
        print("✅ 循環依賴預防機制實現成功！")
        return True
    else:
        print("❌ 部分測試失敗，需要進一步調試")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)