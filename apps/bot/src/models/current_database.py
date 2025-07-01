"""
當前生產環境資料庫模型
基於實際的生產環境資料庫結構定義
"""

from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base: Any = declarative_base()


class Machine(Base):
    """機台資料表 - 基於生產環境實際結構"""

    __tablename__ = "machines"

    id = Column(String(10), primary_key=True)  # 生產環境是 VARCHAR(10)
    name = Column(String(100), nullable=False)  # 生產環境是 VARCHAR(100)
    status = Column(String(20), nullable=False)  # 生產環境是 VARCHAR(20)
    temperature = Column(Numeric(5, 2))
    utilization_rate = Column(Numeric(5, 2))
    last_maintenance = Column(Date)
    location = Column(String(50))  # 生產環境是 VARCHAR(50)
    created_at = Column(DateTime, server_default=func.current_timestamp())


class MachineFault(Base):
    """機台故障記錄表 - 基於生產環境實際結構"""

    __tablename__ = "machine_faults"

    fault_id = Column(Integer, primary_key=True, autoincrement=True)
    machine_id = Column(String(50), ForeignKey("machines.id"), nullable=False)
    fault_type = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False)
    fault_date = Column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    description = Column(Text)
    resolved = Column(Boolean, server_default="false")
    resolution_date = Column(DateTime)
    created_at = Column(DateTime, server_default=func.current_timestamp())


class MachineUtilization(Base):
    """機台使用率歷史記錄表 - 基於生產環境實際結構"""

    __tablename__ = "machine_utilization"

    id = Column(Integer, primary_key=True, autoincrement=True)
    machine_id = Column(String(10), nullable=False)  # 生產環境是 VARCHAR(10)
    utilization_rate = Column(Numeric(5, 2), nullable=False)
    timestamp = Column(DateTime, server_default=func.current_timestamp())
    status = Column(String(20), server_default="active")


class Employee(Base):
    """員工資料表 - 基於生產環境實際結構"""

    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    department = Column(String(50))
    hire_date = Column(Date)
    salary = Column(Numeric(10, 2))
    created_at = Column(DateTime, server_default=func.current_timestamp())


class Product(Base):
    """產品資料表 - 基於生產環境實際結構"""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50))
    price = Column(Numeric(8, 2))  # 生產環境是 NUMERIC(8,2)
    stock = Column(Integer)  # 生產環境是 stock 不是 stock_quantity
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp())


class Order(Base):
    """訂單資料表 - 基於生產環境實際結構"""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_name = Column(String(100), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, nullable=False, server_default="1")
    order_date = Column(
        DateTime, server_default=func.current_timestamp()
    )  # 生產環境是 TIMESTAMP
    total_amount = Column(Numeric(10, 2))
    status = Column(String(20), server_default="pending")


# 資料庫配置
DATABASE_URL = "postgresql://admin:admin@localhost:5432/mydb"
