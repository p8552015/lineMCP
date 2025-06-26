#!/usr/bin/env python3
"""
整合測試運行腳本
用於執行所有資料庫和端到端整合測試
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description=""):
    """執行命令並返回結果"""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    print(f"執行: {cmd}")
    print("-" * 60)
    
    result = subprocess.run(cmd, shell=True, capture_output=False)
    
    if result.returncode == 0:
        print(f"✅ {description} - 成功")
    else:
        print(f"❌ {description} - 失敗 (退出碼: {result.returncode})")
    
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="運行整合測試")
    parser.add_argument("--verbose", "-v", action="store_true", help="詳細輸出")
    parser.add_argument("--fast", "-f", action="store_true", help="快速模式（跳過效能測試）")
    parser.add_argument("--database-only", "-d", action="store_true", help="僅運行資料庫測試")
    parser.add_argument("--health-check", "-c", action="store_true", help="僅運行健康檢查測試")
    parser.add_argument("--performance", "-p", action="store_true", help="僅運行效能測試")
    
    args = parser.parse_args()
    
    # 確保在正確的目錄
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    print("🚀 LINE MCP Bot 整合測試套件")
    print(f"📁 工作目錄: {os.getcwd()}")
    
    # 基本參數
    pytest_args = "-v" if args.verbose else "-q"
    pytest_args += " --tb=short"
    
    failed_tests = []
    
    # 1. 資料庫連接測試
    if not args.performance:
        cmd = f"python -m pytest tests/integration/test_database_integration.py::TestDatabaseConnection {pytest_args}"
        if run_command(cmd, "資料庫連接測試") != 0:
            failed_tests.append("資料庫連接測試")
    
    # 2. 資料庫Schema測試
    if not args.performance:
        cmd = f"python -m pytest tests/integration/test_database_integration.py::TestDatabaseSchema {pytest_args}"
        if run_command(cmd, "資料庫Schema測試") != 0:
            failed_tests.append("資料庫Schema測試")
    
    # 3. 資料庫查詢測試
    if not args.performance:
        cmd = f"python -m pytest tests/integration/test_database_integration.py::TestDatabaseQueries {pytest_args}"
        if run_command(cmd, "資料庫查詢測試") != 0:
            failed_tests.append("資料庫查詢測試")
    
    # 4. 健康檢查測試
    if args.health_check or not (args.database_only or args.performance):
        cmd = f"python -m pytest tests/integration/test_database_integration.py::TestDatabaseHealthCheck {pytest_args}"
        if run_command(cmd, "資料庫健康檢查測試") != 0:
            failed_tests.append("資料庫健康檢查測試")
    
    # 5. 效能測試
    if args.performance or not (args.fast or args.database_only or args.health_check):
        cmd = f"python -m pytest tests/integration/test_database_integration.py::TestDatabasePerformance {pytest_args}"
        if run_command(cmd, "資料庫效能測試") != 0:
            failed_tests.append("資料庫效能測試")
    
    # 6. 錯誤處理測試
    if not args.performance:
        cmd = f"python -m pytest tests/integration/test_database_integration.py::TestDatabaseErrorHandling {pytest_args}"
        if run_command(cmd, "資料庫錯誤處理測試") != 0:
            failed_tests.append("資料庫錯誤處理測試")
    
    # 7. 事務測試
    if not args.performance:
        cmd = f"python -m pytest tests/integration/test_database_integration.py::TestDatabaseTransactions {pytest_args}"
        if run_command(cmd, "資料庫事務測試") != 0:
            failed_tests.append("資料庫事務測試")
    
    # 8. 端到端測試（如果不是僅資料庫模式）
    if not (args.database_only or args.performance):
        if os.path.exists("tests/integration/test_end_to_end_integration.py"):
            cmd = f"python -m pytest tests/integration/test_end_to_end_integration.py::TestEndToEndIntegration::test_system_startup_health_check {pytest_args}"
            if run_command(cmd, "端到端健康檢查測試") != 0:
                failed_tests.append("端到端健康檢查測試")
    
    # 總結報告
    print("\n" + "="*60)
    print("📊 測試結果總結")
    print("="*60)
    
    if not failed_tests:
        print("🎉 所有測試都通過了！")
        print("\n✅ 系統狀態：健康")
        print("✅ 資料庫連接：正常")
        print("✅ 核心功能：正常")
        if not args.fast:
            print("✅ 效能指標：符合要求")
        
        # 運行快速的健康檢查
        print("\n🔍 執行最終健康檢查...")
        health_cmd = "python -c \"import asyncio; from src.utils.database_health_check import run_health_check; asyncio.run(run_health_check())\""
        if run_command(health_cmd, "最終健康檢查") == 0:
            print("\n🎯 整合測試完成 - 系統準備就緒！")
            return 0
        else:
            print("\n⚠️ 最終健康檢查失敗")
            return 1
    else:
        print(f"❌ 有 {len(failed_tests)} 個測試失敗：")
        for test in failed_tests:
            print(f"   • {test}")
        
        print("\n💡 建議：")
        print("   1. 檢查資料庫連接是否正常")
        print("   2. 確認所有必需的資料表已建立")
        print("   3. 檢查資料庫資料是否完整")
        print("   4. 運行 './start-production.sh db-status' 進行診斷")
        
        return 1


if __name__ == "__main__":
    sys.exit(main()) 