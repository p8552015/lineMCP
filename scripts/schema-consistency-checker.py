#!/usr/bin/env python3
"""
Schema 一致性檢查器
檢查實際資料庫 Schema 與期望規範的一致性
"""

import asyncio
import asyncpg
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SchemaValidationResult:
    """Schema 驗證結果"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    summary: Dict[str, Any]


@dataclass  
class ColumnInfo:
    """欄位資訊"""
    name: str
    data_type: str
    is_nullable: bool
    column_default: Optional[str]
    is_primary_key: bool


@dataclass
class TableInfo:
    """表格資訊"""
    name: str
    columns: List[ColumnInfo]
    primary_key: Optional[str]
    foreign_keys: List[Dict[str, str]]
    indexes: List[Dict[str, Any]]


class SchemaConsistencyChecker:
    """Schema 一致性檢查器"""
    
    def __init__(self, database_url: str, expected_schema_path: str):
        self.database_url = database_url
        self.expected_schema_path = expected_schema_path
        self.expected_schema: Dict[str, Any] = {}
        self.actual_schema: Dict[str, TableInfo] = {}
        
    async def load_expected_schema(self) -> None:
        """載入期望的 Schema 規範"""
        try:
            with open(self.expected_schema_path, 'r', encoding='utf-8') as f:
                self.expected_schema = json.load(f)
        except FileNotFoundError:
            raise Exception(f"期望 Schema 檔案不存在: {self.expected_schema_path}")
        except json.JSONDecodeError as e:
            raise Exception(f"期望 Schema 檔案格式錯誤: {e}")
    
    async def fetch_actual_schema(self) -> None:
        """取得實際資料庫 Schema"""
        conn = await asyncpg.connect(self.database_url)
        try:
            # 取得所有表格名稱
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            
            for table_row in tables:
                table_name = table_row['table_name']
                table_info = await self._fetch_table_info(conn, table_name)
                self.actual_schema[table_name] = table_info
                
        finally:
            await conn.close()
    
    async def _fetch_table_info(self, conn: asyncpg.Connection, table_name: str) -> TableInfo:
        """取得特定表格的詳細資訊"""
        
        # 取得欄位資訊
        columns_query = """
            SELECT 
                c.column_name,
                c.data_type,
                c.is_nullable::boolean,
                c.column_default,
                CASE WHEN tc.constraint_type = 'PRIMARY KEY' THEN true ELSE false END as is_primary_key
            FROM information_schema.columns c
            LEFT JOIN information_schema.key_column_usage kcu 
                ON c.table_name = kcu.table_name AND c.column_name = kcu.column_name
            LEFT JOIN information_schema.table_constraints tc 
                ON kcu.constraint_name = tc.constraint_name AND tc.constraint_type = 'PRIMARY KEY'
            WHERE c.table_name = $1 AND c.table_schema = 'public'
            ORDER BY c.ordinal_position
        """
        
        column_rows = await conn.fetch(columns_query, table_name)
        columns = []
        primary_key = None
        
        for row in column_rows:
            column = ColumnInfo(
                name=row['column_name'],
                data_type=row['data_type'],
                is_nullable=row['is_nullable'],
                column_default=row['column_default'],
                is_primary_key=row['is_primary_key']
            )
            columns.append(column)
            
            if column.is_primary_key:
                primary_key = column.name
        
        # 取得外鍵資訊
        foreign_keys_query = """
            SELECT 
                kcu.column_name,
                ccu.table_name AS references_table,
                ccu.column_name AS references_column
            FROM information_schema.key_column_usage kcu
            JOIN information_schema.table_constraints tc 
                ON kcu.constraint_name = tc.constraint_name
            JOIN information_schema.constraint_column_usage ccu 
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND kcu.table_name = $1
        """
        
        fk_rows = await conn.fetch(foreign_keys_query, table_name)
        foreign_keys = [
            {
                'column': row['column_name'],
                'references_table': row['references_table'],
                'references_column': row['references_column']
            }
            for row in fk_rows
        ]
        
        # 取得索引資訊
        indexes_query = """
            SELECT 
                i.relname as index_name,
                array_agg(a.attname ORDER BY a.attnum) as column_names
            FROM pg_class t
            JOIN pg_index ix ON t.oid = ix.indrelid
            JOIN pg_class i ON i.oid = ix.indexrelid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
            WHERE t.relname = $1
                AND t.relkind = 'r'
                AND i.relname NOT LIKE '%_pkey'
            GROUP BY i.relname
            ORDER BY i.relname
        """
        
        index_rows = await conn.fetch(indexes_query, table_name)
        indexes = [
            {
                'name': row['index_name'],
                'columns': list(row['column_names'])
            }
            for row in index_rows
        ]
        
        return TableInfo(
            name=table_name,
            columns=columns,
            primary_key=primary_key,
            foreign_keys=foreign_keys,
            indexes=indexes
        )
    
    async def validate_schema(self) -> SchemaValidationResult:
        """驗證 Schema 一致性"""
        errors = []
        warnings = []
        suggestions = []
        
        expected_tables = self.expected_schema.get('tables', {})
        
        # 檢查缺少的表格
        for table_name in expected_tables.keys():
            if table_name not in self.actual_schema:
                errors.append(f"❌ 缺少必需的表格: {table_name}")
                suggestions.append(f"💡 建議: 在資料庫中創建 {table_name} 表格")
        
        # 檢查多餘的表格
        for table_name in self.actual_schema.keys():
            if table_name not in expected_tables:
                warnings.append(f"⚠️  發現未定義的表格: {table_name}")
        
        # 檢查表格結構
        for table_name, expected_table in expected_tables.items():
            if table_name in self.actual_schema:
                table_errors, table_warnings, table_suggestions = self._validate_table_structure(
                    table_name, expected_table, self.actual_schema[table_name]
                )
                errors.extend(table_errors)
                warnings.extend(table_warnings)
                suggestions.extend(table_suggestions)
        
        # 生成摘要
        summary = {
            'total_tables_expected': len(expected_tables),
            'total_tables_actual': len(self.actual_schema),
            'missing_tables': len([e for e in errors if '缺少必需的表格' in e]),
            'extra_tables': len([w for w in warnings if '發現未定義的表格' in w]),
            'total_errors': len(errors),
            'total_warnings': len(warnings),
            'validation_timestamp': datetime.now().isoformat(),
            'schema_version': self.expected_schema.get('version', 'unknown')
        }
        
        return SchemaValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            summary=summary
        )
    
    def _validate_table_structure(
        self, 
        table_name: str, 
        expected_table: Dict[str, Any], 
        actual_table: TableInfo
    ) -> Tuple[List[str], List[str], List[str]]:
        """驗證單一表格結構"""
        errors = []
        warnings = []
        suggestions = []
        
        # 檢查主鍵
        expected_pk = expected_table.get('primary_key')
        if expected_pk != actual_table.primary_key:
            errors.append(
                f"❌ {table_name} 主鍵不匹配: 期望 {expected_pk}, 實際 {actual_table.primary_key}"
            )
            suggestions.append(
                f"💡 建議: 修改 {table_name} 表的主鍵為 {expected_pk}"
            )
        
        # 檢查欄位
        expected_columns = {col['name']: col for col in expected_table.get('required_columns', [])}
        actual_columns = {col.name: col for col in actual_table.columns}
        
        # 檢查缺少的欄位
        for col_name in expected_columns.keys():
            if col_name not in actual_columns:
                errors.append(f"❌ {table_name} 缺少必需欄位: {col_name}")
                suggestions.append(f"💡 建議: 在 {table_name} 表中新增 {col_name} 欄位")
        
        # 檢查欄位類型
        for col_name, expected_col in expected_columns.items():
            if col_name in actual_columns:
                actual_col = actual_columns[col_name]
                expected_type = expected_col['type'].upper()
                actual_type = actual_col.data_type.upper()
                
                # 簡化類型比較 (處理 PostgreSQL 特殊類型)
                if not self._types_compatible(expected_type, actual_type):
                    warnings.append(
                        f"⚠️  {table_name}.{col_name} 類型不匹配: 期望 {expected_type}, 實際 {actual_type}"
                    )
        
        # 檢查外鍵
        expected_fks = {fk['column']: fk for fk in expected_table.get('foreign_keys', [])}
        actual_fks = {fk['column']: fk for fk in actual_table.foreign_keys}
        
        for fk_col, expected_fk in expected_fks.items():
            if fk_col not in actual_fks:
                errors.append(f"❌ {table_name} 缺少外鍵約束: {fk_col}")
                suggestions.append(
                    f"💡 建議: 為 {table_name}.{fk_col} 新增外鍵約束 → {expected_fk['references_table']}.{expected_fk['references_column']}"
                )
            else:
                actual_fk = actual_fks[fk_col]
                if (expected_fk['references_table'] != actual_fk['references_table'] or 
                    expected_fk['references_column'] != actual_fk['references_column']):
                    errors.append(
                        f"❌ {table_name}.{fk_col} 外鍵目標不匹配: "
                        f"期望 {expected_fk['references_table']}.{expected_fk['references_column']}, "
                        f"實際 {actual_fk['references_table']}.{actual_fk['references_column']}"
                    )
        
        # 檢查索引
        expected_indexes = {idx['name']: idx for idx in expected_table.get('indexes', [])}
        actual_indexes = {idx['name']: idx for idx in actual_table.indexes}
        
        for idx_name in expected_indexes.keys():
            if idx_name not in actual_indexes:
                warnings.append(f"⚠️  {table_name} 缺少建議的索引: {idx_name}")
                suggestions.append(f"💡 建議: 為 {table_name} 創建索引 {idx_name} 以提升查詢效能")
        
        return errors, warnings, suggestions
    
    def _types_compatible(self, expected: str, actual: str) -> bool:
        """檢查資料類型是否相容"""
        # PostgreSQL 類型映射
        type_mappings = {
            'SERIAL': ['INTEGER', 'BIGINT'],
            'VARCHAR': ['CHARACTER VARYING', 'TEXT'],
            'DECIMAL': ['NUMERIC'],
            'TIMESTAMP': ['TIMESTAMP WITHOUT TIME ZONE', 'TIMESTAMP WITH TIME ZONE'],
            'BOOLEAN': ['BOOL']
        }
        
        # 直接匹配
        if expected == actual:
            return True
        
        # 檢查映射
        for base_type, alternatives in type_mappings.items():
            if expected.startswith(base_type) and actual in alternatives:
                return True
            if actual.startswith(base_type) and expected in alternatives:
                return True
        
        return False
    
    def print_validation_result(self, result: SchemaValidationResult) -> None:
        """印出驗證結果"""
        print("=" * 80)
        print("🔍 Schema 一致性檢查報告")
        print("=" * 80)
        
        # 摘要
        print(f"📊 檢查摘要:")
        print(f"   ✅ 狀態: {'通過' if result.is_valid else '失敗'}")
        print(f"   📅 檢查時間: {result.summary['validation_timestamp']}")
        print(f"   📋 Schema 版本: {result.summary['schema_version']}")
        print(f"   📊 表格數量: 期望 {result.summary['total_tables_expected']}, 實際 {result.summary['total_tables_actual']}")
        print()
        
        # 錯誤
        if result.errors:
            print("❌ 嚴重錯誤:")
            for error in result.errors:
                print(f"   {error}")
            print()
        
        # 警告
        if result.warnings:
            print("⚠️  警告:")
            for warning in result.warnings:
                print(f"   {warning}")
            print()
        
        # 建議
        if result.suggestions:
            print("💡 修復建議:")
            for suggestion in result.suggestions:
                print(f"   {suggestion}")
            print()
        
        print("=" * 80)
        if result.is_valid:
            print("🎉 Schema 一致性檢查通過！")
        else:
            print("🚨 Schema 一致性檢查失敗，請修復上述問題")
        print("=" * 80)


async def main():
    """主程式"""
    if len(sys.argv) < 2:
        print("使用方式: python schema-consistency-checker.py <database_url> [expected_schema_path]")
        print("範例: python schema-consistency-checker.py postgresql://admin:admin@localhost:5432/mydb")
        sys.exit(1)
    
    database_url = sys.argv[1]
    
    # 預設 Schema 檔案路徑
    script_dir = Path(__file__).parent
    default_schema_path = script_dir.parent / "schema" / "expected-schema.json"
    
    expected_schema_path = sys.argv[2] if len(sys.argv) > 2 else str(default_schema_path)
    
    try:
        checker = SchemaConsistencyChecker(database_url, expected_schema_path)
        
        print("📋 載入期望 Schema...")
        await checker.load_expected_schema()
        
        print("🔍 取得實際資料庫 Schema...")
        await checker.fetch_actual_schema()
        
        print("✅ 驗證 Schema 一致性...")
        result = await checker.validate_schema()
        
        checker.print_validation_result(result)
        
        # 根據結果設定退出碼
        sys.exit(0 if result.is_valid else 1)
        
    except Exception as e:
        print(f"❌ 檢查過程發生錯誤: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())