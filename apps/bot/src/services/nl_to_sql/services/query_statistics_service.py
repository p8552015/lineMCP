"""
查詢統計追蹤服務

實現 SRP (單一職責原則)：
- 專門負責查詢統計資料的收集和分析
- 不包含解析、建構等其他職責

實現 DIP (依賴倒置原則)：
- 實現 IStatistics 抽象介面
- 可被其他組件透過介面使用

實現 OCP (開閉原則)：
- 支援多種統計指標擴展
- 可添加新的統計分析方法
"""

import time
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

import structlog

from ..interfaces.statistics_interfaces import IStatistics

logger = structlog.get_logger()


class QueryStatisticsService(IStatistics):
    """
    查詢統計追蹤服務
    
    職責：
    - 記錄查詢解析的成功和失敗統計
    - 分析解析器效能和準確性
    - 提供統計報告和趨勢分析
    
    設計原則：
    - SRP: 只負責統計追蹤，不處理解析邏輯
    - DIP: 實現 IStatistics 抽象介面
    - OCP: 支援多種統計指標和分析方法的擴展
    """
    
    def __init__(self, max_history_size: int = 10000):
        """
        初始化統計服務
        
        Args:
            max_history_size: 最大歷史記錄數量
        """
        self._max_history_size = max_history_size
        
        # 統計計數器
        self._success_counts: Dict[str, int] = defaultdict(int)
        self._failure_counts: Dict[str, int] = defaultdict(int)
        
        # 信心度統計
        self._confidence_scores: Dict[str, List[float]] = defaultdict(list)
        
        # 時間統計
        self._parse_times: Dict[str, List[float]] = defaultdict(list)
        
        # 詳細歷史記錄
        self._history: deque = deque(maxlen=max_history_size)
        
        # 錯誤統計
        self._error_types: Dict[str, int] = defaultdict(int)
        
        # 查詢類型統計
        self._query_type_stats: Dict[str, int] = defaultdict(int)
        
        # 服務啟動時間
        self._start_time = time.time()
        
        logger.info("📊 查詢統計服務初始化完成",
                   max_history_size=max_history_size)
    
    def record_success(
        self, 
        operation_type: str, 
        duration: float, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        記錄成功操作（實現 IStatistics 介面）
        
        Args:
            operation_type: 操作類型（如 "rule_parsing", "ai_parsing"）
            duration: 操作耗時（秒）
            metadata: 操作元數據
        """
        # 🔥 關鍵修復：完整的輸入驗證和類型安全處理
        try:
            # 驗證必要參數
            if not operation_type:
                logger.warning("操作類型為空，使用預設值")
                operation_type = "unknown"
            
            # 從 metadata 提取原有參數，保持向後兼容
            parser_type = metadata.get('parser_type', operation_type) if metadata else operation_type
            confidence = self._safe_confidence_conversion(metadata.get('confidence', 1.0) if metadata else 1.0)
            query_type = metadata.get('query_type') if metadata else None
            
            # 🔥 增強的 duration 類型轉換，捕獲所有可能的異常
            safe_duration = self._safe_duration_conversion(duration, 0.0)
            parse_time = safe_duration * 1000 if safe_duration > 0 else None  # 轉換為毫秒
            
            # 更新計數器
            self._success_counts[parser_type] += 1
            
            # 記錄信心度
            self._confidence_scores[parser_type].append(confidence)
            
            # 記錄解析時間
            if parse_time is not None:
                self._parse_times[parser_type].append(parse_time)
            
            # 記錄查詢類型統計
            if query_type:
                self._query_type_stats[query_type] += 1
            
            # 添加到歷史記錄
            record = {
                "timestamp": time.time(),
                "parser_type": parser_type,
                "result": "success",
                "confidence": confidence,
                "parse_time": parse_time,
                "query_type": query_type,
                "operation_type": operation_type,
                "duration": safe_duration
            }
            self._history.append(record)
            
            # 清理舊數據（保持記憶體使用合理）
            self._cleanup_old_data(parser_type)
            
            logger.debug("✅ 記錄成功操作",
                        operation=operation_type,
                        parser=parser_type,
                        confidence=confidence,
                        query_type=query_type)
                        
        except Exception as e:
            logger.error("❌ 記錄成功操作時發生錯誤", 
                        operation_type=str(operation_type),
                        duration=str(duration),
                        metadata=str(metadata)[:200] if metadata else None,
                        error=str(e))
            # 不拋出異常，避免影響主要功能
    
    def record_failure(
        self, 
        operation_type: str, 
        error_type: str, 
        error_message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        記錄失敗操作（實現 IStatistics 介面）
        
        Args:
            operation_type: 操作類型
            error_type: 錯誤類型
            error_message: 錯誤訊息
            metadata: 錯誤元數據
        """
        # 🔥 關鍵修復：完整的輸入驗證和類型安全處理
        try:
            # 驗證必要參數
            if not operation_type:
                logger.warning("操作類型為空，使用預設值")
                operation_type = "unknown"
            if not error_type:
                error_type = "unknown_error"
            if not error_message:
                error_message = "無錯誤訊息"
            
            # 從 metadata 提取原有參數，保持向後兼容
            parser_type = metadata.get('parser_type', operation_type) if metadata else operation_type
            error = f"{error_type}: {error_message}"
            
            # 🔥 增強的 duration 類型轉換
            safe_duration = self._safe_duration_conversion(metadata.get('duration', 0) if metadata else 0, 0.0)
            parse_time = safe_duration * 1000 if safe_duration > 0 else None  # 轉換為毫秒
            
            # 更新計數器
            self._failure_counts[parser_type] += 1
            
            # 記錄錯誤類型
            error_category = self._categorize_error(error)
            self._error_types[error_category] += 1
            
            # 記錄解析時間
            if parse_time is not None:
                self._parse_times[parser_type].append(parse_time)
            
            # 添加到歷史記錄
            record = {
                "timestamp": time.time(),
                "parser_type": parser_type,
                "result": "failure",
                "error": error,
                "error_category": error_category,
                "parse_time": parse_time,
                "operation_type": operation_type,
                "error_type": error_type,
                "error_message": error_message
            }
            self._history.append(record)
            
            logger.debug("❌ 記錄失敗操作",
                        operation=operation_type,
                        parser=parser_type,
                        error_type=error_type,
                        error_category=error_category)
                        
        except Exception as e:
            logger.error("❌ 記錄失敗操作時發生錯誤", 
                        operation_type=str(operation_type),
                        error_type=str(error_type),
                        error_message=str(error_message)[:200],
                        metadata=str(metadata)[:200] if metadata else None,
                        error=str(e))
            # 不拋出異常，避免影響主要功能
    
    def get_stats(self) -> Dict[str, Any]:
        """
        獲取統計資訊
        
        Returns:
            Dict[str, Any]: 完整統計資訊
        """
        current_time = time.time()
        uptime = current_time - self._start_time
        
        # 計算總體統計 - 確保類型安全
        total_success = int(sum(self._success_counts.values()))
        total_failure = int(sum(self._failure_counts.values()))
        total_requests = total_success + total_failure
        
        # 計算成功率 - 類型安全的除法
        success_rate = float(total_success) / float(total_requests) if total_requests > 0 else 0.0
        
        # 計算平均信心度 - 類型安全版本
        all_confidences = []
        for confidences in self._confidence_scores.values():
            # 確保所有信心度值都是數值類型
            safe_confidences = self._safe_numeric_list_conversion(confidences)
            all_confidences.extend(safe_confidences)
        avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
        
        # 計算平均解析時間 - 類型安全版本
        all_parse_times = []
        for times in self._parse_times.values():
            # 確保所有時間值都是數值類型
            safe_times = self._safe_numeric_list_conversion(times)
            all_parse_times.extend(safe_times)
        avg_parse_time = sum(all_parse_times) / len(all_parse_times) if all_parse_times else 0.0
        
        # 解析器效能統計 - 類型安全版本
        parser_stats = {}
        for parser_type in set(list(self._success_counts.keys()) + list(self._failure_counts.keys())):
            success = int(self._success_counts[parser_type])
            failure = int(self._failure_counts[parser_type])
            total = success + failure
            
            # 確保統計數據的類型安全
            confidences = self._safe_numeric_list_conversion(self._confidence_scores[parser_type])
            times = self._safe_numeric_list_conversion(self._parse_times[parser_type])
            
            parser_stats[parser_type] = {
                "success_count": success,
                "failure_count": failure,
                "total_count": total,
                "success_rate": float(success) / float(total) if total > 0 else 0.0,
                "avg_confidence": sum(confidences) / len(confidences) if confidences else 0.0,
                "avg_parse_time": sum(times) / len(times) if times else 0.0,
                "confidence_std": self._calculate_std(confidences),
                "parse_time_std": self._calculate_std(times)
            }
        
        return {
            "summary": {
                "total_requests": total_requests,
                "total_success": total_success,
                "total_failure": total_failure,
                "success_rate": success_rate,
                "avg_confidence": avg_confidence,
                "avg_parse_time": avg_parse_time,
                "uptime_seconds": uptime
            },
            "parser_statistics": parser_stats,
            "query_type_distribution": dict(self._query_type_stats),
            "error_distribution": dict(self._error_types),
            "performance_metrics": self._get_performance_metrics(),
            "recent_trends": self._get_recent_trends()
        }
    
    def get_parser_performance(self, parser_type: str) -> Dict[str, Any]:
        """
        獲取特定解析器的效能統計
        
        Args:
            parser_type: 解析器類型
            
        Returns:
            Dict[str, Any]: 解析器效能統計
        """
        success = int(self._success_counts[parser_type])
        failure = int(self._failure_counts[parser_type])
        total = success + failure
        
        # 確保統計數據的類型安全
        confidences = self._safe_numeric_list_conversion(self._confidence_scores[parser_type])
        times = self._safe_numeric_list_conversion(self._parse_times[parser_type])
        
        # 計算百分位數
        confidence_percentiles = self._calculate_percentiles(confidences)
        time_percentiles = self._calculate_percentiles(times)
        
        return {
            "parser_type": parser_type,
            "request_counts": {
                "success": success,
                "failure": failure,
                "total": total
            },
            "success_rate": float(success) / float(total) if total > 0 else 0.0,
            "confidence_metrics": {
                "average": sum(confidences) / len(confidences) if confidences else 0.0,
                "standard_deviation": self._calculate_std(confidences),
                "percentiles": confidence_percentiles,
                "min": min(confidences) if confidences else 0.0,
                "max": max(confidences) if confidences else 0.0
            },
            "performance_metrics": {
                "avg_parse_time": sum(times) / len(times) if times else 0.0,
                "parse_time_std": self._calculate_std(times),
                "time_percentiles": time_percentiles,
                "min_time": min(times) if times else 0.0,
                "max_time": max(times) if times else 0.0
            }
        }
    
    def get_recent_activity(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        獲取最近活動記錄
        
        Args:
            hours: 查詢的小時數
            
        Returns:
            List[Dict[str, Any]]: 最近活動記錄
        """
        cutoff_time = time.time() - (hours * 3600)
        
        recent_records = []
        for record in self._history:
            if record["timestamp"] >= cutoff_time:
                recent_records.append(record)
        
        # 按時間排序（最新的在前）
        recent_records.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return recent_records
    
    def clear_statistics(self) -> None:
        """
        清除所有統計資料
        """
        self._success_counts.clear()
        self._failure_counts.clear()
        self._confidence_scores.clear()
        self._parse_times.clear()
        self._history.clear()
        self._error_types.clear()
        self._query_type_stats.clear()
        self._start_time = time.time()
        
        logger.info("🗑️ 統計資料已清除")
    
    def export_statistics(self, format: str = "dict") -> Any:
        """
        匯出統計資料
        
        Args:
            format: 匯出格式（"dict", "json", "csv"）
            
        Returns:
            Any: 匯出的統計資料
        """
        stats = self.get_stats()
        
        if format == "dict":
            return stats
        elif format == "json":
            import json
            return json.dumps(stats, indent=2, default=str)
        elif format == "csv":
            return self._export_to_csv(stats)
        else:
            raise ValueError(f"不支援的匯出格式: {format}")
    
    def _categorize_error(self, error: str) -> str:
        """
        分類錯誤類型
        
        Args:
            error: 錯誤訊息
            
        Returns:
            str: 錯誤類別
        """
        error_lower = error.lower()
        
        if "timeout" in error_lower:
            return "timeout"
        elif "network" in error_lower or "connection" in error_lower:
            return "network"
        elif "json" in error_lower or "parse" in error_lower:
            return "parsing"
        elif "ai" in error_lower or "model" in error_lower:
            return "ai_service"
        elif "config" in error_lower or "setting" in error_lower:
            return "configuration"
        else:
            return "unknown"
    
    def _cleanup_old_data(self, parser_type: str, max_records: int = 1000) -> None:
        """
        清理舊資料以控制記憶體使用
        
        Args:
            parser_type: 解析器類型
            max_records: 最大保留記錄數
        """
        # 清理信心度記錄
        if len(self._confidence_scores[parser_type]) > max_records:
            self._confidence_scores[parser_type] = self._confidence_scores[parser_type][-max_records:]
        
        # 清理時間記錄
        if len(self._parse_times[parser_type]) > max_records:
            self._parse_times[parser_type] = self._parse_times[parser_type][-max_records:]
    
    def _calculate_std(self, values: List[float]) -> float:
        """
        計算標準差
        
        Args:
            values: 數值列表（已經過類型安全轉換）
            
        Returns:
            float: 標準差
        """
        if not values or len(values) < 2:
            return 0.0
        
        # 使用已經轉換過的數值列表
        numeric_values = values  # 輸入已是安全的數值列表
        
        if len(numeric_values) < 2:
            return 0.0
        
        mean = sum(numeric_values) / len(numeric_values)
        variance = sum((x - mean) ** 2 for x in numeric_values) / len(numeric_values)
        return variance ** 0.5
    
    def _calculate_percentiles(self, values: List[float]) -> Dict[str, float]:
        """
        計算百分位數
        
        Args:
            values: 數值列表（已經過類型安全轉換）
            
        Returns:
            Dict[str, float]: 百分位數字典
        """
        if not values:
            return {"p50": 0.0, "p75": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0}
        
        # 使用已經轉換過的數值列表
        numeric_values = values  # 輸入已是安全的數值列表
        
        if not numeric_values:
            return {"p50": 0.0, "p75": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0}
        
        sorted_values = sorted(numeric_values)
        n = len(sorted_values)
        
        def percentile(p):
            index = int(p * n / 100)
            return sorted_values[min(index, n - 1)]
        
        return {
            "p50": percentile(50),
            "p75": percentile(75),
            "p90": percentile(90),
            "p95": percentile(95),
            "p99": percentile(99)
        }
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """
        獲取效能指標
        
        Returns:
            Dict[str, Any]: 效能指標
        """
        all_parse_times = []
        for times in self._parse_times.values():
            # 使用類型安全的轉換
            safe_times = self._safe_numeric_list_conversion(times)
            all_parse_times.extend(safe_times)
        
        if not all_parse_times:
            return {"status": "no_data"}
        
        return {
            "parse_time_percentiles": self._calculate_percentiles(all_parse_times),
            "total_samples": len(all_parse_times),
            "performance_grade": self._grade_performance(all_parse_times)
        }
    
    def _get_recent_trends(self, hours: int = 24) -> Dict[str, Any]:
        """
        獲取最近趨勢
        
        Args:
            hours: 分析的小時數
            
        Returns:
            Dict[str, Any]: 趨勢分析
        """
        recent_records = self.get_recent_activity(hours)
        
        if not recent_records:
            return {"status": "no_recent_data"}
        
        # 計算時段統計
        hourly_stats = defaultdict(lambda: {"success": 0, "failure": 0})
        
        for record in recent_records:
            hour = datetime.fromtimestamp(record["timestamp"]).hour
            result = record.get("result", "other")
            if result not in hourly_stats[hour]:
                hourly_stats[hour][result] = 0
            hourly_stats[hour][result] += 1
        
        return {
            "time_range_hours": hours,
            "total_recent_requests": len(recent_records),
            "hourly_distribution": dict(hourly_stats),
            "trend_direction": self._analyze_trend_direction(recent_records)
        }
    
    def _grade_performance(self, parse_times: List[float]) -> str:
        """
        評估效能等級
        
        Args:
            parse_times: 解析時間列表（已經過類型安全轉換）
            
        Returns:
            str: 效能等級
        """
        if not parse_times:
            return "unknown"
        
        # 🔥 關鍵修復：即使參數聲明為已轉換，仍進行二次安全轉換
        # 這防止了外部調用時傳入未轉換數據的情況
        numeric_times = self._safe_numeric_list_conversion(parse_times)
        
        if not numeric_times:
            return "unknown"
            
        # 🔥 關鍵修復：確保 avg_time 為數值類型 - 強化版
        try:
            avg_time = sum(numeric_times) / len(numeric_times)
            # 🛡️ 雙重類型轉換保護
            avg_time = self._safe_float_conversion(avg_time, 0.0)
            
            # 🛡️ 額外驗證：確保結果確實是數值類型
            if not isinstance(avg_time, (int, float)):
                logger.error("❌ 平均時間計算後仍非數值類型", 
                           result_type=type(avg_time).__name__, 
                           result_value=str(avg_time))
                return "unknown"
                
            # 🛡️ 確保是有效的數值（非 NaN 或無限值）
            if not (isinstance(avg_time, (int, float)) and 
                    not (isinstance(avg_time, float) and 
                         (avg_time != avg_time or avg_time == float('inf') or avg_time == float('-inf')))):
                logger.warning("平均時間為無效數值", avg_time=avg_time)
                return "unknown"
                
        except Exception as e:
            logger.warning("平均時間計算失敗", 
                         parse_times_count=len(numeric_times),
                         error=str(e))
            return "unknown"
        
        # 🔥 關鍵修復：終極類型安全的比較邏輯
        try:
            # 🛡️ 雙重類型轉換保護 - 確保絕對是數值類型
            if not isinstance(avg_time, (int, float)):
                # 嘗試字符串轉換
                if isinstance(avg_time, str):
                    avg_time_float = float(avg_time.strip())
                else:
                    avg_time_float = float(avg_time)
            else:
                avg_time_float = float(avg_time)
            
            # 🛡️ 最終類型驗證：確保是有效的浮點數
            if not isinstance(avg_time_float, (int, float)):
                logger.error("❌ 類型轉換後仍非數值", 
                           result_type=type(avg_time_float).__name__)
                return "unknown"
            
            # 🛡️ 檢查是否為有效數值（不是 NaN 或無限值）
            import math
            if math.isnan(avg_time_float) or math.isinf(avg_time_float):
                logger.warning("檢測到 NaN 或無限值", avg_time=avg_time_float)
                return "unknown"
            
            # 🛡️ 確保為正數
            if avg_time_float < 0:
                logger.warning("檢測到負數時間值", avg_time=avg_time_float)
                return "unknown"
            
            # 🔥 絕對安全的比較：明確轉換為浮點數並比較
            time_ms = float(avg_time_float)  # 最終保護
            
            if time_ms < 50.0:
                return "excellent"
            elif time_ms < 100.0:
                return "good"  
            elif time_ms < 200.0:
                return "fair"
            else:
                return "poor"
                
        except (TypeError, ValueError, OverflowError) as e:
            logger.error("❌ 效能評級比較失敗", 
                        original_avg_time=str(avg_time),
                        original_type=type(avg_time).__name__,
                        error_type=type(e).__name__,
                        error_details=str(e))
            return "unknown"
    
    def _analyze_trend_direction(self, recent_records: List[Dict[str, Any]]) -> str:
        """
        分析趨勢方向
        
        Args:
            recent_records: 最近記錄
            
        Returns:
            str: 趨勢方向
        """
        if len(recent_records) < 10:
            return "insufficient_data"
        
        # 分成兩半分析
        mid_point = len(recent_records) // 2
        first_half = recent_records[mid_point:]  # 較早的記錄
        second_half = recent_records[:mid_point]  # 較晚的記錄
        
        # 🔥 關鍵修復：計算成功率 - 增強類型安全版本
        first_success_count = sum(1 for r in first_half if r["result"] == "success")
        second_success_count = sum(1 for r in second_half if r["result"] == "success")
        
        # 🔥 確保計數為整數
        first_success_count = int(first_success_count)
        second_success_count = int(second_success_count)
        first_half_len = int(len(first_half))
        second_half_len = int(len(second_half))
        
        # 🔥 安全的成功率計算
        try:
            first_success_rate = float(first_success_count) / float(first_half_len) if first_half_len > 0 else 0.0
            second_success_rate = float(second_success_count) / float(second_half_len) if second_half_len > 0 else 0.0
            
            # 🔥 確保成功率為浮點數
            first_success_rate = self._safe_float_conversion(first_success_rate, 0.0)
            second_success_rate = self._safe_float_conversion(second_success_rate, 0.0)
            
            diff = second_success_rate - first_success_rate
            diff = self._safe_float_conversion(diff, 0.0)
            
            # 🔥 使用明確的浮點數比較
            if diff > 0.1:
                return "improving"
            elif diff < -0.1:
                return "declining"
            else:
                return "stable"
                
        except (TypeError, ValueError, ZeroDivisionError) as e:
            logger.warning("趨勢分析計算失敗", 
                         first_count=first_success_count,
                         second_count=second_success_count,
                         error=str(e))
            return "unknown"
    
    def _export_to_csv(self, stats: Dict[str, Any]) -> str:
        """
        匯出為 CSV 格式
        
        Args:
            stats: 統計資料
            
        Returns:
            str: CSV 格式字串
        """
        lines = []
        
        # 標題行
        lines.append("Parser,Success,Failure,Success_Rate,Avg_Confidence,Avg_Parse_Time")
        
        # 資料行
        for parser, data in stats["parser_statistics"].items():
            lines.append(f"{parser},{data['success_count']},{data['failure_count']},"
                        f"{data['success_rate']:.3f},{data['avg_confidence']:.3f},"
                        f"{data['avg_parse_time']:.3f}")
        
        return "\n".join(lines)
    
    def _safe_float_conversion(self, value: Any, default: float = 0.0) -> float:
        """
        安全地將值轉換為浮點數
        
        Args:
            value: 要轉換的值
            default: 轉換失敗時的預設值
            
        Returns:
            float: 轉換後的浮點數
        """
        try:
            if value is None:
                return default
            
            # 如果已經是數值類型
            if isinstance(value, (int, float)):
                return float(value)
            
            # 如果是字串，嘗試轉換
            if isinstance(value, str):
                if value.strip() == '':
                    return default
                return float(value.strip())
                
            # 其他類型嘗試直接轉換
            return float(value)
            
        except (ValueError, TypeError) as e:
            # 增強的錯誤日誌記錄
            logger.warning("數值轉換失敗，使用預設值", 
                        original_value=str(value)[:100],  # 限制長度避免日誌過長
                        original_type=type(value).__name__,
                        default_value=default, 
                        error_type=type(e).__name__,
                        error_message=str(e)[:200],  # 限制錯誤訊息長度
                        conversion_context="float")
            return default
    
    def _safe_duration_conversion(self, duration: Any, default: float = 0.0) -> float:
        """
        安全地將 duration 參數轉換為浮點數
        
        Args:
            duration: 要轉換的 duration 值
            default: 轉換失敗時的預設值
            
        Returns:
            float: 轉換後的浮點數
        """
        try:
            converted = self._safe_float_conversion(duration, default)
            # 確保 duration 為非負數
            return max(0.0, converted)
        except Exception as e:
            logger.debug("Duration 轉換失敗，使用預設值", 
                        duration=str(duration), 
                        default=default, 
                        error=str(e))
            return default
    
    def _safe_confidence_conversion(self, confidence: Any, default: float = 1.0) -> float:
        """
        安全地將 confidence 參數轉換為浮點數
        
        Args:
            confidence: 要轉換的 confidence 值
            default: 轉換失敗時的預設值
            
        Returns:
            float: 轉換後的浮點數（限制在 0.0-1.0 範圍）
        """
        try:
            converted = self._safe_float_conversion(confidence, default)
            # 確保 confidence 在 0.0-1.0 範圍內
            return max(0.0, min(1.0, converted))
        except Exception as e:
            logger.debug("Confidence 轉換失敗，使用預設值", 
                        confidence=str(confidence), 
                        default=default, 
                        error=str(e))
            return default
    
    def _safe_numeric_list_conversion(self, values: List[Any]) -> List[float]:
        """
        安全地將數值列表轉換為浮點數列表
        
        Args:
            values: 要轉換的數值列表
            
        Returns:
            List[float]: 轉換後的浮點數列表（移除無效值）
        """
        if not values:
            return []
        
        converted_values = []
        for value in values:
            if value is not None:
                converted = self._safe_float_conversion(value, None)
                if converted is not None:
                    converted_values.append(converted)
        
        return converted_values
    
    def _validate_statistics_integrity(self) -> Dict[str, Any]:
        """
        驗證統計數據的完整性
        
        Returns:
            Dict[str, Any]: 完整性驗證結果
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "summary": {}
        }
        
        try:
            # 檢查計數器的一致性
            all_parser_types = set(list(self._success_counts.keys()) + list(self._failure_counts.keys()))
            
            for parser_type in all_parser_types:
                success_count = self._success_counts[parser_type]
                failure_count = self._failure_counts[parser_type]
                
                # 檢查信心度記錄數量是否合理
                confidence_count = len(self._confidence_scores[parser_type])
                if confidence_count > success_count:
                    validation_result["warnings"].append(
                        f"Parser {parser_type}: 信心度記錄數({confidence_count}) > 成功次數({success_count})"
                    )
                
                # 檢查時間記錄是否有異常值
                times = self._safe_numeric_list_conversion(self._parse_times[parser_type])
                if times:
                    avg_time = sum(times) / len(times)
                    max_time = max(times)
                    if max_time > avg_time * 10:  # 異常值檢測
                        validation_result["warnings"].append(
                            f"Parser {parser_type}: 發現異常解析時間 {max_time:.2f}ms (平均: {avg_time:.2f}ms)"
                        )
            
            # 檢查歷史記錄的完整性
            if len(self._history) > self._max_history_size:
                validation_result["errors"].append(
                    f"歷史記錄超出最大限制: {len(self._history)} > {self._max_history_size}"
                )
                validation_result["is_valid"] = False
            
            # 生成摘要
            validation_result["summary"] = {
                "total_parsers": len(all_parser_types),
                "total_history_records": len(self._history),
                "uptime_hours": (time.time() - self._start_time) / 3600,
                "data_consistency": "良好" if validation_result["is_valid"] else "需要修復"
            }
            
        except Exception as e:
            validation_result["errors"].append(f"驗證過程中發生錯誤: {str(e)}")
            validation_result["is_valid"] = False
            logger.error("統計數據完整性驗證失敗", error=str(e))
        
        return validation_result
    
    def _get_detailed_conversion_diagnostic(self, value: Any, context: str = "") -> Dict[str, Any]:
        """
        獲取詳細的轉換診斷信息
        
        Args:
            value: 要診斷的值
            context: 轉換的上下文信息
            
        Returns:
            Dict[str, Any]: 詳細診斷信息
        """
        diagnostic = {
            "original_value": str(value),
            "original_type": type(value).__name__,
            "context": context,
            "conversion_successful": False,
            "converted_value": None,
            "error_details": None
        }
        
        try:
            converted = self._safe_float_conversion(value, None)
            if converted is not None:
                diagnostic["conversion_successful"] = True
                diagnostic["converted_value"] = converted
            else:
                diagnostic["error_details"] = "轉換結果為 None"
        except Exception as e:
            diagnostic["error_details"] = str(e)
        
        return diagnostic
    
    def get_service_health(self) -> Dict[str, Any]:
        """
        獲取統計服務的健康狀況
        
        Returns:
            Dict[str, Any]: 服務健康狀況
        """
        try:
            validation_result = self._validate_statistics_integrity()
            
            # 計算基本指標
            total_success = sum(self._success_counts.values())
            total_failure = sum(self._failure_counts.values())
            total_requests = total_success + total_failure
            
            health_status = {
                "status": "healthy" if validation_result["is_valid"] else "degraded",
                "uptime_hours": (time.time() - self._start_time) / 3600,
                "total_requests": total_requests,
                "success_rate": float(total_success) / float(total_requests) if total_requests > 0 else 0.0,
                "data_integrity": validation_result,
                "memory_usage": {
                    "history_size": len(self._history),
                    "max_history_size": self._max_history_size,
                    "usage_percentage": (len(self._history) / self._max_history_size) * 100
                },
                "active_parsers": len(set(list(self._success_counts.keys()) + list(self._failure_counts.keys()))),
                "last_activity": max([r.get("timestamp", 0) for r in self._history]) if self._history else self._start_time
            }
            
            # 添加健康建議
            recommendations = []
            if len(self._history) > self._max_history_size * 0.9:
                recommendations.append("建議考慮清理舊的歷史記錄")
            if total_requests > 0 and (total_success / total_requests) < 0.8:
                recommendations.append("成功率偏低，建議檢查解析器配置")
            if validation_result["warnings"]:
                recommendations.append("發現數據警告，建議檢查統計完整性")
            
            health_status["recommendations"] = recommendations
            
            return health_status
            
        except Exception as e:
            logger.error("獲取服務健康狀況失敗", error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "recommendations": ["服務可能需要重啟"]
            }
    
    # 實現 IStatistics 抽象介面的缺失方法
    
    def record_event(
        self, 
        event_type, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        記錄統計事件（實現 IStatistics 介面）
        
        Args:
            event_type: 事件類型
            metadata: 可選的事件元數據
        """
        try:
            # 將事件類型轉換為字串處理
            event_name = getattr(event_type, 'value', str(event_type))
            
            # 記錄到歷史
            self._history.append({
                "timestamp": time.time(),
                "timestamp_iso": datetime.now().isoformat(),
                "event_type": event_name,
                "result": ("success" if "success" in event_name.lower() else ("failure" if "failure" in event_name.lower() else "info")),
                "metadata": metadata or {}
            })
            
            # 更新相關計數器
            if "success" in event_name.lower():
                parser_type = metadata.get("parser_type", "unknown") if metadata else "unknown"
                self._success_counts[parser_type] += 1
            elif "failure" in event_name.lower():
                parser_type = metadata.get("parser_type", "unknown") if metadata else "unknown"
                self._failure_counts[parser_type] += 1
                
        except Exception as e:
            # 根據契約要求，統計失敗不應影響主流程
            logger.debug("統計事件記錄失敗", event_type=str(event_type), error=str(e))
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """
        獲取統計摘要（實現 IStatistics 介面）
        
        Returns:
            Dict[str, Any]: 統計摘要
        """
        total_success = sum(self._success_counts.values())
        total_failure = sum(self._failure_counts.values())
        total_requests = total_success + total_failure
        
        success_rate = float(total_success) / float(total_requests) if total_requests > 0 else 0.0
        
        # 計算平均回應時間 - 類型安全版本
        all_times = []
        for times in self._parse_times.values():
            # 確保所有時間值都是數值類型
            safe_times = self._safe_numeric_list_conversion(times)
            all_times.extend(safe_times)
        
        avg_response_time = sum(all_times) / len(all_times) if all_times else 0.0
        
        # 錯誤分布
        error_distribution = dict(self._error_types)
        
        return {
            "total_requests": total_requests,
            "success_rate": success_rate,
            "average_response_time": avg_response_time,
            "error_distribution": error_distribution,
            "uptime_seconds": time.time() - self._start_time
        }
    
    def get_detailed_stats(
        self, 
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        operation_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        獲取詳細統計資料（實現 IStatistics 介面）
        
        Args:
            start_time: 開始時間（ISO 格式）
            end_time: 結束時間（ISO 格式）
            operation_type: 過濾的操作類型
            
        Returns:
            Dict[str, Any]: 詳細統計資料
        """
        # 基礎統計（可以根據時間和操作類型過濾，這裡先返回全部）
        return {
            "parser_statistics": {
                parser: {
                    "success_count": self._success_counts[parser],
                    "failure_count": self._failure_counts[parser],
                    "confidence_scores": self._confidence_scores[parser][-100:],  # 最近100個
                    "parse_times": self._parse_times[parser][-100:]  # 最近100個
                }
                for parser in set(list(self._success_counts.keys()) + list(self._failure_counts.keys()))
            },
            "query_type_distribution": dict(self._query_type_stats),
            "recent_history": list(self._history)[-100:],  # 最近100條記錄
            "filter_applied": {
                "start_time": start_time,
                "end_time": end_time,
                "operation_type": operation_type
            }
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        獲取效能指標（實現 IStatistics 介面）
        
        Returns:
            Dict[str, Any]: 效能指標
        """
        return self._get_performance_metrics()
    
    def reset_stats(self) -> None:
        """
        重置統計資料（實現 IStatistics 介面）
        
        注意：此操作會清除所有統計資料，請謹慎使用
        """
        self.clear_statistics()
    
    def export_stats(self, format_type: str = "json") -> str:
        """
        匯出統計資料（實現 IStatistics 介面）
        
        Args:
            format_type: 匯出格式（"json", "csv", "xml"）
            
        Returns:
            str: 格式化的統計資料
        """
        return self.export_statistics(format_type)