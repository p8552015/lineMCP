"""
資料庫模型定義
使用 SQLAlchemy 定義所有資料表結構，用於 Alembic 遷移管理
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Numeric, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class Machine(Base):
    """機台資料表"""
    __tablename__ = 'machines'
    
    id = Column(String(50), primary_key=True, comment='機台ID')
    name = Column(String(255), nullable=False, comment='機台名稱')
    status = Column(String(50), nullable=False, comment='機台狀態')
    temperature = Column(Numeric(5, 2), comment='溫度')
    utilization_rate = Column(Numeric(5, 2), comment='使用率')
    last_maintenance = Column(Date, comment='上次維護日期')
    location = Column(String(255), comment='位置')
    created_at = Column(DateTime, default=func.now(), comment='建立時間')


class MachineFault(Base):
    """機台故障記錄表"""
    __tablename__ = 'machine_faults'
    
    fault_id = Column(Integer, primary_key=True, autoincrement=True, comment='故障ID')
    machine_id = Column(String(50), ForeignKey('machines.id'), nullable=False, comment='機台ID')
    fault_type = Column(String(100), nullable=False, comment='故障類型')
    severity = Column(String(20), nullable=False, comment='嚴重程度')
    fault_date = Column(DateTime, default=func.now(), nullable=False, comment='故障發生時間')
    description = Column(Text, comment='故障描述')
    resolved = Column(Boolean, default=False, comment='是否已解決')
    resolution_date = Column(DateTime, comment='解決時間')
    created_at = Column(DateTime, default=func.now(), comment='記錄建立時間')


class MachineUtilization(Base):
    """機台使用率歷史記錄表"""
    __tablename__ = 'machine_utilization'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='記錄ID')
    machine_id = Column(String(50), ForeignKey('machines.id'), nullable=False, comment='機台ID')
    utilization_rate = Column(Numeric(5, 2), nullable=False, comment='使用率')
    temperature = Column(Numeric(5, 2), comment='溫度')
    recorded_at = Column(DateTime, default=func.now(), nullable=False, comment='記錄時間')
    shift = Column(String(20), comment='班別')
    operator = Column(String(100), comment='操作員')


class Employee(Base):
    """員工資料表"""
    __tablename__ = 'employees'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='員工ID')
    name = Column(String(100), nullable=False, comment='姓名')
    department = Column(String(50), comment='部門')
    position = Column(String(50), comment='職位')
    email = Column(String(100), comment='電子郵件')
    hire_date = Column(Date, comment='入職日期')
    salary = Column(Numeric(10, 2), comment='薪資')


class Product(Base):
    """產品資料表"""
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='產品ID')
    name = Column(String(100), nullable=False, comment='產品名稱')
    category = Column(String(50), comment='產品類別')
    price = Column(Numeric(10, 2), comment='價格')
    stock_quantity = Column(Integer, comment='庫存數量')
    description = Column(Text, comment='產品描述')


class Order(Base):
    """訂單資料表"""
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='訂單ID')
    customer_name = Column(String(100), nullable=False, comment='客戶名稱')
    product_id = Column(Integer, ForeignKey('products.id'), comment='產品ID')
    quantity = Column(Integer, nullable=False, comment='數量')
    order_date = Column(Date, default=func.current_date(), comment='訂單日期')
    total_amount = Column(Numeric(10, 2), comment='總金額')
    status = Column(String(20), default='pending', comment='訂單狀態')


# 資料庫配置
DATABASE_URL = "postgresql://admin:admin@localhost:5432/mydb"