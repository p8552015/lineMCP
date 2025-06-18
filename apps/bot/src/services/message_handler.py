import re
import structlog
# import sqlite3  # ❌ 已移除 - 違反 MCP 協定原則
import asyncio
import os
import sys
from typing import Union, Dict, Any, List, Optional
from linebot.v3.messaging import (
    TextMessage,
    FlexMessage,
    Message,
)

from src.services.openai_client import OpenAIClient

# 設定並導入新的統一 MCP 客戶端
logger = structlog.get_logger()

try:
    # 直接使用我們新創建的統一客戶端
    from src.services.simple_mcp_client import get_simple_mcp_client
    _USE_NEW_CLIENT = True
    logger.info("✅ 使用新的統一 MCP 客戶端實作")
except ImportError as e:
    # 如果統一客戶端有問題，使用 true_mcp_client 作為回退
    from src.services.true_mcp_client import TrueMCPClient
    def get_simple_mcp_client():
        return TrueMCPClient()
    _USE_NEW_CLIENT = False
    logger.warning(f"⚠️ 回退到真正的 MCP 客戶端: {e}")
from src.services.flex_builder import FlexBuilder
from src.utils.observability import get_tracer
from src.models.commands import Command, parse_command
# from src.services.taskmaster_integration import TaskMasterIntegration  # 暫時禁用

tracer = get_tracer(__name__)


