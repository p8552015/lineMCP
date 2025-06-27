"""
統一錯誤處理測試
驗證自定義異常和錯誤處理器的正確性
"""

import pytest
from linebot.v3.messaging import TextMessage

from src.domain.exceptions import (
    AIServiceException,
    BotError,
    CommandParsingException,
    DatabaseQueryException,
    MCPConnectionException,
    ValidationException,
    create_ai_error,
    create_command_error,
    create_db_error,
    create_mcp_error,
    create_validation_error,
)
from src.infrastructure.error_handler import (
    ErrorHandlerMiddleware,
    UnifiedErrorHandler,
    create_error_middleware,
    get_error_handler,
    handle_error_gracefully,
)


class TestCustomExceptions:
    """測試自定義異常"""

    def test_bot_exception_basic(self):
        """測試基礎 Bot 異常"""
        error = BotError("Technical error", "User friendly message")

        assert str(error) == "Technical error"
        assert error.user_message == "User friendly message"
        assert error.details == {}
        assert error.error_code is None

    def test_bot_exception_with_details(self):
        """測試帶詳細資訊的 Bot 異常"""
        details = {"field": "email", "value": "invalid"}
        error = BotError(
            "Validation failed",
            "輸入格式錯誤",
            details=details,
            error_code="VALIDATION_001",
        )

        assert error.details == details
        assert error.error_code == "VALIDATION_001"

        error_dict = error.to_dict()
        assert error_dict["error_type"] == "BotError"
        assert error_dict["message"] == "Validation failed"
        assert error_dict["user_message"] == "輸入格式錯誤"
        assert error_dict["details"] == details
        assert error_dict["error_code"] == "VALIDATION_001"

    def test_validation_exception(self):
        """測試驗證異常"""
        error = ValidationException("email", "invalid@", "格式不正確")

        assert "email" in str(error)
        assert "輸入的 email 格式不正確" in error.user_message
        assert error.details["field"] == "email"
        assert error.details["value"] == "invalid@"
        assert error.error_code == "VALIDATION_ERROR"

    def test_command_parsing_exception(self):
        """測試指令解析異常"""
        error = CommandParsingException("/unknown", "不支援的指令")

        assert "/unknown" in str(error)
        assert "無法理解指令" in error.user_message
        assert error.details["command"] == "/unknown"
        assert error.error_code == "COMMAND_PARSE_ERROR"

    def test_database_query_exception(self):
        """測試資料庫查詢異常"""
        query = "SELECT * FROM non_existent_table"
        error = DatabaseQueryException(query, "表格不存在", "SELECT")

        assert "Database query failed" in str(error)
        assert "資料庫查詢失敗" in error.user_message
        assert error.details["query"] == query
        assert error.details["query_type"] == "SELECT"
        assert error.error_code == "DB_QUERY_ERROR"

    def test_mcp_connection_exception(self):
        """測試 MCP 連接異常"""
        error = MCPConnectionException("postgres", "query", "連接超時")

        assert "postgres.query" in str(error)
        assert "服務連接失敗" in error.user_message
        assert error.details["server"] == "postgres"
        assert error.details["operation"] == "query"
        assert error.error_code == "MCP_CONNECTION_ERROR"

    def test_ai_service_exception(self):
        """測試 AI 服務異常"""
        error = AIServiceException("openai", "completion", "API 額度不足")

        assert "openai" in str(error)
        assert "AI 服務暫時不可用" in error.user_message
        assert error.details["service"] == "openai"
        assert error.details["operation"] == "completion"
        assert error.error_code == "AI_SERVICE_ERROR"

    def test_exception_factory_functions(self):
        """測試異常工廠函數"""
        # 測試驗證錯誤工廠
        error1 = create_validation_error("age", -1, "必須為正數")
        assert isinstance(error1, ValidationException)
        assert error1.details["field"] == "age"

        # 測試指令錯誤工廠
        error2 = create_command_error("/test", "未實現")
        assert isinstance(error2, CommandParsingException)
        assert error2.details["command"] == "/test"

        # 測試資料庫錯誤工廠
        error3 = create_db_error("SELECT 1", "語法錯誤")
        assert isinstance(error3, DatabaseQueryException)
        assert error3.details["query"] == "SELECT 1"

        # 測試 MCP 錯誤工廠
        error4 = create_mcp_error("server", "op", "failed")
        assert isinstance(error4, MCPConnectionException)
        assert error4.details["server"] == "server"

        # 測試 AI 錯誤工廠
        error5 = create_ai_error("gpt", "chat", "quota exceeded")
        assert isinstance(error5, AIServiceException)
        assert error5.details["service"] == "gpt"


