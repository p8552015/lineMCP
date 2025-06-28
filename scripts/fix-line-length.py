#!/usr/bin/env python3
"""
自動修復行長度問題 (E501) 的腳本
"""
import re
import subprocess
from pathlib import Path

def get_e501_errors():
    """獲取所有E501錯誤"""
    result = subprocess.run([
        "poetry", "run", "ruff", "check", "src/", 
        "--select", "E501", "--output-format=concise"
    ], capture_output=True, text=True, cwd="apps/bot")
    
    errors = []
    for line in result.stdout.split('\n'):
        if ':' in line and 'E501' in line:
            parts = line.split(':')
            if len(parts) >= 3:
                file_path = parts[0]
                line_num = int(parts[1]) 
                errors.append((file_path, line_num, line))
    return errors

def fix_long_string(content, line_num):
    """修復長字串"""
    lines = content.split('\n')
    if line_num > len(lines):
        return content
        
    line = lines[line_num - 1]
    
    # 處理 logger.error/info 等調用
    if 'logger.' in line and ('error(' in line or 'info(' in line or 'warning(' in line):
        # 查找引號內容
        quote_pattern = r'(["\'])([^"\']*)\1'
        matches = list(re.finditer(quote_pattern, line))
        if matches:
            indent = len(line) - len(line.lstrip())
            # 分割長字串
            new_lines = [line[:matches[0].start()] + '(']
            for i, match in enumerate(matches):
                if i == len(matches) - 1:
                    new_lines.append(' ' * (indent + 4) + match.group() + line[match.end():])
                else:
                    new_lines.append(' ' * (indent + 4) + match.group() + ', ')
            new_lines[0] = new_lines[0].rstrip() + '('
            new_lines[-1] = new_lines[-1].rstrip() + ')'
            
            lines[line_num - 1:line_num] = new_lines
            return '\n'.join(lines)
    
    # 處理 TextMessage 調用
    if 'TextMessage(' in line and 'text=' in line:
        indent = len(line) - len(line.lstrip())
        if 'text=' in line:
            # 找到 text= 部分
            text_start = line.find('text=')
            before_text = line[:text_start + 5]
            after_text = line[text_start + 5:]
            
            # 檢查是否有長字串
            if len(after_text) > 50:
                lines[line_num - 1] = before_text + '('
                lines.insert(line_num, ' ' * (indent + 4) + after_text)
                lines.insert(line_num + 1, ' ' * indent + ')')
                return '\n'.join(lines)
    
    # 處理字典中的長字串
    if '": (' in line and any(keyword in line for keyword in ['不帶參數', '顯示系統', '列出所有']):
        indent = len(line) - len(line.lstrip())
        # 分割字典值
        colon_pos = line.find('": (')
        if colon_pos != -1:
            key_part = line[:colon_pos + 4]
            value_part = line[colon_pos + 4:]
            
            # 分割長字串
            strings = re.findall(r'"[^"]*"', value_part)
            if len(strings) > 1:
                new_lines = [key_part]
                for i, s in enumerate(strings):
                    if i == len(strings) - 1:
                        new_lines.append(' ' * (indent + 4) + s)
                    else:
                        new_lines.append(' ' * (indent + 4) + s + ' ')
                new_lines.append(' ' * indent + '),')
                
                lines[line_num - 1:line_num] = new_lines
                return '\n'.join(lines)
    
    return content

def main():
    print("🔧 開始自動修復行長度問題...")
    
    errors = get_e501_errors()
    print(f"發現 {len(errors)} 個E501錯誤")
    
    # 按檔案分組
    files_to_fix = {}
    for file_path, line_num, error_line in errors:
        if file_path not in files_to_fix:
            files_to_fix[file_path] = []
        files_to_fix[file_path].append((line_num, error_line))
    
    fixed_count = 0
    for file_path, error_lines in files_to_fix.items():
        file_obj = Path("apps/bot") / file_path
        if not file_obj.exists():
            continue
            
        print(f"修復 {file_path} ({len(error_lines)} 個錯誤)")
        content = file_obj.read_text(encoding='utf-8')
        
        # 按行號倒序修復，避免行號偏移
        for line_num, error_line in sorted(error_lines, reverse=True):
            new_content = fix_long_string(content, line_num)
            if new_content != content:
                content = new_content
                fixed_count += 1
        
        file_obj.write_text(content, encoding='utf-8')
    
    print(f"✅ 修復完成，共修復 {fixed_count} 個問題")
    
    # 檢查剩餘錯誤
    remaining_errors = get_e501_errors()
    print(f"剩餘 {len(remaining_errors)} 個E501錯誤")

if __name__ == "__main__":
    main()