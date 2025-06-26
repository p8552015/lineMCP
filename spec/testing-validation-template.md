# 測試驗證流程樣板

## 🎯 樣板目標

此樣板提供完整的測試驗證流程標準，確保軟體品質和系統穩定性，建立可靠的品質保證機制。

## 📋 測試金字塔策略

### 測試層級分布
```
        🔺 E2E Tests (10%)
       🔺🔺 Integration Tests (20%)  
     🔺🔺🔺 Unit Tests (70%)
```

- **單元測試 (70%)**：快速、獨立、可重複
- **整合測試 (20%)**：模組間交互驗證
- **端到端測試 (10%)**：完整用戶流程

## 📊 測試任務規劃表

```markdown
<!-- TASKS START -->
| ID | 測試類型 | 測試範圍 | 優先級 | 覆蓋率目標 | 狀態 | 開始時間 | 完成時間 |
|---|---|---|---|---|---|---|---|
| T-01 | 單元測試 | 核心業務邏輯 | High | 95% | TODO | - | - |
| T-02 | 整合測試 | API 介面 | High | 90% | TODO | - | - |
| T-03 | 系統測試 | 完整功能流程 | Medium | 85% | TODO | - | - |
| T-04 | 效能測試 | 負載壓力測試 | Medium | 基線達標 | TODO | - | - |
| T-05 | 安全測試 | 漏洞掃描 | High | 0 高危漏洞 | TODO | - | - |
<!-- TASKS END -->
```

## 🧪 測試流程規範

### 階段一：測試規劃
1. **需求分析**：理解測試需求和驗收標準
2. **測試策略**：制定測試方法和工具選擇
3. **環境準備**：建立測試環境和測試資料
4. **基線建立**：建立效能和品質基線

### 階段二：測試設計
1. **測試案例設計**：涵蓋正常、異常、邊界情況
2. **測試資料準備**：準備各種測試情境資料
3. **Mock 服務設計**：外部依賴的模擬設計
4. **自動化腳本**：測試自動化腳本開發

### 階段三：測試執行
1. **單元測試執行**：快速反饋迴圈
2. **整合測試執行**：模組間相容性驗證
3. **系統測試執行**：完整功能驗證
4. **回歸測試執行**：確保無副作用

### 階段四：結果分析
1. **測試報告生成**：詳細的測試結果報告
2. **覆蓋率分析**：程式碼覆蓋率統計
3. **缺陷分析**：問題分類和嚴重程度評估
4. **改善建議**：測試流程優化建議

## 🔧 測試工具配置

### Python 測試工具鏈
```bash
# 安裝測試依賴
poetry add --group dev pytest pytest-asyncio pytest-cov pytest-mock

# 基本測試執行
poetry run pytest -v

# 測試覆蓋率
poetry run pytest --cov=src --cov-report=html --cov-report=term

# 平行測試執行
poetry run pytest -n auto

# 特定標記測試
poetry run pytest -m "not slow"
```

### 測試配置檔案
```ini
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --strict-markers
    --strict-config
    --cov=src
    --cov-branch
    --cov-report=term-missing
    --cov-fail-under=80
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    smoke: marks tests as smoke tests
```

## 📏 測試覆蓋率標準

### 覆蓋率目標
| 測試類型 | 最低要求 | 推薦目標 | 優秀標準 |
|---------|----------|----------|----------|
| 單元測試 | 80% | 90% | 95% |
| 整合測試 | 70% | 85% | 90% |
| 分支覆蓋 | 75% | 85% | 90% |
| 函數覆蓋 | 85% | 95% | 98% |

### 覆蓋率檢查腳本
```bash
#!/bin/bash
# coverage-check.sh

echo "🧪 執行測試覆蓋率檢查..."

# 執行測試並生成覆蓋率報告
poetry run pytest --cov=src --cov-report=json --cov-fail-under=80

# 解析覆蓋率結果
COVERAGE=$(python -c "import json; print(json.load(open('coverage.json'))['totals']['percent_covered'])")

echo "📊 當前覆蓋率: ${COVERAGE}%"

if (( $(echo "$COVERAGE >= 80" | bc -l) )); then
    echo "✅ 覆蓋率達標"
    exit 0
else
    echo "❌ 覆蓋率不足，最低要求 80%"
    exit 1
fi
```