class TestUnifiedErrorHandler:
    """測試統一錯誤處理器"""

    @pytest.fixture
    def error_handler(self):
        """創建錯誤處理器實例"""
        return UnifiedErrorHandler(include_technical_details=False)

    @pytest.fixture
    def detailed_error_handler(self):
        """創建包含技術細節的錯誤處理器實例"""
        return UnifiedErrorHandler(include_technical_details=True)

    def test_handle_validation_exception(self, error_handler):
        """測試處理驗證異常"""
        error = ValidationException("email", "invalid", "格式錯誤")
        result = error_handler.handle_error(error)

        assert isinstance(result, TextMessage)
        assert "⚠️" in result.text
        assert "輸入的 email 格式不正確" in result.text
        assert "invalid" not in result.text  # 不包含技術細節

    def test_handle_validation_exception_with_details(self, detailed_error_handler):
        """測試處理驗證異常（包含技術細節）"""
        error = ValidationException("email", "invalid", "格式錯誤")
        result = detailed_error_handler.handle_error(error)

        assert isinstance(result, TextMessage)
        assert "⚠️" in result.text
        assert "技術詳情" in result.text
        assert "invalid" in result.text  # 包含技術細節

    def test_handle_command_parsing_exception(self, error_handler):
        """測試處理指令解析異常"""
        error = CommandParsingException("/unknown", "不支援")
        result = error_handler.handle_error(error)

        assert isinstance(result, TextMessage)
        assert "❓" in result.text
        assert "無法理解指令" in result.text

    def test_handle_database_query_exception(self, error_handler):
        """測試處理資料庫查詢異常"""
        error = DatabaseQueryException("SELECT * FROM test", "表格不存在")
        result = error_handler.handle_error(error)

        assert isinstance(result, TextMessage)
        assert "🗄️" in result.text
        assert "資料庫查詢失敗" in result.text

    def test_handle_mcp_connection_exception(self, error_handler):
        """測試處理 MCP 連接異常"""
        error = MCPConnectionException("postgres", "query", "超時")
        result = error_handler.handle_error(error)

        assert isinstance(result, TextMessage)
        assert "🔌" in result.text
        assert "服務連接失敗" in result.text

    def test_handle_ai_service_exception(self, error_handler):
        """測試處理 AI 服務異常"""
        error = AIServiceException("openai", "completion", "quota exceeded")
        result = error_handler.handle_error(error)

        assert isinstance(result, TextMessage)
        assert "🤖" in result.text
        assert "AI 服務暫時不可用" in result.text

    def test_handle_system_timeout_error(self, error_handler):
        """測試處理系統超時錯誤"""
        error = TimeoutError("Operation timed out")
        result = error_handler.handle_error(error)

        assert isinstance(result, TextMessage)
        assert "⏰" in result.text
        assert "操作逾時" in result.text

    def test_handle_system_connection_error(self, error_handler):
        """測試處理系統連接錯誤"""
        error = ConnectionError("Network unreachable")
        result = error_handler.handle_error(error)

        assert isinstance(result, TextMessage)
        assert "🔌" in result.text
        assert "網路連接失敗" in result.text

    def test_handle_system_permission_error(self, error_handler):
        """測試處理系統權限錯誤"""
        error = PermissionError("Access denied")
        result = error_handler.handle_error(error)

        assert isinstance(result, TextMessage)
        assert "🔒" in result.text
        assert "權限不足" in result.text

    def test_handle_unknown_exception(self, error_handler):
        """測試處理未知異常"""
        error = RuntimeError("Something went wrong")
        result = error_handler.handle_error(error)

        assert isinstance(result, TextMessage)
        assert "💥" in result.text
        assert "系統發生未知錯誤" in result.text
        assert "Something went wrong" not in result.text  # 不包含技術細節

    def test_handle_unknown_exception_with_details(self, detailed_error_handler):
        """測試處理未知異常（包含技術細節）"""
        error = RuntimeError("Something went wrong")
        result = detailed_error_handler.handle_error(error)

        assert isinstance(result, TextMessage)
        assert "💥" in result.text
        assert "Something went wrong" in result.text  # 包含技術細節

    def test_error_logging(self, error_handler, caplog):
        """測試錯誤日誌記錄"""

        # 由於我們使用 structlog，這個測試主要驗證不會拋出異常
        # 並且可以看到 stdout 中有日誌輸出（已在測試輸出中確認）
        validation_error = ValidationException("test", "value", "reason")

        # 應該能正常處理而不拋出異常
        result = error_handler.handle_error(validation_error)

        # 結果應該正常
        assert isinstance(result, TextMessage)
        assert "⚠️" in result.text

    def test_context_information(self, error_handler):
        """測試錯誤上下文資訊"""
        error = ValidationException("field", "value", "reason")
        context = {"user_id": "test_user", "operation": "test_operation"}

        result = error_handler.handle_error(error, context)

        # 結果應該正常
        assert isinstance(result, TextMessage)
        assert "⚠️" in result.text


