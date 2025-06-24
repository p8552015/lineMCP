#!/usr/bin/env python3
"""
MCP 回應標準化解析器
統一處理 MCP 協議的各種回應格式
"""

import json
import re
from typing import Any, Dict, Union

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
    def parse_query_result(result: Union[dict[str, Any], str]) -> list[dict[str, Any]]:
        """
        標準化 MCP 查詢結果解析（增強容錯版本）

        Args:
            result: MCP 工具調用的原始回應

        Returns:
            解析後的資料列表

        Raises:
            MCPQueryError: 查詢失敗
            MCPParseError: 解析失敗
        """
        try:
            # 記錄原始回應用於除錯
            logger.debug("開始解析 MCP 回應", 
                        original_type=type(result).__name__,
                        content_preview=str(result)[:200] if isinstance(result, str) else "dict")
            
            # 如果是字串，先解析為標準格式
            if isinstance(result, str):
                result = MCPResponseParser.parse_response(result)
                
            # 檢查基本成功狀態
            if not result.get("success", False):
                error_msg = result.get("error", "未知錯誤")
                error_type = result.get("error_type", "unknown")
                parsed_from = result.get("parsed_from", "unknown")
                
                # 增強的錯誤日誌記錄
                logger.error("MCP 查詢失敗", 
                            error_type=error_type,
                            error_message=error_msg,
                            parsed_from=parsed_from,
                            raw_response_preview=str(result)[:300])
                            
                raise MCPQueryError(f"MCP 查詢失敗 ({error_type}): {error_msg}")

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
                    # 檢查是否為純文本錯誤訊息
                    if MCPResponseParser._is_error_text(text_content):
                        logger.info("檢測到純文本錯誤訊息，進行錯誤格式解析",
                                   error_text_preview=text_content[:100])
                        error_response = MCPResponseParser._parse_error_text(text_content)
                        raise MCPQueryError(error_response["error"])
                    else:
                        # 增強的 JSON 解析錯誤處理
                        logger.error("JSON 解析失敗，嘗試錯誤恢復", 
                                   json_error=str(e),
                                   error_position=getattr(e, 'pos', 'unknown'),
                                   original_content_length=len(text_content),
                                   content_preview=text_content[:200],
                                   content_suffix=text_content[-50:] if len(text_content) > 50 else text_content)
                        
                        # 嘗試錯誤恢復策略
                        recovered_data = MCPResponseParser._attempt_recovery(text_content)
                        if recovered_data is not None:
                            logger.info("成功恢復解析", recovered_items=len(recovered_data) if isinstance(recovered_data, list) else 1)
                            return recovered_data if isinstance(recovered_data, list) else [recovered_data]
                        
                        raise MCPParseError(f"JSON 解析失敗且無法恢復：{str(e)}")

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
    def parse_single_value(result: Union[dict[str, Any], str], field_name: str) -> Any:
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
    def parse_count_result(result: Union[dict[str, Any], str]) -> int:
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
    def is_success(result: Union[dict[str, Any], str]) -> bool:
        """檢查 MCP 回應是否成功"""
        if isinstance(result, str):
            result = MCPResponseParser.parse_response(result)
        return result.get("success", False)

    @staticmethod
    def get_error_message(result: Union[dict[str, Any], str]) -> str:
        """獲取 MCP 回應中的錯誤訊息"""
        if isinstance(result, str):
            result = MCPResponseParser.parse_response(result)
        return result.get("error", "未知錯誤")
    
    @staticmethod
    def _detect_response_format(content: str) -> str:
        """
        檢測回應格式類型
        
        Args:
            content: 回應內容
            
        Returns:
            str: 格式類型 ('json', 'error_text', 'unknown')
        """
        if not content or not content.strip():
            return 'unknown'
            
        content = content.strip()
        
        # 檢查是否為 JSON 格式
        if content.startswith(('{', '[')):
            try:
                json.loads(content)
                return 'json'
            except json.JSONDecodeError:
                pass
        
        # 檢查是否為錯誤文本
        if MCPResponseParser._is_error_text(content):
            return 'error_text'
            
        return 'unknown'
    
    @staticmethod
    def _attempt_recovery(content: str) -> Union[list, dict, None]:
        """
        嘗試從損壞的 JSON 中恢復資料
        
        Args:
            content: 損壞的 JSON 內容
            
        Returns:
            Union[list, dict, None]: 恢復的資料或 None（如果無法恢復）
        """
        try:
            # 策略 1：移除常見的格式問題
            cleaned = content.strip()
            
            # 移除 BOM 標記
            if cleaned.startswith('\ufeff'):
                cleaned = cleaned[1:]
            
            # 修復常見的引號問題
            if "'" in cleaned and '"' not in cleaned:
                cleaned = cleaned.replace("'", '"')
            
            # 修復尾隨逗號問題
            cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
            
            # 修復控制字符
            cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
            
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass
            
            # 策略 2：嘗試提取部分有效的 JSON
            # 尋找 JSON 數組或對象的開始
            json_patterns = [
                r'\[.*\]',  # 數組
                r'\{.*\}',  # 對象
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, cleaned, re.DOTALL)
                for match in matches:
                    try:
                        parsed = json.loads(match)
                        logger.info("部分 JSON 恢復成功", 
                                   original_length=len(content),
                                   recovered_length=len(match))
                        return parsed
                    except json.JSONDecodeError:
                        continue
            
            # 策略 3：嘗試逐行解析（對於多行 JSON）
            lines = cleaned.split('\n')
            for i in range(len(lines)):
                for j in range(i + 1, len(lines) + 1):
                    candidate = '\n'.join(lines[i:j]).strip()
                    if candidate.startswith(('{', '[')):
                        try:
                            parsed = json.loads(candidate)
                            logger.info("逐行解析恢復成功", 
                                       start_line=i, 
                                       end_line=j-1)
                            return parsed
                        except json.JSONDecodeError:
                            continue
            
            logger.debug("所有恢復策略均失敗", content_length=len(content))
            return None
            
        except Exception as e:
            logger.debug("錯誤恢復過程中發生異常", error=str(e))
            return None
    
    @staticmethod
    def _is_error_text(content: str) -> bool:
        """
        檢查是否為純文本錯誤訊息
        
        Args:
            content: 回應內容
            
        Returns:
            bool: 是否為錯誤文本
        """
        if not content:
            return False
            
        content = content.strip().lower()
        
        # 常見的錯誤訊息模式（增強版本）
        error_patterns = [
            r'^error:',
            r'^exception:',
            r'^failed:',
            r'not allowed',
            r'permission denied',
            r'invalid',
            r'forbidden',
            r'unauthorized',
            r'not found',
            r'timeout',
            r'connection',
            r'only .* are allowed',
            r'only select queries are allowed',  # 特定於規格書中的錯誤
            r'expecting value',  # JSON 解析錯誤
            r'syntax error',
            r'parse error',
            r'database error',
            r'sql error',
            r'query failed',
            r'access denied',
            r'operation not permitted',
            r'resource not available',
            r'service unavailable'
        ]
        
        for pattern in error_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
                
        return False
    
    @staticmethod
    def _parse_error_text(content: str) -> Dict[str, Any]:
        """
        解析純文本錯誤訊息
        
        Args:
            content: 錯誤文本內容
            
        Returns:
            Dict[str, Any]: 標準化的錯誤回應格式
        """
        content = content.strip()
        
        # 分類錯誤類型（增強版本）
        error_type = 'unknown_error'
        content_lower = content.lower()
        
        # SQL 安全限制錯誤
        if 'only select queries are allowed' in content_lower:
            error_type = 'sql_security_restriction'
        elif 'only' in content_lower and 'allowed' in content_lower:
            error_type = 'security_restriction'
        # JSON 解析錯誤
        elif 'expecting value' in content_lower or 'json' in content_lower:
            error_type = 'json_parse_error'
        # 權限錯誤
        elif any(word in content_lower for word in ['permission', 'unauthorized', 'access denied']):
            error_type = 'permission_error'
        # 資源不存在錯誤
        elif 'not found' in content_lower:
            error_type = 'not_found_error'
        # 網路/連接錯誤
        elif any(word in content_lower for word in ['timeout', 'connection', 'network']):
            error_type = 'connection_error'
        # 資料庫錯誤
        elif any(word in content_lower for word in ['database', 'sql', 'query']):
            error_type = 'database_error'
        # 服務不可用錯誤
        elif 'service unavailable' in content_lower or 'resource not available' in content_lower:
            error_type = 'service_unavailable'
        # 驗證錯誤
        elif any(word in content_lower for word in ['invalid', 'validation', 'syntax']):
            error_type = 'validation_error'
            
        return {
            "success": False,
            "error": content,
            "error_type": error_type,
            "data": None,
            "parsed_from": "error_text"
        }
    
    @staticmethod
    def parse_response(content: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        智能解析各種格式的 MCP 回應
        
        Args:
            content: 回應內容（字串或字典）
            
        Returns:
            Dict[str, Any]: 標準化的回應格式
            
        Raises:
            MCPParseError: 解析失敗
        """
        try:
            # 如果已經是字典格式，直接返回
            if isinstance(content, dict):
                return content
                
            # 如果是字串，需要解析
            if isinstance(content, str):
                format_type = MCPResponseParser._detect_response_format(content)
                
                if format_type == 'json':
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError as e:
                        # 嘗試錯誤恢復
                        logger.warning("JSON 解析失敗，嘗試恢復", 
                                     error=str(e),
                                     content_preview=content[:100])
                        recovered_data = MCPResponseParser._attempt_recovery(content)
                        if recovered_data is not None:
                            logger.info("JSON 恢復成功")
                            return {
                                "success": True,
                                "data": recovered_data,
                                "parsed_from": "recovery"
                            }
                        raise MCPParseError(f"JSON 解析失敗且無法恢復：{str(e)}")
                        
                elif format_type == 'error_text':
                    logger.info("處理錯誤文本格式")
                    return MCPResponseParser._parse_error_text(content)
                    
                else:
                    # 未知格式，嘗試多種解析策略
                    logger.warning("未知回應格式，嘗試多種解析策略", 
                                 content_preview=content[:100])
                    
                    # 嘗試作為 JSON 解析（即使格式檢測失敗）
                    try:
                        parsed = json.loads(content)
                        logger.info("未知格式成功解析為 JSON")
                        return {
                            "success": True,
                            "data": parsed,
                            "parsed_from": "fallback_json"
                        }
                    except json.JSONDecodeError:
                        pass
                    
                    # 嘗試錯誤恢復
                    recovered_data = MCPResponseParser._attempt_recovery(content)
                    if recovered_data is not None:
                        logger.info("未知格式通過恢復策略解析成功")
                        return {
                            "success": True,
                            "data": recovered_data,
                            "parsed_from": "fallback_recovery"
                        }
                    
                    # 最後作為錯誤處理
                    return {
                        "success": False,
                        "error": content,
                        "error_type": "unknown_format",
                        "data": None,
                        "parsed_from": "unknown"
                    }
            else:
                raise MCPParseError(f"不支援的回應類型：{type(content)}")
                
        except (MCPQueryError, MCPParseError):
            raise
        except Exception as e:
            logger.error(f"回應解析時發生未預期錯誤：{e}", exc_info=True)
            raise MCPParseError(f"回應解析失敗：{str(e)}")
