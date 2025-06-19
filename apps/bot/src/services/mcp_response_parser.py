#!/usr/bin/env python3
"""
MCP 回應標準化解析器
統一處理 MCP 協議的各種回應格式
"""

import json
from typing import Any

import structlog

logger = structlog.get_logger()


class MCPParseError(Exception):
    """MCP 解析錯誤"""

    pass


class MCPQueryError(Exception):
    """MCP 查詢錯誤"""

    pass


class MCPResponseParser:
    """MCP 回應標準化解析器"""

    @staticmethod
    def parse_query_result(result: dict[str, Any]) -> list[dict[str, Any]]:
        """
        標準化 MCP 查詢結果解析

        Args:
            result: MCP 工具調用的原始回應

        Returns:
            解析後的資料列表

        Raises:
            MCPQueryError: 查詢失敗
            MCPParseError: 解析失敗
        """
        try:
            # 檢查基本成功狀態
            if not result.get("success", False):
                error_msg = result.get("error", "未知錯誤")
                raise MCPQueryError(f"MCP 查詢失敗：{error_msg}")

            data = result.get("data")
            if data is None:
                logger.warning("MCP 回應中沒有 data 欄位")
                return []

            # 處理直接的列表格式
            if isinstance(data, list):
                return data

            # 處理複雜的巢狀格式：{content: [{type: 'text', text: "JSON字串"}]}
            if isinstance(data, dict) and "content" in data:
                content_list = data.get("content", [])
                if not content_list:
                    logger.warning("MCP 回應中 content 為空")
                    return []

                # 取第一個 content 項目
                first_content = content_list[0]
                if not isinstance(first_content, dict):
                    raise MCPParseError(f"Content 格式錯誤：{type(first_content)}")

                text_content = first_content.get("text", "")
                if not text_content:
                    logger.warning("Content 中沒有 text 欄位")
                    return []

                # 解析 JSON 字串
                try:
                    # 處理 Python 字典字串（使用單引號）
                    if text_content.startswith("[{") and "'" in text_content:
                        parsed_data = json.loads(text_content.replace("'", '"'))
                    else:
                        parsed_data = json.loads(text_content)

                    if isinstance(parsed_data, list):
                        return parsed_data
                    elif isinstance(parsed_data, dict):
                        return [parsed_data]
                    else:
                        raise MCPParseError(
                            f"解析後的資料不是有效格式：{type(parsed_data)}"
                        )

                except json.JSONDecodeError as e:
                    logger.error(f"JSON 解析失敗：{e}，原始內容：{text_content}")
                    raise MCPParseError(f"JSON 解析失敗：{str(e)}")

            # 處理其他字典格式
            if isinstance(data, dict):
                return [data]

            # 無法識別的格式
            raise MCPParseError(f"無法識別的 MCP 回應格式：{type(data)}")

        except (MCPQueryError, MCPParseError):
            # 重新拋出已知錯誤
            raise
        except Exception as e:
            logger.error(f"MCP 回應解析時發生未預期錯誤：{e}", exc_info=True)
            raise MCPParseError(f"回應解析失敗：{str(e)}")

    @staticmethod
    def parse_single_value(result: dict[str, Any], field_name: str) -> Any:
        """
        從 MCP 回應中解析單一值

        Args:
            result: MCP 工具調用的原始回應
            field_name: 要提取的欄位名稱

        Returns:
            解析後的單一值
        """
        try:
            data_list = MCPResponseParser.parse_query_result(result)
            if not data_list:
                return None

            first_row = data_list[0]
            return first_row.get(field_name)

        except (MCPQueryError, MCPParseError):
            raise
        except Exception as e:
            raise MCPParseError(f"單一值解析失敗：{str(e)}")

    @staticmethod
    def parse_count_result(result: dict[str, Any]) -> int:
        """
        解析計數查詢結果

        Args:
            result: MCP 工具調用的原始回應

        Returns:
            計數值
        """
        try:
            # 嘗試常見的計數欄位名稱
            count_fields = ["count", "COUNT(*)", "total", "num"]

            data_list = MCPResponseParser.parse_query_result(result)
            if not data_list:
                return 0

            first_row = data_list[0]

            # 查找計數欄位
            for field in count_fields:
                if field in first_row:
                    value = first_row[field]
                    return int(value) if value is not None else 0

            # 如果只有一個數值欄位，假設它就是計數
            numeric_fields = [
                k
                for k, v in first_row.items()
                if isinstance(v, (int, float)) or (isinstance(v, str) and v.isdigit())
            ]

            if len(numeric_fields) == 1:
                value = first_row[numeric_fields[0]]
                return int(value) if value is not None else 0

            logger.warning(f"無法識別計數欄位，可用欄位：{list(first_row.keys())}")
            return 0

        except (MCPQueryError, MCPParseError):
            raise
        except Exception as e:
            raise MCPParseError(f"計數解析失敗：{str(e)}")

    @staticmethod
    def is_success(result: dict[str, Any]) -> bool:
        """檢查 MCP 回應是否成功"""
        return result.get("success", False)

    @staticmethod
    def get_error_message(result: dict[str, Any]) -> str:
        """獲取 MCP 回應中的錯誤訊息"""
        return result.get("error", "未知錯誤")
