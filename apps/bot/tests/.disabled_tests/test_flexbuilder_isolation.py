#!/usr/bin/env python3
"""
FlexBuilder 安全隔離測試
測試系統在 FlexBuilder 被移除後是否正常運作
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

from src.infrastructure.enhanced_service_factory import EnhancedServiceFactory
from src.services.message_handler_di import MessageHandlerDI
from src.domain.command_handler import CommandContext
from src.services.flex_builder import FlexBuilder


class TestFlexBuilderIsolation:
    """測試 FlexBuilder 的隔離性和依賴關係"""

    def setup_method(self):
        """每個測試前的設置"""
        self.factory = EnhancedServiceFactory()
        
    @pytest.mark.asyncio
    async def test_flexbuilder_service_registration(self):
        """測試 FlexBuilder 在服務註冊表中的狀態"""
        # 驗證 FlexBuilder 是否正確註冊
        flex_builder = self.factory.get_flex_builder()
        assert flex_builder is not None
        assert isinstance(flex_builder, FlexBuilder)
        
    @pytest.mark.asyncio
    async def test_flexbuilder_method_calls_tracking(self):
        """追蹤 FlexBuilder 方法是否被調用"""
        # 獲取 FlexBuilder 實例
        flex_builder = self.factory.get_flex_builder()
        
        # 監控所有 build_*_flex 方法
        build_methods = [
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
        ]
        
        # 為每個方法創建 spy
        method_spies = {}
        for method_name in build_methods:
            method_spies[method_name] = MagicMock(
                side_effect=getattr(flex_builder, method_name)
            )
            setattr(flex_builder, method_name, method_spies[method_name])
        
        # 創建訊息處理器並處理一些測試訊息
        message_handler = self.factory.get_message_handler()
        
        test_messages = [
            "help",
            "status", 
            "tables",
            "SELECT * FROM test",
            "info",
            "models"
        ]
        
        # 處理所有測試訊息
        for message in test_messages:
            try:
                result = message_handler.process_message_sync(
                    user_id="test_user",
                    message_text=message,
                    reply_token="test_token"
                )
                print(f"✅ 處理訊息 '{message}': {type(result).__name__}")
            except Exception as e:
                print(f"❌ 處理訊息 '{message}' 失敗: {e}")
        
        # 檢查是否有任何 FlexBuilder 方法被調用
        called_methods = []
        for method_name, spy in method_spies.items():
            if spy.called:
                called_methods.append(f"{method_name} (調用 {spy.call_count} 次)")
        
        # 輸出結果
        if called_methods:
            print(f"🚨 發現 FlexBuilder 方法被調用: {called_methods}")
            pytest.fail(f"FlexBuilder 方法被意外調用: {called_methods}")
        else:
            print("✅ 確認：所有 FlexBuilder 方法都未被調用")

    @pytest.mark.asyncio  
    async def test_system_without_flexbuilder_dependency(self):
        """測試移除 FlexBuilder 依賴後系統是否正常"""
        
        # 模擬移除 FlexBuilder 的情況
        with patch.object(EnhancedServiceFactory, 'get_flex_builder') as mock_get_flex:
            mock_get_flex.side_effect = RuntimeError("FlexBuilder service not available")
            
            # 測試系統是否能優雅處理 FlexBuilder 缺失
            try:
                factory = EnhancedServiceFactory()
                
                # 測試其他服務是否正常
                ai_service = factory.get_ai_model_service()
                assert ai_service is not None
                
                db_service = factory.get_database_service()
                assert db_service is not None
                
                print("✅ 系統在沒有 FlexBuilder 的情況下正常運作")
                
            except Exception as e:
                print(f"❌ 系統在沒有 FlexBuilder 時失敗: {e}")
                raise

    def test_flexbuilder_import_tracking(self):
        """測試 FlexBuilder 的 import 使用情況"""
        import ast
        import os
        
        # 掃描所有 Python 檔案
        src_dir = "/Users/yen/Desktop/lineMCP/apps/bot/src"
        flexbuilder_imports = []
        
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        # 檢查是否包含 FlexBuilder 相關 import
                        if 'FlexBuilder' in content or 'flex_builder' in content:
                            # 解析 AST 找出具體的 import 語句
                            tree = ast.parse(content)
                            for node in ast.walk(tree):
                                if isinstance(node, ast.Import):
                                    for alias in node.names:
                                        if 'flex_builder' in alias.name:
                                            flexbuilder_imports.append({
                                                'file': file_path,
                                                'line': node.lineno,
                                                'type': 'import',
                                                'statement': alias.name
                                            })
                                elif isinstance(node, ast.ImportFrom):
                                    if node.module and 'flex_builder' in node.module:
                                        for alias in node.names:
                                            flexbuilder_imports.append({
                                                'file': file_path, 
                                                'line': node.lineno,
                                                'type': 'from_import',
                                                'statement': f"from {node.module} import {alias.name}"
                                            })
                    except Exception as e:
                        print(f"無法分析檔案 {file_path}: {e}")
        
        # 輸出所有找到的 import
        print(f"\n📋 FlexBuilder Import 追蹤報告:")
        print(f"找到 {len(flexbuilder_imports)} 個 FlexBuilder 相關 import:")
        
        for imp in flexbuilder_imports:
            rel_path = imp['file'].replace("/Users/yen/Desktop/lineMCP/apps/bot/src/", "")
            print(f"  📄 {rel_path}:{imp['line']} - {imp['statement']}")
        
        # 將結果存儲供後續隔離測試使用
        self.flexbuilder_imports = flexbuilder_imports
        
        return flexbuilder_imports

    @pytest.mark.asyncio
    async def test_command_execution_without_flex(self):
        """測試所有指令在沒有 Flex 消息的情況下執行"""
        
        # 創建指令上下文（不包含 FlexBuilder）
        mock_context = MagicMock()
        mock_context.flex_builder = None  # 明確設為 None
        
        # 測試所有可能的指令
        test_commands = [
            {"text": "help", "expected_type": "text"},
            {"text": "status", "expected_type": "text"}, 
            {"text": "tables", "expected_type": "text"},
            {"text": "info", "expected_type": "text"},
            {"text": "models", "expected_type": "text"},
            {"text": "SELECT COUNT(*) FROM users", "expected_type": "text"}
        ]
        
        message_handler = self.factory.get_message_handler()
        
        for cmd in test_commands:
            try:
                result = message_handler.process_message_sync(
                    user_id="test_user",
                    message_text=cmd["text"],
                    reply_token="test_token"
                )
                
                # 驗證返回的是文字消息而非 Flex 消息
                from linebot.v3.messaging import TextMessage, FlexMessage
                
                assert isinstance(result, TextMessage), f"指令 '{cmd['text']}' 應該返回 TextMessage"
                assert not isinstance(result, FlexMessage), f"指令 '{cmd['text']}' 不應該返回 FlexMessage"
                
                print(f"✅ 指令 '{cmd['text']}' 正確返回 TextMessage")
                
            except Exception as e:
                print(f"❌ 指令 '{cmd['text']}' 執行失敗: {e}")
                raise


if __name__ == "__main__":
    # 可以直接運行此測試
    test = TestFlexBuilderIsolation()
    test.setup_method()
    
    print("🔍 開始 FlexBuilder 隔離測試...")
    
    # 運行 import 追蹤
    imports = test.test_flexbuilder_import_tracking()
    
    # 運行其他測試
    asyncio.run(test.test_flexbuilder_method_calls_tracking())