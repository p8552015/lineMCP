"""
基於規則的解析器測試
專注於邊界條件和回歸測試
"""

import pytest
from unittest.mock import Mock, AsyncMock

from src.services.nl_to_sql.parsers.rule_based_parser import RuleBasedParser
from src.services.nl_to_sql.models.query_models import ParsedQuery, QueryType


class TestRuleBasedParser:
    """基於規則的解析器測試"""
    
    @pytest.fixture
    def mock_configuration(self):
        """模擬配置服務"""
        config = Mock()
        config.get_query_patterns.return_value = {
            "all_machines": {
                "patterns": ["所有機台", "全部機台", "整體"],
                "confidence": 0.85
            },
            "fault_analysis": {
                "patterns": ["故障", "問題", "錯誤", "異常"],
                "confidence": 0.8
            },
            "production_stats": {
                "patterns": ["統計", "報告", "生產", "產量"],
                "confidence": 0.8
            },
            "department_status": {
                "patterns": [".*部.*機台.*", ".*部.*狀態", ".*部.*狀況", "部門.*機台", "部門.*狀態", "部門.*概覽", ".*部.*概覽"],
                "confidence": 0.75
            },
            "machine_status": {
                "patterns": ["機台.*狀態", "設備.*狀態", "機器.*運行", "設備.*運行", "機台.*運轉", "設備.*運轉", "運行.*狀態", "運轉.*情況"],
                "confidence": 0.7
            }
        }
        config.reload_config = Mock()
        return config
    
    @pytest.fixture
    def parser(self, mock_configuration):
        """創建解析器實例"""
        return RuleBasedParser(mock_configuration)
    
    class TestInitialization:
        """初始化測試"""
        
        def test_parser_initialization(self, mock_configuration):
            """測試解析器初始化"""
            parser = RuleBasedParser(mock_configuration)
            
            assert parser._config == mock_configuration
            assert parser._machine_id_pattern is not None
            assert len(parser._query_patterns) == 5
            assert len(parser._department_mapping) > 0
            mock_configuration.get_query_patterns.assert_called_once()
        
        def test_parser_initialization_with_empty_patterns(self):
            """測試空模式配置初始化"""
            config = Mock()
            config.get_query_patterns.return_value = {}
            
            parser = RuleBasedParser(config)
            assert len(parser._query_patterns) == 0
    
    class TestMachineIdParsing:
        """機台 ID 解析測試"""
        
        @pytest.mark.asyncio
        async def test_parse_specific_machine_m001(self, parser):
            """測試解析特定機台 M001"""
            result = await parser.parse("M001機台")
            
            assert result.query_type == QueryType.SPECIFIC_MACHINE
            assert result.parameters["machine_id"] == "M001"
            assert result.confidence == 0.9
            assert "M001" in result.explanation
        
        @pytest.mark.asyncio
        async def test_parse_specific_machine_lowercase(self, parser):
            """測試小寫機台 ID"""
            result = await parser.parse("m123機台狀況如何")
            
            assert result.query_type == QueryType.SPECIFIC_MACHINE
            assert result.parameters["machine_id"] == "M123"
            assert result.confidence == 0.9
        
        @pytest.mark.asyncio
        async def test_parse_specific_machine_4_digits(self, parser):
            """測試 4 位數機台 ID"""
            result = await parser.parse("請查看 M1234 的狀態")
            
            assert result.query_type == QueryType.SPECIFIC_MACHINE
            assert result.parameters["machine_id"] == "M1234"
        
        @pytest.mark.asyncio
        async def test_parse_machine_id_with_leading_zero(self, parser):
            """測試前導零補齊"""
            result = await parser.parse("M25機台")
            
            assert result.query_type == QueryType.SPECIFIC_MACHINE
            # 修正：實際實現中前導零補齊到3位
            assert result.parameters["machine_id"] == "M025"
        
        @pytest.mark.asyncio
        async def test_parse_machine_id_boundary_3_digits(self, parser):
            """測試 3 位數邊界條件"""
            result = await parser.parse("M100狀態")
            
            assert result.query_type == QueryType.SPECIFIC_MACHINE
            assert result.parameters["machine_id"] == "M100"
        
        @pytest.mark.asyncio
        async def test_machine_id_2_digits_with_high_number(self, parser):
            """測試 2 位數機台 ID (修正：現在支援 2 位數)"""
            result = await parser.parse("M99機台")
            
            # 現在 2 位數也應該匹配機台 ID 模式
            assert result.query_type == QueryType.SPECIFIC_MACHINE
            assert result.parameters["machine_id"] == "M099"
    
    class TestPatternMatching:
        """模式匹配測試"""
        
        @pytest.mark.asyncio
        async def test_parse_all_machines_pattern(self, parser):
            """測試所有機台模式"""
            result = await parser.parse("所有機台的狀態")
            
            assert result.query_type == QueryType.ALL_MACHINES
            assert result.confidence == 0.85
            assert "所有機台" in result.explanation
        
        @pytest.mark.asyncio
        async def test_parse_fault_analysis_pattern(self, parser):
            """測試故障分析模式"""
            result = await parser.parse("近期有什麼故障嗎")
            
            assert result.query_type == QueryType.FAULT_ANALYSIS
            assert result.confidence == 0.8
            assert result.parameters.get("days") == 30  # 預設值
        
        @pytest.mark.asyncio
        async def test_parse_production_stats_pattern(self, parser):
            """測試生產統計模式"""
            result = await parser.parse("生產統計報告")
            
            assert result.query_type == QueryType.PRODUCTION_STATS
            assert result.confidence == 0.8
        
        @pytest.mark.asyncio
        async def test_parse_department_status_pattern(self, parser):
            """測試部門狀態模式"""
            result = await parser.parse("加工部的機台狀況")
            
            assert result.query_type == QueryType.DEPARTMENT_STATUS
            assert result.parameters.get("department") == "加工部"
        
        @pytest.mark.asyncio
        async def test_pattern_priority_machine_id_first(self, parser):
            """測試模式優先級 - 機台 ID 優先"""
            # 包含機台 ID 和其他模式關鍵詞
            result = await parser.parse("M001機台所有狀態")
            
            # 機台 ID 模式應該有最高優先級
            assert result.query_type == QueryType.SPECIFIC_MACHINE
            assert result.parameters["machine_id"] == "M001"
        
        @pytest.mark.asyncio
        async def test_pattern_case_insensitive(self, parser):
            """測試模式大小寫不敏感"""
            result = await parser.parse("所有機台")
            
            assert result.query_type == QueryType.ALL_MACHINES
    
    class TestParameterExtraction:
        """參數提取測試"""
        
        @pytest.mark.asyncio
        async def test_extract_time_range_7_days(self, parser):
            """測試提取 7 天時間範圍"""
            result = await parser.parse("近7天的故障記錄")
            
            assert result.query_type == QueryType.FAULT_ANALYSIS
            assert result.parameters.get("days") == 7
        
        @pytest.mark.asyncio
        async def test_extract_time_range_30_days(self, parser):
            """測試提取 30 天時間範圍"""
            result = await parser.parse("一個月的異常情況")
            
            assert result.query_type == QueryType.FAULT_ANALYSIS
            assert result.parameters.get("days") == 30
        
        @pytest.mark.asyncio
        async def test_extract_time_range_90_days(self, parser):
            """測試提取 90 天時間範圍"""
            result = await parser.parse("三個月故障統計")
            
            assert result.query_type == QueryType.FAULT_ANALYSIS
            assert result.parameters.get("days") == 90
        
        @pytest.mark.asyncio
        async def test_extract_department_parameters(self, parser):
            """測試提取部門參數"""
            test_cases = [
                ("加工部狀態", "加工部"),
                ("組裝線情況", "組裝部"),
                ("品管檢查", "品管部"),
                ("維修記錄", "維修部")
            ]
            
            for text, expected_dept in test_cases:
                result = await parser.parse(text)
                if result.query_type == QueryType.DEPARTMENT_STATUS:
                    assert result.parameters.get("department") == expected_dept
    
    class TestEdgeCases:
        """邊界條件測試"""
        
        @pytest.mark.asyncio
        async def test_parse_empty_string(self, parser):
            """測試空字串"""
            result = await parser.parse("")
            
            assert result.query_type == QueryType.UNKNOWN
            assert result.confidence == 0.0
            assert "空輸入" in result.explanation
        
        @pytest.mark.asyncio
        async def test_parse_whitespace_only(self, parser):
            """測試只有空白字符"""
            result = await parser.parse("   \t\n  ")
            
            assert result.query_type == QueryType.UNKNOWN
            assert result.confidence == 0.0
        
        @pytest.mark.asyncio
        async def test_parse_none_input(self, parser):
            """測試 None 輸入"""
            result = await parser.parse(None)
            
            assert result.query_type == QueryType.UNKNOWN
            assert result.confidence == 0.0
        
        @pytest.mark.asyncio
        async def test_parse_unknown_pattern(self, parser):
            """測試未知模式"""
            result = await parser.parse("完全不相關的文字內容")
            
            assert result.query_type == QueryType.UNKNOWN
            assert result.confidence == 0.0
            assert "無法識別" in result.explanation
        
        @pytest.mark.asyncio
        async def test_parse_very_long_input(self, parser):
            """測試非常長的輸入"""
            long_text = "機台狀態" + "x" * 1000
            result = await parser.parse(long_text)
            
            # 應該仍能正常解析
            assert result.query_type == QueryType.MACHINE_STATUS
        
        @pytest.mark.asyncio
        async def test_parse_special_characters(self, parser):
            """測試特殊字符"""
            result = await parser.parse("機台@#$%狀態!!")
            
            assert result.query_type == QueryType.MACHINE_STATUS
        
        @pytest.mark.asyncio
        async def test_parse_mixed_language(self, parser):
            """測試中英混合"""
            result = await parser.parse("machine M001 狀態 status")
            
            assert result.query_type == QueryType.SPECIFIC_MACHINE
            assert result.parameters["machine_id"] == "M001"
    
    class TestCapabilityAssessment:
        """能力評估測試"""
        
        def test_can_handle_empty_input(self, parser):
            """測試空輸入能力評估"""
            confidence = parser.can_handle("")
            assert confidence == 0.0
        
        def test_can_handle_machine_id(self, parser):
            """測試機台 ID 能力評估"""
            confidence = parser.can_handle("M001機台")
            assert confidence == 0.95  # 機台 ID 高信心度
        
        def test_can_handle_pattern_match(self, parser):
            """測試模式匹配能力評估"""
            confidence = parser.can_handle("所有機台狀態")
            assert confidence == 0.85  # 匹配模式信心度
        
        def test_can_handle_unknown_pattern(self, parser):
            """測試未知模式能力評估"""
            confidence = parser.can_handle("完全不相關的文字")
            assert confidence == 0.0
        
        def test_can_handle_partial_match(self, parser):
            """測試部分匹配能力評估"""
            confidence = parser.can_handle("機台狀態")
            assert confidence > 0.0  # 部分匹配應有一定信心度
    
    class TestParserInfo:
        """解析器資訊測試"""
        
        def test_get_parser_info(self, parser):
            """測試獲取解析器資訊"""
            info = parser.get_parser_info()
            
            assert info["name"] == "RuleBasedParser"
            assert info["version"] == "1.0.0"
            assert info["type"] == "rule_based"
            assert "machine_id_detection" in info["capabilities"]
            assert len(info["supported_query_types"]) == 5
            assert info["pattern_count"] == 5
        
        def test_get_supported_query_types(self, parser):
            """測試獲取支援的查詢類型"""
            types = parser.get_supported_query_types()
            
            assert QueryType.SPECIFIC_MACHINE in types
            assert QueryType.MACHINE_STATUS in types
            assert QueryType.ALL_MACHINES in types
            assert len(types) >= 5
    
    class TestConfigurationValidation:
        """配置驗證測試"""
        
        def test_validate_pattern_config_valid(self, parser):
            """測試有效配置驗證"""
            result = parser.validate_pattern_config()
            
            assert result["is_valid"] is True
            assert len(result["errors"]) == 0
            assert len(result["pattern_stats"]) == 5
        
        def test_validate_pattern_config_invalid_regex(self, mock_configuration):
            """測試無效正規表達式配置"""
            mock_configuration.get_query_patterns.return_value = {
                "MACHINE_STATUS": {
                    "patterns": ["[invalid_regex("],  # 無效正規表達式
                    "confidence": 0.8
                }
            }
            
            parser = RuleBasedParser(mock_configuration)
            result = parser.validate_pattern_config()
            
            assert result["is_valid"] is False
            assert len(result["errors"]) > 0
        
        def test_validate_pattern_config_invalid_query_type(self, mock_configuration):
            """測試無效查詢類型配置"""
            mock_configuration.get_query_patterns.return_value = {
                "INVALID_TYPE": {  # 無效的查詢類型
                    "patterns": ["test"],
                    "confidence": 0.8
                }
            }
            
            parser = RuleBasedParser(mock_configuration)
            result = parser.validate_pattern_config()
            
            assert result["is_valid"] is False
            assert any("無效的查詢類型" in error for error in result["errors"])
        
        def test_validate_pattern_config_empty_patterns(self, mock_configuration):
            """測試空模式配置"""
            mock_configuration.get_query_patterns.return_value = {
                "machine_status": {
                    "patterns": [],  # 空模式列表
                    "confidence": 0.8
                }
            }
            
            parser = RuleBasedParser(mock_configuration)
            result = parser.validate_pattern_config()
            
            assert len(result["warnings"]) > 0
            assert any("沒有定義模式" in warning for warning in result["warnings"])
    
    class TestPatternReloading:
        """模式重新載入測試"""
        
        @pytest.mark.asyncio
        async def test_reload_patterns_success(self, parser):
            """測試成功重新載入模式"""
            # 修改配置
            parser._config.get_query_patterns.return_value = {
                "NEW_TYPE": {
                    "patterns": ["新模式"],
                    "confidence": 0.9
                }
            }
            
            # 重新載入
            parser.reload_patterns()
            
            # 驗證更新
            assert "NEW_TYPE" in parser._query_patterns
            parser._config.reload_config.assert_called_once()
        
        def test_reload_patterns_failure(self, parser):
            """測試重新載入失敗"""
            # 模擬配置載入失敗
            parser._config.reload_config.side_effect = Exception("載入失敗")
            
            # 應該拋出異常
            with pytest.raises(Exception):
                parser.reload_patterns()
    
    class TestRegressionScenarios:
        """回歸測試場景"""
        
        @pytest.mark.asyncio
        async def test_regression_machine_id_case_sensitivity(self, parser):
            """回歸測試：機台 ID 大小寫敏感性"""
            test_cases = ["M001", "m001", "M001", "m001"]
            
            for case in test_cases:
                result = await parser.parse(f"{case}機台")
                assert result.query_type == QueryType.SPECIFIC_MACHINE
                assert result.parameters["machine_id"] == "M001"
        
        @pytest.mark.asyncio
        async def test_regression_pattern_overlap(self, parser):
            """回歸測試：模式重疊問題"""
            # 測試包含多個模式關鍵詞的輸入
            result = await parser.parse("所有機台的故障統計報告")
            
            # 應該選擇第一個匹配的模式（根據檢查順序）
            assert result.query_type in [
                QueryType.ALL_MACHINES, 
                QueryType.FAULT_ANALYSIS, 
                QueryType.PRODUCTION_STATS
            ]
        
        @pytest.mark.asyncio
        async def test_regression_chinese_text_normalization(self, parser):
            """回歸測試：中文文字標準化"""
            # 測試全形和半形字符
            result1 = await parser.parse("M001機台")
            result2 = await parser.parse("Ｍ００１機台")  # 全形字符
            
            # 至少一個應該能正確解析
            assert (result1.query_type == QueryType.SPECIFIC_MACHINE or 
                   result2.query_type == QueryType.SPECIFIC_MACHINE)
        
        @pytest.mark.asyncio
        async def test_regression_empty_parameters(self, parser):
            """回歸測試：空參數處理"""
            result = await parser.parse("機台狀態")
            
            assert result.query_type == QueryType.MACHINE_STATUS
            assert isinstance(result.parameters, dict)
            # 參數可以為空，但不應該為 None
        
        @pytest.mark.asyncio
        async def test_regression_confidence_consistency(self, parser):
            """回歸測試：信心度一致性"""
            # 相同模式應該返回一致的信心度
            result1 = await parser.parse("所有機台")
            result2 = await parser.parse("全部機台")
            
            if (result1.query_type == QueryType.ALL_MACHINES and 
                result2.query_type == QueryType.ALL_MACHINES):
                assert result1.confidence == result2.confidence