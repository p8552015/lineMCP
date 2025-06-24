#!/usr/bin/env python3
"""
代碼生命週期管理器
負責監控未使用代碼，實施6個月生命週期管理機制
"""

import os
import ast
import json
import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, asdict
import argparse


@dataclass
class CodeItem:
    """代碼項目追蹤"""
    file_path: str
    item_type: str  # function, class, method, variable
    item_name: str
    line_number: int
    first_detected: str  # ISO格式日期
    last_checked: str
    referenced_count: int
    status: str  # active, unused, deprecated, marked_for_removal
    retention_reason: Optional[str] = None


class CodeLifecycleManager:
    """代碼生命週期管理器"""
    
    def __init__(self, project_root: str, config_file: str = "code_lifecycle.json"):
        self.project_root = Path(project_root)
        self.config_file = self.project_root / config_file
        self.items: Dict[str, CodeItem] = {}
        self.load_tracking_data()
        
    def load_tracking_data(self):
        """載入現有追蹤數據"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item_data in data.get('tracked_items', []):
                    key = f"{item_data['file_path']}:{item_data['item_name']}"
                    self.items[key] = CodeItem(**item_data)
                    
    def save_tracking_data(self):
        """保存追蹤數據"""
        data = {
            'last_updated': datetime.datetime.now().isoformat(),
            'tracked_items': [asdict(item) for item in self.items.values()]
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
    def scan_python_files(self) -> List[Path]:
        """掃描Python文件"""
        python_files = []
        for pattern in ['**/*.py']:
            python_files.extend(self.project_root.glob(pattern))
        
        # 排除測試文件和__pycache__
        return [f for f in python_files 
                if not any(exclude in str(f) for exclude in 
                          ['__pycache__', '.git', '.venv', 'test_', '_test.py'])]
    
    def extract_definitions(self, file_path: Path) -> List[Tuple[str, str, int]]:
        """提取文件中的定義"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            definitions = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not node.name.startswith('_'):  # 排除私有方法
                        definitions.append(('function', node.name, node.lineno))
                elif isinstance(node, ast.ClassDef):
                    definitions.append(('class', node.name, node.lineno))
                elif isinstance(node, ast.AsyncFunctionDef):
                    if not node.name.startswith('_'):
                        definitions.append(('async_function', node.name, node.lineno))
                        
            return definitions
            
        except Exception as e:
            print(f"解析文件失敗 {file_path}: {e}")
            return []
    
    def check_references(self, item_name: str, exclude_file: Path) -> int:
        """檢查代碼項目的引用次數"""
        reference_count = 0
        python_files = self.scan_python_files()
        
        for file_path in python_files:
            if file_path == exclude_file:
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 簡單的文本搜索，可以改進為AST分析
                    reference_count += content.count(item_name)
            except Exception:
                continue
                
        return reference_count
    
    def update_tracking(self):
        """更新追蹤數據"""
        current_date = datetime.datetime.now().isoformat()
        found_items = set()
        
        python_files = self.scan_python_files()
        
        for file_path in python_files:
            relative_path = str(file_path.relative_to(self.project_root))
            definitions = self.extract_definitions(file_path)
            
            for item_type, item_name, line_number in definitions:
                key = f"{relative_path}:{item_name}"
                found_items.add(key)
                
                if key in self.items:
                    # 更新現有項目
                    item = self.items[key]
                    item.last_checked = current_date
                    item.line_number = line_number
                    item.referenced_count = self.check_references(item_name, file_path)
                else:
                    # 新項目
                    ref_count = self.check_references(item_name, file_path)
                    status = 'unused' if ref_count == 0 else 'active'
                    
                    self.items[key] = CodeItem(
                        file_path=relative_path,
                        item_type=item_type,
                        item_name=item_name,
                        line_number=line_number,
                        first_detected=current_date,
                        last_checked=current_date,
                        referenced_count=ref_count,
                        status=status
                    )
        
        # 標記已刪除的項目
        for key, item in self.items.items():
            if key not in found_items and item.status != 'removed':
                item.status = 'removed'
                item.last_checked = current_date
    
    def get_unused_items(self, age_months: int = 6) -> List[CodeItem]:
        """獲取未使用超過指定月數的項目"""
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=age_months * 30)
        
        unused_items = []
        for item in self.items.values():
            if (item.status == 'unused' and 
                datetime.datetime.fromisoformat(item.first_detected) < cutoff_date):
                unused_items.append(item)
                
        return unused_items
    
    def mark_for_retention(self, file_path: str, item_name: str, reason: str):
        """標記代碼保留"""
        key = f"{file_path}:{item_name}"
        if key in self.items:
            self.items[key].retention_reason = reason
            self.items[key].status = 'retained'
            print(f"✅ 已標記保留: {item_name} (原因: {reason})")
        else:
            print(f"❌ 找不到項目: {file_path}:{item_name}")
    
    def generate_report(self) -> str:
        """生成報告"""
        report = []
        report.append("# 代碼生命週期管理報告")
        report.append(f"生成時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 統計數據
        total_items = len(self.items)
        unused_items = [item for item in self.items.values() if item.status == 'unused']
        retained_items = [item for item in self.items.values() if item.status == 'retained']
        old_unused = self.get_unused_items(6)
        
        report.append("## 📊 統計概覽")
        report.append(f"- 總代碼項目: {total_items}")
        report.append(f"- 未使用項目: {len(unused_items)}")
        report.append(f"- 保留項目: {len(retained_items)}")
        report.append(f"- 超過6個月未使用: {len(old_unused)}")
        report.append("")
        
        # 候選移除列表
        if old_unused:
            report.append("## ⚠️ 候選移除項目 (超過6個月未使用)")
            report.append("| 文件 | 項目 | 類型 | 首次檢測 | 行號 |")
            report.append("|:---|:---|:---:|:---:|:---:|")
            
            for item in old_unused:
                age_days = (datetime.datetime.now() - 
                           datetime.datetime.fromisoformat(item.first_detected)).days
                report.append(f"| {item.file_path} | `{item.item_name}` | {item.item_type} | {age_days}天前 | {item.line_number} |")
            report.append("")
        
        # 保留項目
        if retained_items:
            report.append("## 🔒 已保留項目")
            report.append("| 文件 | 項目 | 保留原因 |")
            report.append("|:---|:---|:---|")
            
            for item in retained_items:
                report.append(f"| {item.file_path} | `{item.item_name}` | {item.retention_reason} |")
            report.append("")
        
        # 建議行動
        report.append("## 🔧 建議行動")
        if old_unused:
            report.append("1. **審查候選移除項目**: 確認是否為預留功能")
            report.append("2. **標記保留理由**: 使用 `mark_retention` 命令")
            report.append("3. **安全移除**: 對於確認無用的代碼，建議移除")
        else:
            report.append("✅ 當前沒有候選移除項目")
        
        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description='代碼生命週期管理器')
    parser.add_argument('--project-root', default='.', help='專案根目錄')
    parser.add_argument('--scan', action='store_true', help='掃描並更新追蹤數據')
    parser.add_argument('--report', action='store_true', help='生成報告')
    parser.add_argument('--mark-retention', nargs=3, 
                       metavar=('FILE', 'ITEM', 'REASON'),
                       help='標記保留項目')
    
    args = parser.parse_args()
    
    manager = CodeLifecycleManager(args.project_root)
    
    if args.scan:
        print("🔍 掃描代碼項目...")
        manager.update_tracking()
        manager.save_tracking_data()
        print(f"✅ 掃描完成，追蹤 {len(manager.items)} 個項目")
    
    if args.mark_retention:
        file_path, item_name, reason = args.mark_retention
        manager.mark_for_retention(file_path, item_name, reason)
        manager.save_tracking_data()
    
    if args.report:
        report = manager.generate_report()
        
        # 保存報告
        report_file = Path(args.project_root) / f"code_lifecycle_report_{datetime.datetime.now().strftime('%Y%m%d')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"📊 報告已生成: {report_file}")
        print("\n" + report)


if __name__ == "__main__":
    main()