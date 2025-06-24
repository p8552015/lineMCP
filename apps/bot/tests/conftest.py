"""
Pytest 配置和共用 fixtures
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

# 添加 src 到 Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture(scope="session")
def event_loop():
    """創建事件循環用於整個測試會話"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_mcp_client():
    """模擬 MCP 客戶端"""
    client = AsyncMock()
    client.call_tool.return_value = {
        "success": True,
        "data": [{"id": 1, "name": "test"}],
    }
    return client


@pytest.fixture
def mock_openai_client():
    """模擬 OpenAI 客戶端"""
    client = Mock()
    client.chat.completions.create.return_value = Mock(
        choices=[Mock(message=Mock(content="Test AI response"))]
    )
    return client


@pytest.fixture
def mock_ai_model_service():
    """模擬 AI 模型服務"""
    service = AsyncMock()
    service.get_available_models.return_value = [
        {
            "name": "gpt-4o-mini",
            "provider": "openai",
            "is_default": True,
            "cost_per_1k_input": 0.15,
            "cost_per_1k_output": 0.60,
            "context_window": 128000,
        }
    ]
    return service


@pytest.fixture
def mock_database_service():
    """模擬資料庫服務"""
    service = AsyncMock()
    service.execute_query.return_value = [
        {"machine_id": "M001", "status": "running"},
        {"machine_id": "M002", "status": "idle"},
    ]
    service.get_table_info.return_value = {
        "machines": {"row_count": 10, "columns": ["id", "name", "status"]}
    }
    service.test_connection.return_value = True
    return service


@pytest.fixture
def mock_nl_service():
    """模擬自然語言處理服務"""
    from apps.bot.backup.nl_to_sql_service import QueryType

    service = AsyncMock()
    service.parse_natural_language.return_value = Mock(
        query_type=QueryType.MACHINE_STATUS,
        confidence=0.9,
        explanation="查詢機台狀態",
        sql_query="SELECT * FROM machines WHERE id = 'M001'",
    )
    service.get_suggested_queries.return_value = [
        "M001機台狀況如何？",
        "查看所有機台",
        "近期故障記錄",
    ]
    return service


@pytest.fixture
def mock_formatter():
    """模擬訊息格式化器"""
    from linebot.v3.messaging import TextMessage

    formatter = Mock()
    formatter.format_query_result.return_value = TextMessage(text="格式化的查詢結果")
    formatter.format_error_message.return_value = TextMessage(text="錯誤訊息")
    formatter.format_suggestion_message.return_value = TextMessage(text="建議訊息")
    return formatter


@pytest.fixture
def sample_line_event():
    """LINE 訊息事件範例"""
    return {
        "type": "message",
        "replyToken": "test_reply_token",
        "source": {"type": "user", "userId": "test_user_id"},
        "message": {"type": "text", "text": "test message"},
    }


@pytest.fixture
def sample_command_context():
    """命令上下文範例"""
    from src.models.commands import Command

    return Command(name="sql", args=["SELECT * FROM machines LIMIT 5"])
