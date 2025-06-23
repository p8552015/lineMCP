"""
自然語言轉 SQL 服務 - 向後兼容包裝器

這是一個向後兼容的包裝器，維持舊有的 NaturalLanguageToSQLService 介面，
但內部使用新的 SOLID 重構架構組件。

SOLID 重構完成後，此檔案作為適配器模式實現，
確保現有代碼無需修改即可使用新架構。
"""

from typing import Any, Dict, Optional
import structlog

from .ai_model_service import AIModelService
from .nl_to_sql.models.query_models import ParsedQuery, QueryType
from .nl_to_sql.interfaces.parsing_interfaces import IParser
from .nl_to_sql.interfaces.query_builder_interfaces import IQueryBuilder
from .nl_to_sql.interfaces.statistics_interfaces import IStatistics, IConfiguration

logger = structlog.get_logger()


class NaturalLanguageToSQLService:
    """
    自然語言轉 SQL 服務 (向後兼容包裝器)
    
    這個類別維持舊有的 API 介面，但內部委託給新的 SOLID 重構組件。
    實現適配器模式，確保向後兼容性。
    
    注意：此為過渡期間的兼容性實現，
    建議新代碼直接使用 SOLID 組件介面。
    """
    
    def __init__(self, ai_model_service: AIModelService):
        """
        初始化自然語言轉 SQL 服務
        
        Args:
            ai_model_service: AI 模型服務實例
            
        注意：新的 SOLID 組件會通過依賴注入框架自動注入
        """
        self.ai_model_service = ai_model_service
        
        # SOLID 組件將會通過服務定位器模式延遲注入
        self._parser: Optional[IParser] = None
        self._query_builder: Optional[IQueryBuilder] = None
        self._statistics: Optional[IStatistics] = None
        self._configuration: Optional[IConfiguration] = None
        
        logger.info("🔄 自然語言轉 SQL 服務 (兼容包裝器) 初始化完成")
    
    def _get_parser(self) -> IParser:
        """延遲獲取解析器（服務定位器模式）"""
        if self._parser is None:
            # 通過全域服務工廠獲取
            from ..infrastructure.enhanced_service_factory import get_enhanced_service_factory
            factory = get_enhanced_service_factory()
            self._parser = factory.get_parser()
        return self._parser
    
    def _get_query_builder(self) -> IQueryBuilder:
        """延遲獲取查詢建構器（服務定位器模式）"""
        if self._query_builder is None:
            from ..infrastructure.enhanced_service_factory import get_enhanced_service_factory
            factory = get_enhanced_service_factory()
            self._query_builder = factory.get_builder()
        return self._query_builder
    
    def _get_statistics(self) -> IStatistics:
        """延遲獲取統計服務（服務定位器模式）"""
        if self._statistics is None:
            from ..infrastructure.enhanced_service_factory import get_enhanced_service_factory
            factory = get_enhanced_service_factory()
            self._statistics = factory.get_statistics()
        return self._statistics
    
    def _get_configuration(self) -> IConfiguration:
        """延遲獲取配置服務（服務定位器模式）"""
        if self._configuration is None:
            from ..infrastructure.enhanced_service_factory import get_enhanced_service_factory
            factory = get_enhanced_service_factory()
            self._configuration = factory.get_configuration()
        return self._configuration
    
    def _validate_input(self, text: str) -> Dict[str, Any]:
        """
        輸入驗證 - 防護空查詢和無效輸入
        
        Args:
            text: 自然語言文字
            
        Returns:
            Dict: 驗證結果 {"valid": bool, "error": str, "normalized_text": str}
        """
        # 基本空值檢查
        if not text:
            return {"valid": False, "error": "輸入不能為空", "normalized_text": ""}
        
        # 字串清理和標準化
        normalized_text = text.strip()
        if not normalized_text:
            return {"valid": False, "error": "輸入只包含空白字符", "normalized_text": ""}
        
        # 長度檢查
        if len(normalized_text) < 2:
            return {"valid": False, "error": "輸入過短，需要至少2個字符", "normalized_text": normalized_text}
        
        if len(normalized_text) > 1000:
            return {"valid": False, "error": "輸入過長，請簡化查詢", "normalized_text": normalized_text}
        
        # 惡意輸入檢查
        suspicious_patterns = [
            "drop table", "delete from", "truncate", "alter table",
            "create table", "insert into", "update set", "--", "/*", "*/"
        ]
        
        text_lower = normalized_text.lower()
        for pattern in suspicious_patterns:
            if pattern in text_lower:
                logger.warning(f"檢測到可疑輸入模式: {pattern}")
                return {"valid": False, "error": "檢測到不安全的輸入內容", "normalized_text": normalized_text}
        
        # 特殊字符檢查（允許中文、英文、數字、基本標點）
        import re
        if not re.match(r'^[\u4e00-\u9fff\w\s\.,?!，。？！\-/]+$', normalized_text):
            return {"valid": False, "error": "包含不支持的特殊字符", "normalized_text": normalized_text}
        
        return {"valid": True, "error": "", "normalized_text": normalized_text}
    
    async def parse_natural_language(
        self, 
        text: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> ParsedQuery:
        """
        解析自然語言為 SQL 查詢（向後兼容介面）- 增強輸入驗證
        
        Args:
            text: 自然語言文字
            context: 可選的上下文資訊
            
        Returns:
            ParsedQuery: 解析結果
        """
        try:
            # 🛡️ 輸入驗證 - 防護空查詢和無效輸入
            validation_result = self._validate_input(text)
            if not validation_result["valid"]:
                logger.warning("❌ 輸入驗證失敗", 
                             error=validation_result["error"], 
                             original_text=text[:50])
                
                # 記錄失敗統計
                self._get_statistics().record_failure(
                    operation_type="input_validation",
                    error_type="ValidationError",
                    error_message=validation_result["error"],
                    metadata={"original_text_length": len(text)}
                )
                
                return ParsedQuery(
                    query_type=QueryType.UNKNOWN,
                    sql_query="",
                    parameters={},
                    confidence=0.0,
                    explanation=f"輸入驗證失敗: {validation_result['error']}"
                )
            
            # 使用驗證後的文字
            normalized_text = validation_result["normalized_text"]
            
            # 記錄開始統計
            self._get_statistics().record_event(
                event_type="parse_start",
                metadata={"text_length": len(normalized_text), "original_length": len(text)}
            )
            
            # 使用新的 SOLID 解析器（使用標準化文字）
            parser = self._get_parser()
            parse_result = await parser.parse(normalized_text, context)
            
            # 🛡️ 空 SQL 防護機制 - 檢查並修復空查詢問題
            if parse_result.query_type != QueryType.UNKNOWN and (not parse_result.sql_query or not parse_result.sql_query.strip()):
                logger.warning("⚠️ 檢測到空 SQL 查詢，啟動自動修復機制", 
                             query_type=parse_result.query_type.value,
                             parameters=parse_result.parameters,
                             original_text=normalized_text[:50])
                
                try:
                    # 使用查詢建構器建構 SQL
                    query_builder = self._get_query_builder()
                    sql_query = query_builder.build_query(parse_result.query_type, parse_result.parameters)
                    
                    # 🛡️ 驗證建構的 SQL
                    if not sql_query or not sql_query.strip():
                        raise ValueError("查詢建構器返回空 SQL")
                    
                    # 基本 SQL 安全檢查
                    if len(sql_query.strip()) < 10:  # 最少應該有基本的 SELECT 語句
                        raise ValueError(f"生成的 SQL 過短: {sql_query}")
                    
                    # 檢查 SQL 語法基本結構
                    sql_lower = sql_query.lower().strip()
                    if not sql_lower.startswith(('select', 'with')):
                        raise ValueError(f"生成的 SQL 必須以 SELECT 或 WITH 開始: {sql_query[:50]}")
                    
                    # 創建包含 SQL 的新結果
                    result = ParsedQuery(
                        query_type=parse_result.query_type,
                        sql_query=sql_query,
                        parameters=parse_result.parameters,
                        confidence=max(parse_result.confidence, 0.8),  # 自動建構的查詢信心度較高
                        explanation=f"自動修復空查詢: {parse_result.explanation}"
                    )
                    
                    logger.info("✅ 空 SQL 自動修復成功", 
                               query_type=result.query_type.value,
                               sql_length=len(sql_query),
                               confidence=result.confidence)
                    
                except Exception as build_error:
                    logger.error("❌ SQL 建構失敗", 
                               query_type=parse_result.query_type.value,
                               error=str(build_error))
                    # 返回失敗結果，但保持解析資訊
                    result = ParsedQuery(
                        query_type=QueryType.UNKNOWN,
                        sql_query="",
                        parameters={},
                        confidence=0.0,
                        explanation=f"SQL 建構失敗: {str(build_error)}"
                    )
            else:
                result = parse_result
            
            # 🛡️ 最終防護 - 確保絕對不會返回空 SQL 查詢
            if result.query_type != QueryType.UNKNOWN and (not result.sql_query or not result.sql_query.strip()):
                logger.error("🚨 嚴重錯誤：最終結果仍包含空 SQL！強制設為 UNKNOWN",
                           query_type=result.query_type.value,
                           parameters=result.parameters)
                
                # 記錄嚴重錯誤統計
                self._get_statistics().record_failure(
                    operation_type="final_sql_validation",
                    error_type="EmptySQLError",
                    error_message="最終結果包含空 SQL",
                    metadata={"original_query_type": result.query_type.value}
                )
                
                # 強制返回安全的失敗結果
                result = ParsedQuery(
                    query_type=QueryType.UNKNOWN,
                    sql_query="",
                    parameters={},
                    confidence=0.0,
                    explanation="系統無法生成有效的 SQL 查詢，請嘗試重新描述您的需求"
                )
            
            # 記錄成功統計
            if result.query_type != QueryType.UNKNOWN:
                self._get_statistics().record_success(
                    operation_type="natural_language_parsing",
                    duration=0.0,  # 在實際實現中應該測量時間
                    metadata={
                        "confidence": result.confidence,
                        "sql_length": len(result.sql_query),
                        "has_parameters": bool(result.parameters)
                    }
                )
            
            logger.info("✅ 自然語言解析完成",
                       query_type=result.query_type.value,
                       confidence=result.confidence,
                       sql_length=len(result.sql_query) if result.sql_query else 0)
            
            return result
            
        except Exception as e:
            # 記錄失敗統計
            self._get_statistics().record_failure(
                operation_type="natural_language_parsing",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            
            logger.error("❌ 自然語言解析失敗", error=str(e))
            
            # 返回失敗的解析結果
            return ParsedQuery(
                query_type=QueryType.UNKNOWN,
                sql_query="",
                parameters={},
                confidence=0.0,
                explanation=f"解析失敗: {str(e)}"
            )
    
    def can_handle_query(self, text: str) -> float:
        """
        檢查是否能處理給定的查詢（向後兼容介面）
        
        Args:
            text: 查詢文字
            
        Returns:
            float: 處理能力信心度 (0-1)
        """
        try:
            parser = self._get_parser()
            return parser.can_handle(text)
        except Exception:
            return 0.0
    
    def get_supported_query_types(self) -> list[QueryType]:
        """
        獲取支援的查詢類型（向後兼容介面）
        
        Returns:
            list[QueryType]: 支援的查詢類型列表
        """
        try:
            builder = self._get_query_builder()
            return builder.get_supported_types()
        except Exception:
            return list(QueryType)
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        獲取服務資訊（向後兼容介面）
        
        Returns:
            Dict[str, Any]: 服務資訊
        """
        try:
            config = self._get_configuration()
            stats = self._get_statistics()
            
            return {
                "service_name": "NaturalLanguageToSQLService",
                "version": "2.0.0-solid-compatible",
                "architecture": "SOLID-refactored-with-compatibility-layer",
                "configuration": config.get_config_metadata(),
                "statistics": stats.get_summary_stats(),
                "features": {
                    "nl_to_sql_enabled": config.is_feature_enabled("nl_to_sql"),
                    "query_statistics": config.is_feature_enabled("query_statistics"),
                    "solid_architecture": True
                }
            }
        except Exception as e:
            return {
                "service_name": "NaturalLanguageToSQLService", 
                "version": "2.0.0-solid-compatible",
                "error": str(e)
            }


# 向後兼容的匯出
__all__ = ["NaturalLanguageToSQLService", "ParsedQuery", "QueryType"]