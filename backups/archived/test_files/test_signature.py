#!/usr/bin/env python3
"""
測試簽名驗證器在開發環境的行為
"""

import sys
import os

# 設置工作目錄到 apps/bot
bot_dir = os.path.join(os.path.dirname(__file__), 'apps', 'bot')
os.chdir(bot_dir)

# 添加 src 目錄到 Python 路徑
sys.path.insert(0, 'src')

from src.config import get_settings
from src.utils.signature_validator import SignatureValidator

def test_signature_validator():
    """測試簽名驗證器"""
    print("🔧 測試簽名驗證器...")
    
    # 獲取設定
    settings = get_settings()
    print(f"環境設定: {settings.app_env}")
    print(f"DEBUG 模式: {settings.app_debug}")
    
    # 創建簽名驗證器
    validator = SignatureValidator(settings.line_channel_secret, settings.app_env)
    print(f"開發環境模式: {validator.is_development}")
    
    # 測試開發環境特殊簽名
    test_body = b'{"events": [{"type": "message"}]}'
    
    print("\n📝 測試開發環境特殊簽名:")
    is_valid, method = validator.validate(test_body, "DEV_BYPASS_SIGNATURE")
    print(f"結果: {is_valid}, 方法: {method}")
    
    print("\n📝 測試空簽名:")
    is_valid, method = validator.validate(test_body, "")
    print(f"結果: {is_valid}, 方法: {method}")
    
    print("\n📝 測試普通簽名:")
    is_valid, method = validator.validate(test_body, "invalid_signature")
    print(f"結果: {is_valid}, 方法: {method}")

if __name__ == "__main__":
    test_signature_validator() 