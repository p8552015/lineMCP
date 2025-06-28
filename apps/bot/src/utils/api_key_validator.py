"""
API Key 驗證和管理工具
防止 API Key 截斷和格式錯誤的完整解決方案
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import structlog

logger = structlog.get_logger()


@dataclass
class APIKeyInfo:
    """API Key 信息結構"""

    provider: str
    key: str
    is_valid: bool
    length: int
    prefix: str
    checksum: str
    error_message: str | None = None


class APIKeyValidator:
    """API Key 驗證器 - 防止截斷和格式錯誤"""

    # API Key 格式規範
    KEY_PATTERNS = {
        "openai": {
            "pattern": r"^sk-proj-[A-Za-z0-9_-]{20,}T3BlbkFJ[A-Za-z0-9_-]{20,}$",
            "min_length": 100,
            "max_length": 200,
            "prefix": "sk-proj-",
            "required_parts": ["sk-proj-", "T3BlbkFJ"],
        },
        "gemini": {
            "pattern": r"^AIza[A-Za-z0-9_-]{35}$",
            "min_length": 39,
            "max_length": 39,
            "prefix": "AIza",
            "required_parts": ["AIza"],
        },
    }

    def __init__(self, env_file_path: str = ".env"):
        self.env_file_path = Path(env_file_path)
        self.backup_path = self.env_file_path.with_suffix(".env.backup")

    def validate_key(self, key: str, provider: str) -> APIKeyInfo:
        """驗證 API Key 完整性和格式"""
        if provider not in self.KEY_PATTERNS:
            return APIKeyInfo(
                provider=provider,
                key=key,
                is_valid=False,
                length=len(key),
                prefix=key[:10] if key else "",
                checksum="",
                error_message=f"不支援的 API 提供商: {provider}",
            )

        pattern_info = self.KEY_PATTERNS[provider]

        # 檢查長度
        if len(key) < pattern_info["min_length"]:
            return APIKeyInfo(
                provider=provider,
                key=key,
                is_valid=False,
                length=len(key),
                prefix=key[:10] if key else "",
                checksum=self._calculate_checksum(key),
                error_message=(
                    f"API Key 太短，預期至少 {pattern_info['min_length']} 字符，"
                    f"實際 {len(key)} 字符"
                ),
            )

        if len(key) > pattern_info["max_length"]:
            return APIKeyInfo(
                provider=provider,
                key=key,
                is_valid=False,
                length=len(key),
                prefix=key[:10] if key else "",
                checksum=self._calculate_checksum(key),
                error_message=(
                    f"API Key 太長，預期最多 {pattern_info['max_length']} 字符，"
                    f"實際 {len(key)} 字符"
                ),
            )

        # 檢查前綴
        if not key.startswith(pattern_info["prefix"]):
            return APIKeyInfo(
                provider=provider,
                key=key,
                is_valid=False,
                length=len(key),
                prefix=key[:10] if key else "",
                checksum=self._calculate_checksum(key),
                error_message=(f"API Key 前綴錯誤，預期以 '{pattern_info['prefix']}' 開始"),
            )

        # 檢查必要部分
        for required_part in pattern_info["required_parts"]:
            if required_part not in key:
                return APIKeyInfo(
                    provider=provider,
                    key=key,
                    is_valid=False,
                    length=len(key),
                    prefix=key[:10] if key else "",
                    checksum=self._calculate_checksum(key),
                    error_message=f"API Key 缺少必要部分: '{required_part}'",
                )

        # 檢查格式
        if not re.match(pattern_info["pattern"], key):
            return APIKeyInfo(
                provider=provider,
                key=key,
                is_valid=False,
                length=len(key),
                prefix=key[:10] if key else "",
                checksum=self._calculate_checksum(key),
                error_message="API Key 格式不符合規範",
            )

        return APIKeyInfo(
            provider=provider,
            key=key,
            is_valid=True,
            length=len(key),
            prefix=key[:10],
            checksum=self._calculate_checksum(key),
        )

    def _calculate_checksum(self, key: str) -> str:
        """計算 API Key 的校驗和"""
        return hashlib.md5(key.encode()).hexdigest()[:8]

    def scan_env_file(self) -> dict[str, APIKeyInfo]:
        """掃描環境文件中的所有 API Keys"""
        results = {}

        if not self.env_file_path.exists():
            logger.warning("環境文件不存在", path=str(self.env_file_path))
            return results

        try:
            with open(self.env_file_path, encoding="utf-8") as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if "=" in line:
                    key_name, key_value = line.split("=", 1)
                    key_name = key_name.strip()
                    key_value = key_value.strip().strip("\"'")

                    # 檢查是否是 API Key
                    provider = None
                    if "OPENAI" in key_name.upper():
                        provider = "openai"
                    elif "GEMINI" in key_name.upper() or "GOOGLE" in key_name.upper():
                        provider = "gemini"

                    if provider:
                        validation_result = self.validate_key(key_value, provider)
                        validation_result.line_number = line_num
                        results[key_name] = validation_result

                        logger.info(
                            "掃描到 API Key",
                            key_name=key_name,
                            provider=provider,
                            is_valid=validation_result.is_valid,
                            length=validation_result.length,
                            line=line_num,
                        )

        except Exception as e:
            logger.error("掃描環境文件失敗", error=str(e))

        return results

    def create_backup(self) -> bool:
        """創建環境文件備份"""
        try:
            if self.env_file_path.exists():
                import shutil

                shutil.copy2(self.env_file_path, self.backup_path)
                logger.info("環境文件備份成功", backup_path=str(self.backup_path))
                return True
        except Exception as e:
            logger.error("創建備份失敗", error=str(e))
        return False

    def safe_update_key(self, key_name: str, new_key: str, provider: str) -> bool:
        """安全更新 API Key"""
        # 先驗證新 Key
        validation = self.validate_key(new_key, provider)
        if not validation.is_valid:
            logger.error(
                "新 API Key 驗證失敗", key_name=key_name, error=validation.error_message
            )
            return False

        # 創建備份
        if not self.create_backup():
            logger.error("無法創建備份，取消更新")
            return False

        try:
            # 讀取現有內容
            lines = []
            if self.env_file_path.exists():
                with open(self.env_file_path, encoding="utf-8") as f:
                    lines = f.readlines()

            # 更新或添加 Key
            key_updated = False
            for i, line in enumerate(lines):
                if line.strip().startswith(f"{key_name}="):
                    lines[i] = f"{key_name}={new_key}\n"
                    key_updated = True
                    break

            if not key_updated:
                lines.append(f"{key_name}={new_key}\n")

            # 寫入文件
            with open(self.env_file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            logger.info(
                "API Key 更新成功",
                key_name=key_name,
                provider=provider,
                length=validation.length,
                checksum=validation.checksum,
            )
            return True

        except Exception as e:
            logger.error("更新 API Key 失敗", error=str(e))
            # 嘗試恢復備份
            try:
                import shutil

                shutil.copy2(self.backup_path, self.env_file_path)
                logger.info("已恢復備份文件")
            except Exception:
                pass
            return False


def main():
    """主函數 - 用於命令行調用"""
    validator = APIKeyValidator()

    print("🔐 API Key 驗證工具")
    print("=" * 50)

    # 掃描現有 Keys
    results = validator.scan_env_file()

    if not results:
        print("❌ 未找到任何 API Keys")
        return

    print(f"📋 找到 {len(results)} 個 API Keys:")
    print()

    for key_name, info in results.items():
        status = "✅ 有效" if info.is_valid else "❌ 無效"
        print(f"🔑 {key_name}")
        print(f"   提供商: {info.provider}")
        print(f"   狀態: {status}")
        print(f"   長度: {info.length}")
        print(f"   前綴: {info.prefix}")
        print(f"   校驗和: {info.checksum}")
        if info.error_message:
            print(f"   錯誤: {info.error_message}")
        print()


if __name__ == "__main__":
    main()
