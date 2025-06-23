#!/usr/bin/env python3
"""
程式碼清理安全檢查器
在刪除代碼前進行多重安全驗證，確保零風險操作
"""

import ast
import os
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
import json

class SafetyChecker:
    def __init__(self, project_root: str = "/Users/yen/Desktop/lineMCP"):
        self.project_root = Path(project_root)
        self.apps_bot = self.project_root / "apps" / "bot"
        self.source_dirs = [
            self.apps_bot / "src",
            self.apps_bot / "tests",
            self.project_root / "apps" / "servers"
        ]
        
    def check_method_safety(self, file_path: str, method_name: str) -> Dict:
        """檢查特定方法的刪除安全性"""
        print(f"🔍 檢查方法安全性: {file_path}::{method_name}")
        
        result = {
            "safe_to_delete": False,
            "references": [],
            "risks": [],
            "recommendations": []
        }
        
        # 1. 全域搜索引用
        references = self._find_all_references(method_name)
        result["references"] = references
        
        # 2. 檢查動態調用
        dynamic_calls = self._check_dynamic_calls(method_name)
        if dynamic_calls:
            result["risks"].append(f"發現動態調用: {dynamic_calls}")
        
        # 3. 檢查裝飾器使用
        decorator_usage = self._check_decorator_usage(file_path, method_name)
        if decorator_usage:
            result["risks"].append(f"可能的裝飾器使用: {decorator_usage}")
        
        # 4. 檢查測試依賴
        test_deps = self._check_test_dependencies(method_name)
        if test_deps:
            result["risks"].append(f"測試依賴: {test_deps}")
        
        # 5. 檢查配置引用
        config_refs = self._check_config_references(method_name)
        if config_refs:
            result["risks"].append(f"配置引用: {config_refs}")
        
        # 6. 安全性評估
        if not references and not result["risks"]:
            result["safe_to_delete"] = True
            result["recommendations"].append("✅ 可以安全刪除")
        elif len(references) == 1 and references[0]["file"] == file_path:
            result["safe_to_delete"] = True
            result["recommendations"].append("✅ 僅在定義檔案中發現，可以安全刪除")
        else:
            result["safe_to_delete"] = False
            result["recommendations"].append("⚠️ 發現引用或風險，需要進一步檢查")
        
        return result
    
    def _find_all_references(self, method_name: str) -> List[Dict]:
        """在所有源碼中搜索方法引用"""
        references = []
        
        # 搜索模式
        patterns = [
            rf"\b{method_name}\s*\(",  # 直接調用
            rf"\.{method_name}\s*\(",  # 對象方法調用
            rf"'{method_name}'",       # 字串引用
            rf'"{method_name}"',       # 雙引號字串引用
            rf"getattr.*{method_name}",  # 動態獲取
        ]
        
        for source_dir in self.source_dirs:
            if not source_dir.exists():
                continue
                
            for pattern in patterns:
                try:
                    # 使用 ripgrep 進行高效搜索
                    result = subprocess.run([
                        "rg", "-n", "--type", "py", pattern, str(source_dir)
                    ], capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        for line in result.stdout.strip().split('\n'):
                            if ':' in line:
                                file_path, line_num, content = line.split(':', 2)
                                references.append({
                                    "file": file_path,
                                    "line": int(line_num),
                                    "content": content.strip(),
                                    "pattern": pattern
                                })
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    # 如果 ripgrep 不可用，使用 grep
                    self._fallback_grep_search(source_dir, pattern, references)
        
        return self._deduplicate_references(references)
    
    def _fallback_grep_search(self, source_dir: Path, pattern: str, references: List[Dict]):
        """備用的 grep 搜索"""
        try:
            result = subprocess.run([
                "grep", "-rn", "--include=*.py", pattern, str(source_dir)
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if ':' in line:
                        parts = line.split(':', 2)
                        if len(parts) >= 3:
                            references.append({
                                "file": parts[0],
                                "line": int(parts[1]),
                                "content": parts[2].strip(),
                                "pattern": pattern
                            })
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    
    def _deduplicate_references(self, references: List[Dict]) -> List[Dict]:
        """去除重複的引用"""
        seen = set()
        unique_refs = []
        
        for ref in references:
            key = (ref["file"], ref["line"])
            if key not in seen:
                seen.add(key)
                unique_refs.append(ref)
        
        return unique_refs
    
    def _check_dynamic_calls(self, method_name: str) -> List[str]:
        """檢查動態方法調用"""
        dynamic_patterns = [
            rf"getattr\([^,]+,\s*['\"]?{method_name}['\"]?",
            rf"hasattr\([^,]+,\s*['\"]?{method_name}['\"]?",
            rf"__getattribute__.*{method_name}",
            rf"globals\(\)\[.*{method_name}",
        ]
        
        found = []
        for source_dir in self.source_dirs:
            if not source_dir.exists():
                continue
                
            for pattern in dynamic_patterns:
                try:
                    result = subprocess.run([
                        "rg", "-n", "--type", "py", pattern, str(source_dir)
                    ], capture_output=True, text=True, timeout=15)
                    
                    if result.returncode == 0 and result.stdout.strip():
                        found.append(f"Pattern: {pattern}")
                except:
                    pass
        
        return found
    
    def _check_decorator_usage(self, file_path: str, method_name: str) -> List[str]:
        """檢查裝飾器使用情況"""
        decorators_found = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析 AST
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == method_name:
                    if node.decorator_list:
                        for decorator in node.decorator_list:
                            if isinstance(decorator, ast.Name):
                                decorators_found.append(decorator.id)
                            elif isinstance(decorator, ast.Attribute):
                                decorators_found.append(f"{decorator.attr}")
        except:
            pass
        
        return decorators_found
    
    def _check_test_dependencies(self, method_name: str) -> List[str]:
        """檢查測試檔案中的依賴"""
        test_deps = []
        test_dir = self.apps_bot / "tests"
        
        if test_dir.exists():
            try:
                result = subprocess.run([
                    "rg", "-n", "--type", "py", method_name, str(test_dir)
                ], capture_output=True, text=True, timeout=15)
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    test_deps = [f"Found in {len(lines)} test files"]
            except:
                pass
        
        return test_deps
    
    def _check_config_references(self, method_name: str) -> List[str]:
        """檢查配置檔案中的引用"""
        config_refs = []
        config_files = [
            "*.yaml", "*.yml", "*.json", "*.toml", "*.ini", "*.conf"
        ]
        
        for pattern in config_files:
            try:
                result = subprocess.run([
                    "find", str(self.project_root), "-name", pattern, "-exec", 
                    "grep", "-l", method_name, "{}", ";"
                ], capture_output=True, text=True, timeout=15)
                
                if result.returncode == 0 and result.stdout.strip():
                    config_refs.append(f"Found in config files: {pattern}")
            except:
                pass
        
        return config_refs
    
    def generate_cleanup_plan(self, cleanup_targets: List[Dict]) -> Dict:
        """生成清理執行計劃"""
        plan = {
            "safe_items": [],
            "risky_items": [],
            "blocked_items": [],
            "total_items": len(cleanup_targets)
        }
        
        for target in cleanup_targets:
            file_path = target["file"]
            method_name = target["method"]
            
            safety_check = self.check_method_safety(file_path, method_name)
            
            target_info = {
                "file": file_path,
                "method": method_name,
                "safety_check": safety_check
            }
            
            if safety_check["safe_to_delete"]:
                plan["safe_items"].append(target_info)
            elif len(safety_check["risks"]) > 0:
                plan["blocked_items"].append(target_info)
            else:
                plan["risky_items"].append(target_info)
        
        return plan
    
    def backup_files(self, file_paths: List[str]) -> bool:
        """備份要修改的檔案"""
        backup_dir = self.project_root / "backups" / "code_cleanup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            for file_path in file_paths:
                src = Path(file_path)
                if src.exists():
                    # 保持相對路徑結構
                    rel_path = src.relative_to(self.project_root)
                    dst = backup_dir / rel_path
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    
                    # 複製檔案
                    import shutil
                    shutil.copy2(src, dst)
                    print(f"✅ 備份: {file_path} -> {dst}")
            
            return True
        except Exception as e:
            print(f"❌ 備份失敗: {e}")
            return False
    
    def validate_syntax(self, file_path: str) -> bool:
        """驗證Python語法正確性"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            ast.parse(content)
            return True
        except SyntaxError as e:
            print(f"❌ 語法錯誤 {file_path}: {e}")
            return False
        except Exception as e:
            print(f"❌ 檔案檢查錯誤 {file_path}: {e}")
            return False

class CleanupExecutor:
    def __init__(self, project_root: str = "/Users/yen/Desktop/lineMCP"):
        self.project_root = Path(project_root)
        self.safety_checker = SafetyChecker(project_root)
        
    def remove_method_safely(self, file_path: str, method_name: str) -> bool:
        """安全地移除方法"""
        print(f"🗑️ 準備移除方法: {file_path}::{method_name}")
        
        # 1. 安全性檢查
        safety_check = self.safety_checker.check_method_safety(file_path, method_name)
        if not safety_check["safe_to_delete"]:
            print(f"❌ 不安全移除: {safety_check['risks']}")
            return False
        
        # 2. 備份檔案
        if not self.safety_checker.backup_files([file_path]):
            return False
        
        # 3. 移除方法
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析AST並移除指定方法
            tree = ast.parse(content)
            new_content = self._remove_method_from_content(content, method_name)
            
            # 4. 驗證語法
            try:
                ast.parse(new_content)
            except SyntaxError:
                print(f"❌ 移除後語法錯誤，操作取消")
                return False
            
            # 5. 寫入檔案
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"✅ 成功移除方法: {method_name}")
            return True
            
        except Exception as e:
            print(f"❌ 移除方法失敗: {e}")
            return False
    
    def _remove_method_from_content(self, content: str, method_name: str) -> str:
        """從內容中移除指定方法"""
        lines = content.split('\n')
        new_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # 檢查是否為方法定義行
            if re.match(rf'\s*def\s+{method_name}\s*\(', line):
                # 跳過方法的所有行（包括裝飾器和文檔字串）
                
                # 先往回找裝飾器
                j = i - 1
                while j >= 0 and (lines[j].strip().startswith('@') or lines[j].strip() == ''):
                    j -= 1
                
                # 從裝飾器開始刪除（如果有的話）
                start_line = j + 1 if j >= 0 else i
                
                # 找到方法結束位置
                indent_level = len(line) - len(line.lstrip())
                i += 1
                
                # 跳過方法體
                while i < len(lines):
                    current_line = lines[i]
                    if current_line.strip() == '':
                        i += 1
                        continue
                    
                    current_indent = len(current_line) - len(current_line.lstrip())
                    if current_indent <= indent_level and current_line.strip():
                        break
                    i += 1
                
                # 移除從 start_line 到 i 的所有行
                # 但保留最後的換行以維持格式
                continue
            else:
                new_lines.append(line)
                i += 1
        
        return '\n'.join(new_lines)

def main():
    """主執行函數"""
    checker = SafetyChecker()
    
    # 定義要檢查的清理目標
    cleanup_targets = [
        {"file": "/Users/yen/Desktop/lineMCP/apps/bot/src/services/database_service.py", "method": "test_connection"},
        {"file": "/Users/yen/Desktop/lineMCP/apps/bot/src/services/database_service.py", "method": "get_table_info"},
        {"file": "/Users/yen/Desktop/lineMCP/apps/bot/src/utils/observability.py", "method": "get_telemetry_health"},
        {"file": "/Users/yen/Desktop/lineMCP/apps/bot/src/utils/redis_client.py", "method": "get_cached_value"},
        {"file": "/Users/yen/Desktop/lineMCP/apps/bot/src/utils/redis_client.py", "method": "set_cached_value"},
    ]
    
    # 生成清理計劃
    plan = checker.generate_cleanup_plan(cleanup_targets)
    
    print("📋 程式碼清理安全檢查報告")
    print("=" * 50)
    print(f"總計項目: {plan['total_items']}")
    print(f"✅ 安全清理: {len(plan['safe_items'])}")
    print(f"⚠️ 需謹慎: {len(plan['risky_items'])}")
    print(f"❌ 禁止清理: {len(plan['blocked_items'])}")
    
    # 輸出詳細報告
    if plan['safe_items']:
        print("\n✅ 可安全清理的項目:")
        for item in plan['safe_items']:
            print(f"  - {item['file']}::{item['method']}")
    
    if plan['risky_items']:
        print("\n⚠️ 需謹慎處理的項目:")
        for item in plan['risky_items']:
            print(f"  - {item['file']}::{item['method']}")
            for risk in item['safety_check']['risks']:
                print(f"    風險: {risk}")
    
    if plan['blocked_items']:
        print("\n❌ 禁止清理的項目:")
        for item in plan['blocked_items']:
            print(f"  - {item['file']}::{item['method']}")
            for risk in item['safety_check']['risks']:
                print(f"    原因: {risk}")
    
    # 保存報告
    report_file = "/Users/yen/Desktop/lineMCP/cleanup_safety_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 詳細報告已保存至: {report_file}")

if __name__ == "__main__":
    main()