"""
測試 QueryStatisticsService 介面符合性
確保實作完全符合 IStatistics 介面定義
"""

import unittest

from src.services.nl_to_sql.interfaces.statistics_interfaces import IStatistics
from src.services.nl_to_sql.services.query_statistics_service import (
    QueryStatisticsService,
)


class TestQueryStatisticsInterface(unittest.TestCase):
    """測試統計服務介面符合性"""

    def setUp(self):
        """初始化測試環境"""
        self.service = QueryStatisticsService()

    def test_implements_interface(self):
        """測試是否實現 IStatistics 介面"""
        assert isinstance(self.service, IStatistics)

    def test_record_success_signature(self):
        """測試 record_success 方法簽名"""
        # 測試基本呼叫
        self.service.record_success(operation_type="test_operation", duration=1.5)

        # 測試帶 metadata 的呼叫
        self.service.record_success(
            operation_type="natural_language_parsing",
            duration=0.5,
            metadata={
                "confidence": 0.95,
                "query_type": "specific_machine",
                "parser_type": "rule_based",
            },
        )

        # 驗證統計資料已記錄
        stats = self.service.get_stats()
        assert stats["summary"]["total_success"] > 0

    def test_record_failure_signature(self):
        """測試 record_failure 方法簽名"""
        # 測試基本呼叫
        self.service.record_failure(
            operation_type="test_operation",
            error_type="ValueError",
            error_message="Test error message",
        )

        # 測試帶 metadata 的呼叫
        self.service.record_failure(
            operation_type="natural_language_parsing",
            error_type="ParseError",
            error_message="Failed to parse query",
            metadata={"parser_type": "ai_enhanced", "duration": 2.0},
        )

        # 驗證統計資料已記錄
        stats = self.service.get_stats()
        assert stats["summary"]["total_failure"] > 0

    def test_backward_compatibility(self):
        """測試向後兼容性"""
        # 測試 metadata 中的參數正確轉換
        self.service.record_success(
            operation_type="parsing",
            duration=0.1,
            metadata={
                "parser_type": "custom_parser",
                "confidence": 0.8,
                "query_type": "all_machines",
            },
        )

        # 驗證內部統計正確記錄
        stats = self.service.get_stats()
        parser_stats = stats["parser_statistics"]

        # 應該有 custom_parser 的統計
        assert "custom_parser" in parser_stats
        assert parser_stats["custom_parser"]["success_count"] == 1

        # 驗證查詢類型統計
        query_stats = stats["query_type_distribution"]
        assert "all_machines" in query_stats
        assert query_stats["all_machines"] == 1

    def test_duration_conversion(self):
        """測試時間單位轉換（秒到毫秒）"""
        self.service.record_success(
            operation_type="test",
            duration=1.5,  # 1.5 秒
            metadata={"parser_type": "test_parser"},
        )

        stats = self.service.get_parser_performance("test_parser")
        # 應該轉換為 1500 毫秒
        self.assertAlmostEqual(
            stats["performance_metrics"]["avg_parse_time"], 1500.0, places=1
        )

    def test_error_categorization(self):
        """測試錯誤分類功能"""
        # 測試不同類型的錯誤
        test_cases = [
            ("timeout", "TimeoutError", "Request timeout"),
            ("network", "ConnectionError", "Network connection failed"),
            ("parsing", "JSONDecodeError", "Failed to parse JSON"),
            ("ai_service", "AIServiceError", "AI model unavailable"),
            ("configuration", "ConfigError", "Invalid configuration"),
        ]

        for _expected_category, error_type, error_message in test_cases:
            self.service.record_failure(
                operation_type="test",
                error_type=error_type,
                error_message=error_message,
            )

        stats = self.service.get_stats()
        error_dist = stats["error_distribution"]

        # 驗證錯誤正確分類
        assert error_dist["timeout"] == 1
        assert error_dist["network"] == 1
        assert error_dist["parsing"] == 1
        assert error_dist["ai_service"] == 1
        assert error_dist["configuration"] == 1


if __name__ == "__main__":
    unittest.main()
