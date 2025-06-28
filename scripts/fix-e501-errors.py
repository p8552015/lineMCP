#!/usr/bin/env python3
"""
E501 行長度錯誤批量修復腳本

基於 Serena MCP 分析報告中的最佳實踐，使用精確的正規表達式批量修復行長度問題。
"""

import re
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple

def get_e501_errors() -> List[Dict[str, str]]:
    """獲取所有 E501 錯誤"""
    try:
        # 運行 ruff 檢查獲取 E501 錯誤
        result = subprocess.run(
            ["ruff", "check", "src/", "--select", "E501", "--output-format", "text"],
            capture_output=True,
            text=True,
            cwd="/Users/yen/Desktop/lineMCP/apps/bot"
        )
        
        errors = []
        for line in result.stdout.split('\n'):
            if 'E501' in line and ':' in line:
                # 解析錯誤行：file:line:col: E501 message
                parts = line.split(':', 3)
                if len(parts) >= 4:
                    errors.append({
                        'file': parts[0],
                        'line': int(parts[1]),
                        'col': int(parts[2]),
                        'message': parts[3].strip()
                    })
        
        return errors
    except Exception as e:
        print(f"獲取 E501 錯誤失敗: {e}")
        return []

def fix_long_lines(file_path: str, errors: List[Dict]) -> bool:
    """修復特定文件中的長行"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        modified = False
        
        # 按行號排序錯誤（從後往前處理避免行號變化）
        file_errors = [e for e in errors if e['file'] == file_path]
        file_errors.sort(key=lambda x: x['line'], reverse=True)
        
        for error in file_errors:
            line_idx = error['line'] - 1
            if line_idx < len(lines):
                original_line = lines[line_idx]
                fixed_line = fix_single_line(original_line)
                
                if fixed_line != original_line:
                    lines[line_idx] = fixed_line
                    modified = True
                    print(f"修復 {file_path}:{error['line']}")
        
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
        
        return False
    except Exception as e:
        print(f"修復文件 {file_path} 失敗: {e}")
        return False

def fix_single_line(line: str) -> str:
    """修復單行長度問題"""
    # 移除行尾空白
    line = line.rstrip() + '\n'
    
    # 如果行不是太長，直接返回
    if len(line.rstrip()) <= 88:
        return line
    
    # 獲取縮排
    indent = len(line) - len(line.lstrip())
    base_indent = ' ' * indent
    
    # 常見模式修復
    patterns = [
        # logger.error/warning/info 長訊息
        (
            r'(\s*logger\.(error|warning|info|debug)\()([^)]+)(\))',
            lambda m: fix_logger_call(m, base_indent)
        ),
        # raise 長錯誤訊息
        (
            r'(\s*raise\s+\w+\()([^)]+)(\))',
            lambda m: fix_raise_call(m, base_indent)
        ),
        # return TextMessage 長內容
        (
            r'(\s*return\s+TextMessage\s*\()([^)]+)(\))',
            lambda m: fix_text_message(m, base_indent)
        ),
        # recommendations.append 長內容
        (
            r'(\s*recommendations\.append\()([^)]+)(\))',
            lambda m: fix_append_call(m, base_indent)
        ),
        # f-string 長字串
        (
            r'(\s*)(.*f"[^"]{50,}".*)',
            lambda m: fix_long_fstring(m, base_indent)
        ),
        # 函數調用長參數
        (
            r'(\s*)(\w+\([^)]{80,}\))',
            lambda m: fix_long_function_call(m, base_indent)
        )
    ]
    
    for pattern, fix_func in patterns:
        match = re.match(pattern, line, re.DOTALL)
        if match:
            try:
                fixed = fix_func(match)
                if fixed and len(fixed.split('\n')[0].rstrip()) <= 88:
                    return fixed
            except:
                continue
    
    # 如果沒有匹配的模式，嘗試通用分割
    return generic_line_split(line, base_indent)

def fix_logger_call(match, base_indent: str) -> str:
    """修復 logger 調用"""
    prefix = match.group(1)
    content = match.group(3)
    suffix = match.group(4)
    
    # 嘗試在 logger 調用後分行
    return f"{prefix}\n{base_indent}    {content.strip()}\n{base_indent}{suffix}\n"

def fix_raise_call(match, base_indent: str) -> str:
    """修復 raise 調用"""
    prefix = match.group(1)
    content = match.group(2)
    suffix = match.group(3)
    
    return f"{prefix}\n{base_indent}    {content.strip()}\n{base_indent}{suffix}\n"

def fix_text_message(match, base_indent: str) -> str:
    """修復 TextMessage"""
    prefix = match.group(1)
    content = match.group(2)
    suffix = match.group(3)
    
    return f"{prefix}\n{base_indent}    {content.strip()}\n{base_indent}{suffix}\n"

def fix_append_call(match, base_indent: str) -> str:
    """修復 append 調用"""
    prefix = match.group(1)
    content = match.group(2)
    suffix = match.group(3)
    
    return f"{prefix}\n{base_indent}    {content.strip()}\n{base_indent}{suffix}\n"

def fix_long_fstring(match, base_indent: str) -> str:
    """修復長 f-string"""
    indent = match.group(1)
    content = match.group(2)
    
    # 簡單的 f-string 分割
    if 'f"' in content and len(content) > 88:
        return f"{indent}{content}\n"  # 暫時不修改，需要更複雜的邏輯
    
    return f"{indent}{content}\n"

def fix_long_function_call(match, base_indent: str) -> str:
    """修復長函數調用"""
    indent = match.group(1)
    content = match.group(2)
    
    # 暫時不修改複雜的函數調用
    return f"{indent}{content}\n"

def generic_line_split(line: str, base_indent: str) -> str:
    """通用行分割"""
    # 如果無法智能分割，保持原樣
    return line

def main():
    """主函數"""
    print("🔧 開始修復 E501 行長度錯誤...")
    
    # 獲取所有 E501 錯誤
    errors = get_e501_errors()
    print(f"發現 {len(errors)} 個 E501 錯誤")
    
    if not errors:
        print("✅ 沒有發現 E501 錯誤")
        return
    
    # 按文件分組
    files_with_errors = {}
    for error in errors:
        file_path = error['file']
        if file_path not in files_with_errors:
            files_with_errors[file_path] = []
        files_with_errors[file_path].append(error)
    
    # 修復每個文件
    fixed_files = 0
    for file_path in files_with_errors:
        if fix_long_lines(file_path, errors):
            fixed_files += 1
    
    print(f"✅ 修復完成，處理了 {fixed_files} 個文件")
    
    # 重新檢查
    remaining_errors = get_e501_errors()
    print(f"剩餘 {len(remaining_errors)} 個 E501 錯誤")

if __name__ == "__main__":
    main()