## 🎯 測試案例設計原則

### 單元測試設計
```python
# 範例：單元測試結構
import pytest
from unittest.mock import Mock, patch

class TestUserService:
    def setup_method(self):
        """每個測試方法前的設置"""
        self.user_service = UserService()
    
    def test_create_user_success(self):
        """測試用戶創建成功情境"""
        # Arrange
        user_data = {"name": "測試用戶", "email": "test@example.com"}
        
        # Act
        result = self.user_service.create_user(user_data)
        
        # Assert
        assert result.success is True
        assert result.user.name == "測試用戶"
    
    def test_create_user_invalid_email(self):
        """測試無效郵箱情境"""
        # Arrange
        user_data = {"name": "測試用戶", "email": "invalid-email"}
        
        # Act & Assert
        with pytest.raises(ValidationError):
            self.user_service.create_user(user_data)
    
    @patch('services.user_service.database')
    def test_create_user_database_error(self, mock_db):
        """測試資料庫錯誤情境"""
        # Arrange
        mock_db.save.side_effect = DatabaseError("連接失敗")
        user_data = {"name": "測試用戶", "email": "test@example.com"}
        
        # Act & Assert
        with pytest.raises(DatabaseError):
            self.user_service.create_user(user_data)
```

### 整合測試設計
```python
# 範例：整合測試結構
class TestUserAPIIntegration:
    @pytest.fixture(autouse=True)
    def setup(self):
        """整合測試環境設置"""
        self.client = TestClient(app)
        self.test_db = create_test_database()
    
    def test_user_registration_flow(self):
        """測試完整用戶註冊流程"""
        # 1. 發送註冊請求
        response = self.client.post("/api/users", json={
            "name": "測試用戶",
            "email": "test@example.com",
            "password": "secure123"
        })
        
        # 2. 驗證回應
        assert response.status_code == 201
        user_data = response.json()
        assert user_data["name"] == "測試用戶"
        
        # 3. 驗證資料庫狀態
        user = self.test_db.get_user(user_data["id"])
        assert user is not None
        assert user.email == "test@example.com"
```

## 🚀 效能測試策略

### 負載測試配置
```python
# locustfile.py - 效能測試腳本
from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """測試開始時的設置"""
        self.login()
    
    def login(self):
        """用戶登入"""
        response = self.client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "testpass"
        })
        self.token = response.json()["token"]
        self.client.headers.update({"Authorization": f"Bearer {self.token}"})
    
    @task(3)
    def view_machines(self):
        """查看機台列表（高頻操作）"""
        self.client.get("/api/machines")
    
    @task(1)
    def query_machine_status(self):
        """查詢特定機台狀態"""
        self.client.get("/api/machines/M001/status")
```

### 效能測試執行
```bash
# 基礎負載測試
locust -f locustfile.py --host=http://localhost:8000 -u 10 -r 2 -t 60s

# 階梯式壓力測試
for users in 10 20 50 100; do
    echo "測試 $users 用戶負載..."
    locust -f locustfile.py --host=http://localhost:8000 -u $users -r 5 -t 120s --html=report_${users}_users.html
done
```

## 🛡️ 安全測試框架

### 安全掃描工具
```bash
# 依賴漏洞掃描
poetry run safety check

# 程式碼安全分析
poetry run bandit -r src/

# SAST 掃描
semgrep --config=auto src/

# 容器安全掃描
docker run --rm -v $(pwd):/workspace clair/clair:latest
```

