#!/usr/bin/env python3
"""
FlexBuilder 安全隔離測試 - 簡化版
測試所有 FlexBuilder 相關的 import 和使用情況
"""

import ast
import os
import sys

def analyze_flexbuilder_usage():
    """分析 FlexBuilder 的使用情況"""
    
    # 添加 src 到路徑
    src_dir = "/Users/yen/Desktop/lineMCP/apps/bot/src"
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    
    print("🔍 FlexBuilder 使用情況分析開始...")
    print("=" * 60)
    
    # 1. 掃描所有 import
    flexbuilder_imports = []
    flexbuilder_usages = []
    
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                rel_path = file_path.replace(src_dir + "/", "")
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')
                    
                    # 檢查 FlexBuilder 相關內容
                    for i, line in enumerate(lines, 1):
                        line_stripped = line.strip()
                        
                        # 檢查 import 語句
                        if ('import' in line_stripped and 
                            ('FlexBuilder' in line_stripped or 'flex_builder' in line_stripped)):
                            flexbuilder_imports.append({
                                'file': rel_path,
                                'line': i,
                                'content': line_stripped
                            })
                        
                        # 檢查使用情況（方法調用、屬性存取等）
                        if ('flex_builder' in line_stripped and 'import' not in line_stripped):
                            flexbuilder_usages.append({
                                'file': rel_path,
                                'line': i, 
                                'content': line_stripped,
                                'type': 'usage'
                            })
                        
                        # 檢查 FlexBuilder 方法調用
                        if any(method in line_stripped for method in [
                            'build_workbooks_list_flex',
                            'build_excel_data_flex',
                            'build_workbook_info_flex', 
                            'build_queries_flex',
                            'build_sql_result_flex',
                            'build_explain_flex',
                            'build_indexes_flex',
                            'build_status_flex',
                            'build_trend_flex',
                            'build_suggestion_flex',
                            'build_dynamic_flex'
                        ]):
                            flexbuilder_usages.append({
                                'file': rel_path,
                                'line': i,
                                'content': line_stripped,
                                'type': 'method_call'
                            })
                            
                except Exception as e:
                    print(f"⚠️ 無法分析檔案 {rel_path}: {e}")
    
    # 2. 輸出報告
    print("\n📋 Import 分析結果:")
    print(f"找到 {len(flexbuilder_imports)} 個 FlexBuilder 相關 import:")
    
    for imp in flexbuilder_imports:
        print(f"  📄 {imp['file']}:{imp['line']} - {imp['content']}")
    
    print(f"\n🔍 使用情況分析結果:")
    print(f"找到 {len(flexbuilder_usages)} 個 FlexBuilder 相關使用:")
    
    for usage in flexbuilder_usages:
        icon = "🔧" if usage['type'] == 'method_call' else "📝"
        print(f"  {icon} {usage['file']}:{usage['line']} - {usage['content']}")
    
    # 3. 安全性評估
    print(f"\n🛡️ 安全性評估:")
    
    method_calls = [u for u in flexbuilder_usages if u['type'] == 'method_call']
    if method_calls:
        print(f"❌ 發現 {len(method_calls)} 個方法調用 - 需要謹慎處理")
        for call in method_calls:
            print(f"   🚨 {call['file']}:{call['line']} - {call['content']}")
    else:
        print("✅ 沒有發現任何 FlexBuilder 方法調用")
    
    non_import_usages = [u for u in flexbuilder_usages if u['type'] == 'usage']
    if non_import_usages:
        print(f"⚠️ 發現 {len(non_import_usages)} 個非 import 使用")
        for usage in non_import_usages:
            print(f"   📝 {usage['file']}:{usage['line']} - {usage['content']}")
    else:
        print("✅ 除了 import 外沒有其他使用")
    
    # 4. 移除建議
    print(f"\n💡 移除建議:")
    
    if not method_calls and len(flexbuilder_usages) <= len(flexbuilder_imports):
        print("✅ 可以安全移除 FlexBuilder:")
        print("   1. FlexBuilder 沒有被實際調用")
        print("   2. 只有依賴注入配置需要清理")
        print("   3. 建議先備份再進行移除")
    else:
        print("⚠️ 需要謹慎處理:")
        print("   1. 發現潛在的使用情況")
        print("   2. 建議先進行隔離測試")
        print("   3. 逐步移除依賴")
    
    return {
        'imports': flexbuilder_imports,
        'usages': flexbuilder_usages,
        'method_calls': method_calls,
        'safe_to_remove': not method_calls and len(flexbuilder_usages) <= len(flexbuilder_imports)
    }

def test_dependency_injection_isolation():
    """測試依賴注入系統對 FlexBuilder 的依賴"""
    
    print("\n🔬 依賴注入隔離測試:")
    print("=" * 40)
    
    try:
        # 嘗試導入和創建服務工廠
        sys.path.insert(0, "/Users/yen/Desktop/lineMCP/apps/bot/src")
        
        from infrastructure.enhanced_service_factory import EnhancedServiceFactory
        from services.flex_builder import FlexBuilder
        
        factory = EnhancedServiceFactory()
        
        # 測試獲取 FlexBuilder
        flex_builder = factory.get_flex_builder()
        print(f"✅ 成功獲取 FlexBuilder 實例: {type(flex_builder)}")
        
        # 檢查 FlexBuilder 的方法
        methods = [attr for attr in dir(flex_builder) if attr.startswith('build_')]
        print(f"📋 FlexBuilder 有 {len(methods)} 個 build 方法")
        
        # 測試其他服務是否正常
        try:
            ai_service = factory.get_ai_model_service()
            print(f"✅ AI 服務正常: {type(ai_service)}")
        except Exception as e:
            print(f"❌ AI 服務異常: {e}")
        
        try:
            db_service = factory.get_database_service()
            print(f"✅ 資料庫服務正常: {type(db_service)}")
        except Exception as e:
            print(f"❌ 資料庫服務異常: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 依賴注入測試失敗: {e}")
        return False

if __name__ == "__main__":
    # 執行分析
    result = analyze_flexbuilder_usage()
    
    # 執行依賴注入測試  
    di_test_result = test_dependency_injection_isolation()
    
    print(f"\n🎯 最終結論:")
    print("=" * 30)
    
    if result['safe_to_remove'] and di_test_result:
        print("✅ FlexBuilder 可以安全移除")
        print("📋 建議的移除步驟:")
        print("   1. 備份 flex_builder.py")
        print("   2. 從 enhanced_service_factory.py 移除註冊")
        print("   3. 從相關類別移除構造函數參數")
        print("   4. 運行完整測試確認系統正常")
        print("   5. 刪除 flex_builder.py 檔案")
    else:
        print("⚠️ 建議進一步測試再移除")
        print("📋 需要額外檢查的項目:")
        if not result['safe_to_remove']:
            print("   - 解決發現的使用情況")
        if not di_test_result:
            print("   - 修復依賴注入問題")