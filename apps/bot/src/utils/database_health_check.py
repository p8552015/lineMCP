"""
資料庫健康檢查模組
用於驗證資料庫Schema是否符合應用程式期望
"""

import asyncio
import asyncpg
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseHealthChecker:
    """資料庫健康檢查器"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.required_tables = {
            'machines': {
                'required_columns': ['id', 'name', 'status', 'temperature', 'utilization_rate'],
                'primary_key': 'id'
            },
            'machine_faults': {
                'required_columns': ['fault_id', 'machine_id', 'fault_type', 'severity', 'fault_date'],
                'primary_key': 'fault_id',
                'foreign_keys': [('machine_id', 'machines', 'id')]
            },
            'machine_utilization': {
                'required_columns': ['id', 'machine_id', 'utilization_rate'],
                'primary_key': 'id',
                'foreign_keys': [('machine_id', 'machines', 'id')]
            },
            'employees': {
                'required_columns': ['id', 'name', 'department'],
                'primary_key': 'id'
            },
            'products': {
                'required_columns': ['id', 'name', 'category', 'price'],
                'primary_key': 'id'
            },
            'orders': {
                'required_columns': ['id', 'customer_name', 'quantity', 'order_date'],
                'primary_key': 'id'
            }
        }
    
    async def check_database_health(self) -> Dict[str, Any]:
        """執行完整的資料庫健康檢查"""
        health_report = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'unknown',
            'connection_status': 'unknown',
            'tables_status': {},
            'missing_tables': [],
            'missing_columns': {},
            'foreign_key_status': {},
            'errors': []
        }
        
        try:
            # 測試資料庫連接
            connection_result = await self._check_connection()
            health_report['connection_status'] = connection_result['status']
            
            if connection_result['status'] != 'healthy':
                health_report['errors'].append(connection_result['error'])
                health_report['overall_status'] = 'critical'
                return health_report
            
            # 檢查資料表
            tables_result = await self._check_tables()
            health_report['tables_status'] = tables_result['tables_status']
            health_report['missing_tables'] = tables_result['missing_tables']
            health_report['missing_columns'] = tables_result['missing_columns']
            
            # 檢查外鍵約束
            fk_result = await self._check_foreign_keys()
            health_report['foreign_key_status'] = fk_result
            
            # 計算整體狀態
            health_report['overall_status'] = self._calculate_overall_status(health_report)
            
        except Exception as e:
            logger.error(f"資料庫健康檢查失敗: {e}")
            health_report['errors'].append(str(e))
            health_report['overall_status'] = 'critical'
        
        return health_report
    
    async def _check_connection(self) -> Dict[str, Any]:
        """檢查資料庫連接"""
        try:
            conn = await asyncpg.connect(self.database_url)
            await conn.fetchval('SELECT 1')
            await conn.close()
            return {'status': 'healthy', 'error': None}
        except Exception as e:
            return {'status': 'critical', 'error': str(e)}
    
    async def _check_tables(self) -> Dict[str, Any]:
        """檢查資料表存在性和結構"""
        result = {
            'tables_status': {},
            'missing_tables': [],
            'missing_columns': {}
        }
        
        try:
            conn = await asyncpg.connect(self.database_url)
            
            # 獲取所有資料表
            existing_tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            existing_table_names = {row['table_name'] for row in existing_tables}
            
            # 檢查每個必需的資料表
            for table_name, table_config in self.required_tables.items():
                if table_name not in existing_table_names:
                    result['missing_tables'].append(table_name)
                    result['tables_status'][table_name] = 'missing'
                    continue
                
                # 檢查資料表欄位
                columns = await conn.fetch("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = $1 AND table_schema = 'public'
                """, table_name)
                
                existing_columns = {row['column_name'] for row in columns}
                required_columns = set(table_config['required_columns'])
                missing_columns = required_columns - existing_columns
                
                if missing_columns:
                    result['missing_columns'][table_name] = list(missing_columns)
                    result['tables_status'][table_name] = 'incomplete'
                else:
                    result['tables_status'][table_name] = 'healthy'
            
            await conn.close()
            
        except Exception as e:
            logger.error(f"檢查資料表時發生錯誤: {e}")
            raise
        
        return result
    
    async def _check_foreign_keys(self) -> Dict[str, Any]:
        """檢查外鍵約束"""
        fk_status = {}
        
        try:
            conn = await asyncpg.connect(self.database_url)
            
            for table_name, table_config in self.required_tables.items():
                if 'foreign_keys' not in table_config:
                    continue
                
                fk_status[table_name] = {}
                
                for fk_column, ref_table, ref_column in table_config['foreign_keys']:
                    # 檢查外鍵約束是否存在
                    fk_exists = await conn.fetchval("""
                        SELECT EXISTS (
                            SELECT 1 
                            FROM information_schema.table_constraints tc
                            JOIN information_schema.key_column_usage kcu 
                                ON tc.constraint_name = kcu.constraint_name
                            JOIN information_schema.constraint_column_usage ccu 
                                ON ccu.constraint_name = tc.constraint_name
                            WHERE tc.constraint_type = 'FOREIGN KEY'
                                AND tc.table_name = $1
                                AND kcu.column_name = $2
                                AND ccu.table_name = $3
                                AND ccu.column_name = $4
                        )
                    """, table_name, fk_column, ref_table, ref_column)
                    
                    fk_status[table_name][f"{fk_column}->{ref_table}.{ref_column}"] = (
                        'healthy' if fk_exists else 'missing'
                    )
            
            await conn.close()
            
        except Exception as e:
            logger.error(f"檢查外鍵約束時發生錯誤: {e}")
            raise
        
        return fk_status
    
    def _calculate_overall_status(self, health_report: Dict[str, Any]) -> str:
        """計算整體健康狀態"""
        if health_report['connection_status'] != 'healthy':
            return 'critical'
        
        if health_report['missing_tables']:
            return 'critical'
        
        # 檢查是否有不完整的資料表
        incomplete_tables = [
            table for table, status in health_report['tables_status'].items()
            if status == 'incomplete'
        ]
        
        if incomplete_tables:
            return 'warning'
        
        # 檢查外鍵狀態
        for table_fks in health_report['foreign_key_status'].values():
            for fk_status in table_fks.values():
                if fk_status == 'missing':
                    return 'warning'
        
        return 'healthy'
    
    async def verify_critical_functionality(self) -> Dict[str, Any]:
        """驗證關鍵功能是否正常運作"""
        verification_result = {
            'timestamp': datetime.now().isoformat(),
            'tests': {},
            'overall_status': 'unknown'
        }
        
        try:
            conn = await asyncpg.connect(self.database_url)
            
            # 測試 1: 機台查詢
            verification_result['tests']['machine_query'] = await self._test_machine_query(conn)
            
            # 測試 2: 故障記錄查詢
            verification_result['tests']['fault_query'] = await self._test_fault_query(conn)
            
            # 測試 3: 使用率查詢
            verification_result['tests']['utilization_query'] = await self._test_utilization_query(conn)
            
            # 測試 4: 關聯查詢
            verification_result['tests']['join_query'] = await self._test_join_query(conn)
            
            await conn.close()
            
            # 計算整體狀態
            all_passed = all(
                test_result['status'] == 'passed' 
                for test_result in verification_result['tests'].values()
            )
            verification_result['overall_status'] = 'passed' if all_passed else 'failed'
            
        except Exception as e:
            logger.error(f"功能驗證失敗: {e}")
            verification_result['overall_status'] = 'error'
            verification_result['error'] = str(e)
        
        return verification_result
    
    async def _test_machine_query(self, conn) -> Dict[str, Any]:
        """測試機台查詢"""
        try:
            result = await conn.fetch('SELECT id, name, status FROM machines LIMIT 5')
            return {
                'status': 'passed',
                'message': f'成功查詢到 {len(result)} 台機台',
                'data_count': len(result)
            }
        except Exception as e:
            return {
                'status': 'failed',
                'message': f'機台查詢失敗: {e}',
                'error': str(e)
            }
    
    async def _test_fault_query(self, conn) -> Dict[str, Any]:
        """測試故障記錄查詢"""
        try:
            result = await conn.fetch('SELECT fault_id, machine_id, fault_type, severity FROM machine_faults LIMIT 5')
            return {
                'status': 'passed',
                'message': f'成功查詢到 {len(result)} 筆故障記錄',
                'data_count': len(result)
            }
        except Exception as e:
            return {
                'status': 'failed',
                'message': f'故障記錄查詢失敗: {e}',
                'error': str(e)
            }
    
    async def _test_utilization_query(self, conn) -> Dict[str, Any]:
        """測試使用率查詢"""
        try:
            result = await conn.fetch('SELECT id, machine_id, utilization_rate FROM machine_utilization LIMIT 5')
            return {
                'status': 'passed',
                'message': f'成功查詢到 {len(result)} 筆使用率記錄',
                'data_count': len(result)
            }
        except Exception as e:
            return {
                'status': 'failed',
                'message': f'使用率查詢失敗: {e}',
                'error': str(e)
            }
    
    async def _test_join_query(self, conn) -> Dict[str, Any]:
        """測試關聯查詢"""
        try:
            result = await conn.fetch("""
                SELECT m.name, COUNT(mf.fault_id) as fault_count
                FROM machines m
                LEFT JOIN machine_faults mf ON m.id = mf.machine_id
                GROUP BY m.id, m.name
                LIMIT 5
            """)
            return {
                'status': 'passed',
                'message': f'成功執行關聯查詢，返回 {len(result)} 筆結果',
                'data_count': len(result)
            }
        except Exception as e:
            return {
                'status': 'failed',
                'message': f'關聯查詢失敗: {e}',
                'error': str(e)
            }


