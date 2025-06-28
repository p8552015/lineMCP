"""
AI 模型查詢指令處理器
處理 /models 指令的 AI 模型資訊查詢
"""

import structlog
from linebot.v3.messaging import Message, TextMessage

from src.domain.command_handler import CommandContext, CommandHandler

logger = structlog.get_logger()


class ModelsCommandHandler(CommandHandler):
    """AI 模型查詢指令處理器"""

    def __init__(self, context: CommandContext):
        self.context = context

    @property
    def command_name(self) -> str:
        return "models"

    @property
    def description(self) -> str:
        return "列出所有可用的 AI 模型及其狀態"

    @property
    def aliases(self) -> list[str]:
        return ["model", "ai"]

    def get_usage(self) -> str:
        return "/models [模型名稱]"

    async def handle(self, user_id: str, args: list[str]) -> Message:
        """處理 AI 模型查詢指令"""
        logger.info("查詢 AI 模型資訊", user_id=user_id, args=args)

        try:
            if args:
                # 查詢特定模型的詳細資訊
                model_name = args[0]
                return await self._get_model_details(model_name)
            else:
                # 列出所有可用模型
                return await self._list_all_models()

        except Exception as e:
            logger.error(f"查詢 AI 模型失敗: {e}", exc_info=True)
            return TextMessage(text="❌ 查詢 AI 模型資訊時發生錯誤\\n\\n" "請稍後再試或聯絡系統管理員")

    async def _list_all_models(self) -> TextMessage:
        """列出所有可用的 AI 模型"""
        logger.info("列出所有 AI 模型")

        try:
            ai_service = self.context.ai_model_service
            models_info = await self._get_models_from_service(ai_service)

            if not models_info["models"]:
                return TextMessage(
                    text="🤖 AI 模型資訊\\n\\n" "⚠️ 目前沒有可用的 AI 模型\\n" "請檢查系統配置或聯絡管理員"
                )

            return self._format_models_list(models_info)

        except Exception as e:
            logger.error(f"獲取模型列表失敗: {e}")
            return TextMessage(text="❌ 無法獲取 AI 模型列表\\n\\n" f"錯誤：{str(e)[:100]}")

    async def _get_model_details(self, model_name: str) -> TextMessage:
        """獲取特定模型的詳細資訊"""
        logger.info(f"查詢模型詳細資訊: {model_name}")

        try:
            ai_service = self.context.ai_model_service
            models_info = await self._get_models_from_service(ai_service)

            # 尋找指定的模型
            target_model = None
            for model in models_info["models"]:
                if (
                    model.get("name", "").lower() == model_name.lower()
                    or model.get("id", "").lower() == model_name.lower()
                ):
                    target_model = model
                    break

            if not target_model:
                available_models = [
                    m.get("name", "unknown") for m in models_info["models"]
                ]
                return TextMessage(
                    text=f"❌ 找不到模型：{model_name}\\n\\n"
                    f"可用模型：{', '.join(available_models[:5])}\\n"
                    "💡 使用 /models 查看所有模型"
                )

            return self._format_model_details(
                target_model, models_info["current_model"]
            )

        except Exception as e:
            logger.error(f"獲取模型詳細資訊失敗: {e}")
            return TextMessage(
                text=f"❌ 無法獲取模型 {model_name} 的詳細資訊\\n\\n" f"錯誤：{str(e)[:100]}"
            )

    async def _get_models_from_service(self, ai_service) -> dict:
        """從 AI 服務獲取模型資訊"""
        models_info = {"models": [], "current_model": None, "total_count": 0}

        # 嘗試不同的方法獲取模型資訊
        try:
            # 方法1：直接獲取 available_models 屬性
            if hasattr(ai_service, "available_models"):
                models = getattr(ai_service, "available_models", [])
                models_info["models"] = models
                models_info["total_count"] = len(models)

            # 方法2：嘗試調用 list_models 方法
            elif hasattr(ai_service, "list_models"):
                models = await ai_service.list_models()
                models_info["models"] = models
                models_info["total_count"] = len(models)

            # 方法3：嘗試獲取當前模型
            if hasattr(ai_service, "current_model"):
                current = getattr(ai_service, "current_model", None)
                models_info["current_model"] = current
            elif hasattr(ai_service, "get_current_model"):
                current = await ai_service.get_current_model()
                models_info["current_model"] = current

        except Exception as e:
            logger.warning(f"部分模型資訊獲取失敗: {e}")

        return models_info

    def _format_models_list(self, models_info: dict) -> TextMessage:
        """格式化模型列表"""
        current_model_name = None
        if models_info["current_model"]:
            current_model_name = models_info["current_model"].get("name", "unknown")

        response_lines = [
            "🤖 AI 模型列表",
            "━━━━━━━━━━━━━━━━━━━━",
            f"📊 總計：{models_info['total_count']} 個模型",
        ]

        if current_model_name:
            response_lines.append(f"⭐ 當前模型：{current_model_name}")

        response_lines.append("")

        # 按提供商分組顯示
        providers = {}
        for model in models_info["models"]:
            provider = model.get("provider", "unknown")
            if provider not in providers:
                providers[provider] = []
            providers[provider].append(model)

        for provider, models in providers.items():
            response_lines.append(f"🏢 {provider}：")

            for model in models[:5]:  # 每個提供商最多顯示5個模型
                model_name = model.get("name", "unknown")
                model_id = model.get("id", "")
                status = "🟢" if model.get("available", True) else "🔴"

                is_current = current_model_name and model_name == current_model_name
                current_marker = " ⭐" if is_current else ""

                if model_id and model_id != model_name:
                    model_display = f"{model_name} ({model_id})"
                else:
                    model_display = model_name

                response_lines.append(f"   {status} {model_display}{current_marker}")

            if len(models) > 5:
                response_lines.append(f"   ... 還有 {len(models) - 5} 個模型")

            response_lines.append("")

        response_lines.extend(["💡 查看模型詳情：/models <模型名稱>", "🔍 檢查模型狀態：/status"])

        return TextMessage(text="\\n".join(response_lines))

    def _format_model_details(self, model: dict, current_model: dict) -> TextMessage:
        """格式化模型詳細資訊"""
        model_name = model.get("name", "unknown")
        model_id = model.get("id", "")
        provider = model.get("provider", "unknown")
        available = model.get("available", True)

        is_current = current_model and current_model.get("name") == model_name

        response_lines = [
            f"🤖 模型詳細資訊：{model_name}",
            "━━━━━━━━━━━━━━━━━━━━",
            "",
            f"🏢 提供商：{provider}",
            f"🆔 模型 ID：{model_id or '未提供'}",
            f"📊 狀態：{'🟢 可用' if available else '🔴 不可用'}",
            f"⭐ 當前使用：{'是' if is_current else '否'}",
        ]

        # 添加模型特定資訊
        if "description" in model:
            response_lines.extend(["", f"📝 描述：{model['description']}"])

        if "capabilities" in model:
            caps = model["capabilities"]
            if isinstance(caps, list):
                response_lines.extend(["", "🎯 功能："])
                for cap in caps[:5]:  # 最多顯示5個功能
                    response_lines.append(f"   • {cap}")

        if "context_window" in model:
            response_lines.append(f"📏 上下文窗口：{model['context_window']:,} tokens")

        if "max_tokens" in model:
            response_lines.append(f"📤 最大輸出：{model['max_tokens']:,} tokens")

        if "cost" in model:
            cost_info = model["cost"]
            if isinstance(cost_info, dict):
                response_lines.extend(["", "💰 費用資訊："])
                for cost_type, amount in cost_info.items():
                    response_lines.append(f"   • {cost_type}: ${amount}")

        response_lines.extend(["", "💡 使用此模型進行自然語言查詢", "🔄 切換模型請聯絡系統管理員"])

        return TextMessage(text="\\n".join(response_lines))
