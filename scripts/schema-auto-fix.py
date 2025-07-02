#!/usr/bin/env python3
"""
Schema 自動修復建議生成器
根據 Schema 一致性檢查結果，生成自動修復建議和 SQL 腳本
"""

import asyncio
import asyncpg
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class FixSuggestion:
    """修復建議"""
    category: str  # 'critical', 'warning', 'optimization'
    title: str
    description: str
    sql_script: str
    estimated_impact: str  # 'low', 'medium', 'high'
    rollback_script: Optional[str] = None


class SchemaAutoFixer:
    """Schema 自動修復建議生成器"""
    
    def __init__(self, database_url: str, expected_schema_path: str):
        self.database_url = database_url
        self.expected_schema_path = expected_schema_path
        self.expected_schema: Dict[str, Any] = {}
        self.fix_suggestions: List[FixSuggestion] = []
        
    async def load_expected_schema(self) -> None:
        """載入期望的 Schema 規範"""
        with open(self.expected_schema_path, 'r', encoding='utf-8') as f:
            self.expected_schema = json.load(f)
    
    async def analyze_and_generate_fixes(self) -> List[FixSuggestion]:
        """分析 Schema 差異並生成修復建議"""
        # 先執行 Schema 檢查取得差異
        from pathlib import Path
        import subprocess
        import tempfile
        
        checker_script = Path(__file__).parent / "schema-consistency-checker.py"
        
        # 執行檢查腳本並捕獲輸出
        try:
            result = subprocess.run(
                [sys.executable, str(checker_script), self.database_url, self.expected_schema_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print("✅ Schema 已經一致，無需修復")
                return []
            
            # 解析輸出找出問題
            await self._parse_checker_output(result.stdout)
            
        except subprocess.TimeoutExpired:
            print("❌ Schema 檢查超時")
            return []
        except Exception as e:
            print(f"❌ 執行 Schema 檢查時發生錯誤: {e}")
            return []
        
        # 生成修復建議
        await self._generate_missing_table_fixes()
        await self._generate_missing_column_fixes()
        await self._generate_missing_index_fixes()
        await self._generate_foreign_key_fixes()
        
        return self.fix_suggestions
    
    async def _parse_checker_output(self, output: str) -> None:
        """解析檢查器輸出"""
        # 這裡可以更精細地解析輸出，目前簡化處理
        pass
    
    async def _generate_missing_table_fixes(self) -> None:
        """生成缺少表格的修復建議"""
        conn = await asyncpg.connect(self.database_url)
        try:
            # 取得現有表格
            existing_tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
            """)
            existing_table_names = {row['table_name'] for row in existing_tables}
            
            expected_tables = self.expected_schema.get('tables', {})
            
            for table_name, table_def in expected_tables.items():
                if table_name not in existing_table_names:
                    # 生成建表 SQL
                    create_sql = self._generate_create_table_sql(table_name, table_def)
                    drop_sql = f"DROP TABLE IF EXISTS {table_name} CASCADE;"
                    
                    self.fix_suggestions.append(FixSuggestion(
                        category='critical',
                        title=f'創建缺少的表格: {table_name}',
                        description=f'根據 Schema 規範創建 {table_name} 表格',
                        sql_script=create_sql,
                        estimated_impact='high',
                        rollback_script=drop_sql
                    ))
                    
        finally:
            await conn.close()
    
    async def _generate_missing_column_fixes(self) -> None:
        """生成缺少欄位的修復建議"""
        conn = await asyncpg.connect(self.database_url)
        try:
            expected_tables = self.expected_schema.get('tables', {})
            
            for table_name, table_def in expected_tables.items():
                # 檢查表格是否存在
                table_exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = $1
                    )
                """, table_name)
                
                if not table_exists:
                    continue
                
                # 取得現有欄位
                existing_columns = await conn.fetch("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = $1 AND table_schema = 'public'
                """, table_name)
                
                existing_column_names = {col['column_name'] for col in existing_columns}
                
                # 檢查缺少的欄位
                for col_def in table_def.get('required_columns', []):
                    col_name = col_def['name']
                    if col_name not in existing_column_names:
                        # 生成新增欄位 SQL
                        add_sql = self._generate_add_column_sql(table_name, col_def)
                        drop_sql = f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {col_name};"
                        
                        self.fix_suggestions.append(FixSuggestion(
                            category='critical',
                            title=f'新增缺少的欄位: {table_name}.{col_name}',
                            description=f'在 {table_name} 表中新增 {col_name} 欄位',
                            sql_script=add_sql,
                            estimated_impact='medium',
                            rollback_script=drop_sql
                        ))
                        
        finally:
            await conn.close()
    
    async def _generate_missing_index_fixes(self) -> None:
        """生成缺少索引的修復建議"""
        conn = await asyncpg.connect(self.database_url)
        try:
            expected_tables = self.expected_schema.get('tables', {})
            
            for table_name, table_def in expected_tables.items():
                # 檢查表格是否存在
                table_exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = $1
                    )
                """, table_name)
                
                if not table_exists:
                    continue
                
                # 取得現有索引
                existing_indexes = await conn.fetch("""
                    SELECT indexname as index_name
                    FROM pg_indexes 
                    WHERE tablename = $1 AND schemaname = 'public'
                """, table_name)
                
                existing_index_names = {idx['index_name'] for idx in existing_indexes}
                
                # 檢查缺少的索引
                for idx_def in table_def.get('indexes', []):
                    idx_name = idx_def['name']
                    if idx_name not in existing_index_names:
                        # 生成建索引 SQL
                        create_sql = self._generate_create_index_sql(table_name, idx_def)
                        drop_sql = f"DROP INDEX IF EXISTS {idx_name};"
                        
                        self.fix_suggestions.append(FixSuggestion(
                            category='optimization',
                            title=f'創建建議的索引: {idx_name}',
                            description=f'為 {table_name} 表創建索引以提升查詢效能',
                            sql_script=create_sql,
                            estimated_impact='low',
                            rollback_script=drop_sql
                        ))
                        
        finally:
            await conn.close()
    
    async def _generate_foreign_key_fixes(self) -> None:
        """生成缺少外鍵約束的修復建議"""
        conn = await asyncpg.connect(self.database_url)
        try:
            expected_tables = self.expected_schema.get('tables', {})
            
            for table_name, table_def in expected_tables.items():
                # 檢查表格是否存在
                table_exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = $1
                    )
                """, table_name)
                
                if not table_exists:
                    continue
                
                # 取得現有外鍵
                existing_fks = await conn.fetch("""
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
                """, table_name)
                
                existing_fk_columns = {fk['column_name'] for fk in existing_fks}
                
                # 檢查缺少的外鍵
                for fk_def in table_def.get('foreign_keys', []):
                    fk_column = fk_def['column']
                    if fk_column not in existing_fk_columns:
                        # 生成新增外鍵 SQL
                        add_sql = self._generate_add_foreign_key_sql(table_name, fk_def)
                        constraint_name = f"fk_{table_name}_{fk_column}"
                        drop_sql = f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {constraint_name};"
                        
                        self.fix_suggestions.append(FixSuggestion(
                            category='critical',
                            title=f'新增外鍵約束: {table_name}.{fk_column}',
                            description=f'為 {table_name}.{fk_column} 新增外鍵約束',
                            sql_script=add_sql,
                            estimated_impact='medium',
                            rollback_script=drop_sql
                        ))
                        
        finally:
            await conn.close()
    
    def _generate_create_table_sql(self, table_name: str, table_def: Dict[str, Any]) -> str:
        """生成建表 SQL"""
        columns = []
        
        for col_def in table_def.get('required_columns', []):
            col_sql = f"    {col_def['name']} {col_def['type']}"
            
            if not col_def.get('nullable', True):
                col_sql += " NOT NULL"
            
            if 'default' in col_def:
                col_sql += f" DEFAULT {col_def['default']}"
            
            if 'PRIMARY KEY' in col_def.get('constraints', []):
                col_sql += " PRIMARY KEY"
            
            columns.append(col_sql)
        
        # 新增外鍵約束
        for fk_def in table_def.get('foreign_keys', []):
            fk_sql = f"    CONSTRAINT fk_{table_name}_{fk_def['column']} " \
                    f"FOREIGN KEY ({fk_def['column']}) " \
                    f"REFERENCES {fk_def['references_table']}({fk_def['references_column']})"
            columns.append(fk_sql)
        
        return f"CREATE TABLE {table_name} (\n" + ",\n".join(columns) + "\n);"
    
    def _generate_add_column_sql(self, table_name: str, col_def: Dict[str, Any]) -> str:
        """生成新增欄位 SQL"""
        sql = f"ALTER TABLE {table_name} ADD COLUMN {col_def['name']} {col_def['type']}"
        
        if not col_def.get('nullable', True):
            sql += " NOT NULL"
        
        if 'default' in col_def:
            sql += f" DEFAULT {col_def['default']}"
        
        return sql + ";"
    
    def _generate_create_index_sql(self, table_name: str, idx_def: Dict[str, Any]) -> str:
        """生成建索引 SQL"""
        columns = ", ".join(idx_def['columns'])
        return f"CREATE INDEX {idx_def['name']} ON {table_name} ({columns});"
    
    def _generate_add_foreign_key_sql(self, table_name: str, fk_def: Dict[str, Any]) -> str:
        """生成新增外鍵約束 SQL"""
        constraint_name = f"fk_{table_name}_{fk_def['column']}"
        return f"ALTER TABLE {table_name} " \
               f"ADD CONSTRAINT {constraint_name} " \
               f"FOREIGN KEY ({fk_def['column']}) " \
               f"REFERENCES {fk_def['references_table']}({fk_def['references_column']});"
    
    def generate_fix_script(self, output_path: str) -> None:
        """生成修復腳本檔案"""
        if not self.fix_suggestions:
            print("📋 沒有需要修復的問題")
            return
        
        script_content = f"""-- Schema 自動修復腳本
