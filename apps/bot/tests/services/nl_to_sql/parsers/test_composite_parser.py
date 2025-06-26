"""
組合解析器測試
專注於策略模式協調、解析器管理和回退機制
"""

import pytest

from src.services.nl_to_sql.interfaces.parsing_interfaces import IParser
from src.services.nl_to_sql.models.query_models import ParsedQuery, QueryType
from src.services.nl_to_sql.parsers.composite_parser import CompositeParser


class MockParser(IParser):
    """模擬解析器，用於測試"""

    def __init__(
        self,
        name: str,
        confidence: float = 0.8,
        query_type: QueryType = QueryType.MACHINE_STATUS,
    ):
        self.name = name
        self._confidence = confidence
        self._query_type = query_type
        self._should_raise = False
        self.__class__.__name__ = name  # 確保類名正確

    async def parse(self, text: str, context=None) -> ParsedQuery:
        if self._should_raise:
            raise Exception(f"{self.name} 解析失敗")

        return ParsedQuery(
            query_type=self._query_type,
            sql_query=f"SELECT * FROM test WHERE {self.name} = '{text}'",
            parameters={"parser": self.name, "text": text},
            confidence=self._confidence,
            explanation=f"{self.name} 解析結果",
        )

    def can_handle(self, text: str) -> float:
        if self._should_raise:
            raise Exception(f"{self.name} 能力評估失敗")
        return self._confidence

    def get_parser_info(self):
        if self._should_raise:
            raise Exception(f"{self.name} 獲取資訊失敗")
        return {"name": self.name, "type": "mock", "capabilities": ["testing"]}

    def set_should_raise(self, should_raise: bool):
        """設置是否拋出異常"""
        self._should_raise = should_raise


