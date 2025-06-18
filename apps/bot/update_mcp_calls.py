#!/usr/bin/env python3
"""
批次更新 message_handler.py 中的 MCP 呼叫
"""

import re

def update_mcp_calls():
    file_path = "src/services/message_handler.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替換 MCP 客戶端呼叫的模式
    patterns = [
        # 模式 1: self.mcp_client.call_tool(server_name="...", tool_name="...", parameters={...})
        (
            r'await self\.mcp_client\.call_tool\(\s*server_name="([^"]+)",\s*tool_name="([^"]+)",\s*parameters=(\{[^}]+\})\s*\)',
            r'await self._call_mcp_tool_compatible("\1", "\2", \3)'
        ),
        # 模式 2: self.mcp_client.call_tool("server", "tool", {...})
        (
            r'await self\.mcp_client\.call_tool\("([^"]+)",\s*"([^"]+)",\s*(\{[^}]+\})\)',
            r'await self._call_mcp_tool_compatible("\1", "\2", \3)'
        ),
        # 模式 3: list_tools 呼叫
        (
            r'await self\.mcp_client\.list_tools\("([^"]+)"\)',
            r'await self.mcp_client.list_tools("\1")'  # 這個保持不變，因為統一客戶端有相同介面
        )
    ]
    
    original_content = content
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
    
    # 檢查是否有變化
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ 已更新 MCP 呼叫")
        
        # 顯示變化的統計
        original_lines = original_content.split('\n')
        new_lines = content.split('\n')
        
        changes = 0
        for i, (old, new) in enumerate(zip(original_lines, new_lines)):
            if old != new:
                changes += 1
                print(f"   行 {i+1}: {old.strip()} -> {new.strip()}")
        
        print(f"📊 總共修改了 {changes} 行")
    else:
        print("ℹ️  沒有找到需要更新的內容")

if __name__ == "__main__":
    update_mcp_calls()