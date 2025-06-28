#!/usr/bin/env python3
"""
自動修復 f(( 語法錯誤腳本
"""

import os
import re
import sys

def fix_logger_syntax_errors(file_path):
    """修復文件中的 logger.error(f(( 語法錯誤"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # 修復 f(( 模式的錯誤
    # 模式1: logger.xxx(f(("message"))
    pattern1 = r'(logger\.\w+\(f\(\(\s*"[^"]*"\)\))'
    content = re.sub(pattern1, lambda m: fix_simple_logger_call(m.group(1)), content)
    
    # 模式2: logger.xxx(f((內容跨行
    pattern2 = r'(logger\.\w+\(f\(\(\s*\n\s*"[^"]*"\)\))'
    content = re.sub(pattern2, lambda m: fix_multiline_logger_call(m.group(1)), content, flags=re.MULTILINE)
    
    # 模式3: 更複雜的跨行模式
    pattern3 = r'logger\.(\w+)\(f\(\(\s*\n\s*"([^"]*)"\)\)'
    def fix_complex_multiline(match):
        method = match.group(1)
        message = match.group(2)
        return f'logger.{method}(\n                f"{message}"\n            )'
    content = re.sub(pattern3, fix_complex_multiline, content, flags=re.MULTILINE)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def fix_simple_logger_call(logger_call):
    """修復簡單的 logger 調用"""
    # 提取方法名和消息
    match = re.match(r'logger\.(\w+)\(f\(\("([^"]*)"\)\)', logger_call)
    if match:
        method, message = match.groups()
        return f'logger.{method}(f"{message}")'
    return logger_call

def fix_multiline_logger_call(logger_call):
    """修復跨行的 logger 調用"""
    # 提取方法名和消息
    match = re.match(r'logger\.(\w+)\(f\(\(\s*\n\s*"([^"]*)"\)\)', logger_call, re.MULTILINE)
    if match:
        method, message = match.groups()
        return f'logger.{method}(\n                f"{message}"\n            )'
    return logger_call

def main():
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        # 默認掃描src目錄
        src_dir = "/Users/yen/Desktop/lineMCP/apps/bot/src"
        files = []
        for root, dirs, filenames in os.walk(src_dir):
            for filename in filenames:
                if filename.endswith('.py'):
                    files.append(os.path.join(root, filename))
    
    fixed_files = []
    for file_path in files:
        try:
            if fix_logger_syntax_errors(file_path):
                fixed_files.append(file_path)
                print(f"✅ 修復: {file_path}")
        except Exception as e:
            print(f"❌ 錯誤: {file_path} - {e}")
    
    print(f"\n📊 總計修復 {len(fixed_files)} 個文件")
    return len(fixed_files)

if __name__ == "__main__":
    main()