-- 生成時間: {datetime.now().isoformat()}
-- 資料庫: {self.database_url}
-- Schema 版本: {self.expected_schema.get('version', 'unknown')}

-- 🚨 注意事項:
-- 1. 請在執行前備份資料庫
-- 2. 建議在測試環境先行驗證
-- 3. 按順序執行以下修復命令
-- 4. 如有問題可使用對應的 rollback 命令回復

BEGIN;

"""
        
        rollback_content = f"""-- Schema 修復回復腳本
-- 生成時間: {datetime.now().isoformat()}

-- 🔄 回復指令 (按相反順序執行):

BEGIN;

"""
        
        # 按重要性排序
        critical_fixes = [f for f in self.fix_suggestions if f.category == 'critical']
        warning_fixes = [f for f in self.fix_suggestions if f.category == 'warning']
        optimization_fixes = [f for f in self.fix_suggestions if f.category == 'optimization']
        
        rollback_scripts = []
        
        for category, fixes in [('CRITICAL', critical_fixes), ('WARNING', warning_fixes), ('OPTIMIZATION', optimization_fixes)]:
            if not fixes:
                continue
                
            script_content += f"\n-- ========== {category} FIXES ==========\n\n"
            
            for i, fix in enumerate(fixes, 1):
                script_content += f"-- {category} #{i}: {fix.title}\n"
                script_content += f"-- {fix.description}\n"
                script_content += f"-- 影響程度: {fix.estimated_impact}\n"
                script_content += f"{fix.sql_script}\n\n"
                
                if fix.rollback_script:
                    rollback_scripts.insert(0, (fix.title, fix.rollback_script))
        
        script_content += "COMMIT;\n"
        script_content += "\n-- ✅ 修復完成，建議執行 Schema 檢查驗證結果\n"
        script_content += "-- ./scripts/check-schema.sh --verbose\n"
        
        # 生成回復腳本
        for title, rollback_script in rollback_scripts:
            rollback_content += f"-- 回復: {title}\n{rollback_script}\n\n"
        
        rollback_content += "COMMIT;\n"
        
        # 寫入檔案
        fix_path = Path(output_path)
        fix_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(fix_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        rollback_path = fix_path.parent / f"{fix_path.stem}_rollback{fix_path.suffix}"
        with open(rollback_path, 'w', encoding='utf-8') as f:
            f.write(rollback_content)
        
        print(f"📄 修復腳本已生成: {fix_path}")
        print(f"🔄 回復腳本已生成: {rollback_path}")
    
    def print_fix_summary(self) -> None:
        """印出修復摘要"""
        if not self.fix_suggestions:
            print("🎉 沒有發現需要修復的 Schema 問題！")
            return
        
        print("=" * 80)
        print("🛠️  Schema 自動修復建議")
        print("=" * 80)
        
        critical = len([f for f in self.fix_suggestions if f.category == 'critical'])
        warning = len([f for f in self.fix_suggestions if f.category == 'warning'])
        optimization = len([f for f in self.fix_suggestions if f.category == 'optimization'])
        
        print(f"📊 修復摘要:")
        print(f"   🚨 關鍵問題: {critical}")
        print(f"   ⚠️  警告問題: {warning}")
        print(f"   ⚡ 優化建議: {optimization}")
        print(f"   📋 總計: {len(self.fix_suggestions)}")
        print()
        
        for category, emoji in [('critical', '🚨'), ('warning', '⚠️ '), ('optimization', '⚡')]:
            category_fixes = [f for f in self.fix_suggestions if f.category == category]
            if category_fixes:
                print(f"{emoji} {category.upper()} 修復建議:")
                for i, fix in enumerate(category_fixes, 1):
                    print(f"   {i}. {fix.title}")
                    print(f"      💡 {fix.description}")
                    print(f"      📈 影響: {fix.estimated_impact}")
                print()
        
        print("💡 建議:")
        print("   1. 先執行關鍵修復確保基本功能")
        print("   2. 在測試環境驗證修復腳本")
        print("   3. 執行完整的資料庫測試")
        print("   4. 執行優化建議提升效能")
        print("=" * 80)


async def main():
    """主程式"""
    if len(sys.argv) < 2:
        print("使用方式: python schema-auto-fix.py <database_url> [expected_schema_path] [output_path]")
        print("範例: python schema-auto-fix.py postgresql://admin:admin@localhost:5432/mydb")
        sys.exit(1)
    
    database_url = sys.argv[1]
    
    # 預設路徑
    script_dir = Path(__file__).parent
    default_schema_path = script_dir.parent / "schema" / "expected-schema.json"
    default_output_path = script_dir.parent / "migrations" / f"schema_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    
    expected_schema_path = sys.argv[2] if len(sys.argv) > 2 else str(default_schema_path)
    output_path = sys.argv[3] if len(sys.argv) > 3 else str(default_output_path)
    
    try:
        fixer = SchemaAutoFixer(database_url, expected_schema_path)
        
        print("📋 載入期望 Schema...")
        await fixer.load_expected_schema()
        
        print("🔍 分析 Schema 差異...")
        fixes = await fixer.analyze_and_generate_fixes()
        
        fixer.print_fix_summary()
        
        if fixes:
            print(f"📄 生成修復腳本...")
            fixer.generate_fix_script(output_path)
            print()
            print("🚀 下一步:")
            print(f"   1. 檢查修復腳本: {output_path}")
            print(f"   2. 在測試環境執行修復")
            print(f"   3. 驗證修復結果: ./scripts/check-schema.sh")
        
    except Exception as e:
        print(f"❌ 自動修復過程發生錯誤: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())