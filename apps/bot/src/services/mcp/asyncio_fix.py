#!/usr/bin/env python3
"""
MCP Asyncio 錯誤修復
解決 MCP Python SDK 的已知 cancel scope 問題
"""

import asyncio
import contextlib
import warnings
from typing import Any, AsyncGenerator, Dict, Optional, Tuple

import structlog

logger = structlog.get_logger()


class MCPAsyncioErrorSuppressor:
    """
    MCP Asyncio 錯誤抑制器
    安全地抑制 MCP SDK 的已知 cancel scope 錯誤
    """

    def __init__(self):
        self._original_excepthook = None
        self._error_count = 0
        self._max_errors_to_log = 3

    def __enter__(self):
        """啟用錯誤抑制"""
        self._original_excepthook = asyncio.get_event_loop().set_exception_handler
        asyncio.get_event_loop().set_exception_handler(self._handle_exception)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """停用錯誤抑制"""
        if self._original_excepthook:
            asyncio.get_event_loop().set_exception_handler(self._original_excepthook)

    def _handle_exception(self, loop, context):
        """處理 asyncio 異常"""
        exception = context.get('exception')
        message = context.get('message', '')
        
        # 檢查是否為已知的 MCP cancel scope 錯誤
        if self._is_mcp_cancel_scope_error(exception, message):
            self._error_count += 1
            
            if self._error_count <= self._max_errors_to_log:
                logger.debug(
                    "🔇 已知 MCP cancel scope 錯誤已抑制",
                    error_count=self._error_count,
                    exception_type=type(exception).__name__ if exception else "Unknown",
                    message=message[:100] + "..." if len(message) > 100 else message
                )
                
                if self._error_count == self._max_errors_to_log:
                    logger.info(
                        "🔇 MCP cancel scope 錯誤抑制已啟用 - 後續相同錯誤將被靜默抑制",
                        total_suppressed=self._error_count
                    )
        else:
            # 對於其他錯誤，使用預設處理器
            if self._original_excepthook:
                self._original_excepthook(loop, context)
            else:
                # 備用處理
                logger.error("Asyncio 未處理異常", context=context)

    def _is_mcp_cancel_scope_error(self, exception: Exception, message: str) -> bool:
        """檢查是否為 MCP cancel scope 錯誤"""
        if not exception and not message:
            return False
            
        # 檢查異常類型
        if exception:
            exception_str = str(exception)
            if "Attempted to exit cancel scope in a different task" in exception_str:
                return True
            if "cancel scope" in exception_str.lower() and "task" in exception_str.lower():
                return True
                
        # 檢查錯誤訊息
        if message:
            mcp_indicators = [
                "stdio_client",
                "mcp.client.stdio",
                "cancel scope",
                "async_generator object",
                "GeneratorExit"
            ]
            
            if any(indicator in message for indicator in mcp_indicators):
                return True
                
        return False


@contextlib.asynccontextmanager
async def suppress_mcp_errors():
    """
    上下文管理器，用於抑制 MCP 的已知錯誤
    
    使用方式:
    async with suppress_mcp_errors():
        # 執行 MCP 操作
        pass
    """
    suppressor = MCPAsyncioErrorSuppressor()
    
    # 同時抑制 Python 警告中的相關錯誤
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", 
            message=".*cancel scope.*task.*",
            category=RuntimeWarning
        )
        warnings.filterwarnings(
            "ignore",
            message=".*async_generator.*stdio_client.*",
            category=RuntimeWarning
        )
        
        with suppressor:
            try:
                yield
            except RuntimeError as e:
                # 捕獲並靜默處理已知的 cancel scope 錯誤
                if "cancel scope" in str(e) and "different task" in str(e):
                    logger.debug("🔇 MCP cancel scope 錯誤已在主線程中抑制", error=str(e))
                else:
                    raise


def apply_global_mcp_error_suppression():
    """
    應用全局 MCP 錯誤抑制
    適用於整個應用程序生命週期
    """
    # 設置全局異常處理器
    def handle_exception(loop, context):
        exception = context.get('exception')
        message = context.get('message', '')
        
        # 檢查是否為 MCP 相關錯誤
        if exception and any(indicator in str(exception) for indicator in [
            "cancel scope",
            "stdio_client",
            "mcp.client"
        ]):
            # 靜默處理
            logger.debug("🔇 全局 MCP 錯誤抑制", error=str(exception)[:100])
            return
            
        # 記錄其他錯誤
        logger.error("未處理的 asyncio 異常", context=context)
    
    # 獲取或創建事件循環
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    loop.set_exception_handler(handle_exception)
    logger.info("✅ 全局 MCP 錯誤抑制已啟用")


class SafeMCPRunner:
    """
    安全的 MCP 運行器
    自動處理 MCP 的 asyncio 問題
    """
    
    @staticmethod
    async def run_with_error_suppression(coro):
        """
        運行協程並抑制 MCP 錯誤
        
        Args:
            coro: 要運行的協程
            
        Returns:
            協程的結果
        """
        async with suppress_mcp_errors():
            return await coro
    
    @staticmethod
    def run_sync_with_error_suppression(coro):
        """
        同步運行協程並抑制 MCP 錯誤
        
        Args:
            coro: 要運行的協程
            
        Returns:
            協程的結果
        """
        async def wrapped_coro():
            async with suppress_mcp_errors():
                return await coro
        
        return asyncio.run(wrapped_coro())