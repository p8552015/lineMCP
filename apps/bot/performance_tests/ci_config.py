"""
CI/CD 環境的效能測試配置
針對 GitHub Actions 環境優化的輕量級測試配置
"""

# CI 環境效能測試配置
CI_PERFORMANCE_CONFIG = {
    "users": 3,              # CI 環境用較少用戶數
    "spawn_rate": 1,         # 每秒啟動 1 個用戶
    "run_time": "60s",       # 執行 60 秒（PR 模式）
    "host": "http://localhost:8000",
    
    # 測試場景權重調整（CI 環境）
    "test_weights": {
        "health_check": 40,     # 健康檢查佔主要比重
        "basic_endpoints": 30,   # 基本端點測試
        "simple_queries": 20,    # 簡單查詢
        "error_handling": 10     # 錯誤處理測試
    },
    
    # 效能閾值（CI 環境較寬鬆）
    "thresholds": {
        "max_response_time_ms": 3000,
        "p95_response_time_ms": 2000,
        "max_error_rate_percent": 5.0,
        "min_requests_per_second": 10
    },
    
    # 測試輸出配置
    "output": {
        "html_report": True,
        "csv_stats": True,
        "json_stats": True,
        "console_stats": True
    }
}

# 本地開發環境配置
LOCAL_PERFORMANCE_CONFIG = {
    "users": 10,
    "spawn_rate": 2,
    "run_time": "300s",
    "host": "http://localhost:8000",
    
    "test_weights": {
        "health_check": 20,
        "basic_endpoints": 25,
        "simple_queries": 30,
        "complex_queries": 15,
        "error_handling": 10
    },
    
    "thresholds": {
        "max_response_time_ms": 2000,
        "p95_response_time_ms": 1000,
        "max_error_rate_percent": 2.0,
        "min_requests_per_second": 20
    },
    
    "output": {
        "html_report": True,
        "csv_stats": True,
        "json_stats": True,
        "console_stats": True
    }
}

def get_config(environment="ci"):
    """根據環境獲取配置"""
    if environment.lower() == "local":
        return LOCAL_PERFORMANCE_CONFIG
    else:
        return CI_PERFORMANCE_CONFIG