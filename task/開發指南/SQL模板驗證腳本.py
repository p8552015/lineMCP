#!/usr/bin/env python3
"""
SQL 模板驗證腳本
用於自動檢查 SQL 模板中的欄位名稱是否與資料庫結構一致
"""

import yaml
import re
import sys
import os
from typing import Dict, List, Set, Tuple
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SQLTemplateValidator:
    """SQL 模板驗證器"""
    
    def __init__(self, database_url: str):
        """
        初始化驗證器
        
        Args:
            database_url: 資料庫連接 URL
        """
        self.database_url = database_url
        self.engine = None
        self.inspector = None
        self.table_columns = {}
        
    def connect_database(self):
        """連接資料庫並獲取結構資訊"""
        try:
            self.engine = create_engine(self.database_url)
            self.inspector = inspect(self.engine)
            
            # 獲取所有表的欄位資訊
            for table_name in self.inspector.get_table_names():
                columns = self.inspector.get_columns(table_name)
                self.table_columns[table_name] = {col['name'] for col in columns}
                
            logger.info(f"成功連接資料庫，發現 {len(self.table_columns)} 個表")
            return True
            
        except Exception as e:
            logger.error(f"資料庫連接失敗: {str(e)}")
            return False
    
    def extract_fields_from_sql(self, sql: str) -> Dict[str, Set[str]]:
        """
        從 SQL 語句中提取欄位名稱
        
        Args:
            sql: SQL 語句
            
        Returns:
            Dict[表名, Set[欄位名稱]]
        """
        # 移除註釋和多餘空白
        sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        sql = ' '.join(sql.split())
        
        # 提取表別名映射
        table_aliases = self._extract_table_aliases(sql)
        
        # 提取欄位引用
        field_references = {}
        
        # 匹配 alias.field_name 格式
        field_pattern = r'\b([a-zA-Z_]\w*)\.([a-zA-Z_]\w*)\b'
        matches = re.findall(field_pattern, sql)
        
        for alias, field in matches:
            if alias in table_aliases:
                table_name = table_aliases[alias]
                if table_name not in field_references:
                    field_references[table_name] = set()
                field_references[table_name].add(field)
        
        return field_references
    
    def _extract_table_aliases(self, sql: str) -> Dict[str, str]:
        """
        提取表別名映射
        
        Args:
            sql: SQL 語句
            
        Returns:
            Dict[別名, 表名]
        """
        aliases = {}
        
        # 匹配 FROM table_name alias 格式
        from_pattern = r'\bFROM\s+([a-zA-Z_]\w*)\s+([a-zA-Z_]\w*)\b'
        matches = re.findall(from_pattern, sql, re.IGNORECASE)
        for table, alias in matches:
            aliases[alias] = table
            
        # 匹配 JOIN table_name alias 格式
        join_pattern = r'\bJOIN\s+([a-zA-Z_]\w*)\s+([a-zA-Z_]\w*)\b'
        matches = re.findall(join_pattern, sql, re.IGNORECASE)
        for table, alias in matches:
            aliases[alias] = table
            
        return aliases
    
    def validate_template_fields(self, template_name: str, sql: str) -> List[str]:
        """
        驗證 SQL 模板中的欄位
        
        Args:
            template_name: 模板名稱
            sql: SQL 語句
            
        Returns:
            List[錯誤訊息]
        """
        errors = []
        
        try:
            # 提取欄位引用
            field_references = self.extract_fields_from_sql(sql)
            
            # 檢查每個欄位是否存在
            for table_name, fields in field_references.items():
                if table_name not in self.table_columns:
                    errors.append(f"表 '{table_name}' 不存在於資料庫中")
                    continue
                    
                table_fields = self.table_columns[table_name]
                for field in fields:
                    if field not in table_fields:
                        # 提供修正建議
                        suggestion = self._suggest_field_correction(field, table_fields)
                        error_msg = f"表 '{table_name}' 中不存在欄位 '{field}'"
                        if suggestion:
                            error_msg += f"，建議使用 '{suggestion}'"
                        errors.append(error_msg)
                        
        except Exception as e:
            errors.append(f"SQL 解析錯誤: {str(e)}")
            
        return errors
    
    def _suggest_field_correction(self, wrong_field: str, available_fields: Set[str]) -> str:
        """
        建議正確的欄位名稱
        
        Args:
            wrong_field: 錯誤的欄位名稱
            available_fields: 可用的欄位名稱集合
            
        Returns:
            建議的欄位名稱
        """
        # 常見錯誤對照表
        common_corrections = {
            'machine_id': 'id',
            'machine_name': 'name',
            'department': 'location'
        }
        
        if wrong_field in common_corrections:
            suggested = common_corrections[wrong_field]
            if suggested in available_fields:
                return suggested
        
        # 模糊匹配
        for field in available_fields:
            if wrong_field.lower() in field.lower() or field.lower() in wrong_field.lower():
                return field
                
        return ""
    
    def test_sql_syntax(self, template_name: str, sql: str) -> List[str]:
        """
        測試 SQL 語法正確性
        
        Args:
            template_name: 模板名稱
            sql: SQL 語句
            
        Returns:
            List[錯誤訊息]
        """
        errors = []
        
        try:
            # 使用 EXPLAIN 來測試語法
            test_sql = f"EXPLAIN {sql}"
            
            # 替換參數佔位符為測試值
            test_sql = re.sub(r':(\w+)', "'test_value'", test_sql)
            
            with self.engine.connect() as conn:
                conn.execute(text(test_sql))
                
        except SQLAlchemyError as e:
            error_msg = str(e)
            if "column" in error_msg.lower() and "does not exist" in error_msg.lower():
                errors.append(f"欄位不存在錯誤: {error_msg}")
            else:
                errors.append(f"SQL 語法錯誤: {error_msg}")
        except Exception as e:
            errors.append(f"未知錯誤: {str(e)}")
            
        return errors
    
    def validate_templates_file(self, templates_file: str) -> Dict[str, List[str]]:
        """
        驗證整個模板檔案
        
        Args:
            templates_file: 模板檔案路徑
            
        Returns:
            Dict[模板名稱, List[錯誤訊息]]
        """
        results = {}
        
        try:
            with open(templates_file, 'r', encoding='utf-8') as f:
                templates = yaml.safe_load(f)
                
            for template_name, template_sql in templates.items():
                errors = []
                
                # 驗證欄位存在性
                field_errors = self.validate_template_fields(template_name, template_sql)
                errors.extend(field_errors)
                
                # 測試 SQL 語法
                syntax_errors = self.test_sql_syntax(template_name, template_sql)
                errors.extend(syntax_errors)
                
                results[template_name] = errors
                
        except Exception as e:
            logger.error(f"讀取模板檔案失敗: {str(e)}")
            return {"file_error": [str(e)]}
            
        return results
    
    def generate_report(self, validation_results: Dict[str, List[str]]) -> str:
        """
        生成驗證報告
        
        Args:
            validation_results: 驗證結果
            
        Returns:
            報告內容
        """
        report = ["# SQL 模板驗證報告", ""]
        
        total_templates = len(validation_results)
        error_templates = sum(1 for errors in validation_results.values() if errors)
        success_templates = total_templates - error_templates
        
        report.extend([
            f"## 總結",
            f"- 總模板數: {total_templates}",
            f"- 通過驗證: {success_templates}",
            f"- 發現錯誤: {error_templates}",
            ""
        ])
        
        if error_templates > 0:
            report.extend(["## 錯誤詳情", ""])
            
            for template_name, errors in validation_results.items():
                if errors:
                    report.append(f"### {template_name}")
                    for error in errors:
                        report.append(f"- ❌ {error}")
                    report.append("")
        
        if success_templates > 0:
            report.extend(["## 通過驗證的模板", ""])
            for template_name, errors in validation_results.items():
                if not errors:
                    report.append(f"- ✅ {template_name}")
        
        return "\n".join(report)

