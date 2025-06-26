"""
測試訊息處理應用服務
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from linebot.v3.messaging import TextMessage

from src.application.messaging_service import MessagingApplicationService
from src.domain.command_handler import CommandContext
from src.services.nl_to_sql.models.query_models import ParsedQuery, QueryType


class TestMessagingApplicationService:
    """訊息處理應用服務測試"""

    @pytest.fixture
    def mock_command_context(self):
        """模擬指令上下文"""
        context = Mock(spec=CommandContext)
        context.mcp_client_factory = AsyncMock()
        context.ai_model_service = Mock()
        context.nl_service = Mock()
        context.db_service = Mock()
        context.formatter = Mock()
        # context.flex_builder 已移除
        context.openai_client = Mock()
        return context

    @pytest.fixture
    def mock_nl_service(self):
        """模擬自然語言處理服務"""
        service = Mock()
        service.parse_natural_language = AsyncMock()
        return service

    @pytest.fixture
    def mock_message_formatter(self):
        """模擬訊息格式化器"""
        formatter = Mock()
        formatter.format_query_result = Mock(return_value=TextMessage(text="formatted"))
        return formatter

    @pytest.fixture
    def mock_command_executor(self):
        """模擬指令執行器"""
        executor = Mock()
        executor.execute_command = AsyncMock(return_value=TextMessage(text="test response"))
        executor.initialize = Mock()
        executor.get_command_info = Mock(return_value={"total_commands": 5, "total_aliases": 3})
        # 默認情況下，對於非指令文本返回 None
        executor.parse_and_validate_command = Mock(return_value=None)
        return executor

    @pytest.fixture
    def messaging_service(
        self, mock_command_context, mock_nl_service, mock_message_formatter, mock_command_executor
    ):
        """訊息處理服務實例"""
        return MessagingApplicationService(
            command_context=mock_command_context,
            nl_service=mock_nl_service,
            message_formatter=mock_message_formatter,
            command_executor=mock_command_executor,
        )

    @pytest.mark.asyncio
    async def test_service_initialization(self, messaging_service):
        """測試服務初始化"""
        assert not messaging_service.is_initialized

        with patch("src.utils.observability.get_tracer"):
            await messaging_service.initialize()

            assert messaging_service.is_initialized
            assert messaging_service._command_executor is not None

    @pytest.mark.asyncio
    async def test_process_command_message(self, messaging_service):
        """測試處理指令訊息"""
        with patch("src.utils.observability.get_tracer"):
            messaging_service._initialized = True
            
            # 設置 command_executor 返回值以識別這是一個指令
            messaging_service._command_executor.parse_and_validate_command.return_value = ("help", [])

            # 執行
            result = await messaging_service.process_message(
                user_id="test_user",
                message_text="/help",
                reply_token="test_token",
            )

            # 驗證
            assert isinstance(result, TextMessage)
            assert messaging_service._stats["command_messages"] == 1
            messaging_service._command_executor.execute_command.assert_called_once_with("test_user", "/help")

    @pytest.mark.asyncio
    async def test_process_natural_language_message_success(
        self, messaging_service, mock_nl_service, mock_message_formatter
    ):
        """測試處理自然語言訊息（成功）"""
        with patch("src.utils.observability.get_tracer"):
            messaging_service._initialized = True
            
            # 確保這不被識別為指令（返回 None）
            messaging_service._command_executor.parse_and_validate_command.return_value = None

            # 設置自然語言處理成功 - 使用 ParsedQuery 對象
            parse_result = ParsedQuery(
                query_type=QueryType.MACHINE_STATUS,
                sql_query="SELECT * FROM machines",
                parameters={},
                confidence=0.8,
                explanation="機台狀態查詢",
            )
            mock_nl_service.parse_natural_language.return_value = parse_result

            # 模擬資料庫服務和工廠
            with patch(
                "src.infrastructure.enhanced_service_factory.get_enhanced_service_factory"
            ) as mock_get_factory:
                mock_factory = Mock()
                mock_db_service = Mock()
                mock_query_result = {
                    "success": True,
                    "data": [{"id": 1, "name": "M001"}],
                }
                mock_db_service.execute_parsed_query = AsyncMock(
                    return_value=mock_query_result
                )
                mock_factory.get_service.return_value = mock_db_service
                mock_get_factory.return_value = mock_factory

                # 執行
                result = await messaging_service.process_message(
                    user_id="test_user",
                    message_text="M001機台狀況如何",
                    reply_token="test_token",
                )

                # 驗證
                assert isinstance(result, TextMessage)
                assert (
                    messaging_service._stats["natural_language_messages"] == 1
                )
                mock_message_formatter.format_query_result.assert_called_once_with(
                    mock_query_result
                )

    @pytest.mark.asyncio
    async def test_process_natural_language_message_failure(
        self, messaging_service, mock_nl_service
    ):
        """測試處理自然語言訊息（失敗）"""
        with patch("src.utils.observability.get_tracer"):
            messaging_service._initialized = True
            
            # 確保這不被識別為指令（返回 None）
            messaging_service._command_executor.parse_and_validate_command.return_value = None

            # 設置自然語言處理失敗
            mock_nl_service.parse_natural_language.return_value = {
                "success": False,
                "error": "無法理解查詢",
            }

            # 執行
            result = await messaging_service.process_message(
                user_id="test_user",
                message_text="無效的查詢",
                reply_token="test_token",
            )

            # 驗證返回預設回應
            assert isinstance(result, TextMessage)
            assert "產線管理助手" in result.text

    @pytest.mark.asyncio
    async def test_process_message_error_handling(self, messaging_service):
        """測試訊息處理錯誤處理"""
        with (
            patch(
                "src.infrastructure.error_handler.handle_error_gracefully"
            ) as mock_handler,
            patch("src.application.messaging_service.CommandExecutor") as MockExecutor,
            patch("src.utils.observability.get_tracer"),
        ):
            # 設置模擬拋出異常 - 讓 _update_user_session 拋出異常來觸發主 try-catch
            mock_handler.return_value = TextMessage(text="錯誤處理")

            # 創建模擬的指令執行器
            mock_executor = Mock()
            mock_executor.initialize = Mock()
            MockExecutor.return_value = mock_executor

            messaging_service._initialized = True
            messaging_service._command_executor = mock_executor

            # 讓 _update_user_session 拋出異常來測試錯誤處理
            original_update_session = messaging_service._update_user_session
            messaging_service._update_user_session = Mock(
                side_effect=Exception("Session update error")
            )

            try:
                # 執行
                result = await messaging_service.process_message(
                    user_id="test_user",
                    message_text="test message",
                    reply_token="test_token",
                )

                # 驗證
                assert isinstance(result, TextMessage)
                assert messaging_service._stats["error_messages"] == 1
                mock_handler.assert_called_once()
            finally:
                # 恢復原始方法
                messaging_service._update_user_session = original_update_session

    def test_classify_message_command(self, messaging_service):
        """測試訊息分類 - 指令"""
        # 模擬 command_executor 的解析結果
        messaging_service._command_executor.parse_and_validate_command.return_value = ("help", [])

        result = messaging_service._classify_message("/help")
        assert result == "command"

    def test_classify_message_natural_language(self, messaging_service):
        """測試訊息分類 - 自然語言"""
        # 模擬 command_executor 返回 None（非指令）
        messaging_service._command_executor.parse_and_validate_command.return_value = None

        result = messaging_service._classify_message("機台狀況如何")
        assert result == "natural_language"

    def test_user_session_management(self, messaging_service):
        """測試用戶會話管理"""
        # 設置非指令訊息的返回值
        messaging_service._command_executor.parse_and_validate_command.return_value = None
        
        # 更新會話
        messaging_service._update_user_session(
            user_id="test_user",
            message_text="test message",
            additional_context={"context_key": "value"},
        )

        # 檢查會話創建
        assert "test_user" in messaging_service._user_sessions
        session = messaging_service._user_sessions["test_user"]
        assert session["message_count"] == 1
        assert session["last_message"] == "test message"
        assert session["context"]["context_key"] == "value"

        # 測試獲取會話
        retrieved_session = messaging_service.get_user_session("test_user")
        assert retrieved_session == session

        # 測試清除會話
        result = messaging_service.clear_user_session("test_user")
        assert result is True
        assert "test_user" not in messaging_service._user_sessions

        # 測試清除不存在的會話
        result = messaging_service.clear_user_session("nonexistent_user")
        assert result is False

    def test_session_command_tracking(self, messaging_service):
        """測試會話中的指令追蹤"""
        # 模擬 command_executor 的解析結果
        messaging_service._command_executor.parse_and_validate_command.return_value = ("help", [])

        messaging_service._update_user_session(
            user_id="test_user", message_text="/help", additional_context=None
        )

        session = messaging_service._user_sessions["test_user"]
        assert session["last_command"] == "help"

    def test_session_result_update(self, messaging_service):
        """測試會話結果更新"""
        # 創建會話
        messaging_service._user_sessions["test_user"] = {"message_count": 1}

        # 更新成功結果
        mock_message = TextMessage(text="success")
        messaging_service._update_session_result(
            user_id="test_user", result=mock_message, success=True
        )

        session = messaging_service._user_sessions["test_user"]
        assert session["last_success"] is True
        assert "last_error" not in session

        # 更新錯誤結果
        messaging_service._update_session_result(
            user_id="test_user", result=None, success=False, error="Test error"
        )

        assert session["last_success"] is False
        assert session["last_error"] == "Test error"

    def test_get_processing_stats(self, messaging_service):
        """測試獲取處理統計"""
        # 設置統計數據
        messaging_service._stats = {
            "total_messages": 100,
            "command_messages": 60,
            "natural_language_messages": 35,
            "error_messages": 5,
        }
        messaging_service._user_sessions = {"user1": {}, "user2": {}}

        stats = messaging_service.get_processing_stats()

        assert stats["total_messages"] == 100
        assert stats["command_messages"] == 60
        assert stats["natural_language_messages"] == 35
        assert stats["error_messages"] == 5
        assert stats["active_sessions"] == 2
        assert stats["command_success_rate"] == 95.0  # (100-5)/100 * 100

    @pytest.mark.asyncio
    async def test_health_checks(self, messaging_service):
        """測試健康檢查"""
        # 設置模擬指令執行器
        messaging_service._initialized = True

        # 設置自然語言服務健康檢查
        messaging_service.nl_service.health_check = AsyncMock(
            return_value={"status": "healthy"}
        )

        checks = await messaging_service._perform_health_checks()

        assert "command_executor" in checks
        assert checks["command_executor"]["status"] == "healthy"
        assert checks["command_executor"]["total_commands"] == 5

        assert "natural_language_service" in checks
        assert checks["natural_language_service"]["status"] == "healthy"

        assert "processing_stats" in checks
        assert checks["processing_stats"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_checks_no_executor(self, messaging_service):
        """測試無指令執行器時的健康檢查"""
        messaging_service._command_executor = None
        messaging_service._initialized = True

        checks = await messaging_service._perform_health_checks()

        assert checks["command_executor"]["status"] == "not_initialized"

    @pytest.mark.asyncio
    async def test_health_checks_executor_error(self, messaging_service):
        """測試指令執行器錯誤時的健康檢查"""
        mock_executor = Mock()
        mock_executor.get_command_info.side_effect = Exception("Executor error")
        messaging_service._command_executor = mock_executor
        messaging_service._initialized = True

        checks = await messaging_service._perform_health_checks()

        assert checks["command_executor"]["status"] == "unhealthy"
        assert "error" in checks["command_executor"]

    @pytest.mark.asyncio
    async def test_shutdown_service(self, messaging_service):
        """測試服務關閉"""
        # 設置一些數據
        messaging_service._user_sessions = {"user1": {}, "user2": {}}
        messaging_service._stats = {
            "total_messages": 100,
            "command_messages": 60,
            "natural_language_messages": 35,
            "error_messages": 5,
        }

        await messaging_service._shutdown_service()

        # 驗證清理
        assert len(messaging_service._user_sessions) == 0
        assert messaging_service._stats["total_messages"] == 0
        assert messaging_service._stats["command_messages"] == 0

    def test_get_default_response(self, messaging_service):
        """測試預設回應"""
        response = messaging_service._get_default_response()

        assert isinstance(response, TextMessage)
        assert "產線管理助手" in response.text
        assert "/help" in response.text

    @pytest.mark.asyncio
    async def test_process_command_message_without_executor(self, messaging_service):
        """測試無指令執行器時處理指令"""
        messaging_service._command_executor = None

        with pytest.raises(RuntimeError, match="指令執行器未初始化"):
            await messaging_service._process_command_message("test_user", "/help")


class TestMessagingServiceIntegration:
    """訊息處理服務集成測試"""

    @pytest.mark.asyncio
    async def test_full_message_processing_lifecycle(self):
        """測試完整的訊息處理生命週期"""
        # 創建真實服務但模擬依賴
        command_context = Mock(spec=CommandContext)
        nl_service = Mock()
        message_formatter = Mock()
        command_executor = Mock()
        command_executor.execute_command = AsyncMock(return_value=TextMessage(text="help"))
        command_executor.initialize = Mock()

        service = MessagingApplicationService(
            command_context=command_context,
            nl_service=nl_service,
            message_formatter=message_formatter,
            command_executor=command_executor,
        )

        # 初始化
        await service.initialize()
        assert service.is_initialized

        # 處理指令訊息
        result = await service.process_message("user1", "/help", "token")
        assert isinstance(result, TextMessage)

        # 處理自然語言訊息
        nl_service.parse_natural_language = AsyncMock(
            return_value={"success": False}
        )

        result = await service.process_message("user1", "hello", "token")
        assert isinstance(result, TextMessage)

        # 關閉服務
        await service.shutdown()
        assert not service.is_initialized
