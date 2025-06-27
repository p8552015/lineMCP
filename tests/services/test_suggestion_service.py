#!/usr/bin/env python3
"""
SuggestionService 單元測試

測試建議生成服務的各種功能：
- AI 動態建議生成
- 智能靜態建議回退
- 關鍵詞分析邏輯
- 錯誤處理和回退機制
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from linebot.v3.messaging import TextMessage

from src.services.suggestion_service import SuggestionService


class TestSuggestionService:
    """SuggestionService 測試類"""

    @pytest.fixture
    def mock_ai_service(self):
        """模擬 AI 服務"""
        ai_service = AsyncMock()
        ai_service.enhance_natural_language_query = AsyncMock()
        return ai_service

    @pytest.fixture
    def mock_formatter(self):
        """模擬訊息格式化器"""
        formatter = MagicMock()
        formatter.format_suggestion_message.return_value = TextMessage(
            text="基本建議訊息"
        )
        return formatter

    @pytest.fixture
    def suggestion_service(self, mock_ai_service, mock_formatter):
        """建議服務實例"""
        return SuggestionService(
            ai_model_service=mock_ai_service,
            message_formatter=mock_formatter
        )

    @pytest.fixture
    def suggestion_service_no_ai(self, mock_formatter):
        """沒有 AI 服務的建議服務"""
        return SuggestionService(
            ai_model_service=None,
            message_formatter=mock_formatter
        )

    @pytest.mark.asyncio
    async def test_ai_suggestion_success(self, suggestion_service, mock_ai_service):
        """測試 AI 建議生成成功"""
        # 準備
        user_input = "查詢某個奇怪的東西"
        mock_ai_service.enhance_natural_language_query.return_value = (
            "💡 我理解您想查詢機台資訊\n\n🔍 請提供具體機台編號", 
            0.8
        )

        # 執行
        result = await suggestion_service.generate_suggestion(user_input)

        # 驗證
        assert isinstance(result, TextMessage)
        assert "💡 我理解您想查詢機台資訊" in result.text
        mock_ai_service.enhance_natural_language_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_ai_suggestion_failure_fallback(self, suggestion_service, mock_ai_service):
        """測試 AI 建議失敗時的回退機制"""
        # 準備
        user_input = "機台相關查詢"
        mock_ai_service.enhance_natural_language_query.side_effect = Exception("AI 服務失敗")

        # 執行
        result = await suggestion_service.generate_suggestion(user_input)

        # 驗證 - 應該回退到智能靜態建議
        assert isinstance(result, TextMessage)
        assert "機台" in result.text or "建議" in result.text
        mock_ai_service.enhance_natural_language_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_ai_service_fallback(self, suggestion_service_no_ai):
        """測試沒有 AI 服務時直接使用靜態建議"""
        # 執行
        result = await suggestion_service_no_ai.generate_suggestion("機台查詢")

        # 驗證 - 直接使用智能靜態建議
        assert isinstance(result, TextMessage)
        assert "建議" in result.text

    def test_smart_suggestion_machine_keywords(self, suggestion_service_no_ai):
        """測試機台關鍵詞的智能建議"""
        # 執行
        result = suggestion_service_no_ai._generate_smart_suggestion("查詢機台狀況")

        # 驗證
        assert isinstance(result, TextMessage)
        assert "機台" in result.text
        assert "M001" in result.text  # 應該包含範例機台編號

    def test_smart_suggestion_fault_keywords(self, suggestion_service_no_ai):
        """測試故障關鍵詞的智能建議"""
        # 執行
        result = suggestion_service_no_ai._generate_smart_suggestion("查詢故障記錄")

        # 驗證
        assert isinstance(result, TextMessage)
        assert "故障" in result.text
        assert "時間範圍" in result.text

    def test_smart_suggestion_department_keywords(self, suggestion_service_no_ai):
        """測試部門關鍵詞的智能建議"""
        # 執行
        result = suggestion_service_no_ai._generate_smart_suggestion("加工部狀況")

        # 驗證
        assert isinstance(result, TextMessage)
        assert "部門" in result.text
        assert "加工部" in result.text

    def test_smart_suggestion_statistics_keywords(self, suggestion_service_no_ai):
        """測試統計關鍵詞的智能建議"""
        # 執行
        result = suggestion_service_no_ai._generate_smart_suggestion("生產統計報告")

        # 驗證
        assert isinstance(result, TextMessage)
        assert "統計" in result.text or "報告" in result.text

    def test_smart_suggestion_general(self, suggestion_service_no_ai):
        """測試通用建議"""
        # 執行
        result = suggestion_service_no_ai._generate_smart_suggestion("不知道什麼")

        # 驗證
        assert isinstance(result, TextMessage)
        assert "查詢" in result.text
        assert "機台" in result.text

    def test_basic_suggestion_fallback(self):
        """測試基本建議回退"""
        # 沒有任何依賴的服務
        service = SuggestionService()

        # 執行
        result = service._generate_basic_suggestion()

        # 驗證
        assert isinstance(result, TextMessage)
        assert "建議" in result.text or "查詢" in result.text

    def test_update_ai_service(self, suggestion_service):
        """測試 AI 服務更新"""
        # 準備
        new_ai_service = AsyncMock()

        # 執行
        suggestion_service.update_ai_service(new_ai_service)

        # 驗證
        assert suggestion_service._ai_service == new_ai_service
        assert suggestion_service._enable_ai_suggestions is True

    def test_update_ai_service_to_none(self, suggestion_service):
        """測試禁用 AI 服務"""
        # 執行
        suggestion_service.update_ai_service(None)

        # 驗證
        assert suggestion_service._ai_service is None
        assert suggestion_service._enable_ai_suggestions is False

    def test_get_service_info(self, suggestion_service):
        """測試服務資訊獲取"""
        # 執行
        info = suggestion_service.get_service_info()

        # 驗證
        assert info["name"] == "SuggestionService"
        assert info["version"] == "1.0.0"
        assert "ai_enabled" in info
        assert "capabilities" in info
        assert len(info["capabilities"]) > 0

    @pytest.mark.asyncio
    async def test_ai_suggestion_empty_response(self, suggestion_service, mock_ai_service):
        """測試 AI 返回空回應時的處理"""
        # 準備
        user_input = "測試查詢"
        mock_ai_service.enhance_natural_language_query.return_value = ("", 0.5)

        # 執行
        result = await suggestion_service.generate_suggestion(user_input)

        # 驗證 - 應該回退到智能靜態建議
        assert isinstance(result, TextMessage)
        assert "建議" in result.text

    @pytest.mark.asyncio
    async def test_ai_suggestion_non_string_response(self, suggestion_service, mock_ai_service):
        """測試 AI 返回非字符串回應時的處理"""
        # 準備
        user_input = "測試查詢"
        mock_ai_service.enhance_natural_language_query.return_value = (None, 0.5)

        # 執行
        result = await suggestion_service.generate_suggestion(user_input)

        # 驗證 - 應該回退到智能靜態建議
        assert isinstance(result, TextMessage)
        assert "建議" in result.text

    def test_build_ai_system_prompt(self, suggestion_service):
        """測試 AI 系統提示建構"""
        # 執行
        prompt = suggestion_service._build_ai_system_prompt()

        # 驗證
        assert "製造業" in prompt
        assert "查詢助手" in prompt
        assert "建議" in prompt

    def test_build_user_analysis_prompt(self, suggestion_service):
        """測試用戶分析提示建構"""
        # 執行
        user_input = "測試查詢"
        prompt = suggestion_service._build_user_analysis_prompt(user_input)

        # 驗證
        assert user_input in prompt
        assert "機台狀態查詢" in prompt
        assert "故障分析" in prompt

    @pytest.mark.asyncio
    async def test_generate_suggestion_with_context(self, suggestion_service, mock_ai_service):
        """測試帶上下文的建議生成"""
        # 準備
        user_input = "查詢測試"
        context = {"database_schema": {"machines": ["id", "status"]}}
        mock_ai_service.enhance_natural_language_query.return_value = (
            "根據資料庫結構的建議", 0.8
        )

        # 執行
        result = await suggestion_service.generate_suggestion(user_input, context)

        # 驗證
        assert isinstance(result, TextMessage)
        mock_ai_service.enhance_natural_language_query.assert_called_once()
        
        # 檢查是否傳遞了資料庫結構
        call_args = mock_ai_service.enhance_natural_language_query.call_args
        assert call_args[0][1] == context["database_schema"]


class TestSuggestionServiceIntegration:
    """SuggestionService 整合測試"""

    @pytest.mark.asyncio
    async def test_full_suggestion_flow_without_ai(self):
        """測試完整建議流程（無 AI）"""
        # 準備 - 只有格式化器的服務
        formatter = MagicMock()
        formatter.format_suggestion_message.return_value = TextMessage(text="基本建議")
        
        service = SuggestionService(ai_model_service=None, message_formatter=formatter)

        # 執行多種查詢
        test_cases = [
            "機台M001狀況",
            "故障記錄查詢", 
            "加工部門狀況",
            "生產統計",
            "不明查詢"
        ]

        for query in test_cases:
            result = await service.generate_suggestion(query)
            assert isinstance(result, TextMessage)
            assert len(result.text) > 10  # 確保有實際內容

    def test_keyword_analysis_coverage(self):
        """測試關鍵詞分析覆蓋度"""
        service = SuggestionService()

        # 測試各種關鍵詞組合
        keyword_tests = [
            ("機台設備", "機台"),
            ("故障問題", "故障"),
            ("加工部", "部門"),
            ("統計報告", "統計"),
            ("Machine Status", "machine"),  # 英文關鍵詞
            ("unknown query", None)  # 無關鍵詞
        ]

        for query, expected_keyword in keyword_tests:
            result = service._generate_smart_suggestion(query)
            assert isinstance(result, TextMessage)
            if expected_keyword:
                assert expected_keyword in result.text or "建議" in result.text