"""
資料表查詢指令處理器
處理 /tables 指令的資料表列表查詢
"""


import structlog
from linebot.v3.messaging import Message, TextMessage

from src.domain.command_handler import CommandContext, CommandHandler
from src.domain.exceptions import create_db_error
from src.services.error_handlers import ErrorContext
from src.services.mcp_response_parser import MCPResponseParser

logger = structlog.get_logger()


class TablesCommandHandler(CommandHandler):
    """資料表查詢指令處理器"""

    def __init__(self, context: CommandContext):
        self.context = context

    @property
    def command_name(self) -> str:
        return "tables"

    @property
    def description(self) -> str:
        return "列出資料庫中的所有資料表"

    @property
    def aliases(self) -> list[str]:
        return ["table", "list"]

    def get_usage(self) -> str:
        return "/tables [資料表名稱]"

    async def handle(self, user_id: str, args: list[str]) -> Message:
        """處理資料表查詢指令"""
        try:
            with ErrorContext("tables_command") as ctx:
                ctx.add_context(user_id=user_id, args=args)

                if args:
                    # 查詢特定資料表的結構
                    table_name = args[0]
                    return await self._get_table_schema(table_name)
                else:
                    # 列出所有資料表
                    return await self._list_all_tables()

        except Exception as e:
            logger.error(f"資料表查詢失敗: {e}", exc_info=True)
            raise create_db_error("SHOW TABLES", str(e), "SCHEMA")

    async def _list_all_tables(self) -> TextMessage:
        """列出所有資料表"""
        logger.info("查詢所有資料表")

        # 使用 MCP 客戶端查詢資料表
        mcp_client = await self.context.get_mcp_client()

        # SQLite 查詢所有資料表
        query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        result = await mcp_client.call_tool("sqlite", "read_query", {"query": query})

        parser = MCPResponseParser()
        tables = parser.parse_query_result(result)

        if not tables:
            return TextMessage(
                text="📋 資料庫查詢結果\\n\\n" "🔍 目前資料庫中沒有資料表"
            )

        # 格式化資料表列表
        response_lines = ["📋 資料庫資料表列表：", "━━━━━━━━━━━━━━━━━━━━", ""]

        for i, table in enumerate(tables, 1):
            table_name = table.get("name", "unknown")
            response_lines.append(f"{i:2d}. {table_name}")

        response_lines.extend(
            [
                "",
                f"📊 總共 {len(tables)} 個資料表",
                "",
                "💡 查看資料表結構：/tables <資料表名稱>",
            ]
        )

        return TextMessage(text="\\n".join(response_lines))

    async def _get_table_schema(self, table_name: str) -> TextMessage:
        """獲取特定資料表的結構"""
        logger.info(f"查詢資料表結構: {table_name}")

        mcp_client = await self.context.get_mcp_client()

        # 查詢資料表結構
        schema_query = f"PRAGMA table_info({table_name})"
        schema_result = await mcp_client.call_tool(
            "sqlite", "read_query", {"query": schema_query}
        )

        parser = MCPResponseParser()
        schema_data = parser.parse_query_result(schema_result)

        if not schema_data:
            return TextMessage(
                text=f"❌ 找不到資料表：{table_name}\\n\\n"
                "💡 使用 /tables 查看所有可用的資料表"
            )

        # 查詢資料表行數
        count_query = f"SELECT COUNT(*) as count FROM {table_name}"
        try:
            count_result = await mcp_client.call_tool(
                "sqlite", "read_query", {"query": count_query}
            )
            count_data = parser.parse_query_result(count_result)
            row_count = count_data[0]["count"] if count_data else 0
        except Exception:
            row_count = "未知"

        # 格式化資料表結構
        response_lines = [
            f"📋 資料表：{table_name}",
            "━━━━━━━━━━━━━━━━━━━━",
            f"📊 資料行數：{row_count}",
            "",
            "🏗️ 欄位結構：",
        ]

        for field in schema_data:
            name = field.get("name", "unknown")
            data_type = field.get("type", "unknown")
            not_null = "NOT NULL" if field.get("notnull") else ""
            primary_key = "PRIMARY KEY" if field.get("pk") else ""
            default_value = (
                f"DEFAULT {field.get('dflt_value')}" if field.get("dflt_value") else ""
            )

            field_info = [data_type, not_null, primary_key, default_value]
            field_desc = " ".join([info for info in field_info if info])

            response_lines.append(f"   • {name}: {field_desc}")

        response_lines.extend(
            ["", f"💡 查看資料：/sql SELECT * FROM {table_name} LIMIT 5"]
        )

        return TextMessage(text="\\n".join(response_lines))
