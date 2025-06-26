"""
SQL 查詢指令處理器
處理 /sql 指令的直接 SQL 查詢
"""

import structlog
from linebot.v3.messaging import Message, TextMessage

from src.domain.command_handler import CommandContext, CommandHandler
from src.domain.exceptions import create_db_error
from src.services.error_handlers import ErrorContext
from src.services.mcp_response_parser import MCPResponseParser

logger = structlog.get_logger()


class SqlCommandHandler(CommandHandler):
    """SQL 查詢指令處理器"""

    def __init__(self, context: CommandContext):
        self.context = context

    @property
    def command_name(self) -> str:
        return "sql"

    @property
    def description(self) -> str:
        return "執行 SQL 查詢並返回結果"

    @property
    def aliases(self) -> list[str]:
        return ["query", "select"]

    def get_usage(self) -> str:
        return "/sql <SQL查詢語句>"

    def validate_args(self, args: list[str]) -> bool:
        """驗證 SQL 參數"""
        if not args:
            return False

        sql_query = " ".join(args).strip()
        if not sql_query:
            return False

        # 基本 SQL 安全檢查
        forbidden_keywords = ["drop", "delete", "update", "insert", "alter", "create"]
        query_lower = sql_query.lower()

        for keyword in forbidden_keywords:
            if keyword in query_lower:
                logger.warning(f"SQL查詢包含禁止的關鍵字: {keyword}")
                return False

        return True

    async def handle(self, user_id: str, args: list[str]) -> Message:
        """處理 SQL 查詢指令"""
        # 驗證參數
        if not self.validate_args(args):
            if not args:
                return TextMessage(
                    text="❌ 請提供SQL查詢語句\\n\\n"
                    f"📝 用法：{self.get_usage()}\\n"
                    "💡 例如：/sql SELECT * FROM machines LIMIT 5"
                )
            else:
                return TextMessage(
                    text="❌ SQL查詢包含不安全的關鍵字\\n\\n"
                    "🔒 只允許 SELECT 查詢以確保資料安全"
                )

        sql_query = " ".join(args).strip()

        # 🔥 緊急修復：檢查空查詢
        if not sql_query:
            logger.error("❌ 緊急阻止：SQL 指令查詢為空", user_id=user_id, args=args)
            return TextMessage(
                text="❌ SQL 查詢不能為空\\n\\n"
                f"📝 用法：{self.get_usage()}\\n"
                "💡 例如：/sql SELECT * FROM machines LIMIT 5"
            )

        try:
            with ErrorContext("sql_command") as ctx:
                ctx.add_context(
                    user_id=user_id,
                    query_preview=sql_query[:100],
                    query_length=len(sql_query),
                )

                logger.info("執行SQL查詢", query=sql_query[:100])

                # 使用 MCP 客戶端執行查詢
                mcp_client = await self.context.get_mcp_client()
                result = await mcp_client.call_tool(
                    "postgres", "query", {"sql": sql_query}
                )

                # 解析結果
                parser = MCPResponseParser()
                data = parser.parse_query_result(result)

                return self._format_sql_result(sql_query, data)

        except Exception as e:
            logger.error(f"SQL查詢執行失敗: {e}", exc_info=True)
            # 拋出領域異常，讓統一錯誤處理器處理
            raise create_db_error(sql_query, str(e), "SELECT") from e

    def _format_sql_result(self, query: str, data: list[dict]) -> TextMessage:
        """格式化 SQL 查詢結果"""
        if not data:
            return TextMessage(
                text=f"📊 SQL查詢完成\\n\\n"
                f"```sql\\n{query}\\n```\\n\\n"
                "🔍 查詢無結果"
            )

        # 構建結果文字
        response_lines = ["📊 SQL查詢結果：", f"```sql\\n{query}\\n```", ""]

        # 顯示前10行結果
        max_rows = min(len(data), 10)
        for i, row in enumerate(data[:max_rows]):
            row_text = f"第{i+1}行: " + ", ".join([f"{k}={v}" for k, v in row.items()])
            # 限制每行長度
            if len(row_text) > 200:
                row_text = row_text[:197] + "..."
            response_lines.append(row_text)

        # 如果有更多結果
        if len(data) > max_rows:
            response_lines.append(f"\\n... 還有 {len(data) - max_rows} 行結果")

        response_lines.append(f"\\n📈 總共 {len(data)} 行結果")

        return TextMessage(text="\\n".join(response_lines))