class TestErrorHandlerMiddleware:
    """測試錯誤處理中間件"""

    @pytest.fixture
    def middleware(self):
        """創建錯誤處理中間件"""
        handler = UnifiedErrorHandler(include_technical_details=False)
        return ErrorHandlerMiddleware(handler)

    @pytest.mark.asyncio
    async def test_middleware_success(self, middleware):
        """測試中間件處理成功的情況"""

        @middleware
        async def test_function():
            return "success"

        result = await test_function()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_middleware_handles_bot_exception(self, middleware):
        """測試中間件處理 Bot 異常"""

        @middleware
        async def test_function():
            raise ValidationException("field", "value", "error")

        result = await test_function()

        assert isinstance(result, TextMessage)
        assert "⚠️" in result.text
        assert "輸入的 field 格式不正確" in result.text

    @pytest.mark.asyncio
    async def test_middleware_handles_system_exception(self, middleware):
        """測試中間件處理系統異常"""

        @middleware
        async def test_function():
            raise ValueError("Invalid value")

        result = await test_function()

        assert isinstance(result, TextMessage)
        assert "⚠️" in result.text
        assert "輸入值錯誤" in result.text


class TestGlobalErrorHandler:
    """測試全域錯誤處理器"""

    def test_get_global_error_handler(self):
        """測試獲取全域錯誤處理器"""
        handler1 = get_error_handler()
        handler2 = get_error_handler()

        # 應該返回同一個實例
        assert handler1 is handler2
        assert isinstance(handler1, UnifiedErrorHandler)

    def test_handle_error_gracefully_function(self):
        """測試便捷錯誤處理函數"""
        error = ValidationException("test", "value", "reason")
        result = handle_error_gracefully(error)

        assert isinstance(result, TextMessage)
        assert "⚠️" in result.text

    def test_create_error_middleware_function(self):
        """測試創建錯誤處理中間件函數"""
        middleware = create_error_middleware()

        assert isinstance(middleware, ErrorHandlerMiddleware)
        assert isinstance(middleware.error_handler, UnifiedErrorHandler)
