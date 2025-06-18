import json
from typing import Dict, Any, List
from linebot.v3.messaging import FlexMessage
from datetime import datetime, timezone

from src.config import get_settings

settings = get_settings()


class FlexBuilder:
    def build_workbooks_list_flex(self, directory: str, data: Dict[str, Any]) -> FlexMessage:
        workbooks = data.get("workbooks", [])
        
        contents = []
        for wb in workbooks[:10]:  # Limit to 10 workbooks
            contents.append({
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": wb.get("name", ""),
                        "size": "sm",
                        "color": "#1F2937",
                        "flex": 3,
                    },
                    {
                        "type": "text",
                        "text": wb.get("size", "0 KB"),
                        "size": "sm",
                        "color": "#6B7280",
                        "flex": 1,
                        "align": "end",
                    },
                ],
                "spacing": "sm",
            })
            contents.append({"type": "separator", "margin": "sm"})
        
        if contents:
            contents.pop()  # Remove last separator
        
        flex_content = {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "Excel 檔案清單",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#1F2937",
                    },
                    {
                        "type": "text",
                        "text": f"目錄: {directory}",
                        "size": "sm",
                        "color": "#6B7280",
                        "margin": "sm",
                    }
                ],
                "backgroundColor": "#F3F4F6",
                "paddingAll": "15px",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": contents if contents else [
                    {
                        "type": "text",
                        "text": "暫無 Excel 檔案",
                        "size": "sm",
                        "color": "#6B7280",
                        "align": "center",
                    }
                ],
                "spacing": "md",
                "paddingAll": "20px",
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"共 {len(workbooks)} 個檔案",
                        "size": "sm",
                        "color": "#1F2937",
                        "align": "center",
                        "weight": "bold",
                    },
                    {
                        "type": "text",
                        "text": f"更新時間：{self._get_current_time()}",
                        "size": "xs",
                        "color": "#9CA3AF",
                        "align": "center",
                        "margin": "sm",
                    }
                ],
                "paddingAll": "10px",
            },
        }
        
        return FlexMessage(
            alt_text="Excel 檔案清單",
            contents=flex_content,
        )

    def build_excel_data_flex(self, filename: str, sheet_name: str, data: Dict[str, Any]) -> FlexMessage:
        rows = data.get("rows", [])
        columns = data.get("columns", [])
        
        # Show first few rows and columns
        display_rows = rows[:5]
        display_cols = columns[:4] if columns else []
        
        contents = []
        
        # Header row
        if display_cols:
            header_contents = []
            for col in display_cols:
                header_contents.append({
                    "type": "text",
                    "text": str(col)[:10],
                    "size": "xs",
                    "color": "#6B7280",
                    "weight": "bold",
                    "flex": 1,
                    "align": "center",
                })
            
            contents.append({
                "type": "box",
                "layout": "horizontal",
                "contents": header_contents,
                "spacing": "sm",
                "backgroundColor": "#E5E7EB",
                "paddingAll": "5px",
            })
        
        # Data rows
        for i, row in enumerate(display_rows):
            row_contents = []
            for col in display_cols:
                value = str(row.get(col, ""))[:10]
                row_contents.append({
                    "type": "text",
                    "text": value,
                    "size": "xs",
                    "color": "#1F2937",
                    "flex": 1,
                    "align": "center",
                })
            
            contents.append({
                "type": "box",
                "layout": "horizontal",
                "contents": row_contents,
                "spacing": "sm",
                "paddingAll": "3px",
            })
            
            if i < len(display_rows) - 1:
                contents.append({"type": "separator", "margin": "sm"})
        
        if len(rows) > 5:
            contents.append({
                "type": "text",
                "text": f"... 還有 {len(rows) - 5} 筆資料",
                "size": "xs",
                "color": "#6B7280",
                "align": "center",
                "margin": "md",
            })
        
        flex_content = {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": filename,
                        "weight": "bold",
                        "size": "lg",
                        "color": "#1F2937",
                    },
                    {
                        "type": "text",
                        "text": f"工作表: {sheet_name}",
                        "size": "sm",
                        "color": "#6B7280",
                        "margin": "sm",
                    }
                ],
                "backgroundColor": "#F3F4F6",
                "paddingAll": "15px",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": contents if contents else [
                    {
                        "type": "text",
                        "text": "無資料",
                        "size": "sm",
                        "color": "#6B7280",
                        "align": "center",
                    }
                ],
                "spacing": "sm",
                "paddingAll": "15px",
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"共 {len(rows)} 筆資料",
                        "size": "sm",
                        "color": "#1F2937",
                        "align": "center",
                        "weight": "bold",
                    },
                    {
                        "type": "text",
                        "text": f"更新時間：{self._get_current_time()}",
                        "size": "xs",
                        "color": "#9CA3AF",
                        "align": "center",
                        "margin": "sm",
                    }
                ],
                "paddingAll": "10px",
            },
        }
        
        return FlexMessage(
            alt_text=f"{filename} - {sheet_name} 資料",
            contents=flex_content,
        )

    def build_workbook_info_flex(self, filename: str, data: Dict[str, Any]) -> FlexMessage:
        sheets = data.get("sheets", [])
        file_info = data.get("file_info", {})
        
        contents = []
        
        # File info section
        if file_info:
            contents.append({
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": "檔案大小",
                        "size": "sm",
                        "color": "#6B7280",
                        "flex": 2,
                    },
                    {
                        "type": "text",
                        "text": file_info.get("size", "N/A"),
                        "size": "sm",
                        "color": "#1F2937",
                        "flex": 3,
                    },
                ],
                "spacing": "sm",
            })
            contents.append({
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": "建立時間",
                        "size": "sm",
                        "color": "#6B7280",
                        "flex": 2,
                    },
                    {
                        "type": "text",
                        "text": file_info.get("created", "N/A"),
                        "size": "sm",
                        "color": "#1F2937",
                        "flex": 3,
                    },
                ],
                "spacing": "sm",
                "margin": "sm",
            })
            contents.append({"type": "separator", "margin": "md"})
        
        # Sheets list
        contents.append({
            "type": "text",
            "text": "工作表清單",
            "size": "sm",
            "color": "#374151",
            "weight": "bold",
            "margin": "md",
        })
        
        for sheet in sheets[:10]:  # Limit to 10 sheets
            contents.append({
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": sheet.get("name", ""),
                        "size": "sm",
                        "color": "#1F2937",
                        "flex": 3,
                    },
                    {
                        "type": "text",
                        "text": f"{sheet.get('rows', 0)} × {sheet.get('cols', 0)}",
                        "size": "sm",
                        "color": "#6B7280",
                        "flex": 2,
                        "align": "end",
                    },
                ],
                "spacing": "sm",
                "margin": "sm",
            })
        
        flex_content = {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "檔案資訊",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#1F2937",
                    },
                    {
                        "type": "text",
                        "text": filename,
                        "size": "sm",
                        "color": "#6B7280",
                        "margin": "sm",
                        "wrap": True,
                    }
                ],
                "backgroundColor": "#F3F4F6",
                "paddingAll": "15px",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": contents if contents else [
                    {
                        "type": "text",
                        "text": "無檔案資訊",
                        "size": "sm",
                        "color": "#6B7280",
                        "align": "center",
                    }
                ],
                "spacing": "sm",
                "paddingAll": "20px",
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"共 {len(sheets)} 個工作表",
                        "size": "sm",
                        "color": "#1F2937",
                        "align": "center",
                        "weight": "bold",
                    },
                    {
                        "type": "text",
                        "text": f"更新時間：{self._get_current_time()}",
                        "size": "xs",
                        "color": "#9CA3AF",
                        "align": "center",
                        "margin": "sm",
                    }
                ],
                "paddingAll": "10px",
            },
        }
        
        return FlexMessage(
            alt_text=f"{filename} 檔案資訊",
            contents=flex_content,
        )

    def build_queries_flex(self, data: Dict[str, Any]) -> FlexMessage:
        queries = data.get("queries", [])
        
        contents = []
        for i, query in enumerate(queries[:5], 1):  # Top 5 queries
            query_text = query.get("query", "")[:50] + "..." if len(query.get("query", "")) > 50 else query.get("query", "")
            
            contents.append({
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"#{i}",
                                "size": "sm",
                                "color": "#6B7280",
                                "flex": 0,
                            },
                            {
                                "type": "text",
                                "text": f"{query.get('total_time', 0):.2f}ms",
                                "size": "sm",
                                "color": "#DC2626",
                                "flex": 1,
                                "align": "end",
                                "weight": "bold",
                            },
                        ],
                    },
                    {
                        "type": "text",
                        "text": query_text,
                        "size": "xs",
                        "color": "#374151",
                        "wrap": True,
                        "margin": "sm",
                    },
                ],
                "spacing": "sm",
            })
            contents.append({"type": "separator", "margin": "md"})
        
        if contents:
            contents.pop()  # Remove last separator
        
        flex_content = {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "最慢查詢排行",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#1F2937",
                    }
                ],
                "backgroundColor": "#F3F4F6",
                "paddingAll": "15px",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": contents if contents else [
                    {
                        "type": "text",
                        "text": "暫無資料",
                        "size": "sm",
                        "color": "#6B7280",
                        "align": "center",
                    }
                ],
                "spacing": "md",
                "paddingAll": "20px",
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"更新時間：{self._get_current_time()}",
                        "size": "xs",
                        "color": "#9CA3AF",
                        "align": "center",
                    }
                ],
                "paddingAll": "10px",
            },
        }
        
        return FlexMessage(
            alt_text="最慢查詢排行",
            contents=flex_content,
        )

    def build_sql_result_flex(self, query: str, data: Dict[str, Any]) -> FlexMessage:
        rows = data.get("rows", [])
        columns = data.get("columns", [])
        
        # Show first few rows and columns
        display_rows = rows[:3]
        display_cols = columns[:3]
        
        contents = []
        
        # Header row
        if display_cols:
            header_contents = []
            for col in display_cols:
                header_contents.append({
                    "type": "text",
                    "text": col[:10],
                    "size": "xs",
                    "color": "#6B7280",
                    "weight": "bold",
                    "flex": 1,
                })
            
            contents.append({
                "type": "box",
                "layout": "horizontal",
                "contents": header_contents,
                "spacing": "sm",
            })
            contents.append({"type": "separator", "margin": "sm"})
        
        # Data rows
        for row in display_rows:
            row_contents = []
            for i, col in enumerate(display_cols):
                value = str(row.get(col, ""))[:10]
                row_contents.append({
                    "type": "text",
                    "text": value,
                    "size": "xs",
                    "color": "#1F2937",
                    "flex": 1,
                })
            
            contents.append({
                "type": "box",
                "layout": "horizontal",
                "contents": row_contents,
                "spacing": "sm",
            })
        
        if len(rows) > 3:
            contents.append({
                "type": "text",
                "text": f"... 還有 {len(rows) - 3} 筆資料",
                "size": "xs",
                "color": "#6B7280",
                "align": "center",
                "margin": "md",
            })
        
        flex_content = {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "SQL 查詢結果",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#1F2937",
                    },
                    {
                        "type": "text",
                        "text": query[:50] + "..." if len(query) > 50 else query,
                        "size": "xs",
                        "color": "#6B7280",
                        "wrap": True,
                        "margin": "sm",
                    }
                ],
                "backgroundColor": "#F3F4F6",
                "paddingAll": "15px",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": contents if contents else [
                    {
                        "type": "text",
                        "text": "查詢無結果",
                        "size": "sm",
                        "color": "#6B7280",
                        "align": "center",
                    }
                ],
                "spacing": "sm",
                "paddingAll": "20px",
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"共 {len(rows)} 筆資料",
                        "size": "sm",
                        "color": "#1F2937",
                        "align": "center",
                        "weight": "bold",
                    },
                    {
                        "type": "text",
                        "text": f"更新時間：{self._get_current_time()}",
                        "size": "xs",
                        "color": "#9CA3AF",
                        "align": "center",
                        "margin": "sm",
                    }
                ],
                "paddingAll": "10px",
            },
        }
        
        return FlexMessage(
            alt_text="SQL 查詢結果",
            contents=flex_content,
        )

    def build_explain_flex(self, query: str, data: Dict[str, Any]) -> FlexMessage:
        plan = data.get("execution_plan", [])
        total_cost = data.get("total_cost", 0)
        
        contents = []
        for step in plan[:5]:  # First 5 steps
            contents.append({
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": step.get("node_type", ""),
                        "size": "sm",
                        "color": "#1F2937",
                        "weight": "bold",
                    },
                    {
                        "type": "text",
                        "text": f"成本: {step.get('total_cost', 0):.2f}",
                        "size": "xs",
                        "color": "#6B7280",
                        "margin": "sm",
                    },
                ],
            })
            contents.append({"type": "separator", "margin": "sm"})
        
        if contents:
            contents.pop()  # Remove last separator
        
        flex_content = {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "查詢執行計畫",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#1F2937",
                    },
                    {
                        "type": "text",
                        "text": f"總成本: {total_cost:.2f}",
                        "size": "sm",
                        "color": "#DC2626",
                        "weight": "bold",
                        "margin": "sm",
                    }
                ],
                "backgroundColor": "#F3F4F6",
                "paddingAll": "15px",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": contents if contents else [
                    {
                        "type": "text",
                        "text": "無法分析查詢",
                        "size": "sm",
                        "color": "#6B7280",
                        "align": "center",
                    }
                ],
                "spacing": "md",
                "paddingAll": "20px",
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"更新時間：{self._get_current_time()}",
                        "size": "xs",
                        "color": "#9CA3AF",
                        "align": "center",
                    }
                ],
                "paddingAll": "10px",
            },
        }
        
        return FlexMessage(
            alt_text="查詢執行計畫分析",
            contents=flex_content,
        )

    def build_indexes_flex(self, schema: str, data: Dict[str, Any]) -> FlexMessage:
        recommendations = data.get("recommendations", [])
        
        contents = []
        for rec in recommendations[:5]:  # Top 5 recommendations
            contents.append({
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": rec.get("table", ""),
                        "size": "sm",
                        "color": "#1F2937",
                        "weight": "bold",
                    },
                    {
                        "type": "text",
                        "text": rec.get("suggested_index", ""),
                        "size": "xs",
                        "color": "#6B7280",
                        "wrap": True,
                        "margin": "sm",
                    },
                    {
                        "type": "text",
                        "text": f"預期改善: {rec.get('improvement', 0)}%",
                        "size": "xs",
                        "color": "#059669",
                        "margin": "sm",
                    },
                ],
            })
            contents.append({"type": "separator", "margin": "md"})
        
        if contents:
            contents.pop()  # Remove last separator
        
        title = f"索引建議 - {schema}" if schema else "索引建議"
        
        flex_content = {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": title,
                        "weight": "bold",
                        "size": "lg",
                        "color": "#1F2937",
                    }
                ],
                "backgroundColor": "#F3F4F6",
                "paddingAll": "15px",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": contents if contents else [
                    {
                        "type": "text",
                        "text": "暫無索引建議",
                        "size": "sm",
                        "color": "#6B7280",
                        "align": "center",
                    }
                ],
                "spacing": "md",
                "paddingAll": "20px",
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"更新時間：{self._get_current_time()}",
                        "size": "xs",
                        "color": "#9CA3AF",
                        "align": "center",
                    }
                ],
                "paddingAll": "10px",
            },
        }
        
        return FlexMessage(
            alt_text=title,
            contents=flex_content,
        )

    def build_status_flex(self, machine_id: str, data: Dict[str, Any]) -> FlexMessage:
        status = data.get("status", "unknown")
        status_color = self._get_status_color(status)
        status_text = self._get_status_text(status)
        
        flex_content = {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"機台狀態 - {machine_id}",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#1F2937",
                    }
                ],
                "backgroundColor": "#F3F4F6",
                "paddingAll": "15px",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": "狀態",
                                "size": "sm",
                                "color": "#6B7280",
                                "flex": 2,
                            },
                            {
                                "type": "text",
                                "text": status_text,
                                "size": "sm",
                                "color": status_color,
                                "flex": 3,
                                "weight": "bold",
                            },
                        ],
                        "spacing": "sm",
                    },
                    {
                        "type": "separator",
                        "margin": "md",
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": "運轉時間",
                                "size": "sm",
                                "color": "#6B7280",
                                "flex": 2,
                            },
                            {
                                "type": "text",
                                "text": f"{data.get('uptime_hours', 0)} 小時",
                                "size": "sm",
                                "color": "#1F2937",
                                "flex": 3,
                            },
                        ],
                        "spacing": "sm",
                        "margin": "md",
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": "溫度",
                                "size": "sm",
                                "color": "#6B7280",
                                "flex": 2,
                            },
                            {
                                "type": "text",
                                "text": f"{data.get('temperature', 0)}°C",
                                "size": "sm",
                                "color": "#1F2937",
                                "flex": 3,
                            },
                        ],
                        "spacing": "sm",
                        "margin": "md",
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": "效率",
                                "size": "sm",
                                "color": "#6B7280",
                                "flex": 2,
                            },
                            {
                                "type": "text",
                                "text": f"{data.get('efficiency', 0)}%",
                                "size": "sm",
                                "color": "#1F2937",
                                "flex": 3,
                            },
                        ],
                        "spacing": "sm",
                        "margin": "md",
                    },
                ],
                "spacing": "md",
                "paddingAll": "20px",
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"更新時間：{self._get_current_time()}",
                        "size": "xs",
                        "color": "#9CA3AF",
                        "align": "center",
                    }
                ],
                "paddingAll": "10px",
            },
        }
        
        return FlexMessage(
            alt_text=f"機台 {machine_id} 狀態：{status_text}",
            contents=flex_content,
        )

    def build_trend_flex(self, period: str, data: Dict[str, Any]) -> FlexMessage:
        machines = data.get("machines", [])
        
        contents = []
        for machine in machines[:5]:
            contents.append({
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": machine.get("id", ""),
                        "size": "sm",
                        "color": "#1F2937",
                        "flex": 2,
                    },
                    {
                        "type": "text",
                        "text": f"{machine.get('fault_count', 0)} 次",
                        "size": "sm",
                        "color": "#DC2626" if machine.get("fault_count", 0) > 5 else "#059669",
                        "flex": 1,
                        "align": "end",
                    },
                ],
                "spacing": "sm",
            })
            contents.append({
                "type": "separator",
                "margin": "sm",
            })
        
        if contents and contents[-1]["type"] == "separator":
            contents.pop()
        
        flex_content = {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"故障趨勢 - {period}",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#1F2937",
                    }
                ],
                "backgroundColor": "#F3F4F6",
                "paddingAll": "15px",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": contents if contents else [
                    {
                        "type": "text",
                        "text": "暫無資料",
                        "size": "sm",
                        "color": "#6B7280",
                        "align": "center",
                    }
                ],
                "spacing": "md",
                "paddingAll": "20px",
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"總故障數：{data.get('total_faults', 0)} 次",
                        "size": "sm",
                        "color": "#1F2937",
                        "align": "center",
                        "weight": "bold",
                    },
                    {
                        "type": "text",
                        "text": f"更新時間：{self._get_current_time()}",
                        "size": "xs",
                        "color": "#9CA3AF",
                        "align": "center",
                        "margin": "sm",
                    }
                ],
                "paddingAll": "10px",
            },
        }
        
        return FlexMessage(
            alt_text=f"{period} 故障趨勢報告",
            contents=flex_content,
        )

    def build_suggestion_flex(self, machine_id: str, data: Dict[str, Any]) -> FlexMessage:
        suggestions = data.get("suggestions", [])
        priority = data.get("priority", "medium")
        priority_color = self._get_priority_color(priority)
        
        suggestion_contents = []
        for i, suggestion in enumerate(suggestions[:3], 1):
            suggestion_contents.append({
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": f"{i}.",
                        "size": "sm",
                        "color": "#6B7280",
                        "flex": 0,
                    },
                    {
                        "type": "text",
                        "text": suggestion,
                        "size": "sm",
                        "color": "#1F2937",
                        "flex": 1,
                        "wrap": True,
                        "margin": "sm",
                    },
                ],
                "spacing": "sm",
            })
        
        flex_content = {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"維修建議 - {machine_id}",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#1F2937",
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": "優先級",
                                "size": "xs",
                                "color": "#6B7280",
                            },
                            {
                                "type": "text",
                                "text": priority.upper(),
                                "size": "xs",
                                "color": priority_color,
                                "weight": "bold",
                                "margin": "sm",
                            },
                        ],
                        "margin": "sm",
                    }
                ],
                "backgroundColor": "#F3F4F6",
                "paddingAll": "15px",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": suggestion_contents if suggestion_contents else [
                    {
                        "type": "text",
                        "text": "目前無需特別維護",
                        "size": "sm",
                        "color": "#059669",
                        "align": "center",
                    }
                ],
                "spacing": "md",
                "paddingAll": "20px",
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "action": {
                            "type": "message",
                            "label": "查看詳細狀態",
                            "text": f"/status {machine_id}",
                        },
                        "style": "secondary",
                        "height": "sm",
                    },
                    {
                        "type": "text",
                        "text": f"更新時間：{self._get_current_time()}",
                        "size": "xs",
                        "color": "#9CA3AF",
                        "align": "center",
                        "margin": "md",
                    }
                ],
                "paddingAll": "10px",
            },
        }
        
        return FlexMessage(
            alt_text=f"機台 {machine_id} 維修建議",
            contents=flex_content,
        )

    def build_dynamic_flex(self, title: str, data: Dict[str, Any]) -> FlexMessage:
        contents = []
        
        for key, value in data.items():
            if key == "results":
                continue
            
            contents.append({
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": self._format_key(key),
                        "size": "sm",
                        "color": "#6B7280",
                        "flex": 2,
                    },
                    {
                        "type": "text",
                        "text": str(value),
                        "size": "sm",
                        "color": "#1F2937",
                        "flex": 3,
                        "wrap": True,
                    },
                ],
                "spacing": "sm",
            })
            contents.append({
                "type": "separator",
                "margin": "sm",
            })
        
        if contents and contents[-1]["type"] == "separator":
            contents.pop()
        
        flex_content = {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": title,
                        "weight": "bold",
                        "size": "lg",
                        "color": "#1F2937",
                    }
                ],
                "backgroundColor": "#F3F4F6",
                "paddingAll": "15px",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": contents if contents else [
                    {
                        "type": "text",
                        "text": "暫無資料",
                        "size": "sm",
                        "color": "#6B7280",
                        "align": "center",
                    }
                ],
                "spacing": "md",
                "paddingAll": "20px",
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"更新時間：{self._get_current_time()}",
                        "size": "xs",
                        "color": "#9CA3AF",
                        "align": "center",
                    }
                ],
                "paddingAll": "10px",
            },
        }
        
        return FlexMessage(
            alt_text=title,
            contents=flex_content,
        )

    def _get_status_color(self, status: str) -> str:
        status_colors = {
            "running": "#059669",
            "idle": "#F59E0B",
            "error": "#DC2626",
            "maintenance": "#6366F1",
        }
        return status_colors.get(status.lower(), "#6B7280")

    def _get_status_text(self, status: str) -> str:
        status_texts = {
            "running": "運行中",
            "idle": "閒置",
            "error": "錯誤",
            "maintenance": "維護中",
        }
        return status_texts.get(status.lower(), "未知")

    def _get_priority_color(self, priority: str) -> str:
        priority_colors = {
            "high": "#DC2626",
            "medium": "#F59E0B",
            "low": "#059669",
        }
        return priority_colors.get(priority.lower(), "#6B7280")

    def _format_key(self, key: str) -> str:
        return key.replace("_", " ").title()

    def _get_current_time(self) -> str:
        now = datetime.now(timezone.utc)
        return now.strftime("%Y-%m-%d %H:%M UTC")