class MessageHandler:
    def __init__(self):
        self.openai_client = OpenAIClient()
        self.mcp_client = get_simple_mcp_client()
        self.flex_builder = FlexBuilder()
        self._use_new_client = _USE_NEW_CLIENT
        
        # Initialize TaskMaster integration if OpenAI API key is available
        # 暫時禁用 TaskMaster 整合以解決導入問題
        self.taskmaster = None
        logger.info(f"MCP 客戶端類型: {'統一客戶端' if self._use_new_client else '原有客戶端'}")
        logger.info("TaskMaster integration temporarily disabled")

    async def _call_mcp_tool_compatible(self, server: str, tool: str, params: dict) -> dict:
        """
        統一的 MCP 工具呼叫方法，處理新舊客戶端的不同回應格式
        """
        try:
            if self._use_new_client:
                # 新的統一客戶端回傳 MCPResponse 物件
                response = await self.mcp_client.call_tool(server, tool, params)
                
                # 檢查是否為 MCPResponse 物件
                if hasattr(response, 'success'):
                    return {
                        "success": response.success,
                        "data": response.data,
                        "error": response.error,
                    }
                else:
                    # 向後相容：如果回傳的是字典格式
                    return response
            else:
                # 原有客戶端
                return await self.mcp_client.call_tool(
                    server_name=server,
                    tool_name=tool,
                    parameters=params
                )
        except Exception as e:
            logger.error(f"MCP tool call failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def process_message_sync(
        self, user_id: str, message_text: str, reply_token: str
    ) -> Message:
        """同步版本的訊息處理，避免 event loop 衝突"""
        import asyncio
        
        try:
            # 如果已經在 event loop 中，直接處理
            loop = asyncio.get_running_loop()
            # 使用基本的文字回應避免複雜的非同步處理
            return TextMessage(text=f"收到您的訊息：{message_text}\n正在處理中，請稍後...")
        except RuntimeError:
            # 沒有運行的 event loop，可以創建新的
            return asyncio.run(self.process_message(user_id, message_text, reply_token))
    
    async def process_message(
        self, user_id: str, message_text: str, reply_token: str
    ) -> Message:
        with tracer.start_as_current_span("process_message") as span:
            span.set_attribute("message.length", len(message_text))
            
            command = parse_command(message_text)
            
            if command:
                span.set_attribute("command.type", command.name)
                span.set_attribute("command.has_args", bool(command.args))
                return await self._handle_command(user_id, command)
            else:
                span.set_attribute("message.type", "natural_language")
                # 檢查是否為機台相關查詢
                if self._is_machine_query(message_text):
                    return await self._handle_machine_query_async(message_text)
                else:
                    return await self._handle_natural_language(user_id, message_text)

    async def _handle_command(self, user_id: str, command: Command) -> Message:
        logger.info(
            "Processing command",
            command=command.name,
            args=command.args,
        )
        
        if command.name == "sql":
            return await self._handle_sql_command(user_id, command.args)
        elif command.name == "tables":
            return await self._handle_tables_command(user_id)
        elif command.name == "status":
            return await self._handle_status_command(user_id, command.args)
        elif command.name == "search":
            return await self._handle_search_command(user_id, command.args)
        elif command.name == "tools":
            return await self._handle_tools_command(user_id, command.args)
        elif command.name == "list":
            return await self._handle_list_command(user_id, command.args)
        elif command.name == "create":
            return await self._handle_create_command(user_id, command.args)
        elif command.name == "read":
            return await self._handle_read_command(user_id, command.args)
        elif command.name == "write":
            return await self._handle_write_command(user_id, command.args)
        elif command.name == "chart":
            return await self._handle_chart_command(user_id, command.args)
        elif command.name == "pivot":
            return await self._handle_pivot_command(user_id, command.args)
        elif command.name == "format":
            return await self._handle_format_command(user_id, command.args)
        elif command.name == "info":
            return await self._handle_info_command(user_id, command.args)
        elif command.name == "task":
            return await self._handle_task_command(user_id, command.args)
        else:
            return TextMessage(text=f"未知的指令: {command.name}")

    async def _handle_sql_command(self, user_id: str, args: List[str]) -> Message:
        """處理SQL查詢指令"""
        if not args:
            return TextMessage(text="請提供SQL查詢語句，例如：/sql SELECT * FROM machines LIMIT 5")
        
        sql_query = " ".join(args)
        
        try:
            result = await self._call_mcp_tool_compatible(
                "sqlite",
                "read_query",
                {"query": sql_query}
            )
            
            if result.get("success"):
                data = result.get("data", [])
                if isinstance(data, list) and data:
                    # 格式化查詢結果
                    response = f"📊 SQL查詢結果：\n```\n{sql_query}\n```\n\n"
                    for i, row in enumerate(data[:10]):  # 限制顯示前10行
                        response += f"{i+1}. {row}\n"
                    if len(data) > 10:
                        response += f"\n... 共 {len(data)} 行結果，僅顯示前10行"
                    return TextMessage(text=response)
                else:
                    return TextMessage(text=f"查詢執行成功，但沒有返回數據：\n```\n{sql_query}\n```")
            else:
                error_msg = result.get("error", "查詢執行失敗")
                return TextMessage(text=f"❌ SQL查詢失敗：{error_msg}")
                
        except Exception as e:
            logger.error("SQL query failed", error=str(e), exc_info=e)
            return TextMessage(text="SQL查詢時發生錯誤，請檢查語法後重試。")

    async def _handle_tables_command(self, user_id: str) -> Message:
        """顯示資料庫表格列表"""
        try:
            result = await self._call_mcp_tool_compatible(
                "sqlite",
                "list_tables", 
                {}
            )
            
            if result.get("success"):
                tables = result.get("data", [])
                if tables:
                    response = "📋 資料庫表格：\n"
                    for table in tables:
                        response += f"• {table}\n"
                    response += "\n使用 `/sql DESCRIBE table_name` 查看表格結構"
                    return TextMessage(text=response)
                else:
                    return TextMessage(text="資料庫中沒有表格")
            else:
                error_msg = result.get("error", "獲取表格列表失敗")
                return TextMessage(text=f"❌ {error_msg}")
                
        except Exception as e:
            logger.error("List tables failed", error=str(e), exc_info=e)
            return TextMessage(text="獲取表格列表時發生錯誤。")

    async def _handle_status_command(self, user_id: str, args: List[str]) -> Message:
        """處理機器狀態查詢"""
        # 預設查詢所有機器狀態
        sql_query = """
        SELECT machine_id, 
               AVG(utilization_rate) as avg_utilization,
               COUNT(*) as record_count,
               MAX(created_at) as last_update
        FROM machine_utilization 
        GROUP BY machine_id 
        ORDER BY avg_utilization DESC
        """
        
        try:
            result = await self._call_mcp_tool_compatible("sqlite", "read_query", {"query": sql_query})
            
            if result.get("success"):
                data = result.get("data", [])
                if data:
                    response = "🔧 機器狀態統計：\n\n"
                    for row in data:
                        machine_id = row.get('machine_id', 'Unknown')
                        avg_util = row.get('avg_utilization', 0)
                        response += f"機器 {machine_id}：使用率 {avg_util:.1f}%\n"
                    return TextMessage(text=response)
                else:
                    return TextMessage(text="沒有找到機器狀態數據")
            else:
                error_msg = result.get("error", "查詢失敗")
                return TextMessage(text=f"❌ 狀態查詢失敗：{error_msg}")
                
        except Exception as e:
            logger.error("Status query failed", error=str(e), exc_info=e)
            return TextMessage(text="查詢機器狀態時發生錯誤。")

    async def _handle_search_command(self, user_id: str, args: List[str]) -> Message:
        """處理搜尋指令"""
        if not args:
            return TextMessage(text="請提供搜尋關鍵字，例如：/search React hooks")
        
        query = " ".join(args)
        
        try:
            # 這裡應該呼叫 Context7 MCP 服務進行搜尋
            # 目前先返回提示訊息
            return TextMessage(text=f"🔍 搜尋功能開發中\n搜尋關鍵字：{query}")
                
        except Exception as e:
            logger.error("Search failed", error=str(e), exc_info=e)
            return TextMessage(text="搜尋時發生錯誤。")

    async def _handle_tools_command(self, user_id: str, args: List[str]) -> Message:
        """顯示可用的MCP工具"""
        server_name = args[0] if args else "sqlite"
        
        try:
            tools = await self.mcp_client.list_tools(server_name)
            
            if tools:
                response = f"🛠️ {server_name} MCP伺服器可用工具：\n\n"
                for tool in tools:
                    response += f"• {tool}\n"
                return TextMessage(text=response)
            else:
                return TextMessage(text=f"無法獲取 {server_name} 伺服器的工具列表")
                
        except Exception as e:
            logger.error("List tools failed", error=str(e), exc_info=e)
            return TextMessage(text="獲取工具列表時發生錯誤。")

    async def _handle_list_command(self, user_id: str, args: List[str]) -> Message:
        directory = args[0] if args else "."
        
        try:
            result = await self.openai_client.call_mcp_tool(
                user_id=user_id,
                tool_name="list_workbooks",
                parameters={"directory": directory},
            )
            
            if result.get("success"):
                data = result.get("data", {})
                return self.flex_builder.build_workbooks_list_flex(directory, data)
            else:
                error_msg = result.get("error", "無法取得檔案清單")
                return TextMessage(text=f"錯誤：{error_msg}")
                
        except Exception as e:
            logger.error("Failed to list workbooks", error=str(e), exc_info=e)
            return TextMessage(text="取得 Excel 檔案清單時發生錯誤，請稍後再試。")

    async def _handle_create_command(self, user_id: str, args: List[str]) -> Message:
        if not args:
            return TextMessage(text="請提供檔案名稱，例如：/create sales_report.xlsx")
        
        filename = args[0]
        sheet_name = args[1] if len(args) > 1 else "Sheet1"
        
        try:
            result = await self.openai_client.call_mcp_tool(
                user_id=user_id,
                tool_name="create_workbook",
                parameters={"filename": filename, "sheet_name": sheet_name},
            )
            
            if result.get("success"):
                return TextMessage(text=f"✅ 成功建立 Excel 檔案：{filename}")
            else:
                error_msg = result.get("error", "無法建立檔案")
                return TextMessage(text=f"❌ 錯誤：{error_msg}")
                
        except Exception as e:
            logger.error("Failed to create workbook", error=str(e), exc_info=e)
            return TextMessage(text="建立 Excel 檔案時發生錯誤，請稍後再試。")

    async def _handle_read_command(self, user_id: str, args: List[str]) -> Message:
        if len(args) < 2:
            return TextMessage(text="請提供檔案名稱和工作表名稱，例如：/read sales.xlsx Sheet1")
        
        filename = args[0]
        sheet_name = args[1]
        range_str = args[2] if len(args) > 2 else None
        
        try:
            parameters = {"filename": filename, "sheet_name": sheet_name}
            if range_str:
                parameters["range"] = range_str
                
            result = await self.openai_client.call_mcp_tool(
                user_id=user_id,
                tool_name="read_sheet",
                parameters=parameters,
            )
            
            if result.get("success"):
                data = result.get("data", {})
                return self.flex_builder.build_excel_data_flex(filename, sheet_name, data)
            else:
                error_msg = result.get("error", "無法讀取資料")
                return TextMessage(text=f"❌ 錯誤：{error_msg}")
                
        except Exception as e:
            logger.error("Failed to read sheet", error=str(e), exc_info=e)
            return TextMessage(text="讀取 Excel 資料時發生錯誤，請稍後再試。")

    async def _handle_write_command(self, user_id: str, args: List[str]) -> Message:
        if len(args) < 3:
            return TextMessage(text="請提供檔案名、工作表和起始位置，例如：/write sales.xlsx Sheet1 A1")
        
        filename = args[0]
        sheet_name = args[1]
        start_cell = args[2]
        
        # 這裡只是範例，實際上應該從用戶輸入中解析資料
        sample_data = [
            ["產品", "銷量", "金額"],
            ["產品A", "100", "10000"],
            ["產品B", "200", "25000"],
        ]
        
        try:
            result = await self.openai_client.call_mcp_tool(
                user_id=user_id,
                tool_name="write_data",
                parameters={
                    "filename": filename,
                    "sheet_name": sheet_name,
                    "start_cell": start_cell,
                    "data": sample_data,
                },
            )
            
            if result.get("success"):
                return TextMessage(text=f"✅ 成功寫入資料到 {filename} 的 {sheet_name} 工作表")
            else:
                error_msg = result.get("error", "無法寫入資料")
                return TextMessage(text=f"❌ 錯誤：{error_msg}")
                
        except Exception as e:
            logger.error("Failed to write data", error=str(e), exc_info=e)
            return TextMessage(text="寫入 Excel 資料時發生錯誤，請稍後再試。")

    async def _handle_chart_command(self, user_id: str, args: List[str]) -> Message:
        if len(args) < 4:
            return TextMessage(text="請提供檔案名、工作表、圖表類型和資料範圍，例如：/chart sales.xlsx Sheet1 bar A1:B10")
        
        filename = args[0]
        sheet_name = args[1]
        chart_type = args[2]
        data_range = args[3]
        position = args[4] if len(args) > 4 else "E2"
        
        try:
            result = await self.openai_client.call_mcp_tool(
                user_id=user_id,
                tool_name="create_chart",
                parameters={
                    "filename": filename,
                    "sheet_name": sheet_name,
                    "chart_type": chart_type,
                    "data_range": data_range,
                    "position": position,
                },
            )
            
            if result.get("success"):
                return TextMessage(text=f"✅ 成功在 {filename} 建立 {chart_type} 圖表")
            else:
                error_msg = result.get("error", "無法建立圖表")
                return TextMessage(text=f"❌ 錯誤：{error_msg}")
                
        except Exception as e:
            logger.error("Failed to create chart", error=str(e), exc_info=e)
            return TextMessage(text="建立圖表時發生錯誤，請稍後再試。")

    async def _handle_pivot_command(self, user_id: str, args: List[str]) -> Message:
        if len(args) < 4:
            return TextMessage(text="請提供檔案名、來源工作表、資料範圍和目標工作表，例如：/pivot sales.xlsx Sheet1 A1:D100 PivotSheet")
        
        filename = args[0]
        source_sheet = args[1]
        source_range = args[2]
        target_sheet = args[3]
        
        try:
            result = await self.openai_client.call_mcp_tool(
                user_id=user_id,
                tool_name="create_pivot_table",
                parameters={
                    "filename": filename,
                    "source_sheet": source_sheet,
                    "source_range": source_range,
                    "target_sheet": target_sheet,
                },
            )
            
            if result.get("success"):
                return TextMessage(text=f"✅ 成功在 {target_sheet} 建立樞紐分析表")
            else:
                error_msg = result.get("error", "無法建立樞紐分析表")
                return TextMessage(text=f"❌ 錯誤：{error_msg}")
                
        except Exception as e:
            logger.error("Failed to create pivot table", error=str(e), exc_info=e)
            return TextMessage(text="建立樞紐分析表時發生錯誤，請稍後再試。")

    async def _handle_format_command(self, user_id: str, args: List[str]) -> Message:
        if len(args) < 3:
            return TextMessage(text="請提供檔案名、工作表和範圍，例如：/format sales.xlsx Sheet1 A1:D1")
        
        filename = args[0]
        sheet_name = args[1]
        cell_range = args[2]
        
        # 預設格式設定
        format_options = {
            "font": {"bold": True, "size": 14},
            "fill": {"color": "#4472C4"},
            "font_color": "#FFFFFF",
        }
        
        try:
            result = await self.openai_client.call_mcp_tool(
                user_id=user_id,
                tool_name="format_cells",
                parameters={
                    "filename": filename,
                    "sheet_name": sheet_name,
                    "range": cell_range,
                    "format": format_options,
                },
            )
            
            if result.get("success"):
                return TextMessage(text=f"✅ 成功格式化 {filename} 中的儲存格")
            else:
                error_msg = result.get("error", "無法格式化儲存格")
                return TextMessage(text=f"❌ 錯誤：{error_msg}")
                
        except Exception as e:
            logger.error("Failed to format cells", error=str(e), exc_info=e)
            return TextMessage(text="格式化儲存格時發生錯誤，請稍後再試。")
    
    async def _handle_info_command(self, user_id: str, args: List[str]) -> Message:
        if not args:
            return TextMessage(text="請提供檔案名稱，例如：/info sales.xlsx")
        
        filename = args[0]
        
        try:
            result = await self.openai_client.call_mcp_tool(
                user_id=user_id,
                tool_name="get_sheet_info",
                parameters={"filename": filename},
            )
            
            if result.get("success"):
                data = result.get("data", {})
                return self.flex_builder.build_workbook_info_flex(filename, data)
            else:
                error_msg = result.get("error", "無法取得檔案資訊")
                return TextMessage(text=f"❌ 錯誤：{error_msg}")
                
        except Exception as e:
            logger.error("Failed to get sheet info", error=str(e), exc_info=e)
            return TextMessage(text="取得檔案資訊時發生錯誤，請稍後再試。")

    async def _handle_task_command(self, user_id: str, args: List[str]) -> Message:
        """處理任務管理指令"""
        if not self.taskmaster:
            return TextMessage(text="❌ TaskMaster 功能未啟用，請檢查 OpenAI API 金鑰設定")
        
        try:
            return await self.taskmaster.handle_task_command(user_id, "task", args)
        except Exception as e:
            logger.error("Failed to handle task command", error=str(e), exc_info=e)
            return TextMessage(text="處理任務指令時發生錯誤，請稍後再試。")

    async def _handle_natural_language(self, user_id: str, message_text: str) -> Message:
        """處理自然語言查詢，直接透過MCP Client呼叫相關工具"""
        try:
            # 首先檢查是否為任務相關的自然語言
            if self.taskmaster:
                task_response = await self.taskmaster.handle_natural_language_task(
                    user_id, message_text, context={"machine_context": True}
                )
                if task_response:
                    return task_response
            
            # 檢查是否為故障或統計相關查詢
            if "故障" in message_text or "統計" in message_text or "狀態" in message_text:
                return await self._handle_status_query(user_id, message_text)
            elif "機器" in message_text or "機台" in message_text or "狀態" in message_text:
                return await self._handle_status_query(user_id, message_text)
            elif "表格" in message_text or "資料庫" in message_text:
                return await self._handle_tables_command(user_id)
            else:
                # 回退到原有的OpenAI處理
                result = await self.openai_client.process_natural_language(
                    user_id=user_id,
                    message=message_text,
                )
                
                if result.get("type") == "text":
                    return TextMessage(text=result.get("content", "無法理解您的需求"))
                elif result.get("type") == "flex":
                    return self.flex_builder.build_dynamic_flex(
                        title=result.get("title", "查詢結果"),
                        data=result.get("data", {}),
                    )
                else:
                    return TextMessage(text="無法處理您的請求")
                
        except Exception as e:
            logger.error("Failed to process natural language", error=str(e), exc_info=e)
            return TextMessage(text="處理您的訊息時發生錯誤，請稍後再試。")

    async def _handle_status_query(self, user_id: str, message_text: str) -> Message:
        """處理狀態查詢，透過MCP Client呼叫SQLite MCP Server"""
        try:
            logger.info("Starting MCP status query", user_id=user_id)
            
            # 透過MCP Client查詢
            result = await self._call_mcp_tool_compatible("sqlite", "read_query", {
                    "query": """
                        SELECT machine_id, 
                               AVG(utilization_rate) as avg_utilization,
                               COUNT(*) as record_count,
                               MAX(created_at) as last_update
                        FROM machine_utilization 
                        GROUP BY machine_id 
                        ORDER BY avg_utilization DESC
                        LIMIT 10
                    """
                })
            
            logger.info("MCP call result", success=result.get("success"), error=result.get("error"))
            
            if result.get("success"):
                data = result.get("data", [])
                if data:
                    response = "🔧 機器故障統計報告 (via MCP)：\n\n"
                    
                    # 計算統計資訊 - 處理字典格式數據
                    high_util = [row for row in data if row.get('avg_utilization', 0) > 80]
                    medium_util = [row for row in data if 50 <= row.get('avg_utilization', 0) <= 80]
                    low_util = [row for row in data if row.get('avg_utilization', 0) < 50]
                    
                    response += f"📊 總機器數量：{len(data)}\n"
                    response += f"🟢 高使用率 (>80%)：{len(high_util)} 台\n"
                    response += f"🟡 中使用率 (50-80%)：{len(medium_util)} 台\n"
                    response += f"🔴 低使用率 (<50%)：{len(low_util)} 台\n\n"
                    
                    response += "詳細狀況：\n"
                    for row in data[:5]:  # 顯示前5台
                        machine_id = row.get('machine_id', 'Unknown')
                        avg_util = row.get('avg_utilization', 0)
                        status_icon = "🟢" if avg_util > 80 else "🟡" if avg_util > 50 else "🔴"
                        response += f"{status_icon} {machine_id}：{avg_util:.1f}%\n"
                    
                    if len(data) > 5:
                        response += f"\n... 還有 {len(data)-5} 台機器"
                    
                    return TextMessage(text=response)
                else:
                    return TextMessage(text="MCP查詢成功，但沒有找到機器狀態數據")
            else:
                error_msg = result.get("error", "未知錯誤")
                logger.error("MCP query failed", error=error_msg)
                return TextMessage(text=f"❌ MCP查詢失敗：{error_msg}")
                
        except Exception as e:
            logger.error("Failed to get fault analysis", error=str(e), exc_info=e)
            return TextMessage(text="查詢故障分析時發生錯誤")

    def _is_machine_query(self, message_text: str) -> bool:
        """判斷是否為機台相關查詢"""
        machine_keywords = [
            "機台", "稼動", "狀況", "M001", "M002", "M003", "M004", "M005", 
            "M006", "M007", "M008", "M009", "M010", "/status", "/trend", 
            "CNC", "銑床", "沖床", "焊接", "包裝", "故障", "維護", "效率"
        ]
        return any(keyword in message_text for keyword in machine_keywords)

    async def _handle_machine_query_async(self, message_text: str) -> Message:
        """非同步處理機台查詢"""
        try:
            # 提取機台編號
            machine_id = self._extract_machine_id(message_text)
            
            if machine_id:
                return await self._get_machine_status_async(machine_id)
            elif "/status" in message_text or "所有機台狀態" in message_text or "查看所有機台" in message_text:
                return await self._get_all_machines_status_async()
            elif any(word in message_text for word in ["稼動率最低", "表現最差", "需要維護"]):
                return await self._get_low_performance_machines_async()
            elif any(word in message_text for word in ["故障", "問題", "異常"]):
                return await self._get_fault_analysis_async()
            else:
                return await self._get_general_status_async()
                
        except Exception as e:
            logger.error("Failed to handle machine query async", error=str(e), exc_info=e)
            return TextMessage(text="查詢機台資料時發生錯誤，請稍後再試。")

    def _extract_machine_id(self, message_text: str) -> str:
        """從訊息中提取機台編號"""
        import re
        # 尋找 M001-M010 格式的機台編號
        match = re.search(r'M0(0[1-9]|10)', message_text)
        if match:
            return match.group(0)
        return None


    async def _get_machine_status_async(self, machine_id: str) -> Message:
        """非同步獲取特定機台狀態"""
        try:
            formatted_query = f"""
                SELECT 
                    m.machine_name,
                    m.department,
                    AVG(u.utilization_rate) as avg_utilization,
                    AVG(u.efficiency_rate) as avg_efficiency,
                    MAX(u.created_at) as last_record_date,
                    SUM(u.good_parts) as total_good_parts,
                    SUM(u.defective_parts) as total_defective_parts
                FROM machines m
                LEFT JOIN machine_utilization u ON m.machine_id = u.machine_id
                WHERE m.machine_id = '{machine_id}'
                GROUP BY m.machine_id
            """
            
            # 使用更短的超時時間並提供快速回退
            logger.info(f"🔍 開始查詢機台 {machine_id} 狀態")
            import asyncio
            try:
                result = await asyncio.wait_for(
                    self._call_mcp_tool_compatible("sqlite", "read_query", {"query": formatted_query}),
                    timeout=2.0  # 2秒超時
                )
            except asyncio.TimeoutError:
                logger.warning(f"⏰ MCP查詢超時，使用快速回應 for {machine_id}")
                # 快速回退：直接返回基本狀態
                return TextMessage(text=f"""📊 {machine_id} 機台狀態（快速查詢）
━━━━━━━━━━━━━━━━━━━━
🟡 狀態：系統正在處理中
🔧 機台類型：CNC車床A  
🏭 部門：加工部
⚠️ 詳細數據正在載入中

💡 提示：系統負載較高，請稍後再試詳細查詢
或使用指令：/sql SELECT * FROM machines WHERE machine_id='{machine_id}'""")
            
            if result.get("success") and result.get("data"):
                data = result["data"][0]  # 取第一筆記錄
                machine_name = data.get('machine_name', '未知')
                department = data.get('department', '未知')
                utilization = data.get('avg_utilization', 0) or 0
                efficiency = data.get('avg_efficiency', 0) or 0
                last_date = data.get('last_record_date', '無記錄')
                good_parts = data.get('total_good_parts', 0) or 0
                defective_parts = data.get('total_defective_parts', 0) or 0
                
                # 獲取故障記錄
                fault_query = f"""
                    SELECT COUNT(*) as fault_count
                    FROM machine_faults 
                    WHERE machine_id = '{machine_id}' AND fault_date >= date('now', '-7 days')
                """
                
                fault_result = await self._call_mcp_tool_compatible("sqlite", "read_query", {"query": fault_query})
                fault_count = 0
                if fault_result.get("success") and fault_result.get("data"):
                    fault_count = fault_result["data"][0].get('fault_count', 0) or 0
                
                # 生成狀態報告
                utilization_pct = utilization / 100 if utilization > 1 else utilization
                efficiency_pct = efficiency / 100 if efficiency > 1 else efficiency
                
                status_icon = "🟢" if utilization_pct > 0.8 else "🟡" if utilization_pct > 0.6 else "🔴"
                
                response = f"📊 {machine_name} ({machine_id}) 狀態報告\n"
                response += f"━━━━━━━━━━━━━━━━━━━━\n"
                response += f"🏭 部門：{department}\n"
                response += f"{status_icon} 稼動率：{utilization_pct:.1%}\n"
                response += f"⚡ 效率：{efficiency_pct:.1%}\n"
                response += f"✅ 良品：{good_parts:,} 件\n"
                response += f"❌ 不良品：{defective_parts:,} 件\n"
                response += f"📅 最後記錄：{last_date}\n"
                
                if fault_count > 0:
                    response += f"🔧 近7天故障：{fault_count} 次\n"
                
                # 建議
                if utilization_pct < 0.6:
                    response += f"\n⚠️ 建議：稼動率偏低，建議立即檢修"
                elif utilization_pct < 0.75:
                    response += f"\n💡 建議：建議安排預防保養"
                elif fault_count > 2:
                    response += f"\n🔧 建議：故障頻繁，需深度檢查"
                else:
                    response += f"\n✅ 狀態：運行正常"
                
                return TextMessage(text=response)
            else:
                return TextMessage(text=f"❌ 找不到機台 {machine_id}，請檢查機台編號")
                    
        except Exception as e:
            logger.error("Failed to get machine status async", error=str(e))
            return TextMessage(text=f"查詢機台 {machine_id} 狀態時發生錯誤")

    def _get_all_machines_status(self) -> Message:
        """獲取所有機台狀態總覽"""
        try:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                return TextMessage(text="正在查詢所有機台狀態...")
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            query = """
                SELECT 
                    m.machine_id,
                    m.machine_name,
                    m.department,
                    AVG(u.utilization_rate) as avg_utilization
                FROM machines m
                LEFT JOIN machine_utilization u ON m.machine_id = u.machine_id
                GROUP BY m.machine_id
                ORDER BY avg_utilization DESC
            """
            
            result = loop.run_until_complete(
                self._call_mcp_tool_compatible("sqlite", "read_query", {"query": query})
            )
            
            if result.get("success") and result.get("data"):
                response = "📊 所有機台狀態總覽\n"
                response += "━━━━━━━━━━━━━━━━━━━━\n"
                
                for row in result["data"]:
                    machine_id = row.get('machine_id', '未知')
                    machine_name = row.get('machine_name', '未知')
                    department = row.get('department', '未知')
                    utilization = row.get('avg_utilization', 0) or 0
                    
                    utilization_pct = utilization / 100 if utilization > 1 else utilization
                    status_icon = "🟢" if utilization_pct > 0.8 else "🟡" if utilization_pct > 0.6 else "🔴"
                    response += f"{status_icon} {machine_id} {machine_name} ({department}) - {utilization_pct:.1%}\n"
                
                loop.close()
                return TextMessage(text=response)
            else:
                loop.close()
                return TextMessage(text="❌ 無法獲取機台狀態資料")
                
        except Exception as e:
            logger.error("Failed to get all machines status", error=str(e))
            return TextMessage(text="查詢所有機台狀態時發生錯誤")

    async def _get_all_machines_status_async(self) -> Message:
        """非同步獲取所有機台狀態總覽"""
        try:
            query = """
                SELECT 
                    m.machine_id,
                    m.machine_name,
                    m.department,
                    AVG(u.utilization_rate) as avg_utilization
                FROM machines m
                LEFT JOIN machine_utilization u ON m.machine_id = u.machine_id
                GROUP BY m.machine_id
                ORDER BY avg_utilization DESC
            """
            
            result = await self._call_mcp_tool_compatible("sqlite", "read_query", {"query": query})
            
            if result.get("success") and result.get("data"):
                response = "📊 所有機台狀態總覽\n"
                response += "━━━━━━━━━━━━━━━━━━━━\n"
                
                for row in result["data"]:
                    machine_id = row.get('machine_id', '未知')
                    machine_name = row.get('machine_name', '未知')
                    department = row.get('department', '未知')
                    utilization = row.get('avg_utilization', 0) or 0
                    
                    utilization_pct = utilization / 100 if utilization > 1 else utilization
                    status_icon = "🟢" if utilization_pct > 0.8 else "🟡" if utilization_pct > 0.6 else "🔴"
                    response += f"{status_icon} {machine_id} {machine_name} ({department}) - {utilization_pct:.1%}\n"
                
                return TextMessage(text=response)
            else:
                return TextMessage(text="❌ 無法獲取機台狀態資料")
                
        except Exception as e:
            logger.error("Failed to get all machines status async", error=str(e))
            return TextMessage(text="查詢所有機台狀態時發生錯誤")

    async def _get_general_status_async(self) -> Message:
        """非同步獲取一般狀態"""
        try:
            # 簡化版本，返回基本狀態
            query = "SELECT COUNT(*) as total_machines FROM machines"
            result = await self._call_mcp_tool_compatible("sqlite", "read_query", {"query": query})
            
            if result.get("success") and result.get("data"):
                machine_count = result["data"][0].get('total_machines', 0)
                response = f"🏭 工廠概況\n"
                response += f"━━━━━━━━━━━━━━━━━━━━\n"
                response += f"📊 總機台數：{machine_count} 台\n"
                response += f"📱 您可以詢問：\n"
                response += f"• M001機台現在狀況如何？\n"
                response += f"• /status 查看所有機台\n"
                response += f"• 故障統計\n"
                return TextMessage(text=response)
            else:
                return TextMessage(text="無法獲取工廠狀況")
                
        except Exception as e:
            logger.error("Failed to get general status async", error=str(e))
            return TextMessage(text="查詢工廠狀況時發生錯誤")

    async def _get_low_performance_machines_async(self) -> Message:
        """非同步獲取低效能機台"""
        return TextMessage(text="低效能機台查詢功能開發中...")

    async def _get_fault_analysis_async(self) -> Message:
        """非同步獲取故障分析"""
        try:
            # 查詢總體故障統計
            stats_query = """
                SELECT 
                    COUNT(*) as total_faults,
                    COUNT(DISTINCT machine_id) as affected_machines,
                    SUM(downtime_minutes) as total_downtime,
                    SUM(repair_cost) as total_cost,
                    AVG(downtime_minutes) as avg_downtime
                FROM machine_faults 
                WHERE fault_date >= date('now', '-30 days')
            """
            
            # 按故障類型統計
            type_query = """
                SELECT 
                    fault_type,
                    COUNT(*) as count,
                    SUM(downtime_minutes) as downtime,
                    AVG(repair_cost) as avg_cost
                FROM machine_faults 
                WHERE fault_date >= date('now', '-30 days')
                GROUP BY fault_type
                ORDER BY count DESC
            """
            
            # 按嚴重性統計
            severity_query = """
                SELECT 
                    severity,
                    COUNT(*) as count,
                    SUM(downtime_minutes) as downtime
                FROM machine_faults 
                WHERE fault_date >= date('now', '-30 days')
                GROUP BY severity
                ORDER BY 
                    CASE severity 
                        WHEN 'CRITICAL' THEN 1 
                        WHEN 'HIGH' THEN 2 
                        WHEN 'MEDIUM' THEN 3 
                        WHEN 'LOW' THEN 4 
                    END
            """
            
            # 按機台統計
            machine_query = """
                SELECT 
                    m.machine_id,
                    m.machine_name,
                    COUNT(f.id) as fault_count,
                    SUM(f.downtime_minutes) as total_downtime
                FROM machines m
                LEFT JOIN machine_faults f ON m.machine_id = f.machine_id 
                    AND f.fault_date >= date('now', '-30 days')
                GROUP BY m.machine_id, m.machine_name
                HAVING fault_count > 0
                ORDER BY fault_count DESC
                LIMIT 5
            """
            
            # 執行所有查詢
            stats_result = await self._call_mcp_tool_compatible("sqlite", "read_query", {"query": stats_query})
            type_result = await self._call_mcp_tool_compatible("sqlite", "read_query", {"query": type_query})
            severity_result = await self._call_mcp_tool_compatible("sqlite", "read_query", {"query": severity_query})
            machine_result = await self._call_mcp_tool_compatible("sqlite", "read_query", {"query": machine_query})
            
            # 組合回應
            response = "📊 近30天故障統計報告\n"
            response += "━━━━━━━━━━━━━━━━━━━━\n\n"
            
            # 總體統計
            if stats_result.get("success") and stats_result.get("data"):
                stats = stats_result["data"][0]
                total_faults = stats.get('total_faults', 0)
                affected_machines = stats.get('affected_machines', 0)
                total_downtime = stats.get('total_downtime', 0) or 0
                total_cost = stats.get('total_cost', 0) or 0
                avg_downtime = stats.get('avg_downtime', 0) or 0
                
                response += f"📈 總體統計:\n"
                response += f"🔧 故障次數: {total_faults} 次\n"
                response += f"🏭 影響機台: {affected_machines} 台\n"
                response += f"⏱️ 總停機時間: {total_downtime:.0f} 分鐘\n"
                response += f"💰 維修成本: ${total_cost:,.0f}\n"
                response += f"📊 平均停機: {avg_downtime:.1f} 分鐘/次\n\n"
            
            # 故障類型統計
            if type_result.get("success") and type_result.get("data"):
                response += "🔍 故障類型分布:\n"
                type_icons = {
                    'ELECTRICAL': '⚡',
                    'MECHANICAL': '🔧', 
                    'SOFTWARE': '💻',
                    'MATERIAL': '📦'
                }
                for row in type_result["data"]:
                    fault_type = row.get('fault_type', '')
                    count = row.get('count', 0)
                    downtime = row.get('downtime', 0) or 0
                    icon = type_icons.get(fault_type, '🔸')
                    response += f"{icon} {fault_type}: {count}次 ({downtime:.0f}分鐘)\n"
                response += "\n"
            
            # 嚴重性統計
            if severity_result.get("success") and severity_result.get("data"):
                response += "⚠️ 故障嚴重性:\n"
                severity_icons = {
                    'CRITICAL': '🔴',
                    'HIGH': '🟠',
                    'MEDIUM': '🟡',
                    'LOW': '🟢'
                }
                for row in severity_result["data"]:
                    severity = row.get('severity', '')
                    count = row.get('count', 0)
                    downtime = row.get('downtime', 0) or 0
                    icon = severity_icons.get(severity, '🔸')
                    response += f"{icon} {severity}: {count}次 ({downtime:.0f}分鐘)\n"
                response += "\n"
            
            # 機台故障排行
            if machine_result.get("success") and machine_result.get("data"):
                response += "🏆 故障頻率排行 (前5名):\n"
                for i, row in enumerate(machine_result["data"][:5], 1):
                    machine_id = row.get('machine_id', '')
                    machine_name = row.get('machine_name', '未知')
                    fault_count = row.get('fault_count', 0)
                    total_downtime = row.get('total_downtime', 0) or 0
                    response += f"{i}. {machine_id} {machine_name}: {fault_count}次 ({total_downtime:.0f}分鐘)\n"
            
            response += "\n💡 建議: 關注高頻故障機台，安排預防性維護"
            
            return TextMessage(text=response)
            
        except Exception as e:
            logger.error("Failed to get fault analysis async", error=str(e))
            return TextMessage(text="獲取故障統計時發生錯誤，請稍後再試。")

    def _get_low_performance_machines(self) -> Message:
        """獲取低效能機台"""
        try:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                return TextMessage(text="正在查詢低效能機台...")
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            query = """
                SELECT 
                    m.machine_id,
                    m.machine_name,
                    m.department,
                    AVG(u.utilization_rate) as avg_utilization,
                    COUNT(f.id) as fault_count
                FROM machines m
                LEFT JOIN machine_utilization u ON m.machine_id = u.machine_id
                LEFT JOIN machine_faults f ON m.machine_id = f.machine_id AND f.fault_date >= date('now', '-7 days')
                GROUP BY m.machine_id
                HAVING avg_utilization < 75 OR fault_count > 2
                ORDER BY avg_utilization ASC
            """
            
            result = loop.run_until_complete(
                self._call_mcp_tool_compatible("sqlite", "read_query", {"query": query})
            )
            
            if result.get("success") and result.get("data"):
                query = """
                    SELECT 
                        m.machine_id,
                        m.machine_name,
                        m.department,
                        AVG(u.utilization_rate) as avg_utilization,
                        COUNT(f.id) as fault_count
                    FROM machines m
                    LEFT JOIN machine_utilization u ON m.machine_id = u.machine_id
                    LEFT JOIN machine_faults f ON m.machine_id = f.machine_id
                    GROUP BY m.machine_id
                    HAVING avg_utilization < 0.75 OR fault_count > 2
                    ORDER BY avg_utilization ASC
                """
                cursor = conn.execute(query)
                results = cursor.fetchall()
                
                if results:
                    response = "⚠️ 需要關注的機台\n"
                    response += "━━━━━━━━━━━━━━━━━━━━\n"
                    
                    for row in results:
                        machine_id = row[0]
                        machine_name = row[1]
                        department = row[2]
                        utilization = row[3] if row[3] else 0
                        fault_count = row[4] if row[4] else 0
                        
                        status_icon = "🔴" if utilization < 0.6 else "🟡"
                        response += f"{status_icon} {machine_id} {machine_name}\n"
                        response += f"   稼動率：{utilization:.1%} | 故障：{fault_count}次\n\n"
                    
                    return TextMessage(text=response)
                else:
                    return TextMessage(text="✅ 所有機台運行狀況良好！")
                    
        except Exception as e:
            logger.error("Failed to get low performance machines", error=str(e))
            return TextMessage(text="查詢低效能機台時發生錯誤")

    def _get_fault_analysis(self) -> Message:
        """❌ 已停用 - 違反 MCP 協定原則的舊方法"""
        logger.warning("⚠️ _get_fault_analysis 已停用 - 違反 MCP 協定")
        return TextMessage(text="請使用 MCP 協定的故障分析功能：_get_fault_analysis_async")

    def _get_general_status(self) -> Message:
        """❌ 已停用 - 違反 MCP 協定原則的舊方法"""
        logger.warning("⚠️ _get_general_status 已停用 - 違反 MCP 協定")
        return TextMessage(text="請使用 MCP 協定的狀況查詢功能：_get_general_status_async")