def main():
    """主函數"""
    if len(sys.argv) < 3:
        print("使用方法: python validate_sql_templates.py <database_url> <templates_file>")
        print("範例: python validate_sql_templates.py postgresql://user:pass@localhost/db templates.yaml")
        sys.exit(1)
    
    database_url = sys.argv[1]
    templates_file = sys.argv[2]
    
    if not os.path.exists(templates_file):
        print(f"錯誤: 模板檔案 '{templates_file}' 不存在")
        sys.exit(1)
    
    # 創建驗證器
    validator = SQLTemplateValidator(database_url)
    
    # 連接資料庫
    if not validator.connect_database():
        print("錯誤: 無法連接資料庫")
        sys.exit(1)
    
    # 執行驗證
    print(f"正在驗證 SQL 模板檔案: {templates_file}")
    results = validator.validate_templates_file(templates_file)
    
    # 生成報告
    report = validator.generate_report(results)
    print(report)
    
    # 保存報告到檔案
    report_file = f"sql_validation_report_{os.path.basename(templates_file)}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n報告已保存到: {report_file}")
    
    # 檢查是否有錯誤
    has_errors = any(errors for errors in results.values())
    if has_errors:
        print("\n⚠️  發現錯誤，請檢查並修復後重新驗證")
        sys.exit(1)
    else:
        print("\n✅ 所有模板驗證通過！")
        sys.exit(0)

if __name__ == "__main__":
    main() 