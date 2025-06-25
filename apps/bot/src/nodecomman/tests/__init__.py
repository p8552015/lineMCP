"""
測試套件模組

提供完整的測試覆蓋：
- 單元測試：各個類別的獨立測試
- 整合測試：多組件協作測試
- 功能測試：M001 機台稼動率和所有機台查詢

測試原則：
- 100% 測試覆蓋率
- Mock 外部依賴
- 測試 SOLID 原則合規性
"""

# 測試配置
import os
import sys
from pathlib import Path

# 確保可以導入被測試的模組
test_dir = Path(__file__).parent
src_dir = test_dir.parent
sys.path.insert(0, str(src_dir))

# 測試數據目錄
TEST_DATA_DIR = test_dir / "data"
MOCK_DATA_DIR = test_dir / "mocks"

# 測試配置
TEST_CONFIG = {
    "timeout": 30,
    "retry_count": 3,
    "mock_external_calls": True,
    "enable_logging": True,
}

__all__ = [
    "TEST_DATA_DIR",
    "MOCK_DATA_DIR", 
    "TEST_CONFIG",
]