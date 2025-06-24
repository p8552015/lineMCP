import base64
import hashlib
import hmac
import time


class SignatureValidator:
    """安全的簽章驗證器"""

    def __init__(self, channel_secret: str, env: str = "production"):
        self.channel_secret = channel_secret.encode("utf-8")
        self.is_development = env.lower() in ["development", "dev", "test"]

    def validate(
        self, body: bytes, signature: str, timestamp: int | None = None
    ) -> tuple[bool, str]:
        """
        驗證請求簽章

        Args:
            body: 請求本文的原始位元組
            signature: X-Line-Signature 標頭值
            timestamp: 可選的時間戳檢查

        Returns:
            (is_valid, validation_method)
        """
        if not signature:
            return False, "missing_signature"

        # 開發環境允許特殊簽章（但仍須明確設定）
        if self.is_development and signature == "DEV_BYPASS_SIGNATURE":
            return True, "development_bypass"

        # 時間戳驗證（防重放攻擊）
        if timestamp and not self._validate_timestamp(timestamp):
            return False, "timestamp_expired"

        # 標準 HMAC-SHA256 驗證
        expected_signature = self._calculate_signature(body)
        is_valid = hmac.compare_digest(expected_signature, signature)

        return is_valid, "hmac_validation"

    def _calculate_signature(self, body: bytes) -> str:
        """計算 HMAC-SHA256 簽章"""
        mac = hmac.new(self.channel_secret, body, hashlib.sha256)
        return base64.b64encode(mac.digest()).decode("utf-8")

    def _validate_timestamp(self, timestamp: int, tolerance_seconds: int = 300) -> bool:
        """驗證請求時間戳（5分鐘容忍度）"""
        current_time = int(time.time())
        return abs(current_time - timestamp) <= tolerance_seconds
