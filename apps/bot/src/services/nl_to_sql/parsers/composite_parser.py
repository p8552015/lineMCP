"""
組合解析器 - 策略模式協調器

實現 SRP (單一職責原則)：
- 專門負責協調多個解析器策略
- 不包含具體解析邏輯，只負責策略選擇

實現 OCP (開閉原則)：
- 支援動態新增解析器策略
- 無需修改現有代碼即可擴展新策略

實現 LSP (里氏替換原則)：
- 完全實現 IParser 介面契約
- 可與其他單一解析器實現互換使用

實現 DIP (依賴倒置原則)：
- 依賴 IParser 抽象介面
- 不直接依賴具體的解析器實現
"""

from typing import Any

import structlog

from ..interfaces.parsing_interfaces import IParser
from ..models.query_models import ParsedQuery, QueryType

logger = structlog.get_logger()


class CompositeParser(IParser):
    """
    組合解析器 - 策略模式協調器

    職責：
    - 管理多個解析器策略
    - 根據信心度選擇最佳解析器
    - 提供解析結果的品質評估

    設計原則：
    - SRP: 只負責策略協調，不包含具體解析邏輯
    - OCP: 支援動態新增解析器，無需修改現有代碼
    - LSP: 完全實現 IParser 契約，可與其他解析器互換
    - DIP: 依賴 IParser 抽象介面，不依賴具體實現
    """

    def __init__(self):
        """
        初始化組合解析器
        """
        self._parsers: list[IParser] = []
        self._strategy_weights: dict[str, float] = {}
        self._fallback_confidence_threshold = 0.5

        logger.info("🎯 組合解析器初始化完成", parser_count=len(self._parsers))

    def add_parser(self, parser: IParser, weight: float = 1.0) -> None:
        """
        新增解析器策略

        Args:
            parser: 解析器實例
            weight: 策略權重 (0-2.0)，用於調整解析器優先級
        """
        if not isinstance(parser, IParser):
            raise ValueError("解析器必須實現 IParser 介面")

        if not 0.0 <= weight <= 2.0:
            raise ValueError("權重必須在 0.0-2.0 範圍內")

        self._parsers.append(parser)
        # 優先使用 parser 的 name 屬性，回退到類名
        parser_name = getattr(parser, 'name', parser.__class__.__name__)
        self._strategy_weights[parser_name] = weight

        logger.info(
            "📝 新增解析器策略",
            parser=parser_name,
            weight=weight,
            total_parsers=len(self._parsers),
        )

    def remove_parser(self, parser_class_name: str) -> bool:
        """
        移除解析器策略

        Args:
            parser_class_name: 解析器類別名稱

        Returns:
            bool: 是否成功移除
        """
        for i, parser in enumerate(self._parsers):
            parser_name = getattr(parser, 'name', parser.__class__.__name__)
            if parser_name == parser_class_name:
                self._parsers.pop(i)
                self._strategy_weights.pop(parser_class_name, None)

                logger.info(
                    "🗑️ 移除解析器策略",
                    parser=parser_class_name,
                    remaining_parsers=len(self._parsers),
                )
                return True

        logger.warning("⚠️ 未找到要移除的解析器", parser=parser_class_name)
        return False

    async def parse(
        self, text: str, context: dict[str, Any] | None = None
    ) -> ParsedQuery:
        """
        使用策略模式解析自然語言文字 - 支援回退機制

        Args:
            text: 使用者輸入的自然語言文字
            context: 可選的解析上下文

        Returns:
            ParsedQuery: 最佳解析結果
        """
        if not text or not text.strip():
            return self._create_empty_query("空輸入")

        if not self._parsers:
            return self._create_empty_query("無可用解析器")

        logger.debug("🎯 開始組合解析（支援回退）", text=text, parser_count=len(self._parsers))

        # 評估所有解析器的處理能力
        parser_capabilities = await self._evaluate_parser_capabilities(text)
        
        # 🔥 新增：按信心度排序，準備回退策略
        sorted_capabilities = sorted(parser_capabilities, key=lambda x: x[1], reverse=True)

        # 依序嘗試每個解析器，直到找到成功的結果
        for parser, confidence in sorted_capabilities:
            if confidence < self._fallback_confidence_threshold:
                logger.info(
                    "⚠️ 跳過信心度低於門檻的解析器",
                    parser=getattr(parser, 'name', parser.__class__.__name__),
                    confidence=confidence,
                    threshold=self._fallback_confidence_threshold
                )
                continue

            try:
                parser_name = getattr(parser, 'name', parser.__class__.__name__)
                logger.debug(f"🔄 嘗試解析器：{parser_name}，信心度：{confidence}")
                
                # 執行解析
                result = await parser.parse(text, context)

                # 🔥 關鍵：檢查解析結果是否有效
                if self._is_valid_result(result):
                    # 調整信心度（考慮權重）
                    weight = self._strategy_weights.get(parser_name, 1.0)
                    adjusted_confidence = min(1.0, result.confidence * weight)

                    # 更新結果信心度
                    enhanced_result = ParsedQuery(
                        query_type=result.query_type,
                        sql_query=result.sql_query,
                        parameters=result.parameters,
                        confidence=adjusted_confidence,
                        explanation=f"[{parser_name}] {result.explanation}",
                    )

                    logger.info(
                        "✅ 組合解析成功",
                        selected_parser=parser_name,
                        original_confidence=result.confidence,
                        adjusted_confidence=adjusted_confidence,
                        query_type=result.query_type.value,
                    )

                    return enhanced_result
                else:
                    # 結果無效，嘗試下一個解析器
                    logger.warning(
                        "⚠️ 解析器返回無效結果，嘗試下一個",
                        parser=parser_name,
                        query_type=result.query_type.value,
                        confidence=result.confidence
                    )
                    continue

            except Exception as e:
                parser_name = getattr(parser, 'name', parser.__class__.__name__)
                logger.warning(
                    "⚠️ 解析器執行異常，嘗試下一個", 
                    parser=parser_name, 
                    error=str(e)
                )
                continue

        # 🔥 所有解析器都失敗時的處理
        logger.error(
            "❌ 所有解析器都無法成功解析", 
            text=text,
            attempted_parsers=[getattr(p[0], 'name', p[0].__class__.__name__) 
                              for p in sorted_capabilities]
        )
        
        return self._create_fallback_query(text, sorted_capabilities)

        except Exception as e:
            parser_name = getattr(best_parser, 'name', best_parser.__class__.__name__)
            logger.error(
                "❌ 解析執行失敗", parser=parser_name, error=str(e)
            )
            return self._create_error_query(text, str(e))

    def can_handle(self, text: str) -> float:
        """
        評估組合解析器的處理能力

        Args:
            text: 要評估的文字

        Returns:
            float: 綜合處理能力信心度 (0-1)
        """
        if not text or not text.strip():
            return 0.0

        if not self._parsers:
            return 0.0

        # 計算所有解析器的綜合信心度
        total_confidence = 0.0
        total_weight = 0.0

        for parser in self._parsers:
            try:
                parser_confidence = parser.can_handle(text)
                parser_name = getattr(parser, 'name', parser.__class__.__name__)
                parser_weight = self._strategy_weights.get(parser_name, 1.0)

                total_confidence += parser_confidence * parser_weight
                total_weight += parser_weight

            except Exception as e:
                parser_name = getattr(parser, 'name', parser.__class__.__name__)
                logger.warning(
                    "⚠️ 解析器能力評估失敗",
                    parser=parser_name,
                    error=str(e),
                )

        # 計算加權平均
        if total_weight > 0:
            weighted_average = total_confidence / total_weight
            return min(1.0, weighted_average)

        return 0.0

    def get_parser_info(self) -> dict[str, Any]:
        """
        獲取組合解析器資訊

        Returns:
            Dict[str, Any]: 解析器資訊
        """
        parser_info_list = []

        for parser in self._parsers:
            try:
                info = parser.get_parser_info()
                parser_name = getattr(parser, 'name', parser.__class__.__name__)
                info["weight"] = self._strategy_weights.get(parser_name, 1.0)
                parser_info_list.append(info)
            except Exception as e:
                parser_name = getattr(parser, 'name', parser.__class__.__name__)
                logger.warning(
                    "⚠️ 獲取解析器資訊失敗",
                    parser=parser_name,
                    error=str(e),
                )

        return {
            "name": "CompositeParser",
            "version": "1.0.0",
            "type": "composite_strategy",
            "capabilities": [
                "multi_strategy_coordination",
                "dynamic_parser_selection",
                "confidence_based_routing",
                "fallback_strategy_support",
            ],
            "parser_count": len(self._parsers),
            "registered_parsers": parser_info_list,
            "fallback_threshold": self._fallback_confidence_threshold,
            "strategy_selection": "highest_confidence",
        }

    def set_fallback_threshold(self, threshold: float) -> None:
        """
        設定回退信心度門檻

        Args:
            threshold: 信心度門檻 (0-1)
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("門檻值必須在 0.0-1.0 範圍內")

        self._fallback_confidence_threshold = threshold
        logger.info("🔧 更新回退門檻", threshold=threshold)

    def get_parser_statistics(self) -> dict[str, Any]:
        """
        獲取解析器統計資訊

        Returns:
            Dict[str, Any]: 統計資訊
        """
        stats = {
            "total_parsers": len(self._parsers),
            "parser_weights": self._strategy_weights.copy(),
            "fallback_threshold": self._fallback_confidence_threshold,
            "parser_details": [],
        }

        for parser in self._parsers:
            parser_name = getattr(parser, 'name', parser.__class__.__name__)
            try:
                parser_info = parser.get_parser_info()
                stats["parser_details"].append(
                    {
                        "name": parser_name,
                        "type": parser_info.get("type", "unknown"),
                        "weight": self._strategy_weights.get(parser_name, 1.0),
                        "capabilities": parser_info.get("capabilities", []),
                    }
                )
            except Exception as e:
                logger.warning("⚠️ 解析器統計獲取失敗", parser=parser_name, error=str(e))

        return stats

    async def _evaluate_parser_capabilities(
        self, text: str
    ) -> list[tuple[IParser, float]]:
        """
        評估所有解析器的處理能力

        Args:
            text: 待解析文字

        Returns:
            List[Tuple[IParser, float]]: 解析器和其信心度列表
        """
        capabilities = []

        for parser in self._parsers:
            try:
                confidence = parser.can_handle(text)
                capabilities.append((parser, confidence))

                parser_name = getattr(parser, 'name', parser.__class__.__name__)
                logger.debug(
                    "📊 解析器能力評估",
                    parser=parser_name,
                    confidence=confidence,
                )

            except Exception as e:
                parser_name = getattr(parser, 'name', parser.__class__.__name__)
                logger.warning(
                    "⚠️ 解析器能力評估異常",
                    parser=parser_name,
                    error=str(e),
                )
                capabilities.append((parser, 0.0))

        # 根據信心度排序
        capabilities.sort(key=lambda x: x[1], reverse=True)
        return capabilities

    def _select_best_parser(
        self, capabilities: list[tuple[IParser, float]]
    ) -> tuple[IParser | None, float]:
        """
        選擇最佳解析器

        Args:
            capabilities: 解析器能力評估結果

        Returns:
            Tuple[Optional[IParser], float]: 最佳解析器和其信心度
        """
        if not capabilities:
            return None, 0.0

        # 選擇信心度最高的解析器
        best_parser, best_confidence = capabilities[0]

        # 檢查是否達到回退門檻
        if best_confidence < self._fallback_confidence_threshold:
            logger.warning(
                "⚠️ 最佳解析器信心度低於門檻",
                best_confidence=best_confidence,
                threshold=self._fallback_confidence_threshold,
            )

        logger.debug(
            "🏆 選擇最佳解析器",
            parser=best_parser.__class__.__name__,
            confidence=best_confidence,
        )

        return best_parser, best_confidence

    def _create_empty_query(self, reason: str) -> ParsedQuery:
        """
        創建空查詢結果

        Args:
            reason: 原因描述

        Returns:
            ParsedQuery: 空查詢結果
        """
        return ParsedQuery(
            query_type=QueryType.UNKNOWN,
            sql_query="",
            parameters={},
            confidence=0.0,
            explanation=f"組合解析器無法處理：{reason}",
        )

    def _create_error_query(self, text: str, error: str) -> ParsedQuery:
        """
        創建錯誤查詢結果

        Args:
            text: 原始輸入文字
            error: 錯誤訊息

        Returns:
            ParsedQuery: 錯誤查詢結果
        """
        return ParsedQuery(
            query_type=QueryType.UNKNOWN,
            sql_query="",
            parameters={"error": error},
            confidence=0.0,
            explanation=f"組合解析器錯誤 ({error}): {text}",
        )

    def _is_valid_result(self, result: ParsedQuery) -> bool:
        """
        檢查解析結果是否有效
        
        Args:
            result: 解析結果
            
        Returns:
            bool: 是否為有效結果
        """
        # 基本有效性檢查
        if not result:
            return False
            
        # 檢查查詢類型
        if result.query_type == QueryType.UNKNOWN:
            return False
            
        # 檢查信心度
        if result.confidence <= 0.0:
            return False
            
        # 檢查是否有錯誤參數
        if result.parameters and "error" in result.parameters:
            return False
            
        return True

    def _create_fallback_query(self, text: str, attempted_parsers: list) -> ParsedQuery:
        """
        創建回退查詢結果（所有解析器都失敗時）
        
        Args:
            text: 原始查詢文字
            attempted_parsers: 嘗試過的解析器列表
            
        Returns:
            ParsedQuery: 回退查詢結果
        """
        parser_names = [getattr(p[0], 'name', p[0].__class__.__name__) 
                       for p in attempted_parsers]
        
        return ParsedQuery(
            query_type=QueryType.UNKNOWN,
            sql_query="",
            parameters={
                "original_text": text,
                "attempted_parsers": parser_names,
                "fallback_reason": "所有解析器都無法成功處理此查詢"
            },
            confidence=0.0,
            explanation=f"組合解析器完全失敗，已嘗試解析器：{', '.join(parser_names)}",
        )

    def validate_configuration(self) -> dict[str, Any]:
        """
        驗證組合解析器配置

        Returns:
            Dict[str, Any]: 驗證結果
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "parser_validation": [],
        }

        # 檢查是否有註冊的解析器
        if not self._parsers:
            validation_result["errors"].append("沒有註冊任何解析器")
            validation_result["is_valid"] = False

        # 驗證每個解析器
        for parser in self._parsers:
            parser_name = getattr(parser, 'name', parser.__class__.__name__)
            parser_validation = {"name": parser_name, "is_valid": True, "errors": []}

            # 檢查解析器是否實現正確的介面
            if not hasattr(parser, "parse") or not hasattr(parser, "can_handle"):
                parser_validation["errors"].append("解析器未正確實現 IParser 介面")
                parser_validation["is_valid"] = False
                validation_result["is_valid"] = False

            # 檢查權重設定
            weight = self._strategy_weights.get(parser_name)
            if weight is None:
                validation_result["warnings"].append(f"解析器 {parser_name} 未設定權重")
            elif not 0.0 <= weight <= 2.0:
                parser_validation["errors"].append(f"無效的權重值: {weight}")
                parser_validation["is_valid"] = False
                validation_result["is_valid"] = False

            validation_result["parser_validation"].append(parser_validation)

        return validation_result
