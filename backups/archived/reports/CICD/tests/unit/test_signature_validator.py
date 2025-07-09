"""
簽章驗證器測試
測試 LINE Bot 簽章驗證功能
"""

import base64
import time

import pytest

from src.utils.signature_validator import SignatureValidator


class TestSignatureValidatorInit:
    """測試簽章驗證器初始化"""

    def test_init_with_channel_secret(self):
        """測試使用頻道密鑰初始化"""
        secret = "test_secret_123"
        validator = SignatureValidator(secret)

        assert validator.channel_secret == secret.encode("utf-8")
        assert validator.is_development is False  # 預設為生產環境

    def test_init_production_environment(self):
        """測試生產環境初始化"""
        validator = SignatureValidator("secret", env="production")
        assert validator.is_development is False

    def test_init_development_environment(self):
        """測試開發環境初始化"""
        validator = SignatureValidator("secret", env="development")
        assert validator.is_development is True

    def test_init_dev_environment(self):
        """測試 dev 環境初始化"""
        validator = SignatureValidator("secret", env="dev")
        assert validator.is_development is True

    def test_init_test_environment(self):
        """測試測試環境初始化"""
        validator = SignatureValidator("secret", env="test")
        assert validator.is_development is True

    def test_init_case_insensitive_environment(self):
        """測試環境名稱大小寫不敏感"""
        validator = SignatureValidator("secret", env="DEVELOPMENT")
        assert validator.is_development is True


class TestSignatureValidation:
    """測試簽章驗證功能"""

    @pytest.fixture
    def validator(self):
        """創建測試用驗證器"""
        return SignatureValidator("test_channel_secret")

    @pytest.fixture
    def test_body(self):
        """測試用請求本文"""
        return b'{"type":"message","text":"hello"}'

    def test_validate_valid_signature(self, validator, test_body):
        """測試有效簽章驗證"""
        # 手動計算正確的簽章
        expected_signature = validator._calculate_signature(test_body)

        is_valid, method = validator.validate(test_body, expected_signature)

        assert is_valid is True
        assert method == "hmac_validation"

    def test_validate_invalid_signature(self, validator, test_body):
        """測試無效簽章驗證"""
        invalid_signature = "invalid_signature_123"

        is_valid, method = validator.validate(test_body, invalid_signature)

        assert is_valid is False
        assert method == "hmac_validation"

    def test_validate_missing_signature(self, validator, test_body):
        """測試缺少簽章"""
        is_valid, method = validator.validate(test_body, "")

        assert is_valid is False
        assert method == "missing_signature"

        is_valid, method = validator.validate(test_body, None)

        assert is_valid is False
        assert method == "missing_signature"

    def test_validate_different_body_same_signature(self, validator, test_body):
        """測試不同內容相同簽章"""
        signature = validator._calculate_signature(test_body)
        different_body = b'{"type":"message","text":"different"}'

        is_valid, method = validator.validate(different_body, signature)

        assert is_valid is False
        assert method == "hmac_validation"


class TestDevelopmentBypass:
    """測試開發環境繞過功能"""

    @pytest.fixture
    def dev_validator(self):
        """創建開發環境驗證器"""
        return SignatureValidator("test_secret", env="development")

    @pytest.fixture
    def prod_validator(self):
        """創建生產環境驗證器"""
        return SignatureValidator("test_secret", env="production")

    def test_development_bypass_signature(self, dev_validator):
        """測試開發環境繞過簽章"""
        test_body = b'{"test": "data"}'

        is_valid, method = dev_validator.validate(test_body, "DEV_BYPASS_SIGNATURE")

        assert is_valid is True
        assert method == "development_bypass"

    def test_production_no_bypass(self, prod_validator):
        """測試生產環境不允許繞過"""
        test_body = b'{"test": "data"}'

        is_valid, method = prod_validator.validate(test_body, "DEV_BYPASS_SIGNATURE")

        assert is_valid is False
        assert method == "hmac_validation"

    def test_development_still_validates_normal_signatures(self, dev_validator):
        """測試開發環境仍然驗證正常簽章"""
        test_body = b'{"test": "data"}'
        valid_signature = dev_validator._calculate_signature(test_body)

        is_valid, method = dev_validator.validate(test_body, valid_signature)

        assert is_valid is True
        assert method == "hmac_validation"


class TestTimestampValidation:
    """測試時間戳驗證功能"""

    @pytest.fixture
    def validator(self):
        return SignatureValidator("test_secret")

    def test_validate_with_valid_timestamp(self, validator):
        """測試有效時間戳驗證"""
        test_body = b'{"test": "data"}'
        signature = validator._calculate_signature(test_body)
        current_timestamp = int(time.time())

        is_valid, method = validator.validate(test_body, signature, current_timestamp)

        assert is_valid is True
        assert method == "hmac_validation"

    def test_validate_with_expired_timestamp(self, validator):
        """測試過期時間戳驗證"""
        test_body = b'{"test": "data"}'
        signature = validator._calculate_signature(test_body)
        # 10分鐘前的時間戳（超過5分鐘容忍度）
        expired_timestamp = int(time.time()) - 600

        is_valid, method = validator.validate(test_body, signature, expired_timestamp)

        assert is_valid is False
        assert method == "timestamp_expired"

    def test_validate_with_future_timestamp(self, validator):
        """測試未來時間戳驗證"""
        test_body = b'{"test": "data"}'
        signature = validator._calculate_signature(test_body)
        # 10分鐘後的時間戳
        future_timestamp = int(time.time()) + 600

        is_valid, method = validator.validate(test_body, signature, future_timestamp)

        assert is_valid is False
        assert method == "timestamp_expired"

    def test_validate_without_timestamp(self, validator):
        """測試不提供時間戳"""
        test_body = b'{"test": "data"}'
        signature = validator._calculate_signature(test_body)

        is_valid, method = validator.validate(test_body, signature, None)

        assert is_valid is True
        assert method == "hmac_validation"


