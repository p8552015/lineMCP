"""
測試資料模型
"""

import pytest
from datetime import datetime
from typing import Any, Dict

from mcp_common.models.base import (
    MCPCall,
    MCPResponse,
    MCPStreamChunk,
    MCPBatchResponse,
    MCPHealthCheck,
    ServerStatus
)
from mcp_common.models.error import (
    MCPError,
    MCPTimeoutError,
    MCPConnectionError,
    MCPValidationError
)
from mcp_common.models.query import (
    MCPQuery,
    MCPQueryResult,
    MCPQueryMetadata
)


class TestMCPCall:
    """測試 MCPCall 模型"""
    
    def test_create_basic_call(self):
        """測試建立基本呼叫"""
        call = MCPCall(
            server="test_server",
            tool="test_tool",
            params={"key": "value"}
        )
        
        assert call.server == "test_server"
        assert call.tool == "test_tool"
        assert call.params == {"key": "value"}
        assert call.id is not None
        assert call.timeout is None
        assert call.priority == "normal"
    
    def test_create_call_with_options(self):
        """測試建立帶選項的呼叫"""
        call = MCPCall(
            server="test_server",
            tool="test_tool",
            params={},
            timeout=30.0,
            priority="high",
            metadata={"request_id": "123"}
        )
        
        assert call.timeout == 30.0
        assert call.priority == "high"
        assert call.metadata["request_id"] == "123"
    
    def test_priority_validation(self):
        """測試優先級驗證"""
        with pytest.raises(ValueError):
            MCPCall(
                server="test",
                tool="test",
                params={},
                priority="invalid"
            )


class TestMCPResponse:
    """測試 MCPResponse 模型"""
    
    def test_create_success_response(self):
        """測試建立成功回應"""
        response = MCPResponse(
            status="success",
            data={"result": "ok"},
            call_id="123"
        )
        
        assert response.status == "success"
        assert response.data["result"] == "ok"
        assert response.call_id == "123"
        assert response.error is None
        assert isinstance(response.timestamp, datetime)
    
    def test_create_error_response(self):
        """測試建立錯誤回應"""
        response = MCPResponse(
            status="error",
            data=None,
            call_id="123",
            error="Something went wrong"
        )
        
        assert response.status == "error"
        assert response.data is None
        assert response.error == "Something went wrong"
    
    def test_execution_time(self):
        """測試執行時間計算"""
        response = MCPResponse(
            status="success",
            data={},
            call_id="123",
            execution_time=1.5
        )
        
        assert response.execution_time == 1.5


class TestMCPStreamChunk:
    """測試 MCPStreamChunk 模型"""
    
    def test_create_chunk(self):
        """測試建立串流區塊"""
        chunk = MCPStreamChunk(
            data={"content": "Hello"},
            sequence=1,
            is_final=False
        )
        
        assert chunk.data["content"] == "Hello"
        assert chunk.sequence == 1
        assert chunk.is_final is False
    
    def test_final_chunk(self):
        """測試最終區塊"""
        chunk = MCPStreamChunk(
            data={"content": "Done"},
            sequence=10,
            is_final=True,
            metadata={"total_chunks": 10}
        )
        
        assert chunk.is_final is True
        assert chunk.metadata["total_chunks"] == 10


class TestMCPBatchResponse:
    """測試 MCPBatchResponse 模型"""
    
    def test_create_batch_response(self):
        """測試建立批次回應"""
        responses = [
            MCPResponse(status="success", data={"i": 0}, call_id="0"),
            MCPResponse(status="success", data={"i": 1}, call_id="1"),
            MCPResponse(status="error", data=None, call_id="2", error="Failed"),
        ]
        
        batch = MCPBatchResponse(
            responses=responses,
            total_time=2.5
        )
        
        assert len(batch.responses) == 3
        assert batch.total_time == 2.5
        assert batch.success_count == 2
        assert batch.error_count == 1
    
    def test_empty_batch(self):
        """測試空批次"""
        batch = MCPBatchResponse(responses=[])
        
        assert len(batch.responses) == 0
        assert batch.success_count == 0
        assert batch.error_count == 0


