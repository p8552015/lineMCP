#!/usr/bin/env python3
"""
PostgreSQL 查詢命令處理器
整合到 LINE Bot 指令系統中
"""

import structlog
from linebot.v3.messaging import Message, TextMessage

from src.domain.command_handler import CommandContext, CommandHandler
from src.commands.postgres_command import PostgreSQLCommand

logger = structlog.get_logger()


class PostgresCommandHandler(CommandHandler):
    """PostgreSQL 查詢命令處理器"""

    def __init__(self, context: CommandContext):
        """初始化 PostgreSQL 命令處理器"""
        self.context = context
        
        # 處理初始化階段 service_factory 為 None 的情況
        if context.service_factory is None:
            # 延遲初始化，在第一次使用時再創建
            self.postgres_command = None
            logger.info("🐘 PostgreSQL 命令處理器已初始化（延遲創建）")
        else:
            self.postgres_command = PostgreSQLCommand(context.service_factory)
            logger.info("🐘 PostgreSQL 命令處理器已初始化")

    @property
    def command_name(self) -> str:
        """命令名稱"""
        return "pg"

    @property
    def description(self) -> str:
        """命令描述"""
        return "PostgreSQL 數據庫查詢"
        
    @property
    def command_description(self) -> str:
        """命令描述（向下兼容）"""
        return self.description

    @property
    def command_usage(self) -> str:
        """命令使用方法"""
        return """
🐘 PostgreSQL 查詢命令

使用方法:
• /pg <查詢內容>
• /pg help - 顯示詳細幫助
• /pg 員工數 - 執行預定義查詢
• /pg 有多少員工在工程部 - 自然語言查詢

預定義查詢關鍵字:
• 員工數、部門統計、機台狀態、產品庫存
• 高薪員工、缺貨產品、運行機台、待處理訂單
"""

    async def handle(self, user_id: str, args: list[str]) -> Message:
        """
        處理 PostgreSQL 查詢命令
        
        Args:
            args: 命令參數
            user_id: 用戶 ID
            
        Returns:
            處理結果訊息
        """
        try:
            # 延遲初始化 PostgreSQL 命令
            if self.postgres_command is None:
                if self.context.service_factory is None:
                    # 如果仍然沒有 service_factory，返回錯誤
                    return TextMessage(text="❌ PostgreSQL 服務暫時不可用，請稍後再試")
                
                self.postgres_command = PostgreSQLCommand(self.context.service_factory)
                logger.info("🐘 PostgreSQL 命令延遲初始化完成")
            if not args:
                return TextMessage(text=self.command_usage)
            
            # 處理幫助命令
            if args[0].lower() in ["help", "幫助", "?", "？"]:
                # 對於幫助命令，如果 postgres_command 不可用，返回基本使用說明
                if self.postgres_command is None:
                    return TextMessage(text=self.command_usage)
                
                help_text = self.postgres_command.get_help_text()
                return TextMessage(text=help_text)
            
            # 合併所有參數為查詢字符串
            query = " ".join(args)
            
            logger.info("🔍 處理 PostgreSQL 查詢命令", query=query, user_id=user_id)
            
            # 執行 PostgreSQL 查詢
            result = await self.postgres_command.execute(query, user_id)
            
            if result.get("success"):
                response_text = result.get("display_text", "查詢執行成功")
                
                # 添加查詢信息
                if result.get("sql_query"):
                    response_text += f"\n\n🔍 執行的 SQL:\n{result['sql_query']}"
                
                return TextMessage(text=response_text)
            else:
                error_text = f"❌ 查詢失敗: {result.get('error', '未知錯誤')}"
                
                # 添加建議
                suggestions = result.get("suggestions", [])
                if suggestions:
                    error_text += "\n\n💡 建議:\n" + "\n".join(suggestions)
                
                return TextMessage(text=error_text)
                
        except Exception as e:
            logger.error("❌ PostgreSQL 命令處理失敗", error=str(e), exc_info=True)
            error_text = f"❌ 命令處理失敗: {str(e)}\n\n使用 '/pg help' 查看使用說明"
            return TextMessage(text=error_text)

    def get_supported_commands(self) -> list[str]:
        """獲取支援的命令列表"""
        return [
            "pg",
            "postgres", 
            "postgresql",
            "數據庫",
            "查詢"
        ]