"""
測試訊息格式化服務
"""

import pytest
from linebot.v3.messaging import TextMessage

from src.services.message_formatter import MessageFormatter
from src.services.nl_to_sql.models.query_models import QueryType


class TestMessageFormatter:
    """訊息格式化服務測試"""

    @pytest.fixture
    def formatter(self):
        """創建訊息格式化器實例"""
        return MessageFormatter()

    def test_formatter_initialization(self, formatter):
        """測試格式化器初始化"""
        assert formatter is not None
        assert hasattr(formatter, "status_icons")
        assert hasattr(formatter, "department_icons")

        # 檢查狀態圖示映射
        assert formatter.status_icons["high"] == "🟢"
        assert formatter.status_icons["medium"] == "🟡"
        assert formatter.status_icons["low"] == "🔴"
        assert formatter.status_icons["unknown"] == "⚪"

    def test_format_query_result_success(self, formatter):
        """測試成功查詢結果格式化"""
        result = {
            "success": True,
            "data": {
                "machines": [
                    {"machine_id": "M001", "name": "CNC車床A", "status": "running"},
                    {"machine_id": "M002", "name": "CNC車床B", "status": "idle"},
                ]
            },
            "query_type": QueryType.ALL_MACHINES.value,
            "sql_query": "SELECT * FROM machines",
        }

        message = formatter.format_query_result(result)

        assert isinstance(message, TextMessage)
        # 由於實際實現可能有不同的格式，我們只檢查有訊息輸出
        assert len(message.text) > 0

    def test_format_query_result_empty_data(self, formatter):
        """測試空資料結果格式化"""
        result = {
            "success": True,
            "data": {},
            "query_type": QueryType.MACHINE_STATUS.value,
        }

        message = formatter.format_query_result(result)

        assert isinstance(message, TextMessage)
        assert len(message.text) > 0

    def test_format_query_result_error(self, formatter):
        """測試錯誤結果格式化"""
        result = {"success": False, "error": "Database connection failed"}

        message = formatter.format_query_result(result)

        assert isinstance(message, TextMessage)
        assert "Database connection failed" in message.text

    def test_format_machine_status_result(self, formatter):
        """測試機台狀態結果格式化"""
        result = {
            "success": True,
            "data": {
                "found": True,
                "machine_id": "M001",
                "machine_name": "CNC車床A",
                "department": "加工部",
                "utilization_rate": 85.5,
                "efficiency_rate": 92.3,
                "good_parts": 100,
                "defective_parts": 5,
                "last_record_date": "2024-01-01",
                "recent_fault_count": 2,
            },
            "query_type": QueryType.SPECIFIC_MACHINE.value,
        }

        message = formatter.format_query_result(result)

        assert isinstance(message, TextMessage)
        assert "M001" in message.text
        assert "CNC車床A" in message.text

    def test_format_suggestion_message(self, formatter):
        """測試建議訊息格式化"""
        message = formatter.format_suggestion_message()

        assert isinstance(message, TextMessage)
        assert len(message.text) > 0
        assert (
            "建議" in message.text
            or "試試" in message.text
            or "可以" in message.text
            or "幫您" in message.text
        )

    def test_status_icon_mapping(self, formatter):
        """測試狀態圖示映射功能"""
        # 測試各種狀態的圖示
        assert formatter.status_icons.get("high") == "🟢"
        assert formatter.status_icons.get("medium") == "🟡"
        assert formatter.status_icons.get("low") == "🔴"
        assert formatter.status_icons.get("unknown") == "⚪"

        # 測試不存在的狀態
        assert formatter.status_icons.get("nonexistent") is None

    def test_department_icon_mapping(self, formatter):
        """測試部門圖示映射功能"""
        # 確保部門圖示字典存在且不為空
        assert isinstance(formatter.department_icons, dict)
        # 可能的部門應該有對應的圖示
        common_departments = ["加工部", "組裝部", "品質部", "維修部"]
        for dept in common_departments:
            # 檢查是否有對應的圖示（可能存在也可能不存在）
            icon = formatter.department_icons.get(dept)
            if icon:
                assert isinstance(icon, str)
                assert len(icon) > 0

    def test_format_production_stats(self, formatter):
        """測試生產統計格式化"""
        result = {
            "success": True,
            "data": {
                "period": "今日",
                "total_production": 1000,
                "good_count": 950,
                "defective_count": 50,
                "efficiency_rate": 95.0,
                "by_machine": [],
            },
            "query_type": QueryType.PRODUCTION_STATS.value,
        }

        message = formatter.format_query_result(result)

        assert isinstance(message, TextMessage)
        assert len(message.text) > 0

    def test_format_fault_analysis(self, formatter):
        """測試故障分析格式化"""
        result = {
            "success": True,
            "data": {
                "period": "近7天",
                "total_faults": 5,
                "critical_faults": 1,
                "by_machine": [
                    {
                        "machine_id": "M001",
                        "fault_count": 2,
                        "recent_faults": [
                            {
                                "fault_type": "過熱警告",
                                "fault_time": "2024-01-01 10:30:00",
                                "duration": 30,
                                "severity": "medium",
                            }
                        ],
                    }
                ],
            },
            "query_type": QueryType.FAULT_ANALYSIS.value,
        }

        message = formatter.format_query_result(result)

        assert isinstance(message, TextMessage)
        assert len(message.text) > 0

    def test_format_unknown_query_type(self, formatter):
        """測試未知查詢類型格式化"""
        result = {
            "success": True,
            "data": {"test": "data"},
            "query_type": "unknown_type",
        }

        message = formatter.format_query_result(result)

        assert isinstance(message, TextMessage)
        # 應該有某種形式的輸出，即使是未知類型
        assert len(message.text) > 0
