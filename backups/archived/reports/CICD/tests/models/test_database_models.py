"""
資料庫模型測試
測試 SQLAlchemy 模型的基本功能
"""

from datetime import date
from decimal import Decimal

# 測試 current_database 模型
from src.models.current_database import (
    Base as CurrentBase,
)
from src.models.current_database import (
    Machine as CurrentMachine,
)
from src.models.current_database import (
    MachineFault as CurrentMachineFault,
)

# 測試 database 模型
from src.models.database import (
    Base as DatabaseBase,
)
from src.models.database import (
    Machine as DatabaseMachine,
)
from src.models.database import (
    MachineFault as DatabaseMachineFault,
)


class TestCurrentDatabaseModels:
    """測試生產環境資料庫模型"""

    def test_current_machine_model_creation(self):
        """測試 Machine 模型創建"""
        machine = CurrentMachine(
            id="M001",
            name="CNC車床A",
            status="running",
            temperature=Decimal("75.50"),
            utilization_rate=Decimal("85.30"),
            last_maintenance=date(2025, 6, 15),
            location="工廠一樓",
        )

        assert machine.id == "M001"
        assert machine.name == "CNC車床A"
        assert machine.status == "running"
        assert machine.temperature == Decimal("75.50")
        assert machine.utilization_rate == Decimal("85.30")
        assert machine.last_maintenance == date(2025, 6, 15)
        assert machine.location == "工廠一樓"

    def test_current_machine_model_table_name(self):
        """測試 Machine 模型表名"""
        assert CurrentMachine.__tablename__ == "machines"

    def test_current_machine_fault_model_creation(self):
        """測試 MachineFault 模型創建"""
        fault = CurrentMachineFault()

        # 檢查表名
        assert fault.__tablename__ == "machine_faults"

    def test_current_base_metadata(self):
        """測試 Base 元數據"""
        assert CurrentBase.metadata is not None
        assert len(CurrentBase.metadata.tables) >= 2  # Machine 和 MachineFault


class TestDatabaseModels:
    """測試標準資料庫模型"""

    def test_database_machine_model_creation(self):
        """測試 Machine 模型創建"""
        machine = DatabaseMachine(
            id="M002",
            name="沖壓機B",
            status="idle",
            temperature=Decimal("65.20"),
            utilization_rate=Decimal("45.80"),
            last_maintenance=date(2025, 6, 10),
            location="工廠二樓",
        )

        assert machine.id == "M002"
        assert machine.name == "沖壓機B"
        assert machine.status == "idle"
        assert machine.temperature == Decimal("65.20")
        assert machine.utilization_rate == Decimal("45.80")
        assert machine.last_maintenance == date(2025, 6, 10)
        assert machine.location == "工廠二樓"

    def test_database_machine_model_table_name(self):
        """測試 Machine 模型表名"""
        assert DatabaseMachine.__tablename__ == "machines"

    def test_database_machine_fault_model_creation(self):
        """測試 MachineFault 模型創建"""
        fault = DatabaseMachineFault()

        # 檢查表名
        assert fault.__tablename__ == "machine_faults"

    def test_database_base_metadata(self):
        """測試 Base 元數據"""
        assert DatabaseBase.metadata is not None
        assert len(DatabaseBase.metadata.tables) >= 2  # Machine 和 MachineFault


class TestModelComparison:
    """測試模型對比"""

    def test_machine_models_have_same_table_name(self):
        """測試兩個 Machine 模型使用相同表名"""
        assert CurrentMachine.__tablename__ == DatabaseMachine.__tablename__

    def test_machine_fault_models_have_same_table_name(self):
        """測試兩個 MachineFault 模型使用相同表名"""
        assert CurrentMachineFault.__tablename__ == DatabaseMachineFault.__tablename__

    def test_machine_models_basic_attributes(self):
        """測試兩個 Machine 模型都有基本屬性"""
        current_attrs = dir(CurrentMachine)
        database_attrs = dir(DatabaseMachine)

        required_attrs = [
            "id",
            "name",
            "status",
            "temperature",
            "utilization_rate",
            "last_maintenance",
            "location",
        ]

        for attr in required_attrs:
            assert attr in current_attrs, f"CurrentMachine 缺少屬性: {attr}"
            assert attr in database_attrs, f"DatabaseMachine 缺少屬性: {attr}"


class TestModelInstantiation:
    """測試模型實例化"""

    def test_current_machine_with_minimal_data(self):
        """測試 CurrentMachine 最小數據創建"""
        machine = CurrentMachine(id="TEST", name="測試機台", status="test")

        assert machine.id == "TEST"
        assert machine.name == "測試機台"
        assert machine.status == "test"

    def test_database_machine_with_minimal_data(self):
        """測試 DatabaseMachine 最小數據創建"""
        machine = DatabaseMachine(id="TEST", name="測試機台", status="test")

        assert machine.id == "TEST"
        assert machine.name == "測試機台"
        assert machine.status == "test"

    def test_model_attributes_are_accessible(self):
        """測試模型屬性可訪問性"""
        current_machine = CurrentMachine(id="M001", name="測試機", status="running")
        database_machine = DatabaseMachine(id="M002", name="測試機", status="idle")

        # 測試屬性訪問不會拋出異常
        assert hasattr(current_machine, "id")
        assert hasattr(current_machine, "name")
        assert hasattr(current_machine, "status")

        assert hasattr(database_machine, "id")
        assert hasattr(database_machine, "name")
        assert hasattr(database_machine, "status")