### 安全測試案例
```python
class TestSecurityFeatures:
    def test_sql_injection_protection(self):
        """測試 SQL 注入保護"""
        malicious_input = "'; DROP TABLE users; --"
        response = self.client.get(f"/api/search?q={malicious_input}")
        
        # 確保請求被正確處理或拒絕
        assert response.status_code in [400, 422]
        
        # 確保資料庫完整性
        users_count = self.db.query("SELECT COUNT(*) FROM users").scalar()
        assert users_count > 0
    
    def test_xss_protection(self):
        """測試 XSS 攻擊保護"""
        malicious_script = "<script>alert('XSS')</script>"
        response = self.client.post("/api/comments", json={
            "content": malicious_script
        })
        
        # 確保腳本被適當轉義
        saved_comment = self.db.get_comment(response.json()["id"])
        assert "<script>" not in saved_comment.content
    
    def test_authentication_required(self):
        """測試認證保護"""
        response = self.client.get("/api/protected-resource")
        assert response.status_code == 401
```

## 📊 測試資料管理

### 測試資料策略
1. **靜態測試資料**：固定的參考資料
2. **動態測試資料**：每次測試生成
3. **真實資料子集**：生產資料的匿名化版本
4. **合成資料**：人工生成的測試資料

### 測試資料工廠
```python
# test_factories.py
import factory
from faker import Faker

fake = Faker(['zh_TW'])

class UserFactory(factory.Factory):
    class Meta:
        model = User
    
    name = factory.LazyFunction(lambda: fake.name())
    email = factory.LazyFunction(lambda: fake.email())
    created_at = factory.LazyFunction(lambda: fake.date_time())

class MachineFactory(factory.Factory):
    class Meta:
        model = Machine
    
    machine_id = factory.Sequence(lambda n: f"M{n:03d}")
    name = factory.LazyFunction(lambda: f"CNC車床{fake.random_letter()}")
    department = factory.Iterator(["加工部", "沖壓部", "組裝部"])
    utilization_rate = factory.LazyFunction(lambda: fake.random.uniform(60, 95))
```

## 🎮 CI/CD 測試整合

### GitHub Actions 測試工作流程
```yaml
# .github/workflows/test.yml
name: 測試流程

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: 設置 Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: 安裝依賴
      run: |
        pip install poetry
        poetry install
    
    - name: 執行單元測試
      run: poetry run pytest tests/unit/ -v
    
    - name: 執行整合測試
      run: poetry run pytest tests/integration/ -v
    
    - name: 生成覆蓋率報告
      run: poetry run pytest --cov=src --cov-report=xml
    
    - name: 上傳覆蓋率結果
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## 📈 測試度量指標

### 品質度量
- **缺陷密度**：每千行程式碼的缺陷數量
- **缺陷逃逸率**：未被測試發現的生產缺陷比例
- **測試執行時間**：完整測試套件執行時間
- **測試穩定性**：測試結果一致性

### 效率度量
- **測試自動化率**：自動化測試覆蓋比例
- **平均修復時間**：從發現缺陷到修復完成的時間
- **回歸測試時間**：回歸測試完整執行時間
- **測試環境可用性**：測試環境正常運行時間

## ❓ 測試常見問題

**Q: 測試執行時間過長怎麼辦？**
A: 1) 使用平行執行 2) 優化測試案例 3) 分層測試執行

**Q: 測試環境不穩定如何處理？**
A: 1) 使用容器化環境 2) 重試機制 3) 環境健康檢查

**Q: 如何處理外部依賴？**
A: 1) Mock 外部服務 2) 使用測試替身 3) 契約測試

**Q: 測試覆蓋率低於標準怎麼辦？**
A: 1) 分析未覆蓋程式碼 2) 補充測試案例 3) 檢查測試品質

## 💡 測試最佳實踐

### 測試設計原則
- **獨立性**：測試間互不影響
- **可重複性**：結果一致可重現
- **快速回饋**：快速發現問題
- **易維護性**：測試易於理解和修改

### 測試執行策略
- **失敗快速**：優先執行易失敗的測試
- **分層執行**：根據測試類型分層執行
- **持續執行**：持續整合環境中自動執行
- **定期清理**：定期清理無效測試

## 🔗 相關資源

- [測試驅動開發指南](../development/tdd-guide.md)
- [Mock 測試最佳實踐](../testing/mocking-best-practices.md)
- [效能測試策略](../testing/performance-testing.md)
- [安全測試指南](../security/security-testing.md)
- [CI/CD 整合配置](../cicd/testing-integration.md)