#!/usr/bin/env python3
"""
生產查詢驗證腳本 - TF-07
驗證核心查詢功能：M001機台稼動率 和 查看所有機台
"""

import asyncio
import sys
import os
import structlog
from pathlib import Path

# 確保能夠導入應用模組
bot_src_path = str(Path(__file__).parent / "apps" / "bot" / "src")
sys.path.insert(0, bot_src_path)
os.chdir(str(Path(__file__).parent / "apps" / "bot"))

from application.application_facade import ApplicationFacade

# 設置日誌
structlog.configure(
    processors=[
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.WriteLoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

async def test_core_queries():
    """測試核心查詢功能"""
    print("🧪 生產查詢驗證開始...")
    
    # 初始化應用門面
    try:
        facade = ApplicationFacade()
        await facade.initialize()
        print("✅ 應用門面初始化成功")
    except Exception as e:
        print(f"❌ 應用門面初始化失敗: {e}")
        return False
    
    # 測試查詢 1: M001機台稼動率
    print("\n📊 測試查詢 1: M001機台稼動率")
    try:
        result1 = await facade.process_message("test_user", "M001機台稼動率")
        print("✅ M001機台稼動率查詢成功")
        print(f"   回應長度: {len(result1)} 字符")
        
        # 檢查預期內容
        expected_keywords = ["M001", "稼動率", "效率", "CNC", "加工部"]
        found_keywords = [kw for kw in expected_keywords if kw in result1]
        print(f"   包含關鍵詞: {found_keywords}")
        
        if len(found_keywords) >= 3:
            print("   ✅ 包含足夠的預期關鍵詞")
        else:
            print("   ⚠️ 關鍵詞數量不足")
            
    except Exception as e:
        print(f"   ❌ M001機台稼動率查詢失敗: {e}")
        result1 = None
    
    # 測試查詢 2: 查看所有機台
    print("\n📋 測試查詢 2: 查看所有機台")
    try:
        result2 = await facade.process_message("test_user", "查看所有機台")
        print("✅ 查看所有機台查詢成功")
        print(f"   回應長度: {len(result2)} 字符")
        
        # 檢查預期內容
        expected_keywords = ["機台", "概覽", "平均", "稼動率", "效率"]
        found_keywords = [kw for kw in expected_keywords if kw in result2]
        print(f"   包含關鍵詞: {found_keywords}")
        
        if len(found_keywords) >= 3:
            print("   ✅ 包含足夠的預期關鍵詞")
        else:
            print("   ⚠️ 關鍵詞數量不足")
            
    except Exception as e:
        print(f"   ❌ 查看所有機台查詢失敗: {e}")
        result2 = None
    
    # 關閉應用門面
    try:
        await facade.shutdown()
        print("\n✅ 應用門面已正常關閉")
    except Exception as e:
        print(f"\n⚠️ 應用門面關閉時發生錯誤: {e}")
    
    # 結果總結
    print("\n" + "="*50)
    print("📊 生產查詢驗證結果總結")
    print("="*50)
    
    if result1 and result2:
        print("✅ 所有核心查詢測試通過")
        print("   - M001機台稼動率: ✅ 成功")
        print("   - 查看所有機台: ✅ 成功")
        return True
    elif result1 or result2:
        print("⚠️ 部分查詢測試通過")
        print(f"   - M001機台稼動率: {'✅ 成功' if result1 else '❌ 失敗'}")
        print(f"   - 查看所有機台: {'✅ 成功' if result2 else '❌ 失敗'}")
        return False
    else:
        print("❌ 所有核心查詢測試失敗")
        print("   - M001機台稼動率: ❌ 失敗")
        print("   - 查看所有機台: ❌ 失敗")
        return False

async def main():
    """主函數"""
    success = await test_core_queries()
    
    if success:
        print("\n🎉 生產查詢驗證完全成功！")
        print("💡 系統已準備好處理生產環境查詢")
        return 0
    else:
        print("\n❌ 生產查詢驗證存在問題")
        print("💡 需要進一步檢查系統配置和服務狀態")
        return 1

if __name__ == "__main__":
    # 設置環境變數
    os.environ["ASYNCIO_FORCE_SELECT_SELECTOR"] = "1"
    
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚡ 用戶中斷測試")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 測試執行過程中發生未預期錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)