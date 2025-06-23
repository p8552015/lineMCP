"""
系統資訊指令處理器
處理 /info 指令的系統資訊顯示
"""


import structlog
from linebot.v3.messaging import Message, TextMessage

from src.domain.command_handler import CommandContext, CommandHandler

logger = structlog.get_logger()


class InfoCommandHandler(CommandHandler):
    """系統資訊指令處理器"""

    def __init__(self, context: CommandContext):
        self.context = context

    @property
    def command_name(self) -> str:
        return "info"

    @property
    def description(self) -> str:
        return "顯示系統版本和配置資訊"

    @property
    def aliases(self) -> list[str]:
        return ["version", "about"]

    def get_usage(self) -> str:
        return "/info"

    async def handle(self, user_id: str, args: list[str]) -> Message:
        """處理系統資訊指令"""
        logger.info("顯示系統資訊", user_id=user_id)

        try:
            system_info = await self._collect_system_info()
            return self._format_system_info(system_info)

        except Exception as e:
            logger.error(f"獲取系統資訊失敗: {e}", exc_info=True)
            return TextMessage(
                text="❌ 獲取系統資訊時發生錯誤\\n\\n" "請稍後再試或聯絡系統管理員"
            )

    async def _collect_system_info(self) -> dict:
        """收集系統資訊"""
        import platform
        import sys
        from datetime import datetime

        info = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "system": {
                "platform": platform.system(),
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "architecture": platform.machine(),
            },
            "application": {
                "name": "LINE MCP 智慧製造監控系統",
                "version": "2.0.0",
                "environment": "Production" if self._is_production() else "Development",
            },
            "features": self._get_available_features(),
            "ai_models": await self._get_ai_models_info(),
            "dependencies": self._get_key_dependencies(),
        }

        return info

    def _is_production(self) -> bool:
        """檢查是否為生產環境"""
        import os

        return os.getenv("ENVIRONMENT", "development").lower() == "production"

    def _get_available_features(self) -> list[str]:
        """獲取可用功能列表"""
        features = [
            "🔍 自然語言查詢",
            "💾 SQL 直接查詢",
            "📊 資料表結構查詢",
            "🤖 多模型 AI 支援",
            "🔌 MCP 協議整合",
            "📱 LINE Bot 整合",
            "🔄 即時狀態監控",
            "🛡️ 統一錯誤處理",
            "📈 效能監控",
            "🔒 安全性驗證",
        ]

        return features

    async def _get_ai_models_info(self) -> dict:
        """獲取 AI 模型資訊"""
        try:
            ai_service = self.context.ai_model_service

            info = {"total_models": 0, "available_models": [], "current_model": "未知"}

            # 嘗試獲取模型資訊
            if hasattr(ai_service, "available_models"):
                models = getattr(ai_service, "available_models", [])
                info["total_models"] = len(models)
                info["available_models"] = [
                    model.get("name", "unknown") for model in models
                ]

            if hasattr(ai_service, "current_model"):
                current = getattr(ai_service, "current_model", None)
                if current:
                    info["current_model"] = current.get("name", "未知")

            return info

        except Exception as e:
            logger.warning(f"無法獲取 AI 模型資訊: {e}")
            return {
                "total_models": "未知",
                "available_models": [],
                "current_model": "未知",
            }

    def _get_key_dependencies(self) -> list[str]:
        """獲取關鍵依賴資訊"""
        dependencies = [
            "FastAPI - Web 框架",
            "LINE Messaging API - LINE Bot 整合",
            "OpenAI API - AI 語言模型",
            "MCP Protocol - 模型上下文協議",
            "SQLite - 資料庫引擎",
            "Structlog - 結構化日誌",
            "Pydantic - 資料驗證",
            "AsyncIO - 非同步處理",
        ]

        return dependencies

    def _format_system_info(self, info: dict) -> TextMessage:
        """格式化系統資訊"""
        response_lines = [
            "ℹ️ 系統資訊",
            "━━━━━━━━━━━━━━━━━━━━",
            f"🕐 查詢時間：{info['timestamp']}",
            "",
            "📱 應用程式資訊：",
            f"   • 名稱：{info['application']['name']}",
            f"   • 版本：{info['application']['version']}",
            f"   • 環境：{info['application']['environment']}",
            "",
            "💻 系統環境：",
            f"   • 作業系統：{info['system']['platform']}",
            f"   • Python 版本：{info['system']['python_version']}",
            f"   • 架構：{info['system']['architecture']}",
            "",
            "🤖 AI 模型：",
            f"   • 可用模型數：{info['ai_models']['total_models']}",
            f"   • 當前模型：{info['ai_models']['current_model']}",
        ]

        # 如果有可用模型列表
        if info["ai_models"]["available_models"]:
            response_lines.append("   • 支援模型：")
            for model in info["ai_models"]["available_models"][:3]:  # 最多顯示3個
                response_lines.append(f"     - {model}")

            if len(info["ai_models"]["available_models"]) > 3:
                remaining = len(info["ai_models"]["available_models"]) - 3
                response_lines.append(f"     ... 還有 {remaining} 個模型")

        # 添加功能列表
        response_lines.extend(
            [
                "",
                "🌟 支援功能：",
            ]
        )

        for feature in info["features"][:8]:  # 最多顯示8個功能
            response_lines.append(f"   • {feature}")

        if len(info["features"]) > 8:
            remaining = len(info["features"]) - 8
            response_lines.append(f"   • ... 還有 {remaining} 個功能")

        # 添加關鍵技術
        response_lines.extend(
            [
                "",
                "🔧 核心技術：",
            ]
        )

        for dep in info["dependencies"][:6]:  # 最多顯示6個依賴
            response_lines.append(f"   • {dep}")

        response_lines.extend(["", "📞 需要協助？使用 /help 查看所有指令"])

        return TextMessage(text="\\n".join(response_lines))