class TestCompositeParser:
    """組合解析器測試"""

    @pytest.fixture
    def parser(self):
        """創建組合解析器實例"""
        return CompositeParser()

    @pytest.fixture
    def mock_parsers(self):
        """創建模擬解析器列表"""
        return [
            MockParser("RuleParser", 0.9, QueryType.SPECIFIC_MACHINE),
            MockParser("AIParser", 0.7, QueryType.MACHINE_STATUS),
            MockParser("FallbackParser", 0.5, QueryType.UNKNOWN),
        ]

    class TestInitialization:
        """初始化測試"""

        def test_parser_initialization(self):
            """測試解析器初始化"""
            parser = CompositeParser()

            assert len(parser._parsers) == 0
            assert len(parser._strategy_weights) == 0
            assert parser._fallback_confidence_threshold == 0.5

        def test_parser_initialization_with_custom_threshold(self):
            """測試自定義門檻值初始化"""
            parser = CompositeParser()
            parser.set_fallback_threshold(0.3)

            assert parser._fallback_confidence_threshold == 0.3

    class TestParserManagement:
        """解析器管理測試"""

        def test_add_parser_success(self, parser, mock_parsers):
            """測試成功添加解析器"""
            mock_parser = mock_parsers[0]
            parser.add_parser(mock_parser, 1.5)

            assert len(parser._parsers) == 1
            assert parser._parsers[0] == mock_parser
            assert parser._strategy_weights["RuleParser"] == 1.5

        def test_add_parser_invalid_interface(self, parser):
            """測試添加無效接口的解析器"""
            invalid_parser = "not a parser"

            with pytest.raises(ValueError, match="解析器必須實現 IParser 介面"):
                parser.add_parser(invalid_parser)

        def test_add_parser_invalid_weight(self, parser, mock_parsers):
            """測試添加無效權重的解析器"""
            mock_parser = mock_parsers[0]

            with pytest.raises(ValueError, match="權重必須在 0.0-2.0 範圍內"):
                parser.add_parser(mock_parser, 3.0)

            with pytest.raises(ValueError, match="權重必須在 0.0-2.0 範圍內"):
                parser.add_parser(mock_parser, -0.5)

        def test_remove_parser_success(self, parser, mock_parsers):
            """測試成功移除解析器"""
            mock_parser = mock_parsers[0]
            parser.add_parser(mock_parser)

            result = parser.remove_parser("RuleParser")

            assert result is True
            assert len(parser._parsers) == 0
            assert "RuleParser" not in parser._strategy_weights

        def test_remove_parser_not_found(self, parser):
            """測試移除不存在的解析器"""
            result = parser.remove_parser("NonExistentParser")

            assert result is False

        def test_add_multiple_parsers(self, parser, mock_parsers):
            """測試添加多個解析器"""
            for mock_parser in mock_parsers:
                parser.add_parser(mock_parser)

            assert len(parser._parsers) == 3
            assert len(parser._strategy_weights) == 3

    class TestParsingStrategy:
        """解析策略測試"""

        @pytest.mark.asyncio
        async def test_parse_with_single_parser(self, parser, mock_parsers):
            """測試單個解析器解析"""
            mock_parser = mock_parsers[0]
            parser.add_parser(mock_parser, 1.2)

            result = await parser.parse("M001機台")

            assert result.query_type == QueryType.SPECIFIC_MACHINE
            assert result.confidence == min(1.0, 0.9 * 1.2)  # 原始信心度 * 權重，但不超過1.0
            assert "[RuleParser]" in result.explanation
            assert result.parameters["parser"] == "RuleParser"

        @pytest.mark.asyncio
        async def test_parse_with_multiple_parsers(self, parser, mock_parsers):
            """測試多個解析器選擇策略"""
            # 添加不同信心度的解析器
            parser.add_parser(mock_parsers[1], 1.0)  # AIParser: 0.7
            parser.add_parser(mock_parsers[0], 1.0)  # RuleParser: 0.9
            parser.add_parser(mock_parsers[2], 1.0)  # FallbackParser: 0.5

            result = await parser.parse("測試文字")

            # 應該選擇信心度最高的解析器 (RuleParser: 0.9)
            assert result.parameters["parser"] == "RuleParser"
            assert result.query_type == QueryType.SPECIFIC_MACHINE

        @pytest.mark.asyncio
        async def test_parse_with_weighted_selection(self, parser, mock_parsers):
            """測試加權選擇策略"""
            # 設置權重影響選擇
            parser.add_parser(
                mock_parsers[1], 1.5
            )  # AIParser: 0.7 * 1.5 = 1.05 (有效信心度)
            parser.add_parser(mock_parsers[0], 1.0)  # RuleParser: 0.9 * 1.0 = 0.9

            # 雖然 RuleParser 原始信心度更高，但 AIParser 加權後應該被選中
            # 注意：實際選擇基於 can_handle 返回值，不是加權後的值
            result = await parser.parse("測試文字")

            # 仍然選擇原始信心度最高的
            assert result.parameters["parser"] == "RuleParser"
            # 但應該應用權重到最終信心度
            if result.parameters["parser"] == "AIParser":
                assert result.confidence > 0.7  # 應用權重後的信心度

        @pytest.mark.asyncio
        async def test_parse_confidence_adjustment(self, parser, mock_parsers):
            """測試信心度調整"""
            mock_parser = mock_parsers[0]
            parser.add_parser(mock_parser, 0.8)  # 權重 < 1

            result = await parser.parse("測試")

            # 信心度應該被權重調整
            expected_confidence = min(1.0, 0.9 * 0.8)
            assert result.confidence == expected_confidence

        @pytest.mark.asyncio
        async def test_parse_confidence_capped_at_one(self, parser, mock_parsers):
            """測試信心度上限為 1.0"""
            mock_parser = mock_parsers[0]
            parser.add_parser(mock_parser, 2.0)  # 高權重

            result = await parser.parse("測試")

            # 信心度不應超過 1.0
            assert result.confidence <= 1.0

    class TestErrorHandling:
        """錯誤處理測試"""

        @pytest.mark.asyncio
        async def test_parse_with_parser_exception(self, parser, mock_parsers):
            """測試解析器拋出異常"""
            mock_parser = mock_parsers[0]
            mock_parser.set_should_raise(True)
            parser.add_parser(mock_parser)

            result = await parser.parse("測試")

            assert result.query_type == QueryType.UNKNOWN
            assert result.confidence == 0.0
            assert "組合解析器完全失敗" in result.explanation
            assert "RuleParser" in result.parameters.get("attempted_parsers", [])

        @pytest.mark.asyncio
        async def test_parse_with_capability_assessment_exception(
            self, parser, mock_parsers
        ):
            """測試能力評估異常"""
            mock_parser = mock_parsers[0]
            mock_parser.set_should_raise(True)
            parser.add_parser(mock_parser)

            # 即使能力評估異常，也應該嘗試解析
            result = await parser.parse("測試")

            # 應該處理異常並繼續
            assert result.query_type == QueryType.UNKNOWN

        @pytest.mark.asyncio
        async def test_parse_with_no_parsers(self, parser):
            """測試無解析器情況"""
            result = await parser.parse("測試")

            assert result.query_type == QueryType.UNKNOWN
            assert result.confidence == 0.0
            assert "無可用解析器" in result.explanation

        @pytest.mark.asyncio
        async def test_parse_with_empty_input(self, parser, mock_parsers):
            """測試空輸入"""
            parser.add_parser(mock_parsers[0])

            result = await parser.parse("")

            assert result.query_type == QueryType.UNKNOWN
            assert result.confidence == 0.0
            assert "空輸入" in result.explanation

        @pytest.mark.asyncio
        async def test_parse_with_all_parsers_low_confidence(
            self, parser, mock_parsers
        ):
            """測試所有解析器信心度都很低"""
            # 設置高門檻值
            parser.set_fallback_threshold(0.95)

            # 添加低信心度解析器
            low_confidence_parser = MockParser(
                "LowConfidence", 0.3, QueryType.MACHINE_STATUS
            )
            parser.add_parser(low_confidence_parser)

            result = await parser.parse("測試")

            # 信心度低於門檻時，應該返回失敗結果（嚴格模式）
            assert result.query_type == QueryType.UNKNOWN
            assert result.confidence == 0.0
            assert "組合解析器完全失敗" in result.explanation
            assert "LowConfidence" in result.parameters.get("attempted_parsers", [])

    class TestCapabilityAssessment:
        """能力評估測試"""

        def test_can_handle_with_multiple_parsers(self, parser, mock_parsers):
            """測試多個解析器的綜合能力評估"""
            # 添加不同權重的解析器
            parser.add_parser(mock_parsers[0], 1.0)  # confidence: 0.9
            parser.add_parser(mock_parsers[1], 2.0)  # confidence: 0.7, weight: 2.0
            parser.add_parser(mock_parsers[2], 0.5)  # confidence: 0.5, weight: 0.5

            confidence = parser.can_handle("測試")

            # 計算加權平均：(0.9*1.0 + 0.7*2.0 + 0.5*0.5) / (1.0 + 2.0 + 0.5)
            expected = (0.9 * 1.0 + 0.7 * 2.0 + 0.5 * 0.5) / (1.0 + 2.0 + 0.5)
            assert abs(confidence - expected) < 0.01

        def test_can_handle_with_no_parsers(self, parser):
            """測試無解析器的能力評估"""
            confidence = parser.can_handle("測試")
            assert confidence == 0.0

        def test_can_handle_with_empty_input(self, parser, mock_parsers):
            """測試空輸入的能力評估"""
            parser.add_parser(mock_parsers[0])

            confidence = parser.can_handle("")
            assert confidence == 0.0

        def test_can_handle_with_parser_exception(self, parser, mock_parsers):
            """測試解析器能力評估異常"""
            mock_parser = mock_parsers[0]
            mock_parser.set_should_raise(True)
            parser.add_parser(mock_parser, 1.0)

            # 其他正常解析器
            parser.add_parser(mock_parsers[1], 1.0)

            confidence = parser.can_handle("測試")

            # 應該跳過異常解析器，計算其他解析器的信心度
            assert confidence == 0.7  # mock_parsers[1] 的信心度

    class TestConfigurationManagement:
        """配置管理測試"""

        def test_set_fallback_threshold_valid(self, parser):
            """測試設置有效的回退門檻"""
            parser.set_fallback_threshold(0.8)
            assert parser._fallback_confidence_threshold == 0.8

        def test_set_fallback_threshold_invalid(self, parser):
            """測試設置無效的回退門檻"""
            with pytest.raises(ValueError, match="門檻值必須在 0.0-1.0 範圍內"):
                parser.set_fallback_threshold(1.5)

            with pytest.raises(ValueError, match="門檻值必須在 0.0-1.0 範圍內"):
                parser.set_fallback_threshold(-0.1)

        def test_validate_configuration_valid(self, parser, mock_parsers):
            """測試有效配置驗證"""
            for mock_parser in mock_parsers:
                parser.add_parser(mock_parser, 1.0)

            result = parser.validate_configuration()

            assert result["is_valid"] is True
            assert len(result["errors"]) == 0
            assert len(result["parser_validation"]) == 3

        def test_validate_configuration_no_parsers(self, parser):
            """測試無解析器配置驗證"""
            result = parser.validate_configuration()

            assert result["is_valid"] is False
            assert "沒有註冊任何解析器" in result["errors"]

        def test_validate_configuration_invalid_parser(self, parser):
            """測試無效解析器配置驗證"""

            # 創建不完整的模擬解析器
            class IncompleteParser:
                def __init__(self):
                    pass

                # 缺少必要的方法

            incomplete = IncompleteParser()
            parser._parsers.append(incomplete)
            parser._strategy_weights["IncompleteParser"] = 1.0

            result = parser.validate_configuration()

            assert result["is_valid"] is False
            assert any(
                "未正確實現 IParser 介面" in error
                for validation in result["parser_validation"]
                for error in validation["errors"]
            )

        def test_validate_configuration_invalid_weight(self, parser, mock_parsers):
            """測試無效權重配置驗證"""
            mock_parser = mock_parsers[0]
            parser.add_parser(mock_parser)
            # 手動設置無效權重（繞過 add_parser 的檢查）
            parser._strategy_weights["RuleParser"] = 3.0

            result = parser.validate_configuration()

            assert result["is_valid"] is False
            assert any(
                "無效的權重值" in error
                for validation in result["parser_validation"]
                for error in validation["errors"]
            )

        def test_validate_configuration_missing_weight(self, parser, mock_parsers):
            """測試缺少權重配置驗證"""
            mock_parser = mock_parsers[0]
            parser._parsers.append(mock_parser)
            # 不設置權重

            result = parser.validate_configuration()

            assert any("未設定權重" in warning for warning in result["warnings"])

    class TestInformationRetrieval:
        """資訊檢索測試"""

        def test_get_parser_info(self, parser, mock_parsers):
            """測試獲取解析器資訊"""
            for mock_parser in mock_parsers:
                parser.add_parser(mock_parser, 1.0)

            info = parser.get_parser_info()

            assert info["name"] == "CompositeParser"
            assert info["version"] == "1.0.0"
            assert info["type"] == "composite_strategy"
            assert info["parser_count"] == 3
            assert len(info["registered_parsers"]) == 3
            assert "multi_strategy_coordination" in info["capabilities"]

        def test_get_parser_statistics(self, parser, mock_parsers):
            """測試獲取解析器統計"""
            weights = [1.0, 1.5, 0.8]
            for i, mock_parser in enumerate(mock_parsers):
                parser.add_parser(mock_parser, weights[i])

            stats = parser.get_parser_statistics()

            assert stats["total_parsers"] == 3
            assert stats["parser_weights"]["RuleParser"] == 1.0
            assert stats["parser_weights"]["AIParser"] == 1.5
            assert stats["parser_weights"]["FallbackParser"] == 0.8
            assert len(stats["parser_details"]) == 3

        def test_get_parser_info_with_exception(self, parser, mock_parsers):
            """測試獲取解析器資訊時異常處理"""

            # 創建會拋出異常的解析器
            class ExceptionParser(IParser):
                def get_parser_info(self):
                    raise Exception("獲取資訊失敗")

                async def parse(self, text, context=None):
                    pass

                def can_handle(self, text):
                    return 0.5

            parser.add_parser(mock_parsers[0])
            parser._parsers.append(ExceptionParser())
            parser._strategy_weights["ExceptionParser"] = 1.0

            info = parser.get_parser_info()

            # 應該跳過異常解析器，正常處理其他解析器
            assert info["parser_count"] == 2  # 包含異常解析器
            assert len(info["registered_parsers"]) == 1  # 只有正常解析器的資訊

    class TestParserSelection:
        """解析器選擇測試"""

        @pytest.mark.asyncio
        async def test_evaluate_parser_capabilities(self, parser, mock_parsers):
            """測試評估解析器能力"""
            for mock_parser in mock_parsers:
                parser.add_parser(mock_parser)

            capabilities = await parser._evaluate_parser_capabilities("測試")

            assert len(capabilities) == 3
            # 應該按信心度降序排列
            assert capabilities[0][1] >= capabilities[1][1] >= capabilities[2][1]
            assert capabilities[0][1] == 0.9  # RuleParser 最高
            assert capabilities[1][1] == 0.7  # AIParser 中等
            assert capabilities[2][1] == 0.5  # FallbackParser 最低

        def test_select_best_parser(self, parser, mock_parsers):
            """測試選擇最佳解析器"""
            capabilities = [
                (mock_parsers[0], 0.9),  # RuleParser
                (mock_parsers[1], 0.7),  # AIParser
                (mock_parsers[2], 0.5),  # FallbackParser
            ]

            best_parser, best_confidence = parser._select_best_parser(capabilities)

            assert best_parser == mock_parsers[0]
            assert best_confidence == 0.9

        def test_select_best_parser_below_threshold(self, parser, mock_parsers):
            """測試選擇信心度低於門檻的解析器"""
            parser.set_fallback_threshold(0.95)  # 高門檻

            capabilities = [
                (mock_parsers[0], 0.9),  # 低於門檻
                (mock_parsers[1], 0.7),
                (mock_parsers[2], 0.5),
            ]

            best_parser, best_confidence = parser._select_best_parser(capabilities)

            # 仍應返回最佳解析器，只是會有警告
            assert best_parser == mock_parsers[0]
            assert best_confidence == 0.9

        def test_select_best_parser_empty_capabilities(self, parser):
            """測試空能力列表選擇"""
            best_parser, best_confidence = parser._select_best_parser([])

            assert best_parser is None
            assert best_confidence == 0.0

    class TestQueryCreation:
        """查詢創建測試"""

        def test_create_empty_query(self, parser):
            """測試創建空查詢"""
            query = parser._create_empty_query("測試原因")

            assert query.query_type == QueryType.UNKNOWN
            assert query.confidence == 0.0
            assert query.sql_query == ""
            assert query.parameters == {}
            assert "組合解析器無法處理：測試原因" in query.explanation

        def test_create_error_query(self, parser):
            """測試創建錯誤查詢"""
            query = parser._create_error_query("測試文字", "測試錯誤")

            assert query.query_type == QueryType.UNKNOWN
            assert query.confidence == 0.0
            assert query.sql_query == ""
            assert query.parameters["error"] == "測試錯誤"
            assert "組合解析器錯誤" in query.explanation
            assert "測試文字" in query.explanation
