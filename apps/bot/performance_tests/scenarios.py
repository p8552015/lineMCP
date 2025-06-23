"""
效能測試場景配置
定義不同的測試場景和配置
"""

from typing import Dict, List, Any


class PerformanceScenarios:
    """效能測試場景定義"""
    
    @staticmethod
    def get_load_test_config() -> Dict[str, Any]:
        """負載測試配置"""
        return {
            "name": "load_test",
            "description": "標準負載測試",
            "users": 10,
            "spawn_rate": 2,
            "run_time": "5m",
            "thresholds": {
                "p95_response_time_ms": 2000,
                "p99_response_time_ms": 5000,
                "error_rate_percent": 1.0
            }
        }
    
    @staticmethod
    def get_stress_test_config() -> Dict[str, Any]:
        """壓力測試配置"""
        return {
            "name": "stress_test", 
            "description": "壓力極限測試",
            "users": 50,
            "spawn_rate": 5,
            "run_time": "10m",
            "thresholds": {
                "p95_response_time_ms": 5000,
                "p99_response_time_ms": 10000,
                "error_rate_percent": 5.0
            }
        }
    
    @staticmethod
    def get_spike_test_config() -> Dict[str, Any]:
        """峰值測試配置"""
        return {
            "name": "spike_test",
            "description": "峰值流量測試",
            "users": 100,
            "spawn_rate": 10,
            "run_time": "3m", 
            "thresholds": {
                "p95_response_time_ms": 8000,
                "p99_response_time_ms": 15000,
                "error_rate_percent": 10.0
            }
        }
    
    @staticmethod
    def get_endurance_test_config() -> Dict[str, Any]:
        """耐久性測試配置"""
        return {
            "name": "endurance_test",
            "description": "長時間穩定性測試",
            "users": 20,
            "spawn_rate": 2,
            "run_time": "30m",
            "thresholds": {
                "p95_response_time_ms": 2500,
                "p99_response_time_ms": 6000,
                "error_rate_percent": 2.0
            }
        }
    
    @staticmethod
    def get_quick_test_config() -> Dict[str, Any]:
        """快速測試配置 - 用於 CI/CD"""
        return {
            "name": "quick_test",
            "description": "CI/CD 快速驗證測試",
            "users": 5,
            "spawn_rate": 1,
            "run_time": "1m",
            "thresholds": {
                "p95_response_time_ms": 1500,
                "p99_response_time_ms": 3000,
                "error_rate_percent": 0.5
            }
        }


class TestQueries:
    """測試查詢模板"""
    
    NATURAL_LANGUAGE_QUERIES = [
        "查看所有機台",
        "M001機台稼動率",
        "M002機台狀態", 
        "顯示生產統計",
        "機台效率排行",
        "查詢故障記錄",
        "今日產量統計",
        "設備維護提醒",
        "異常警報查詢",
        "效率分析報告",
        "查看昨日產量",
        "機台M003運轉狀態",
        "顯示所有部門效率",
        "查詢本週故障次數",
        "分析生產趨勢"
    ]
    
    SQL_QUERIES = [
        "SELECT * FROM machines LIMIT 10",
        "SELECT machine_id, name, status FROM machines",
        "SELECT COUNT(*) FROM production_data",
        "SELECT AVG(efficiency_rate) FROM production_data WHERE machine_id = 'M001'",
        "SELECT machine_id, SUM(good_count) FROM production_data GROUP BY machine_id",
        "SELECT * FROM machines WHERE status = 'running'",
        "SELECT DATE(record_time), AVG(utilization_rate) FROM production_data GROUP BY DATE(record_time)",
        "SELECT machine_id, MAX(efficiency_rate) FROM production_data GROUP BY machine_id",
        "SELECT COUNT(*) FROM production_data WHERE good_count > 1000",
        "SELECT * FROM production_data ORDER BY record_time DESC LIMIT 5"
    ]
    
    COMMANDS = [
        "/help",
        "/status",
        "/info", 
        "/tables",
        "/models",
        "/health",
        "/version"
    ]
    
    COMPLEX_QUERIES = [
        "分析過去一週M001機台的效率趨勢，並與M002做比較",
        "查詢所有機台中良品率超過95%的設備，按效率排序",
        "統計本月各部門的總產量和平均效率，生成排行榜",
        "找出最近7天故障超過2次的機台，分析故障原因",
        "比較各機台的稼動率變化趨勢，識別效率下降的設備"
    ]


class PerformanceMetrics:
    """效能指標定義"""
    
    @staticmethod
    def get_response_time_targets() -> Dict[str, int]:
        """回應時間目標 (毫秒)"""
        return {
            "health_check": 100,
            "metrics": 200,
            "simple_query": 1000,
            "complex_query": 3000,
            "sql_query": 2000,
            "webhook": 2000
        }
    
    @staticmethod
    def get_throughput_targets() -> Dict[str, int]:
        """吞吐量目標 (每秒請求數)"""
        return {
            "health_check": 100,
            "metrics": 50,
            "webhook": 20,
            "concurrent_queries": 10
        }
    
    @staticmethod
    def get_resource_limits() -> Dict[str, Any]:
        """資源使用限制"""
        return {
            "max_memory_mb": 512,
            "max_cpu_percent": 80,
            "max_disk_io_mb": 100,
            "max_network_mb": 50
        }
    
    @staticmethod
    def get_stability_requirements() -> Dict[str, Any]:
        """穩定性要求"""
        return {
            "max_error_rate_percent": 1.0,
            "max_timeout_rate_percent": 0.5,
            "min_uptime_percent": 99.9,
            "max_memory_leak_mb_per_hour": 10
        }