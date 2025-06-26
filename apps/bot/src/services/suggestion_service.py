#!/usr/bin/env python3
"""
建議生成服務 - 符合 SRP 原則的專門化服務

實現 SRP (單一職責原則)：
- 專門負責生成用戶查詢建議
- 不包含訊息處理、格式化等其他職責

實現 DIP (依賴倒置原則)：
- 依賴 IAIModelService 抽象介面
- 不直接依賴具體的 AI 服務實現

實現 OCP (開閉原則)：
- 支援不同的建議生成策略
- 可擴展新的建議生成方法
"""

import structlog
from linebot.v3.messaging import Message, TextMessage
from typing import Any, Dict, Optional

logger = structlog.get_logger()


class SuggestionService:
    """
    建議生成服務
    
    職責：
    - 分析用戶無法識別的查詢
    - 生成動態或靜態建議
    - 提供針對性的查詢範例
    
    設計原則：
    - SRP: 只負責建議生成，不處理訊息路由等
    - DIP: 依賴 AI 服務抽象介面
    - OCP: 支援擴展新的建議策略
    """
    
    def __init__(self, ai_model_service=None, message_formatter=None):
        """
        初始化建議生成服務
        
        Args:
            ai_model_service: AI 模型服務（可選）
            message_formatter: 訊息格式化器（回退用）
        """
        self._ai_service = ai_model_service
        self._formatter = message_formatter
        
        # 建議生成策略配置
        self._enable_ai_suggestions = bool(ai_model_service)
        self._fallback_to_smart_suggestions = True
        
        logger.info(
            "🔮 建議生成服務初始化完成",
            ai_enabled=self._enable_ai_suggestions,
            smart_fallback=self._fallback_to_smart_suggestions
        )
    
    async def generate_suggestion(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Message:
        """
        生成查詢建議
        
        Args:
            user_input: 用戶原始輸入
            context: 可選上下文資訊
            
        Returns:
            Message: 建議訊息
        """
        logger.debug("🔮 開始生成建議", user_input=user_input[:50])
        
        try:
            # 1. 優先嘗試 AI 動態建議
            if self._enable_ai_suggestions:
                ai_suggestion = await self._generate_ai_suggestion(user_input, context)
                if ai_suggestion:
                    return ai_suggestion
            
            # 2. 回退到智能靜態建議
            if self._fallback_to_smart_suggestions:
                return self._generate_smart_suggestion(user_input)
            
            # 3. 最終回退到基本靜態建議
            return self._generate_basic_suggestion()
            
        except Exception as e:
            logger.error(f"❌ 建議生成失敗：{e}")
            return self._generate_basic_suggestion()
    
    async def _generate_ai_suggestion(self, user_input: str, context: Optional[Dict[str, Any]]) -> Optional[Message]:
        """
        使用 AI 生成動態建議
        
        Args:
            user_input: 用戶輸入
            context: 上下文資訊
            
        Returns:
            Optional[Message]: AI 生成的建議，如果失敗則返回 None
        """
        if not self._ai_service:
            return None
            
        try:
            # 準備 AI 系統提示
            system_prompt = self._build_ai_system_prompt()
            
            # 準備用戶查詢分析提示
            user_prompt = self._build_user_analysis_prompt(user_input)
            
            # 調用 AI 服務
            logger.debug("🤖 調用 AI 服務生成建議")
            
            database_schema = context.get("database_schema", {}) if context else {}
            ai_response, confidence = await self._ai_service.enhance_natural_language_query(
                user_prompt, database_schema
            )
            
            if ai_response and isinstance(ai_response, str) and ai_response.strip():
                logger.info("✅ AI 建議生成成功", confidence=confidence)
                return TextMessage(text=ai_response.strip())
            else:
                logger.warning("⚠️ AI 建議生成返回空結果")
                return None
                
        except Exception as e:
            logger.warning(f"⚠️ AI 建議生成失敗：{e}")
            return None
    
    def _generate_smart_suggestion(self, user_input: str) -> Message:
        """
        生成智能靜態建議（基於關鍵詞分析）
        
        Args:
            user_input: 用戶輸入
            
        Returns:
            Message: 智能建議訊息
        """
        logger.debug("🧠 生成智能靜態建議")
        
        user_input_lower = user_input.lower()
        
        suggestion = "💡 我無法完全理解您的查詢，讓我為您提供一些建議：\n\n"
        
        # 根據關鍵詞提供針對性建議
        if any(keyword in user_input_lower for keyword in ["機台", "設備", "machine"]):
            suggestion += self._get_machine_query_suggestions()
            
        elif any(keyword in user_input_lower for keyword in ["故障", "問題", "錯誤", "維修"]):
            suggestion += self._get_fault_query_suggestions()
            
        elif any(keyword in user_input_lower for keyword in ["部門", "加工", "組裝", "品管"]):
            suggestion += self._get_department_query_suggestions()
            
        elif any(keyword in user_input_lower for keyword in ["統計", "報告", "生產", "效率"]):
            suggestion += self._get_statistics_query_suggestions()
            
        else:
            suggestion += self._get_general_query_suggestions()
        
        suggestion += "\n💡 您也可以使用 /help 查看完整使用說明"
        
        return TextMessage(text=suggestion)
    
    def _generate_basic_suggestion(self) -> Message:
        """
        生成基本靜態建議（最終回退）
        
        Returns:
            Message: 基本建議訊息
        """
        if self._formatter:
            return self._formatter.format_suggestion_message()
        
        # 如果連格式化器都沒有，返回最基本的建議
        message = "💡 抱歉，我無法理解您的查詢。\n\n"
        message += "🔍 請嘗試：\n"
        message += "• 查詢特定機台：「M001機台狀況」\n"
        message += "• 查看所有機台：「所有機台狀態」\n"
        message += "• 故障分析：「近期故障記錄」\n"
        message += "• 使用指令：/help 查看更多說明"
        
        return TextMessage(text=message)
    
    def _build_ai_system_prompt(self) -> str:
        """建構 AI 系統提示"""
        return """你是一個製造業生產線查詢助手。用戶剛才輸入了一個你無法理解的查詢。

請分析用戶的輸入，然後生成友善的建議，告訴用戶：
1. 可能的查詢意圖
2. 需要補充什麼具體資訊才能幫助查詢
3. 提供2-3個類似的查詢範例

回覆格式：
💡 我理解您想查詢 [推測的意圖]

🔍 為了提供準確的結果，請提供：
• [具體需要的資訊1]
• [具體需要的資訊2]

📝 您可以試試這樣問：
• [具體範例1]
• [具體範例2]
"""
    
    def _build_user_analysis_prompt(self, user_input: str) -> str:
        """建構用戶查詢分析提示"""
        return f"""用戶輸入："{user_input}"

請分析此查詢並提供建設性的建議。

可查詢的類型包括：
- 機台狀態查詢（如：M001機台狀況）
- 故障分析（如：近期故障記錄）
- 生產統計（如：生產效率報告）
- 部門狀況（如：加工部機台狀況）
- 所有機台概覽

請用繁體中文回覆，語氣要友善專業。"""
    
    def _get_machine_query_suggestions(self) -> str:
        """機台查詢建議"""
        return """🔍 如果您想查詢機台資訊，請提供：
• 具體機台編號（如：M001、M100）
• 或說明想查詢的機台類型

📝 您可以試試：
• 「M001機台狀況如何？」
• 「查看所有機台狀態」"""
    
    def _get_fault_query_suggestions(self) -> str:
        """故障查詢建議"""
        return """🔍 如果您想查詢故障資訊，請提供：
• 時間範圍（如：近期、最近一週）
• 特定機台或整體故障

📝 您可以試試：
• 「最近一週的故障記錄」
• 「M001機台故障歷史」"""
    
    def _get_department_query_suggestions(self) -> str:
        """部門查詢建議"""
        return """🔍 如果您想查詢部門資訊，請提供：
• 具體部門名稱
• 想了解的資訊類型

📝 您可以試試：
• 「加工部機台狀況」
• 「組裝部今日產量」"""
    
    def _get_statistics_query_suggestions(self) -> str:
        """統計查詢建議"""
        return """🔍 如果您想查詢統計報告，請提供：
• 報告類型（產量、效率、故障統計）
• 時間範圍

📝 您可以試試：
• 「本月生產統計報告」
• 「機台效率分析」"""
    
    def _get_general_query_suggestions(self) -> str:
        """通用查詢建議"""
        return """🔍 我可以幫您查詢：
• 機台運行狀態和效能
• 故障記錄和維修歷史
• 生產統計和效率分析
• 部門運營狀況

📝 試試這些查詢：
• 「所有機台目前狀況」
• 「近期故障統計」
• 「生產效率報告」"""
    
    def update_ai_service(self, ai_service) -> None:
        """
        更新 AI 服務（支援動態配置）
        
        Args:
            ai_service: 新的 AI 服務實例
        """
        self._ai_service = ai_service
        self._enable_ai_suggestions = bool(ai_service)
        
        logger.info(
            "🔄 AI 服務已更新", 
            ai_enabled=self._enable_ai_suggestions
        )
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        獲取服務資訊
        
        Returns:
            Dict[str, Any]: 服務狀態和配置
        """
        return {
            "name": "SuggestionService",
            "version": "1.0.0",
            "ai_enabled": self._enable_ai_suggestions,
            "smart_fallback": self._fallback_to_smart_suggestions,
            "capabilities": [
                "ai_dynamic_suggestions",
                "keyword_based_analysis", 
                "contextual_recommendations",
                "multilevel_fallback"
            ]
        }