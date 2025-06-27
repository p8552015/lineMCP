#!/usr/bin/env python3
"""
CompositeParser 回退機制測試

專門測試新增的回退功能：
- 多解析器順序嘗試
- 結果有效性檢查
- 完全失敗時的回退處理
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.nl_to_sql.parsers.composite_parser import CompositeParser
from src.services.nl_to_sql.models.query_models import ParsedQuery, QueryType


class MockParser:
    """模擬解析器"""
    
    def __init__(self, name: str, can_handle_score: float, parse_result: ParsedQuery = None, should_fail: bool = False):
        self.name = name
        self._can_handle_score = can_handle_score
        self._parse_result = parse_result
        self._should_fail = should_fail
    
    def can_handle(self, text: str) -> float:
        return self._can_handle_score
    
    async def parse(self, text: str, context=None) -> ParsedQuery:
        if self._should_fail:
            raise Exception(f"Parser {self.name} failed")
        return self._parse_result or ParsedQuery(
            query_type=QueryType.UNKNOWN,
            sql_query="",
            parameters={},
            confidence=0.0,
            explanation=f"Mock result from {self.name}"
        )
    
    def get_parser_info(self):
        return {
            "name": self.name,
            "type": "mock",
            "capabilities": ["test"]
        }


class TestCompositeParserFallback:
    """CompositeParser 回退機制測試"""

    @pytest.fixture
    def composite_parser(self):
        """創建組合解析器實例"""
        return CompositeParser()

    def test_valid_result_detection(self, composite_parser):
        """測試有效結果檢測"""
        # 有效結果
        valid_result = ParsedQuery(
            query_type=QueryType.MACHINE_STATUS,
            sql_query="SELECT * FROM machines",
            parameters={},
            confidence=0.8,
            explanation="Valid query"
        )
        assert composite_parser._is_valid_result(valid_result) is True

        # 無效結果 - UNKNOWN 類型
        invalid_result = ParsedQuery(
            query_type=QueryType.UNKNOWN,
            sql_query="",
            parameters={},
            confidence=0.0,
            explanation="Unknown"
        )
        assert composite_parser._is_valid_result(invalid_result) is False

        # 無效結果 - 零信心度
        zero_confidence = ParsedQuery(
            query_type=QueryType.MACHINE_STATUS,
            sql_query="SELECT * FROM machines",
            parameters={},
            confidence=0.0,
            explanation="Zero confidence"
        )
        assert composite_parser._is_valid_result(zero_confidence) is False

        # 無效結果 - 包含錯誤
        error_result = ParsedQuery(
            query_type=QueryType.MACHINE_STATUS,
            sql_query="",
            parameters={"error": "Something went wrong"},
            confidence=0.5,
            explanation="Error occurred"
        )
        assert composite_parser._is_valid_result(error_result) is False

        # 邊界情況 - None
        assert composite_parser._is_valid_result(None) is False

    def test_fallback_query_creation(self, composite_parser):
        """測試回退查詢創建"""
        # 準備
        attempted_parsers = [
            (MockParser("AIParser", 0.8), 0.8),
            (MockParser("RuleParser", 0.6), 0.6)
        ]
        
        # 執行
        result = composite_parser._create_fallback_query("test query", attempted_parsers)
        
        # 驗證
        assert result.query_type == QueryType.UNKNOWN
        assert result.confidence == 0.0
        assert "test query" in result.parameters["original_text"]
        assert "AIParser" in result.parameters["attempted_parsers"]
        assert "RuleParser" in result.parameters["attempted_parsers"]
        assert "所有解析器都無法成功處理" in result.parameters["fallback_reason"]

    @pytest.mark.asyncio
    async def test_successful_first_parser(self, composite_parser):
        """測試第一個解析器成功的情況"""
        # 準備
        successful_result = ParsedQuery(
            query_type=QueryType.MACHINE_STATUS,
            sql_query="SELECT * FROM machines WHERE id = 'M001'",
            parameters={"machine_id": "M001"},
            confidence=0.9,
            explanation="Successful parse"
        )
        
        high_confidence_parser = MockParser("HighParser", 0.8, successful_result)
        low_confidence_parser = MockParser("LowParser", 0.3)
        
        composite_parser.add_parser(high_confidence_parser, 1.0)
        composite_parser.add_parser(low_confidence_parser, 1.0)
        
        # 執行
        result = await composite_parser.parse("M001機台狀況")
        
        # 驗證 - 應該使用第一個成功的解析器
        assert result.query_type == QueryType.MACHINE_STATUS
        assert result.confidence > 0.0
        assert "[HighParser]" in result.explanation

    @pytest.mark.asyncio
    async def test_fallback_to_second_parser(self, composite_parser):
        """測試回退到第二個解析器"""
        # 準備
        failing_result = ParsedQuery(
            query_type=QueryType.UNKNOWN,
            sql_query="",
            parameters={"error": "AI service failed"},
            confidence=0.0,
            explanation="Failed to parse"
        )
        
        successful_result = ParsedQuery(
            query_type=QueryType.MACHINE_STATUS,
            sql_query="SELECT * FROM machines",
            parameters={},
            confidence=0.7,
            explanation="Rule-based parse"
        )
        
        failing_parser = MockParser("FailingParser", 0.9, failing_result)
        successful_parser = MockParser("BackupParser", 0.6, successful_result)
        
        composite_parser.add_parser(failing_parser, 1.0)
        composite_parser.add_parser(successful_parser, 1.0)
        
        # 執行
        result = await composite_parser.parse("機台狀況查詢")
        
        # 驗證 - 應該回退到第二個解析器
        assert result.query_type == QueryType.MACHINE_STATUS
        assert result.confidence > 0.0
        assert "[BackupParser]" in result.explanation

    @pytest.mark.asyncio
    async def test_exception_handling_fallback(self, composite_parser):
        """測試異常處理和回退"""
        # 準備
        successful_result = ParsedQuery(
            query_type=QueryType.MACHINE_STATUS,
            sql_query="SELECT * FROM machines",
            parameters={},
            confidence=0.6,
            explanation="Backup successful"
        )
        
        exception_parser = MockParser("ExceptionParser", 0.8, should_fail=True)
        backup_parser = MockParser("BackupParser", 0.5, successful_result)
        
        composite_parser.add_parser(exception_parser, 1.0)
        composite_parser.add_parser(backup_parser, 1.0)
        
        # 執行
        result = await composite_parser.parse("測試查詢")
        
        # 驗證 - 應該跳過異常解析器，使用備用解析器
        assert result.query_type == QueryType.MACHINE_STATUS
        assert "[BackupParser]" in result.explanation

    @pytest.mark.asyncio
    async def test_all_parsers_fail(self, composite_parser):
        """測試所有解析器都失敗的情況"""
        # 準備
        failing_result1 = ParsedQuery(
            query_type=QueryType.UNKNOWN,
            sql_query="",
            parameters={},
            confidence=0.0,
            explanation="Failed 1"
        )
        
        failing_result2 = ParsedQuery(
            query_type=QueryType.UNKNOWN,
            sql_query="",
            parameters={"error": "Parse error"},
            confidence=0.0,
            explanation="Failed 2"
        )
        
        parser1 = MockParser("Parser1", 0.8, failing_result1)
        parser2 = MockParser("Parser2", 0.6, failing_result2)
        
        composite_parser.add_parser(parser1, 1.0)
        composite_parser.add_parser(parser2, 1.0)
        
        # 執行
        result = await composite_parser.parse("無法解析的查詢")
        
        # 驗證 - 應該返回回退查詢
        assert result.query_type == QueryType.UNKNOWN
        assert result.confidence == 0.0
        assert "無法解析的查詢" in result.parameters["original_text"]
        assert "Parser1" in result.parameters["attempted_parsers"]
        assert "Parser2" in result.parameters["attempted_parsers"]

    @pytest.mark.asyncio
    async def test_confidence_threshold_filtering(self, composite_parser):
        """測試信心度門檻過濾"""
        # 設定較高的門檻
        composite_parser.set_fallback_threshold(0.7)
        
        # 準備
        low_confidence_result = ParsedQuery(
            query_type=QueryType.MACHINE_STATUS,
            sql_query="SELECT * FROM machines",
            parameters={},
            confidence=0.8,
            explanation="Low confidence parser"
        )
        
        low_confidence_parser = MockParser("LowParser", 0.5, low_confidence_result)  # 低於門檻
        composite_parser.add_parser(low_confidence_parser, 1.0)
        
        # 執行
        result = await composite_parser.parse("測試查詢")
        
        # 驗證 - 應該跳過低信心度解析器，返回回退結果
        assert result.query_type == QueryType.UNKNOWN
        assert "LowParser" in result.parameters["attempted_parsers"]

    @pytest.mark.asyncio
    async def test_parser_weight_adjustment(self, composite_parser):
        """測試解析器權重調整"""
        # 準備
        base_result = ParsedQuery(
            query_type=QueryType.MACHINE_STATUS,
            sql_query="SELECT * FROM machines",
            parameters={},
            confidence=0.6,
            explanation="Base result"
        )
        
        weighted_parser = MockParser("WeightedParser", 0.7, base_result)
        composite_parser.add_parser(weighted_parser, 1.5)  # 1.5倍權重
        
        # 執行
        result = await composite_parser.parse("測試查詢")
        
        # 驗證 - 信心度應該被權重調整
        assert result.confidence == min(1.0, 0.6 * 1.5)  # 0.9
        assert "[WeightedParser]" in result.explanation

    @pytest.mark.asyncio
    async def test_empty_input_handling(self, composite_parser):
        """測試空輸入處理"""
        # 準備解析器
        parser = MockParser("TestParser", 0.8)
        composite_parser.add_parser(parser, 1.0)
        
        # 測試空字符串
        result = await composite_parser.parse("")
        assert result.query_type == QueryType.UNKNOWN
        assert "空輸入" in result.explanation
        
        # 測試只有空白的字符串
        result = await composite_parser.parse("   ")
        assert result.query_type == QueryType.UNKNOWN
        assert "空輸入" in result.explanation

    @pytest.mark.asyncio
    async def test_no_parsers_registered(self, composite_parser):
        """測試沒有註冊解析器的情況"""
        # 執行 - 沒有添加任何解析器
        result = await composite_parser.parse("測試查詢")
        
        # 驗證
        assert result.query_type == QueryType.UNKNOWN
        assert "無可用解析器" in result.explanation

    def test_parser_sorting_by_confidence(self, composite_parser):
        """測試解析器按信心度排序"""
        # 準備不同信心度的解析器
        parser_high = MockParser("HighParser", 0.9)
        parser_medium = MockParser("MediumParser", 0.6) 
        parser_low = MockParser("LowParser", 0.3)
        
        # 故意以錯誤順序添加
        composite_parser.add_parser(parser_medium, 1.0)
        composite_parser.add_parser(parser_high, 1.0)
        composite_parser.add_parser(parser_low, 1.0)
        
        # 執行能力評估
        import asyncio
        capabilities = asyncio.run(composite_parser._evaluate_parser_capabilities("測試"))
        
        # 驗證排序正確
        assert len(capabilities) == 3
        assert capabilities[0][1] == 0.9  # 最高信心度
        assert capabilities[1][1] == 0.6  # 中等信心度  
        assert capabilities[2][1] == 0.3  # 最低信心度


class TestCompositeParserFallbackIntegration:
    """CompositeParser 回退機制整合測試"""

    @pytest.mark.asyncio
    async def test_realistic_ai_to_rule_fallback(self):
        """測試現實場景：AI 解析器失敗回退到規則解析器"""
        composite = CompositeParser()
        
        # 模擬 AI 解析器（高信心度但會失敗）
        ai_result = ParsedQuery(
            query_type=QueryType.UNKNOWN,
            sql_query="",
            parameters={"error": "API rate limit exceeded"},
            confidence=0.0,
            explanation="AI service unavailable"
        )
        ai_parser = MockParser("AIEnhancedParser", 0.8, ai_result)
        
        # 模擬規則解析器（低信心度但穩定）
        rule_result = ParsedQuery(
            query_type=QueryType.MACHINE_STATUS,
            sql_query="SELECT * FROM machines WHERE machine_id = ?",
            parameters={"machine_id": "M001"},
            confidence=0.6,
            explanation="Rule-based parsing successful"
        )
        rule_parser = MockParser("RuleBasedParser", 0.5, rule_result)
        
        # 註冊解析器
        composite.add_parser(ai_parser, 1.2)  # AI 有較高權重
        composite.add_parser(rule_parser, 1.0)
        
        # 執行
        result = await composite.parse("M001機台狀況如何？")
        
        # 驗證 - 應該成功回退到規則解析器
        assert result.query_type == QueryType.MACHINE_STATUS
        assert result.confidence > 0.0
        assert "[RuleBasedParser]" in result.explanation
        assert "M001" in result.parameters["machine_id"]

    @pytest.mark.asyncio
    async def test_gradual_degradation(self):
        """測試逐步降級處理"""
        composite = CompositeParser()
        
        # 三層解析器：AI > 混合 > 基礎規則
        ai_parser = MockParser("AI", 0.9, should_fail=True)
        hybrid_parser = MockParser("Hybrid", 0.7, ParsedQuery(
            query_type=QueryType.UNKNOWN, sql_query="", parameters={}, confidence=0.0, explanation="Failed"
        ))
        basic_parser = MockParser("Basic", 0.4, ParsedQuery(
            query_type=QueryType.MACHINE_STATUS, sql_query="SELECT * FROM machines", 
            parameters={}, confidence=0.5, explanation="Basic rule match"
        ))
        
        composite.add_parser(ai_parser, 1.0)
        composite.add_parser(hybrid_parser, 1.0)
        composite.add_parser(basic_parser, 1.0)
        
        # 執行
        result = await composite.parse("查詢機台")
        
        # 驗證 - 應該最終使用基礎解析器
        assert result.query_type == QueryType.MACHINE_STATUS
        assert "[Basic]" in result.explanation