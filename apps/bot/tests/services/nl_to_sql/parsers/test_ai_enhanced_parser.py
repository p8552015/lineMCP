"""
AI 增強解析器測試
專注於 AI 增強邏輯、邊界條件和錯誤處理
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock

from src.services.nl_to_sql.parsers.ai_enhanced_parser import AIEnhancedParser
from src.services.nl_to_sql.models.query_models import ParsedQuery, QueryType


class TestAIEnhancedParser:
    """AI 增強解析器測試"""

    @pytest.fixture
    def mock_ai_service(self):
        """模擬 AI 服務"""
        ai_service = Mock()
        ai_service.enhance_natural_language_query = AsyncMock()
        return ai_service

    @pytest.fixture
    def parser(self, mock_ai_service):
        """創建解析器實例"""
        return AIEnhancedParser(mock_ai_service)

    @pytest.fixture
    def parser_no_ai(self):
        """創建無 AI 服務的解析器實例"""
        return AIEnhancedParser(None)

    class TestInitialization:
        """初始化測試"""

        def test_parser_initialization_with_ai(self, mock_ai_service):
            """測試帶 AI 服務的初始化"""
            parser = AIEnhancedParser(mock_ai_service)

            assert parser._ai_service == mock_ai_service
            assert parser._system_prompt is not None
            assert len(parser._query_type_mapping) == 6

        def test_parser_initialization_without_ai(self):
            """測試無 AI 服務的初始化"""
            parser = AIEnhancedParser(None)

            assert parser._ai_service is None
            assert parser._system_prompt is not None

        def test_system_prompt_content(self, parser):
            """測試系統提示內容"""
            prompt = parser._system_prompt

            assert "machine_status" in prompt
            assert "fault_analysis" in prompt
            assert "JSON" in prompt
            assert "confidence" in prompt

    class TestJSONResponseParsing:
        """JSON 響應解析測試"""

        @pytest.mark.asyncio
        async def test_parse_valid_json_response(self, parser, mock_ai_service):
            """測試有效 JSON 響應解析"""
            # 模擬 AI 返回有效 JSON
            ai_response = {
                "query_type": "machine_status",
                "confidence": 0.85,
                "target_entities": ["機台"],
                "parameters": {"department": "加工部"},
                "explanation": "查詢機台狀態",
            }
            mock_ai_service.enhance_natural_language_query.return_value = (
                json.dumps(ai_response),
                0.85,
            )

            result = await parser.parse("機台狀態如何")

            assert result.query_type == QueryType.MACHINE_STATUS
            assert result.confidence == 0.85
            assert result.parameters["department"] == "加工部"
            assert "查詢機台狀態" in result.explanation

        @pytest.mark.asyncio
        async def test_parse_json_with_specific_machine(self, parser, mock_ai_service):
            """測試包含特定機台的 JSON 響應"""
            ai_response = {
                "query_type": "specific_machine",
                "confidence": 0.9,
                "target_entities": ["M001"],
                "parameters": {"machine_id": "M001"},
                "explanation": "查詢特定機台",
            }
            mock_ai_service.enhance_natural_language_query.return_value = (
                json.dumps(ai_response),
                0.9,
            )

            result = await parser.parse("M001機台狀況")

            assert result.query_type == QueryType.SPECIFIC_MACHINE
            assert result.parameters["machine_id"] == "M001"

        @pytest.mark.asyncio
        async def test_parse_invalid_json_response(self, parser, mock_ai_service):
            """測試無效 JSON 響應"""
            # 模擬 AI 返回無效 JSON
            mock_ai_service.enhance_natural_language_query.return_value = (
                "{invalid json format",
                0.8,
            )

            result = await parser.parse("機台狀態")

            # 應該回退到文字解析
            assert result.query_type != QueryType.UNKNOWN  # 應該能推斷出類型

        @pytest.mark.asyncio
        async def test_parse_json_with_unknown_query_type(
            self, parser, mock_ai_service
        ):
            """測試未知查詢類型的 JSON 響應"""
            ai_response = {
                "query_type": "unknown_type",  # 無效類型
                "confidence": 0.8,
                "target_entities": [],
                "parameters": {},
                "explanation": "未知查詢",
            }
            mock_ai_service.enhance_natural_language_query.return_value = (
                json.dumps(ai_response),
                0.8,
            )

            result = await parser.parse("機台狀態")

            # 應該通過內容推斷正確類型
            assert result.query_type == QueryType.MACHINE_STATUS

    class TestTextResponseParsing:
        """文字響應解析測試"""

        @pytest.mark.asyncio
        async def test_parse_text_response_with_sql(self, parser, mock_ai_service):
            """測試包含 SQL 的文字響應"""
            # 模擬 AI 返回包含 SQL 的文字
            mock_ai_service.enhance_natural_language_query.return_value = (
                "SELECT * FROM machine_status WHERE machine_id = 'M001'",
                0.8,
            )

            result = await parser.parse("M001機台狀態")

            assert result.query_type == QueryType.SPECIFIC_MACHINE
            assert result.confidence == 0.8 * 0.8  # 文字解析信心度調整

        @pytest.mark.asyncio
        async def test_parse_text_response_inference(self, parser, mock_ai_service):
            """測試文字響應類型推斷"""
            test_cases = [
                ("故障記錄查詢", QueryType.FAULT_ANALYSIS),
                ("生產統計報告", QueryType.PRODUCTION_STATS),
                ("所有機台概覽", QueryType.ALL_MACHINES),
                ("部門狀態檢查", QueryType.DEPARTMENT_STATUS),
            ]

            for text, expected_type in test_cases:
                mock_ai_service.enhance_natural_language_query.return_value = (
                    f"查詢 {text}",
                    0.8,
                )

                result = await parser.parse(text)
                assert result.query_type == expected_type

        @pytest.mark.asyncio
        async def test_parse_empty_text_response(self, parser, mock_ai_service):
            """測試空文字響應"""
            mock_ai_service.enhance_natural_language_query.return_value = ("", 0.8)

            result = await parser.parse("機台狀態")

            # 應該回退到原始文字推斷
            assert result.query_type == QueryType.MACHINE_STATUS

    class TestQueryTypeInference:
        """查詢類型推斷測試"""

        @pytest.mark.asyncio
        async def test_infer_query_type_from_content(self, parser, mock_ai_service):
            """測試從內容推斷查詢類型"""
            test_cases = [
                ("機台故障問題", QueryType.FAULT_ANALYSIS),
                ("生產效率統計", QueryType.PRODUCTION_STATS),
                ("所有機台整體狀況", QueryType.ALL_MACHINES),
                ("加工部門狀態", QueryType.DEPARTMENT_STATUS),
                ("M001機台檢查", QueryType.SPECIFIC_MACHINE),
                ("機台運行狀態", QueryType.MACHINE_STATUS),
            ]

            # 模擬 AI 返回空結果，測試推斷邏輯
            mock_ai_service.enhance_natural_language_query.return_value = ("", 0.8)

            for text, expected_type in test_cases:
                result = await parser.parse(text)
                assert result.query_type == expected_type, f"Failed for: {text}"

        def test_infer_query_type_from_sql(self, parser):
            """測試從 SQL 推斷查詢類型"""
            test_cases = [
                ("SELECT * FROM fault_records", QueryType.FAULT_ANALYSIS),
                ("SELECT * FROM production_stats", QueryType.PRODUCTION_STATS),
                ("SELECT * FROM machine_status", QueryType.MACHINE_STATUS),
                ("SELECT * FROM machines", QueryType.ALL_MACHINES),
                (
                    "SELECT * FROM status WHERE machine_id = 'M001'",
                    QueryType.SPECIFIC_MACHINE,
                ),
            ]

            for sql, expected_type in test_cases:
                inferred_type = parser._infer_query_type_from_sql(sql)
                assert inferred_type == expected_type, f"Failed for: {sql}"

    class TestParameterExtraction:
        """參數提取測試"""

        @pytest.mark.asyncio
        async def test_extract_machine_id_from_text(self, parser, mock_ai_service):
            """測試從文字提取機台 ID"""
            mock_ai_service.enhance_natural_language_query.return_value = ("", 0.8)

            result = await parser.parse("請檢查 M123 的狀況")

            assert result.parameters.get("machine_id") == "M123"

        @pytest.mark.asyncio
        async def test_extract_machine_id_from_sql(self, parser, mock_ai_service):
            """測試從 SQL 提取機台 ID"""
            sql_response = "SELECT * FROM status WHERE machine_id = 'M456'"
            mock_ai_service.enhance_natural_language_query.return_value = (
                sql_response,
                0.8,
            )

            result = await parser.parse("機台狀態")

            assert result.parameters.get("machine_id") == "M456"

        @pytest.mark.asyncio
        async def test_extract_time_range_parameters(self, parser, mock_ai_service):
            """測試提取時間範圍參數"""
            test_cases = [
                ("近期故障", 7),
                ("一個月問題", 30),
                ("最近異常", 7),
            ]

            mock_ai_service.enhance_natural_language_query.return_value = ("", 0.8)

            for text, expected_days in test_cases:
                result = await parser.parse(text)
                if result.query_type == QueryType.FAULT_ANALYSIS:
                    assert result.parameters.get("days") == expected_days

        @pytest.mark.asyncio
        async def test_extract_department_parameters(self, parser, mock_ai_service):
            """測試提取部門參數"""
            test_cases = [
                ("加工部問題", "加工部"),
                ("組裝狀況", "組裝部"),
                ("品管檢查", "品管部"),
                ("維修記錄", "維修部"),
            ]

            mock_ai_service.enhance_natural_language_query.return_value = ("", 0.8)

            for text, expected_dept in test_cases:
                result = await parser.parse(text)
                if "department" in result.parameters:
                    assert result.parameters["department"] == expected_dept

    class TestErrorHandling:
        """錯誤處理測試"""

        @pytest.mark.asyncio
        async def test_parse_with_ai_service_exception(self, parser, mock_ai_service):
            """測試 AI 服務異常"""
            # 模擬 AI 服務拋出異常
            mock_ai_service.enhance_natural_language_query.side_effect = Exception(
                "AI 服務錯誤"
            )

            result = await parser.parse("機台狀態")

            assert result.query_type == QueryType.UNKNOWN
            assert result.confidence == 0.0
            assert "AI 解析錯誤" in result.explanation
            assert "AI 服務錯誤" in result.explanation
            # 檢查錯誤是否在參數中（可能在 error 鍵或說明中）
            has_error = (
                "AI 服務錯誤" in result.parameters.get("error", "")
                or "AI 服務錯誤" in result.explanation
            )

        @pytest.mark.asyncio
        async def test_parse_without_ai_service(self, parser_no_ai):
            """測試無 AI 服務"""
            result = await parser_no_ai.parse("機台狀態")

            assert result.query_type == QueryType.UNKNOWN
            assert result.confidence == 0.0
            assert "AI 服務不可用" in result.explanation

        @pytest.mark.asyncio
        async def test_parse_non_string_ai_result(self, parser, mock_ai_service):
            """測試非字符串 AI 結果"""
            # 模擬 AI 返回非字符串結果
            mock_ai_service.enhance_natural_language_query.return_value = (123, 0.8)

            result = await parser.parse("機台狀態")

            assert result.query_type == QueryType.UNKNOWN
            assert "AI 解析錯誤" in result.explanation

        @pytest.mark.asyncio
        async def test_parse_malformed_json(self, parser, mock_ai_service):
            """測試格式錯誤的 JSON"""
            # 模擬 AI 返回格式錯誤的 JSON
            mock_ai_service.enhance_natural_language_query.return_value = (
                '{"incomplete": json',
                0.8,
            )

            result = await parser.parse("機台狀態")

            # 應該回退到文字解析而不是返回錯誤
            assert result.query_type != QueryType.UNKNOWN

    class TestEdgeCases:
        """邊界條件測試"""

        @pytest.mark.asyncio
        async def test_parse_empty_input(self, parser):
            """測試空輸入"""
            result = await parser.parse("")

            assert result.query_type == QueryType.UNKNOWN
            assert result.confidence == 0.0
            assert "空輸入" in result.explanation

        @pytest.mark.asyncio
        async def test_parse_none_input(self, parser):
            """測試 None 輸入"""
            result = await parser.parse(None)

            assert result.query_type == QueryType.UNKNOWN
            assert result.confidence == 0.0

        @pytest.mark.asyncio
        async def test_parse_whitespace_input(self, parser):
            """測試空白字符輸入"""
            result = await parser.parse("   \t\n   ")

            assert result.query_type == QueryType.UNKNOWN
            assert result.confidence == 0.0

        @pytest.mark.asyncio
        async def test_parse_very_long_input(self, parser, mock_ai_service):
            """測試非常長的輸入"""
            long_text = "機台狀態" + "a" * 10000
            mock_ai_service.enhance_natural_language_query.return_value = (
                '{"query_type": "machine_status", "confidence": 0.8}',
                0.8,
            )

            result = await parser.parse(long_text)

            # 應該能正常處理
            assert result.query_type == QueryType.MACHINE_STATUS

        @pytest.mark.asyncio
        async def test_confidence_boundary_values(self, parser, mock_ai_service):
            """測試信心度邊界值"""
            test_cases = [
                (-0.5, 0.0),  # 負值應該被調整到 0
                (0.0, 0.0),  # 最小值
                (0.5, 0.5),  # 中間值
                (1.0, 1.0),  # 最大值
                (1.5, 1.0),  # 超過最大值應該被調整到 1
            ]

            for input_conf, expected_conf in test_cases:
                ai_response = {
                    "query_type": "machine_status",
                    "confidence": input_conf,
                    "parameters": {},
                    "explanation": "測試",
                }
                mock_ai_service.enhance_natural_language_query.return_value = (
                    json.dumps(ai_response),
                    0.8,
                )

                result = await parser.parse("機台狀態")
                assert result.confidence == expected_conf

    class TestCapabilityAssessment:
        """能力評估測試"""

        def test_can_handle_with_ai_service(self, parser):
            """測試帶 AI 服務的能力評估"""
            # 簡單查詢
            confidence1 = parser.can_handle("機台狀態")
            assert 0.6 <= confidence1 <= 1.0

            # 複雜查詢
            complex_query = (
                "請分析加工部M001機台在過去一個月的故障情況，並與其他機台進行比較"
            )
            confidence2 = parser.can_handle(complex_query)
            assert confidence2 > confidence1  # 複雜查詢應該有更高信心度

        def test_can_handle_without_ai_service(self, parser_no_ai):
            """測試無 AI 服務的能力評估"""
            confidence = parser_no_ai.can_handle("機台狀態")
            assert confidence == 0.0

        def test_can_handle_empty_input(self, parser):
            """測試空輸入能力評估"""
            confidence = parser.can_handle("")
            assert confidence == 0.0

        def test_assess_query_complexity(self, parser):
            """測試查詢複雜度評估"""
            simple_query = "狀態"
            complex_query = "請比較加工部和組裝部的生產效率，並分析最近的故障趨勢"

            simple_score = parser._assess_query_complexity(simple_query)
            complex_score = parser._assess_query_complexity(complex_query)

            assert complex_score > simple_score

    class TestParserInfo:
        """解析器資訊測試"""

        def test_get_parser_info(self, parser):
            """測試獲取解析器資訊"""
            info = parser.get_parser_info()

            assert info["name"] == "AIEnhancedParser"
            assert info["version"] == "1.0.0"
            assert info["type"] == "ai_enhanced"
            assert "complex_query_understanding" in info["capabilities"]
            assert info["ai_service_available"] is True
            assert info["requires_context"] is True

        def test_get_parser_info_no_ai(self, parser_no_ai):
            """測試無 AI 服務的解析器資訊"""
            info = parser_no_ai.get_parser_info()

            assert info["ai_service_available"] is False

        def test_get_supported_query_types(self, parser):
            """測試獲取支援的查詢類型"""
            types = parser.get_supported_query_types()

            assert len(types) == 6
            assert QueryType.MACHINE_STATUS in types
            assert QueryType.SPECIFIC_MACHINE in types
            assert QueryType.FAULT_ANALYSIS in types

    class TestAIServiceStatus:
        """AI 服務狀態測試"""

        def test_get_ai_service_status_available(self, parser):
            """測試可用 AI 服務狀態"""
            status = parser.get_ai_service_status()

            assert status["available"] is True
            assert status["status"] == "ready"
            assert "AI 服務可用" in status["message"]

        def test_get_ai_service_status_not_available(self, parser_no_ai):
            """測試不可用 AI 服務狀態"""
            status = parser_no_ai.get_ai_service_status()

            assert status["available"] is False
            assert status["status"] == "not_configured"
            assert "AI 服務未配置" in status["message"]

    class TestSystemPromptManagement:
        """系統提示管理測試"""

        def test_update_system_prompt(self, parser):
            """測試更新系統提示"""
            new_prompt = "新的系統提示內容"
            parser.update_system_prompt(new_prompt)

            assert parser._system_prompt == new_prompt

        def test_build_system_prompt(self, parser):
            """測試建構系統提示"""
            prompt = parser._build_system_prompt()

            assert "工業製造查詢分析助手" in prompt
            assert "JSON" in prompt
            assert "confidence" in prompt

    class TestContextManagement:
        """上下文管理測試"""

        @pytest.mark.asyncio
        async def test_prepare_ai_context(self, parser, mock_ai_service):
            """測試準備 AI 上下文"""
            context = {"schema": {"tables": ["machines", "status"]}}
            mock_ai_service.enhance_natural_language_query.return_value = (
                '{"query_type": "unknown"}',
                0.8,
            )

            await parser.parse("測試", context)

            # 驗證 AI 服務被正確調用
            mock_ai_service.enhance_natural_language_query.assert_called_once()
            call_args = mock_ai_service.enhance_natural_language_query.call_args
            assert call_args[0][0] == "測試"  # 第一個參數是文字
            assert isinstance(call_args[0][1], dict)  # 第二個參數是上下文

        def test_prepare_ai_context_structure(self, parser):
            """測試 AI 上下文結構"""
            context = {"schema": {"tables": ["test"]}}
            ai_context = parser._prepare_ai_context("測試文字", context)

            assert ai_context["query_text"] == "測試文字"
            assert ai_context["language"] == "zh-TW"
            assert ai_context["domain"] == "manufacturing"
            assert "database_schema" in ai_context
            assert "entity_examples" in ai_context