class TestMCPHealthCheck:
    """測試 MCPHealthCheck 模型"""
    
    def test_create_health_check(self):
        """測試建立健康檢查"""
        health = MCPHealthCheck(
            overall="healthy",
            servers={
                "server1": ServerStatus(
                    status="healthy",
                    latency_ms=10.5,
                    last_checked=datetime.now()
                ),
                "server2": ServerStatus(
                    status="degraded",
                    latency_ms=150.0,
                    last_checked=datetime.now(),
                    error="High latency"
                )
            }
        )
        
        assert health.overall == "healthy"
        assert len(health.servers) == 2
        assert health.servers["server1"].status == "healthy"
        assert health.servers["server2"].status == "degraded"
        assert health.servers["server2"].error == "High latency"
    
    def test_overall_status_validation(self):
        """測試整體狀態驗證"""
        with pytest.raises(ValueError):
            MCPHealthCheck(
                overall="invalid",
                servers={}
            )


class TestMCPErrors:
    """測試錯誤類型"""
    
    def test_base_error(self):
        """測試基本錯誤"""
        error = MCPError("Something went wrong", code="ERR001")
        
        assert str(error) == "Something went wrong"
        assert error.code == "ERR001"
        assert error.details is None
    
    def test_error_with_details(self):
        """測試帶詳細資訊的錯誤"""
        error = MCPError(
            "Database error",
            code="DB_ERR",
            details={"table": "users", "operation": "insert"}
        )
        
        assert error.details["table"] == "users"
        assert error.details["operation"] == "insert"
    
    def test_timeout_error(self):
        """測試超時錯誤"""
        error = MCPTimeoutError("Request timed out", timeout=30.0)
        
        assert "Request timed out" in str(error)
        assert error.timeout == 30.0
    
    def test_connection_error(self):
        """測試連線錯誤"""
        error = MCPConnectionError(
            "Failed to connect",
            server="test_server",
            retry_count=3
        )
        
        assert error.server == "test_server"
        assert error.retry_count == 3
    
    def test_validation_error(self):
        """測試驗證錯誤"""
        error = MCPValidationError(
            "Invalid parameter",
            field="email",
            value="invalid@"
        )
        
        assert error.field == "email"
        assert error.value == "invalid@"


class TestMCPQuery:
    """測試查詢模型"""
    
    def test_create_query(self):
        """測試建立查詢"""
        query = MCPQuery(
            query="SELECT * FROM users",
            params={"limit": 10},
            database="test_db"
        )
        
        assert query.query == "SELECT * FROM users"
        assert query.params["limit"] == 10
        assert query.database == "test_db"
        assert query.timeout is None
    
    def test_query_with_options(self):
        """測試帶選項的查詢"""
        query = MCPQuery(
            query="SELECT * FROM users WHERE id = ?",
            params={"id": 123},
            timeout=5.0,
            metadata={"cache": True}
        )
        
        assert query.timeout == 5.0
        assert query.metadata["cache"] is True


class TestMCPQueryResult:
    """測試查詢結果模型"""
    
    def test_create_query_result(self):
        """測試建立查詢結果"""
        result = MCPQueryResult(
            rows=[
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"}
            ],
            columns=["id", "name"],
            metadata=MCPQueryMetadata(
                row_count=2,
                execution_time_ms=15.5,
                affected_rows=0
            )
        )
        
        assert len(result.rows) == 2
        assert result.columns == ["id", "name"]
        assert result.metadata.row_count == 2
        assert result.metadata.execution_time_ms == 15.5
    
    def test_empty_result(self):
        """測試空結果"""
        result = MCPQueryResult(
            rows=[],
            columns=["id", "name"],
            metadata=MCPQueryMetadata(
                row_count=0,
                execution_time_ms=5.0
            )
        )
        
        assert len(result.rows) == 0
        assert result.metadata.row_count == 0