#!/usr/bin/env python3
"""
設定 mcp_common 模組的 Python 路徑
這個檔案應在專案開始時執行，確保可以正確導入 mcp_common
"""

import sys
import os

# 添加 mcp_common 模組路徑
mcp_common_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'libs', 'python'
)

if mcp_common_path not in sys.path:
    sys.path.insert(0, mcp_common_path)
    print(f"✅ 已添加 mcp_common 路徑: {mcp_common_path}")

# 測試導入
try:
    from mcp_common import get_mcp_client
    from mcp_common.unified_client import get_simple_mcp_client
    print("✅ mcp_common 模組導入成功")
except ImportError as e:
    print(f"❌ mcp_common 模組導入失敗: {e}")
    sys.exit(1)

if __name__ == "__main__":
    print("🚀 MCP Common 模組設定完成")
    print("現在可以使用:")
    print("  from mcp_common.unified_client import get_simple_mcp_client")
    print("  from mcp_common import get_mcp_client")