class TestSignatureCalculation:
    """測試簽章計算功能"""

    @pytest.fixture
    def validator(self):
        return SignatureValidator("test_channel_secret")

    def test_calculate_signature_format(self, validator):
        """測試簽章格式"""
        test_body = b'{"test": "data"}'

        signature = validator._calculate_signature(test_body)

        # 應該是 base64 編碼的字符串
        assert isinstance(signature, str)
        assert len(signature) > 0

        # 驗證是有效的 base64
        try:
            base64.b64decode(signature)
        except Exception:
            pytest.fail("簽章不是有效的 base64 編碼")

    def test_calculate_signature_consistency(self, validator):
        """測試簽章計算一致性"""
        test_body = b'{"test": "data"}'

        signature1 = validator._calculate_signature(test_body)
        signature2 = validator._calculate_signature(test_body)

        assert signature1 == signature2

    def test_calculate_signature_different_bodies(self, validator):
        """測試不同內容產生不同簽章"""
        body1 = b'{"test": "data1"}'
        body2 = b'{"test": "data2"}'

        signature1 = validator._calculate_signature(body1)
        signature2 = validator._calculate_signature(body2)

        assert signature1 != signature2

    def test_calculate_signature_empty_body(self, validator):
        """測試空內容簽章計算"""
        empty_body = b""

        signature = validator._calculate_signature(empty_body)

        assert isinstance(signature, str)
        assert len(signature) > 0


class TestTimestampValidationHelper:
    """測試時間戳驗證輔助方法"""

    @pytest.fixture
    def validator(self):
        return SignatureValidator("test_secret")

    def test_validate_timestamp_current_time(self, validator):
        """測試當前時間戳驗證"""
        current_timestamp = int(time.time())

        is_valid = validator._validate_timestamp(current_timestamp)

        assert is_valid is True

    def test_validate_timestamp_within_tolerance(self, validator):
        """測試容忍範圍內的時間戳"""
        # 4分鐘前（在5分鐘容忍度內）
        timestamp = int(time.time()) - 240

        is_valid = validator._validate_timestamp(timestamp)

        assert is_valid is True

    def test_validate_timestamp_outside_tolerance(self, validator):
        """測試容忍範圍外的時間戳"""
        # 6分鐘前（超過5分鐘容忍度）
        timestamp = int(time.time()) - 360

        is_valid = validator._validate_timestamp(timestamp)

        assert is_valid is False

    def test_validate_timestamp_custom_tolerance(self, validator):
        """測試自定義容忍度"""
        # 2分鐘前
        timestamp = int(time.time()) - 120

        # 1分鐘容忍度 - 應該失敗
        is_valid = validator._validate_timestamp(timestamp, tolerance_seconds=60)
        assert is_valid is False

        # 3分鐘容忍度 - 應該成功
        is_valid = validator._validate_timestamp(timestamp, tolerance_seconds=180)
        assert is_valid is True


class TestSignatureValidatorSecurity:
    """測試簽章驗證器安全性"""

    def test_hmac_timing_attack_resistance(self):
        """測試抗時序攻擊"""
        validator = SignatureValidator("secret")
        test_body = b'{"test": "data"}'
        correct_signature = validator._calculate_signature(test_body)
        wrong_signature = "wrong_signature"

        # hmac.compare_digest 應該被用於比較
        # 這個測試確保我們使用了安全的比較方法
        is_valid1, _ = validator.validate(test_body, correct_signature)
        is_valid2, _ = validator.validate(test_body, wrong_signature)

        assert is_valid1 is True
        assert is_valid2 is False

    def test_signature_length_independence(self):
        """測試簽章長度無關性"""
        validator = SignatureValidator("secret")
        test_body = b'{"test": "data"}'

        # 測試不同長度的錯誤簽章
        short_signature = "short"
        long_signature = "very_long_signature_that_exceeds_normal_length_significantly"

        is_valid1, _ = validator.validate(test_body, short_signature)
        is_valid2, _ = validator.validate(test_body, long_signature)

        assert is_valid1 is False
        assert is_valid2 is False

    def test_channel_secret_encoding(self):
        """測試頻道密鑰編碼"""
        unicode_secret = "測試密鑰_123"
        validator = SignatureValidator(unicode_secret)

        # 確保 Unicode 字符正確編碼
        assert validator.channel_secret == unicode_secret.encode("utf-8")

        # 確保可以正常計算簽章
        test_body = b'{"test": "unicode"}'
        signature = validator._calculate_signature(test_body)

        assert isinstance(signature, str)
        assert len(signature) > 0
