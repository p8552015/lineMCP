#!/usr/bin/env python3
"""
訊息格式化服務
將查詢結果格式化為用戶友好的訊息
"""

from typing import Any

import structlog
from linebot.v3.messaging import Message, TextMessage

from .nl_to_sql.models.query_models import QueryType

logger = structlog.get_logger()


class MessageFormatter:
    """訊息格式化服務"""

    def __init__(self) -> None:
        # 狀態圖示映射
        self.status_icons = {
            "high": "🟢",  # 高效率
            "medium": "🟡",  # 中等效率
            "low": "🔴",  # 低效率
            "unknown": "⚪",  # 未知狀態
        }

        # 部門圖示映射
        self.department_icons = {
            "加工部": "🔧",
            "組裝部": "🔩",
            "品管部": "🔍",
            "維修部": "🛠️",
            "生產部": "🏭",
        }

    def format_query_result(self, result: dict[str, Any]) -> Message:
        """
        格式化查詢結果為 LINE 訊息

        Args:
            result: 資料庫查詢結果

        Returns:
            格式化的 LINE 訊息
        """
        if not result.get("success", False):
            return self._format_error_message(result)

        query_type = result.get("query_type")
        data = result.get("data", {})

        try:
            if query_type == QueryType.SPECIFIC_MACHINE.value:
                return self._format_machine_status(data)
            elif query_type == QueryType.ALL_MACHINES.value:
                return self._format_all_machines(data)
            elif query_type == QueryType.FAULT_ANALYSIS.value:
                return self._format_fault_analysis(data)
            elif query_type == QueryType.PRODUCTION_STATS.value:
                return self._format_production_stats(data)
            elif query_type == QueryType.DEPARTMENT_STATUS.value:
                return self._format_department_status(data)
            else:
                return self._format_generic_result(data)

        except Exception as e:
            logger.error(f"Message formatting error: {e}")
            return TextMessage(text="📊 查詢成功，但格式化結果時發生錯誤")

    def _format_error_message(self, result: dict[str, Any]) -> TextMessage:
        """格式化錯誤訊息"""
        error = result.get("error", "未知錯誤")
        suggestion = result.get("suggestion", "")

        message = f"❌ {error}"
        if suggestion:
            message += f"\n\n💡 {suggestion}"

        return TextMessage(text=message)

    def _format_machine_status(self, data: dict[str, Any]) -> TextMessage:
        """格式化機台狀態訊息"""
        if not data.get("found", False):
            machine_id = data.get("machine_id", "未知")
            return TextMessage(
                text=f"❌ {data.get('message', f'找不到機台 {machine_id}')}"
            )

        machine_id = data.get("machine_id", "未知")
        machine_name = data.get("machine_name", "未知機台")
        department = data.get("department", "未知部門")
        utilization = data.get("utilization_rate", 0)
        efficiency = data.get("efficiency_rate", 0)
        good_parts = data.get("good_parts", 0)
        defective_parts = data.get("defective_parts", 0)
        last_date = data.get("last_record_date", "無記錄")
        fault_count = data.get("recent_fault_count", 0)

        # 確定狀態圖示
        status_icon = self._get_status_icon(
            utilization / 100 if utilization > 1 else utilization
        )
        dept_icon = self.department_icons.get(department, "🏭")

        # 格式化利用率和效率
        util_pct = utilization / 100 if utilization > 1 else utilization
        eff_pct = efficiency / 100 if efficiency > 1 else efficiency

        message = f"📊 {machine_name} ({machine_id}) 狀態報告\n"
        message += "━━━━━━━━━━━━━━━━━━━━\n"
        message += f"{dept_icon} 部門：{department}\n"
        message += f"{status_icon} 稼動率：{util_pct:.1%}\n"
        message += f"⚡ 效率：{eff_pct:.1%}\n"
        message += f"✅ 良品：{good_parts:,} 件\n"
        message += f"❌ 不良品：{defective_parts:,} 件\n"
        message += f"📅 最後記錄：{last_date}\n"

        if fault_count > 0:
            message += f"🔧 近7天故障：{fault_count} 次\n"

        # 添加建議
        if util_pct < 0.6:
            message += "\n💡 建議：檢查機台狀況，稼動率偏低"
        elif util_pct > 0.9:
            message += "\n💡 建議：機台運行良好，可考慮增加產能"
        elif fault_count > 3:
            message += "\n💡 建議：建議安排預防保養"
        elif util_pct > 0.8:
            message += "\n💡 建議：機台狀況良好"

        return TextMessage(text=message)

    def _format_all_machines(self, data: dict[str, Any]) -> TextMessage:
        """格式化所有機台狀態訊息"""
        machines = data.get("machines", [])
        summary = data.get("summary", {})
        total_count = data.get("total_count", 0)

        if total_count == 0:
            return TextMessage(text="❌ 沒有找到任何機台資料")

        message = f"📋 所有機台狀態概覽 ({total_count} 台)\n"
        message += "━━━━━━━━━━━━━━━━━━━━\n"

        # 整體統計
        avg_util = summary.get("average_utilization", 0)
        avg_eff = summary.get("average_efficiency", 0)
        high_perf = summary.get("high_performance_count", 0)
        low_perf = summary.get("low_performance_count", 0)

        message += "📊 整體統計：\n"
        message += f"   平均稼動率：{avg_util:.1%}\n"
        message += f"   平均效率：{avg_eff:.1%}\n"
        message += f"   🟢 高效機台：{high_perf} 台\n"
        message += f"   🔴 低效機台：{low_perf} 台\n\n"

        # 機台詳情（只顯示前8台，避免訊息過長）
        display_machines = machines[:8]
        message += "🔧 機台詳情：\n"

        for machine in display_machines:
            machine_id = machine.get("machine_id", "")
            machine_name = machine.get("machine_name", "")
            department = machine.get("department", "")
            utilization = machine.get("utilization_rate", 0)

            util_pct = utilization / 100 if utilization > 1 else utilization
            status_icon = self._get_status_icon(util_pct)
            dept_icon = self.department_icons.get(department, "🏭")

            message += f"{status_icon} {machine_id} {machine_name}\n"
            message += f"   {dept_icon} {department} | 稼動率 {util_pct:.1%}\n"

        if len(machines) > 8:
            message += f"\n... 還有 {len(machines) - 8} 台機台"
            message += "\n💡 使用 /sql 查詢更多詳情"

        return TextMessage(text=message)

    def _format_fault_analysis(self, data: dict[str, Any]) -> TextMessage:
        """格式化故障分析訊息"""
        total_faults = data.get("total_faults", 0)
        days = data.get("analysis_period_days", 30)
        fault_types = data.get("fault_types", [])
        most_common = data.get("most_common_fault")

        if total_faults == 0:
            return TextMessage(text=f"✅ 近 {days} 天沒有故障記錄，系統運行良好！")

        message = f"🔧 故障分析報告（近 {days} 天）\n"
        message += "━━━━━━━━━━━━━━━━━━━━\n"
        message += f"📈 總故障次數：{total_faults} 次\n\n"

        if most_common:
            message += "🚨 最常見故障：\n"
            message += f"   類型：{most_common['fault_type']}\n"
            message += f"   嚴重性：{most_common['severity']}\n"
            message += (
                f"   次數：{most_common['count']} 次 "
                f"({most_common['percentage']:.1f}%)\n\n"
            )

        # 故障類型分布（顯示前5個）
        if fault_types:
            message += "📊 故障類型分布：\n"
            for _i, fault in enumerate(fault_types[:5]):
                severity_icon = self._get_severity_icon(fault.get("severity", ""))
                message += f"{severity_icon} {fault['fault_type']} "
                message += f"({fault['count']} 次, {fault['percentage']:.1f}%)\n"

        # 建議
        if total_faults > 10:
            message += "\n⚠️ 建議：故障頻率較高，建議加強預防性維護"
        elif most_common and most_common["count"] > total_faults * 0.5:
            message += "\n💡 建議：重點關注主要故障類型的根本原因"

        return TextMessage(text=message)

    def _format_production_stats(self, data: dict[str, Any]) -> TextMessage:
        """格式化生產統計訊息"""
        departments = data.get("departments", [])
        summary = data.get("summary", {})

        if not departments:
            return TextMessage(text="❌ 沒有生產統計資料")

        message = "🏭 生產統計報告\n"
        message += "━━━━━━━━━━━━━━━━━━━━\n"

        # 整體統計
        total_machines = summary.get("total_machines", 0)
        total_good = summary.get("total_good_parts", 0)
        total_defective = summary.get("total_defective_parts", 0)
        quality_rate = summary.get("overall_quality_rate", 0)

        message += "📊 整體概況：\n"
        message += f"   機台總數：{total_machines} 台\n"
        message += f"   良品總數：{total_good:,} 件\n"
        message += f"   不良品：{total_defective:,} 件\n"
        message += f"   品質率：{quality_rate:.1f}%\n\n"

        # 各部門統計
        message += "🏭 各部門表現：\n"
        for dept in departments:
            dept_name = dept.get("department", "未知部門")
            machine_count = dept.get("machine_count", 0)
            utilization = dept.get("avg_utilization", 0)
            good_parts = dept.get("total_good_parts", 0)

            util_pct = utilization / 100 if utilization > 1 else utilization
            status_icon = self._get_status_icon(util_pct)
            dept_icon = self.department_icons.get(dept_name, "🏭")

            message += f"{dept_icon} {dept_name}\n"
            message += (
                f"   {status_icon} 稼動率 {util_pct:.1%} | "
                f"{machine_count} 台 | {good_parts:,} 件\n"
            )

        return TextMessage(text=message)

    def _format_department_status(self, data: dict[str, Any]) -> TextMessage:
        """格式化部門狀態訊息"""
        department = data.get("department", "未知部門")
        machines = data.get("machines", [])
        machine_count = data.get("machine_count", 0)

        if machine_count == 0:
            return TextMessage(
                text=(f"❌ {data.get('message', f'{department} 沒有機台資料')}")
            )

        dept_icon = self.department_icons.get(department, "🏭")

        message = f"{dept_icon} {department} 狀態報告\n"
        message += "━━━━━━━━━━━━━━━━━━━━\n"
        message += f"📊 機台總數：{machine_count} 台\n\n"

        # 機台詳情
        for machine in machines:
            machine_id = machine.get("machine_id", "")
            machine_name = machine.get("machine_name", "")
            utilization = machine.get("utilization_rate", 0)
            efficiency = machine.get("efficiency_rate", 0)

            util_pct = utilization / 100 if utilization > 1 else utilization
            eff_pct = efficiency / 100 if efficiency > 1 else efficiency
            status_icon = self._get_status_icon(util_pct)

            message += f"{status_icon} {machine_id} {machine_name}\n"
            message += f"   稼動率 {util_pct:.1%} | 效率 {eff_pct:.1%}\n"

        return TextMessage(text=message)

    def _format_generic_result(self, data: dict[str, Any]) -> TextMessage:
        """格式化一般查詢結果"""
        if isinstance(data, dict) and "raw_data" in data:
            raw_data = data["raw_data"]
            if isinstance(raw_data, list) and raw_data:
                message = "📊 查詢結果：\n"
                message += "━━━━━━━━━━━━━━━━━━━━\n"

                for i, row in enumerate(raw_data[:5]):  # 限制顯示5行
                    message += f"{i+1}. {row}\n"

                if len(raw_data) > 5:
                    message += f"\n... 共 {len(raw_data)} 行結果"

                return TextMessage(text=message)

        return TextMessage(text="📊 查詢完成，結果格式未識別")

    def _get_status_icon(self, utilization_rate: float) -> str:
        """根據稼動率獲取狀態圖示"""
        if utilization_rate >= 0.8:
            return self.status_icons["high"]
        elif utilization_rate >= 0.6:
            return self.status_icons["medium"]
        elif utilization_rate > 0:
            return self.status_icons["low"]
        else:
            return self.status_icons["unknown"]

    def _get_severity_icon(self, severity: str) -> str:
        """根據嚴重性獲取圖示"""
        severity_lower = severity.lower()
        if "high" in severity_lower or "嚴重" in severity_lower:
            return "🔴"
        elif "medium" in severity_lower or "中等" in severity_lower:
            return "🟡"
        elif "low" in severity_lower or "輕微" in severity_lower:
            return "🟢"
        else:
            return "⚪"

    def format_suggestion_message(self) -> TextMessage:
        """格式化建議查詢訊息"""
        message = "💡 您可以嘗試以下查詢：\n"
        message += "━━━━━━━━━━━━━━━━━━━━\n"
        message += "🔍 機台查詢：\n"
        message += "   • M001機台狀況如何？\n"
        message += "   • 查看所有機台\n"
        message += "   • 加工部狀況\n\n"
        message += "🔧 故障分析：\n"
        message += "   • 近期故障記錄\n"
        message += "   • 故障統計分析\n\n"
        message += "📊 生產統計：\n"
        message += "   • 生產統計報告\n"
        message += "   • 機台稼動率\n\n"
        message += "🛠️ 進階查詢：\n"
        message += "   • /sql SELECT * FROM machines\n"
        message += "   • /tables 查看所有表格"

        return TextMessage(text=message)
