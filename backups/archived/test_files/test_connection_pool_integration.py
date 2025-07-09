#!/usr/bin/env python3
"""
MCP 連接池整合測試腳本
驗證 T-05 連接池和 ProductionMCPClient 整合效果
"""

import asyncio
import sys
import os

# 添加路徑
bot_src_path = os.path.join(os.path.dirname(__file__), 'apps/bot/src')
sys.path.insert(0, bot_src_path)
os.chdir(os.path.join(os.path.dirname(__file__), 'apps/bot'))

async def test_connection_pool_integration():
    """測試連接池整合"""
    print("🏊 MCP 連接池整合測試開始...")
    
    try:
        # 導入必要的模組
        from services.production_mcp_client import get_production_mcp_client
        from services.mcp_connection_pool import get_connection_pool
        
        # 獲取客戶端和連接池
        client = get_production_mcp_client()
        pool = get_connection_pool()
        
        print("\n📋 測試項目:")
        results = []
        
        # 1. 測試連接池啟動
        print("\n1. 測試連接池自動啟動")
        try:
            await client._ensure_pool_started()
            print("   ✅ 連接池啟動成功")
            results.append({"test": "pool_startup", "result": "success"})
        except Exception as e:
            print(f"   ❌ 連接池啟動失敗: {e}")
            results.append({"test": "pool_startup", "result": "failed", "error": str(e)})
        
        # 2. 測試連接池狀態查詢
        print("\n2. 測試連接池狀態查詢")
        try:
            status = await client.get_connection_pool_status()
            print(f"   ✅ 連接池狀態: {status.get('total_connections', 0)} 個連接")
            print(f"   📊 健康連接: {status.get('healthy_connections', 0)} 個")
            results.append({"test": "pool_status", "result": "success", "data": status})
        except Exception as e:
            print(f"   ❌ 狀態查詢失敗: {e}")
            results.append({"test": "pool_status", "result": "failed", "error": str(e)})
        
        # 3. 測試成功記錄
        print("\n3. 測試成功操作記錄")
        try:
            await pool.record_success("sqlite", 0.123)
            print("   ✅ 成功操作記錄完成")
            results.append({"test": "record_success", "result": "success"})
        except Exception as e:
            print(f"   ❌ 成功記錄失敗: {e}")
            results.append({"test": "record_success", "result": "failed", "error": str(e)})
        
        # 4. 測試失敗記錄
        print("\n4. 測試失敗操作記錄")
        try:
            await pool.record_failure("sqlite", "測試錯誤")
            print("   ✅ 失敗操作記錄完成")
            results.append({"test": "record_failure", "result": "success"})
        except Exception as e:
            print(f"   ❌ 失敗記錄失敗: {e}")
            results.append({"test": "record_failure", "result": "failed", "error": str(e)})
        
        # 5. 測試連接獲取
        print("\n5. 測試連接獲取")
        try:
            connection_info = await pool.get_connection("sqlite")
            if connection_info:
                print(f"   ✅ 連接獲取成功: {connection_info.status.value}")
                results.append({"test": "get_connection", "result": "success", "status": connection_info.status.value})
            else:
                print("   ❌ 無法獲取連接")
                results.append({"test": "get_connection", "result": "failed", "error": "無連接"})
        except Exception as e:
            print(f"   ❌ 連接獲取失敗: {e}")
            results.append({"test": "get_connection", "result": "failed", "error": str(e)})
        
        # 6. 測試指標統計
        print("\n6. 測試指標統計")
        try:
            status = await pool.get_pool_status()
            connections = status.get("connections", {})
            if "sqlite" in connections:
                sqlite_stats = connections["sqlite"]
                print(f"   📊 成功次數: {sqlite_stats.get('success_count', 0)}")
                print(f"   📊 失敗次數: {sqlite_stats.get('failure_count', 0)}")
                print(f"   📊 成功率: {sqlite_stats.get('success_rate', 0.0):.2f}")
                print(f"   📊 平均回應時間: {sqlite_stats.get('average_response_time', 0.0):.3f}s")
                results.append({"test": "metrics", "result": "success", "stats": sqlite_stats})
            else:
                print("   ⚠️ 無 sqlite 連接統計")
                results.append({"test": "metrics", "result": "partial", "error": "無統計"})
        except Exception as e:
            print(f"   ❌ 指標統計失敗: {e}")
            results.append({"test": "metrics", "result": "failed", "error": str(e)})
        
        # 7. 測試連接池清理
        print("\n7. 測試連接池清理")
        try:
            await client.close_all_connections()
            print("   ✅ 連接池清理成功")
            results.append({"test": "cleanup", "result": "success"})
        except Exception as e:
            print(f"   ❌ 連接池清理失敗: {e}")
            results.append({"test": "cleanup", "result": "failed", "error": str(e)})
        
        # 統計結果
        print(f"\n📊 測試結果統計:")
        total_tests = len(results)
        success_tests = sum(1 for r in results if r["result"] == "success")
        
        print(f"   總測試數: {total_tests}")
        print(f"   成功通過: {success_tests}")
        print(f"   成功率: {success_tests/total_tests*100:.1f}%")
        
        # 驗證關鍵功能
        critical_tests = ["pool_startup", "record_success", "record_failure", "get_connection"]
        critical_passed = sum(1 for r in results if r["test"] in critical_tests and r["result"] == "success")
        
        print(f"\n🎯 關鍵功能檢查:")
        print(f"   連接池啟動: {'✅' if any(r['test'] == 'pool_startup' and r['result'] == 'success' for r in results) else '❌'}")
        print(f"   成功記錄: {'✅' if any(r['test'] == 'record_success' and r['result'] == 'success' for r in results) else '❌'}")
        print(f"   失敗記錄: {'✅' if any(r['test'] == 'record_failure' and r['result'] == 'success' for r in results) else '❌'}")
        print(f"   連接管理: {'✅' if any(r['test'] == 'get_connection' and r['result'] == 'success' for r in results) else '❌'}")
        
        overall_success = critical_passed >= 3  # 至少3個關鍵功能正常
        print(f"   整體評估: {'✅ 連接池整合成功' if overall_success else '❌ 連接池整合需要改進'}")
        
        return overall_success
        
    except Exception as e:
        print(f"❌ 測試初始化失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection_pool_integration())
    sys.exit(0 if success else 1)