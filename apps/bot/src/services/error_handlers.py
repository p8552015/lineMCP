#!/usr/bin/env python3
"""
統一錯誤處理裝飾器
提供一致的錯誤處理和日誌記錄
"""

import asyncio
import functools
from collections.abc import Callable
from typing import Any

import structlog
from linebot.v3.messaging import Message, TextMessage

from .mcp_response_parser import MCPParseError, MCPQueryError

logger = structlog.get_logger()


def mcp_error_handler(
    error_message: str = "操作失敗",
    timeout_seconds: int = 30,
    include_technical_details: bool = False,
):
    """
    MCP 操作錯誤處理裝飾器

    Args:
        error_message: 使用者看到的錯誤訊息前綴
        timeout_seconds: 操作逾時秒數
        include_technical_details: 是否在錯誤訊息中包含技術細節
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Message:
            func_name = func.__name__

            try:
                # 設定逾時
                return await asyncio.wait_for(
                    func(*args, **kwargs), timeout=timeout_seconds
                )

            except TimeoutError:
                logger.error(
                    f"MCP operation timeout in {func_name}",
                    timeout_seconds=timeout_seconds,
                )
                return TextMessage(text=f"⏰ {error_message}（操作逾時，請稍後再試）")

            except MCPQueryError as e:
                logger.error(f"MCP query error in {func_name}", error=str(e))
                if include_technical_details:
                    return TextMessage(text=f"❌ {error_message}：{str(e)}")
                else:
                    return TextMessage(text=f"❌ {error_message}，請檢查查詢條件")

            except MCPParseError as e:
                logger.error(f"MCP parse error in {func_name}", error=str(e))
                if include_technical_details:
                    return TextMessage(
                        text=f"🔧 {error_message}：資料格式解析錯誤 - {str(e)}"
                    )
                else:
                    return TextMessage(text=f"🔧 {error_message}，資料格式異常")

            except ConnectionError as e:
                logger.error(f"Connection error in {func_name}", error=str(e))
                return TextMessage(text=f"🔌 {error_message}，無法連接到資料服務")

            except PermissionError as e:
                logger.error(f"Permission error in {func_name}", error=str(e))
                return TextMessage(text=f"🔒 {error_message}，權限不足")

            except Exception as e:
                logger.error(
                    f"Unexpected error in {func_name}", error=str(e), exc_info=True
                )
                if include_technical_details:
                    return TextMessage(text=f"💥 {error_message}：{str(e)}")
                else:
                    return TextMessage(text=f"💥 {error_message}，請聯絡系統管理員")

        return wrapper

    return decorator


def async_retry(
    max_attempts: int = 3,
    delay_seconds: float = 1.0,
    backoff_multiplier: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """
    非同步重試裝飾器

    Args:
        max_attempts: 最大重試次數
        delay_seconds: 初始延遲秒數
        backoff_multiplier: 延遲倍數
        exceptions: 要重試的例外類型
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            func_name = func.__name__
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        # 最後一次嘗試失敗
                        logger.error(
                            f"All retry attempts failed for {func_name}",
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            error=str(e),
                        )
                        raise

                    # 計算延遲時間
                    delay = delay_seconds * (backoff_multiplier**attempt)

                    logger.warning(
                        f"Retry attempt {attempt + 1}/{max_attempts} for {func_name}",
                        delay=delay,
                        error=str(e),
                    )

                    await asyncio.sleep(delay)

                except Exception as e:
                    # 不在重試列表中的例外直接拋出
                    logger.error(f"Non-retryable error in {func_name}", error=str(e))
                    raise

            # 理論上不會到達這裡
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def log_performance(include_args: bool = False):
    """
    效能監控裝飾器

    Args:
        include_args: 是否在日誌中包含函數參數
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            import time

            func_name = func.__name__
            start_time = time.time()

            try:
                if include_args:
                    logger.info(
                        f"Starting {func_name}",
                        args=args[1:] if args else [],  # 跳過 self
                        kwargs=kwargs,
                    )
                else:
                    logger.info(f"Starting {func_name}")

                result = await func(*args, **kwargs)

                execution_time = time.time() - start_time
                logger.info(
                    f"Completed {func_name}", execution_time=f"{execution_time:.3f}s"
                )

                return result

            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"Failed {func_name}",
                    execution_time=f"{execution_time:.3f}s",
                    error=str(e),
                )
                raise

        return wrapper

    return decorator


class ErrorContext:
    """錯誤上下文管理器，用於收集錯誤詳情"""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.context_data: dict[str, Any] = {}

    def __enter__(self):
        import time

        self.start_time = time.time()
        logger.info(f"Starting operation: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import time

        execution_time = time.time() - self.start_time if self.start_time else 0

        if exc_type is None:
            logger.info(
                f"Operation completed: {self.operation_name}",
                execution_time=f"{execution_time:.3f}s",
                **self.context_data,
            )
        else:
            logger.error(
                f"Operation failed: {self.operation_name}",
                execution_time=f"{execution_time:.3f}s",
                error_type=exc_type.__name__,
                error_message=str(exc_val),
                **self.context_data,
            )

        return False  # 不抑制例外

    def add_context(self, **kwargs):
        """添加上下文資料"""
        self.context_data.update(kwargs)
