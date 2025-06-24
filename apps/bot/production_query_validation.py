#!/usr/bin/env python3
"""
生產查詢驗證 - TF-07
專門驗證 M001機台稼動率 和 查看所有機台 查詢
"""

import asyncio
import os
from application.application_facade import ApplicationFacade
from infrastructure.enhanced_service_factory import EnhancedServiceFactory

async def validate_production_queries():
    """驗證生產關鍵查詢"""
    print("🧪 開始生產查詢驗證...")
    
    # 設置環境變數
    os.environ["ASYNCIO_FORCE_SELECT_SELECTOR"] = "1"
    
    service_factory = None
    try:
        # 初始化服務工廠
        service_factory = EnhancedServiceFactory()
        print("✅ 服務工廠初始化成功")
        
        # 獲取NL-to-SQL服務
        nl_service = service_factory.get_nl_service()
        print("✅ NL-to-SQL 服務獲取成功")
        
        # 關鍵查詢 1: M001機台稼動率
        print("\n📊 測試關鍵查詢 1: M001機台稼動率")
        parsed_result1 = await nl_service.parse_natural_language("M001機台稼動率")
        
        if parsed_result1 and parsed_result1.sql_query and parsed_result1.sql_query.strip():
            print("✅ M001機台稼動率查詢成功")
            print(f"📝 查詢類型: {parsed_result1.query_type.value}")
            print(f"📝 信心度: {parsed_result1.confidence:.2f}")
            print(f"📝 SQL長度: {len(parsed_result1.sql_query)} 字符")
            print(f"📝 說明: {parsed_result1.explanation}")
            
            # 檢查預期內容
            expected_elements = ["M001", "machine_id", "SELECT"]
            found_elements = []
            if "M001" in str(parsed_result1.parameters):
                found_elements.append("M001")
            if "machine_id" in str(parsed_result1.parameters):
                found_elements.append("machine_id")
            if "SELECT" in parsed_result1.sql_query:
                found_elements.append("SELECT")
            
            print(f"🔍 包含預期元素: {found_elements}")
            
            if len(found_elements) >= 2:
                print("✅ M001查詢格式符合預期")
                query1_success = True
            else:
                print("⚠️ M001查詢格式需要改進")
                query1_success = False
        else:
            print("❌ M001機台稼動率查詢失敗 - 空SQL查詢")
            query1_success = False
        
        # 關鍵查詢 2: 查看所有機台
        print("\n📋 測試關鍵查詢 2: 查看所有機台")
        parsed_result2 = await nl_service.parse_natural_language("查看所有機台")
        
        if parsed_result2 and parsed_result2.sql_query and parsed_result2.sql_query.strip():
            print("✅ 查看所有機台查詢成功")
            print(f"📝 查詢類型: {parsed_result2.query_type.value}")
            print(f"📝 信心度: {parsed_result2.confidence:.2f}")
            print(f"📝 SQL長度: {len(parsed_result2.sql_query)} 字符")
            print(f"📝 說明: {parsed_result2.explanation}")
            
            # 檢查預期內容
            expected_elements = ["all_machines", "SELECT", "機台"]
            found_elements = []
            if "all_machines" in parsed_result2.query_type.value:
                found_elements.append("all_machines")
            if "SELECT" in parsed_result2.sql_query:
                found_elements.append("SELECT")
            if "機台" in parsed_result2.explanation:
                found_elements.append("機台")
            
            print(f"🔍 包含預期元素: {found_elements}")
            
            if len(found_elements) >= 2:
                print("✅ 所有機台查詢格式符合預期")
                query2_success = True
            else:
                print("⚠️ 所有機台查詢格式需要改進")
                query2_success = False
        else:
            print("❌ 查看所有機台查詢失敗 - 空SQL查詢")
            query2_success = False
        
        # 驗證結果總結
        print("\n" + "="*50)
        print("📊 生產查詢驗證結果")
        print("="*50)
        print(f"M001機台稼動率: {'✅ 通過' if query1_success else '❌ 失敗'}")
        print(f"查看所有機台: {'✅ 通過' if query2_success else '❌ 失敗'}")
        
        if query1_success and query2_success:
            print("\n🎉 所有關鍵查詢驗證通過！")
            print("💡 系統已準備好處理生產環境的核心查詢需求")
            return True
        else:
            print("\n⚠️ 部分查詢驗證未通過")
            print("💡 建議檢查 NL-to-SQL 服務和資料庫連接")
            return False
            
    except Exception as e:
        print(f"❌ 驗證過程發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 服務工廠不需要特殊清理
        print("🧹 測試資源清理完成")

if __name__ == "__main__":
    try:
        success = asyncio.run(validate_production_queries())
        if success:
            print("\n🏆 TF-07 生產查詢驗證：成功")
            exit(0)
        else:
            print("\n❌ TF-07 生產查詢驗證：失敗")
            exit(1)
    except KeyboardInterrupt:
        print("\n⚡ 驗證被用戶中斷")
        exit(1)
    except Exception as e:
        print(f"\n💥 執行過程中發生未預期錯誤: {e}")
        exit(1)