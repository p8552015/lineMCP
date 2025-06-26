#!/usr/bin/env python3
"""
SuggestionService 單元測試
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from linebot.v3.messaging import TextMessage

from src.services.suggestion_service import SuggestionService


class TestSuggestionService:
    """SuggestionService 測試類"""

    def test_basic_suggestion_fallback(self):
        """測試基本建議回退"""
        # 沒有任何依賴的服務
        service = SuggestionService()

        # 執行
        result = service._generate_basic_suggestion()

        # 驗證
        assert isinstance(result, TextMessage)
        assert "建議" in result.text or "查詢" in result.text

    def test_smart_suggestion_machine_keywords(self):
        """測試機台關鍵詞的智能建議"""
        service = SuggestionService()
        
        # 執行
        result = service._generate_smart_suggestion("查詢機台狀況")

        # 驗證
        assert isinstance(result, TextMessage)
        assert "機台" in result.text

    def test_service_initialization(self):
        """測試服務初始化"""
        service = SuggestionService()
        assert service is not None
        
        info = service.get_service_info()
        assert info["name"] == "SuggestionService"
        assert info["version"] == "1.0.0"