async def run_health_check(database_url: str = "postgresql://admin:admin@localhost:5432/mydb") -> Dict[str, Any]:
    """執行完整的資料庫健康檢查"""
    checker = DatabaseHealthChecker(database_url)
    
    print("🔍 開始資料庫健康檢查...")
    health_report = await checker.check_database_health()
    
    print("🧪 開始功能驗證測試...")
    verification_report = await checker.verify_critical_functionality()
    
    return {
        'health_check': health_report,
        'functionality_verification': verification_report
    }


if __name__ == "__main__":
    # 直接執行健康檢查
    result = asyncio.run(run_health_check())
    
    print("\n" + "="*50)
    print("資料庫健康檢查報告")
    print("="*50)
    
    health = result['health_check']
    print(f"整體狀態: {health['overall_status']}")
    print(f"連接狀態: {health['connection_status']}")
    
    if health['missing_tables']:
        print(f"缺失資料表: {', '.join(health['missing_tables'])}")
    
    if health['missing_columns']:
        for table, columns in health['missing_columns'].items():
            print(f"資料表 {table} 缺失欄位: {', '.join(columns)}")
    
    print("\n" + "="*50)
    print("功能驗證報告")
    print("="*50)
    
    verification = result['functionality_verification']
    print(f"整體狀態: {verification['overall_status']}")
    
    for test_name, test_result in verification['tests'].items():
        status_icon = "✅" if test_result['status'] == 'passed' else "❌"
        print(f"{status_icon} {test_name}: {test_result['message']}")