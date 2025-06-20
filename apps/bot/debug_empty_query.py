#!/usr/bin/env python3
"""
診斷空查詢問題的調試腳本
檢查所有可能產生空查詢的組件
"""

import sys
import os
import asyncio
import structlog

# 添加 src 路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')
sys.path.insert(0, src_path)

logger = structlog.get_logger()

async def diagnose_empty_query_issue():
    """診斷空查詢問題"""
    
    print("🔍 開始診斷空查詢問題...")
    
    try:
        # 1. 檢查服務工廠
        print("\n1️⃣ 檢查增強服務工廠...")
        from src.infrastructure.enhanced_service_factory import get_enhanced_service_factory
        
        factory = get_enhanced_service_factory()
        print(f"✅ 服務工廠獲取成功: {type(factory).__name__}")
        
        # 2. 檢查配置服務
        print("\n2️⃣ 檢查配置服務...")
        config_service = factory.get_configuration()
        print(f"✅ 配置服務獲取成功: {type(config_service).__name__}")
        
        # 檢查 SQL 模板配置
        try:
            sql_templates = config_service.get_sql_templates()
            print(f"✅ SQL 模板配置獲取成功，模板數量: {len(sql_templates)}")
            
            for template_name, template_content in sql_templates.items():
                if not template_content or not template_content.strip():
                    print(f"❌ 發現空模板: {template_name}")
                else:
                    print(f"✅ 模板 {template_name}: {len(template_content)} 字符")
                    
        except Exception as e:
            print(f"❌ 獲取 SQL 模板失敗: {e}")
        
        # 3. 檢查模板管理器
        print("\n3️⃣ 檢查模板管理器...")
        template_manager = factory.get_template_manager()
        print(f"✅ 模板管理器獲取成功: {type(template_manager).__name__}")
        
        # 檢查所有模板
        from src.services.nl_to_sql.models.query_models import QueryType
        
        for query_type in QueryType:
            if query_type == QueryType.UNKNOWN:
                continue
                
            try:
                template = template_manager.get_template(query_type)
                if not template or not template.strip():
                    print(f"❌ 查詢類型 {query_type.value} 的模板為空")
                else:
                    print(f"✅ 查詢類型 {query_type.value}: {len(template)} 字符")
                    
            except Exception as e:
                print(f"❌ 獲取模板失敗 {query_type.value}: {e}")
        
        # 4. 檢查 SQL 查詢建構器
        print("\n4️⃣ 檢查 SQL 查詢建構器...")
        query_builder = factory.get_builder()
        print(f"✅ 查詢建構器獲取成功: {type(query_builder).__name__}")
        
        # 測試建構 SQL
        try:
            test_sql = query_builder.build_query(
                QueryType.ALL_MACHINES, 
                {}
            )
            if not test_sql or not test_sql.strip():
                print("❌ 建構的測試 SQL 為空")
            else:
                print(f"✅ 測試 SQL 建構成功: {len(test_sql)} 字符")
                print(f"   預覽: {test_sql[:100]}...")
                
        except Exception as e:
            print(f"❌ SQL 建構測試失敗: {e}")
        
        # 5. 檢查解析器
        print("\n5️⃣ 檢查解析器...")
        parser = factory.get_parser()
        print(f"✅ 解析器獲取成功: {type(parser).__name__}")
        
        # 測試解析
        try:
            test_parse_result = await parser.parse("查看所有機台", {})
            print(f"✅ 測試解析成功:")
            print(f"   查詢類型: {test_parse_result.query_type.value}")
            print(f"   信心度: {test_parse_result.confidence}")
            print(f"   SQL 長度: {len(test_parse_result.sql_query) if test_parse_result.sql_query else 0}")
            
            if not test_parse_result.sql_query or not test_parse_result.sql_query.strip():
                print("❌ 解析結果的 SQL 為空")
            else:
                print(f"   SQL 預覽: {test_parse_result.sql_query[:100]}...")
                
        except Exception as e:
            print(f"❌ 解析測試失敗: {e}")
        
        # 6. 檢查 NL to SQL 服務
        print("\n6️⃣ 檢查 NL to SQL 服務...")
        try:
            from src.services.ai_model_service import AIModelService
            from src.services.nl_to_sql_service import NaturalLanguageToSQLService
            
            # 模擬初始化
            ai_service = AIModelService()
            nl_service = NaturalLanguageToSQLService(ai_service)
            
            print(f"✅ NL to SQL 服務初始化成功")
            
            # 測試解析
            test_result = await nl_service.parse_natural_language("查看所有機台")
            
            print(f"✅ NL 服務測試解析成功:")
            print(f"   查詢類型: {test_result.query_type.value}")
            print(f"   信心度: {test_result.confidence}")
            print(f"   SQL 長度: {len(test_result.sql_query) if test_result.sql_query else 0}")
            
            if not test_result.sql_query or not test_result.sql_query.strip():
                print("❌ NL 服務返回的 SQL 為空")
                print(f"   錯誤說明: {test_result.explanation}")
            else:
                print(f"   SQL 預覽: {test_result.sql_query[:100]}...")
                
        except Exception as e:
            print(f"❌ NL to SQL 服務測試失敗: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n🎯 診斷完成")
        
    except Exception as e:
        print(f"❌ 診斷過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(diagnose_empty_query_issue())