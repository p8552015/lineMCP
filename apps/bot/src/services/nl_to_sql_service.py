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
    
    async def parse_natural_language(
        self, 
        text: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> ParsedQuery:
        """
        解析自然語言為 SQL 查詢（向後兼容介面）
        
        Args:
            text: 自然語言文字
            context: 可選的上下文資訊
            
        Returns:
            ParsedQuery: 解析結果
        """
        try:
            # 記錄開始統計
            self._get_statistics().record_event(
                event_type="parse_start",
                metadata={"text_length": len(text)}
            )
            
            # 使用新的 SOLID 解析器
            parser = self._get_parser()
            parse_result = await parser.parse(text, context)
            
            # 🔥 緊急修復：如果解析器沒有建構 SQL，我們來建構
            if parse_result.query_type != QueryType.UNKNOWN and (not parse_result.sql_query or not parse_result.sql_query.strip()):
                logger.warning("⚠️ 解析器返回空 SQL，嘗試建構查詢", 
                             query_type=parse_result.query_type.value,
                             parameters=parse_result.parameters)
                
                try:
                    # 使用查詢建構器建構 SQL
                    query_builder = self._get_query_builder()
                    sql_query = query_builder.build_query(parse_result.query_type, parse_result.parameters)
                    
                    # 創建包含 SQL 的新結果
                    result = ParsedQuery(
                        query_type=parse_result.query_type,
                        sql_query=sql_query,
                        parameters=parse_result.parameters,
                        confidence=parse_result.confidence,
                        explanation=parse_result.explanation
                    )
                    
                    logger.info("✅ SQL 建構成功", 
                               query_type=result.query_type.value,
                               sql_length=len(sql_query))
                    
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
            
            # 記錄成功統計
            self._get_statistics().record_success(
                operation_type="natural_language_parsing",
                duration=0.0,  # 在實際實現中應該測量時間
                metadata={"confidence": result.confidence}
            )
            
            logger.info("✅ 自然語言解析完成",
                       query_type=result.query_type.value,
                       confidence=result.confidence)
            
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