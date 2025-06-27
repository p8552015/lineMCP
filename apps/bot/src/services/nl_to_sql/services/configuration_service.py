"""
配置管理服務

實現 SRP (單一職責原則)：
- 專門負責配置檔案的載入和管理
- 不包含解析、查詢建構等其他職責

實現 DIP (依賴倒置原則)：
- 實現 IConfiguration 抽象介面
- 可被其他組件透過介面使用

實現 OCP (開閉原則)：
- 支援多種配置來源（檔案、資料庫等）
- 可擴展新的配置格式
"""

from pathlib import Path
from typing import Any

import structlog
import yaml

from ..interfaces.statistics_interfaces import IConfiguration

logger = structlog.get_logger()


class ConfigurationService(IConfiguration):
    """
    配置管理服務

    職責：
    - 載入和管理 YAML 配置檔案
    - 提供配置資料的存取介面
    - 支援配置熱更新和驗證

    設計原則：
    - SRP: 只負責配置管理，不處理業務邏輯
    - DIP: 實現 IConfiguration 抽象介面
    - OCP: 支援多種配置來源和格式擴展
    """

    def __init__(self, config_base_path: str | None = None):
        """
        初始化配置服務

        Args:
            config_base_path: 配置檔案基礎路徑，預設為模組內的 config 目錄
        """
        # 環境變數優先級：NL_TO_SQL_CONFIG_DIR > 傳入參數 > 預設路徑
        from src.config import get_settings

        settings = get_settings()
        env_config_dir = (
            settings.nl_to_sql_config_dir if settings.nl_to_sql_config_dir else None
        )

        if env_config_dir:
            self._config_base_path = Path(env_config_dir)
        elif config_base_path:
            self._config_base_path = Path(config_base_path)
        else:
            # 預設路徑：相對於當前檔案的 ../config 目錄
            current_dir = Path(__file__).parent
            self._config_base_path = current_dir.parent / "config"

        # 載入環境變數配置
        self._env_config = self._load_environment_variables()

        # 配置快取
        self._config_cache: dict[str, Any] = {}

        # 配置檔案路徑
        self._config_files = {
            "query_patterns": self._config_base_path / "query_patterns.yaml",
            "sql_templates": self._config_base_path / "sql_templates.yaml",
            "parser_settings": self._config_base_path / "parser_settings.yaml",
        }

        # 載入所有配置
        self._load_all_configurations()

        # 合併環境變數配置
        self._merge_environment_config()

        logger.info(
            "⚙️ 配置服務初始化完成",
            config_path=str(self._config_base_path),
            config_files_count=len(self._config_files),
            env_config_count=len(self._env_config),
        )

    def get_query_patterns(self) -> dict[str, Any]:
        """
        獲取查詢模式配置

        Returns:
            Dict[str, Any]: 查詢模式配置字典
        """
        patterns_config = self._config_cache.get("query_patterns", {})

        # 提取主要的查詢模式
        query_patterns = {}
        for key, value in patterns_config.items():
            if isinstance(value, dict) and "patterns" in value:
                query_patterns[key] = value

        logger.debug("📋 獲取查詢模式", pattern_count=len(query_patterns))
        return query_patterns

    def get_sql_templates(self) -> dict[str, str]:
        """
        獲取 SQL 模板配置

        Returns:
            Dict[str, str]: 模板名稱到模板字串的映射
        """
        templates_config = self._config_cache.get("sql_templates", {})

        # 提取模板字串
        sql_templates = {}
        for key, value in templates_config.items():
            if isinstance(value, dict) and "template" in value:
                sql_templates[key] = value["template"].strip()

        logger.debug("📝 獲取 SQL 模板", template_count=len(sql_templates))
        return sql_templates

    def get_parser_settings(self) -> dict[str, Any]:
        """
        獲取解析器設定

        Returns:
            Dict[str, Any]: 解析器設定字典
        """
        settings = self._config_cache.get("parser_settings", {})
        logger.debug("⚙️ 獲取解析器設定", settings_keys=list(settings.keys()))
        return settings

    def get_template_security_config(self) -> dict[str, Any]:
        """
        獲取模板安全性配置

        Returns:
            Dict[str, Any]: 安全性配置字典
        """
        templates_config = self._config_cache.get("sql_templates", {})

        # 提取安全性設定
        template_settings = templates_config.get("template_settings", {})
        security_config = template_settings.get("security", {})

        logger.debug(
            "🔒 獲取模板安全性配置",
            security_keys=list(security_config.keys()),
            forbidden_keywords_count=len(security_config.get("forbidden_keywords", [])),
        )

        return security_config

    def get_setting(self, key_path: str, default: Any = None) -> Any:
        """
        獲取特定設定值（支援路徑式存取）

        Args:
            key_path: 設定鍵路徑，如
                "global_parser_settings.default_confidence_threshold"
            default: 預設值

        Returns:
            Any: 設定值
        """
        try:
            keys = key_path.split(".")
            current_value = self._config_cache

            for key in keys:
                if isinstance(current_value, dict) and key in current_value:
                    current_value = current_value[key]
                else:
                    logger.debug("⚠️ 設定路徑不存在", key_path=key_path)
                    return default

            return current_value

        except Exception as e:
            logger.warning("❌ 獲取設定失敗", key_path=key_path, error=str(e))
            return default

    def set_setting(self, key_path: str, value: Any) -> bool:
        """
        設定特定設定值

        Args:
            key_path: 設定鍵路徑
            value: 新值

        Returns:
            bool: 是否設定成功
        """
        try:
            keys = key_path.split(".")
            current_dict = self._config_cache

            # 導航到目標位置
            for key in keys[:-1]:
                if key not in current_dict:
                    current_dict[key] = {}
                current_dict = current_dict[key]

            # 設定值
            current_dict[keys[-1]] = value

            logger.info("✅ 設定已更新", key_path=key_path, value=value)
            return True

        except Exception as e:
            logger.error("❌ 設定更新失敗", key_path=key_path, error=str(e))
            return False

    def reload_config(self) -> None:
        """
        重新載入所有配置檔案
        """
        try:
            logger.info("🔄 開始重新載入配置")

            old_cache = self._config_cache.copy()
            self._config_cache.clear()

            self._load_all_configurations()

            logger.info(
                "✅ 配置重新載入完成",
                config_count=len(self._config_cache),
                changed_configs=self._get_changed_configs(old_cache),
            )

        except Exception as e:
            logger.error("❌ 配置重新載入失敗", error=str(e))
            # 恢復舊配置
            self._config_cache = old_cache
            raise

    def validate_configuration(self) -> dict[str, Any]:
        """
        驗證配置的有效性

        Returns:
            Dict[str, Any]: 驗證結果
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "config_stats": {},
        }

        # 驗證查詢模式配置
        patterns_validation = self._validate_query_patterns()
        validation_result["config_stats"]["query_patterns"] = patterns_validation
        if not patterns_validation["is_valid"]:
            validation_result["is_valid"] = False
            validation_result["errors"].extend(patterns_validation["errors"])

        # 驗證 SQL 模板配置
        templates_validation = self._validate_sql_templates()
        validation_result["config_stats"]["sql_templates"] = templates_validation
        if not templates_validation["is_valid"]:
            validation_result["is_valid"] = False
            validation_result["errors"].extend(templates_validation["errors"])

        # 驗證解析器設定
        settings_validation = self._validate_parser_settings()
        validation_result["config_stats"]["parser_settings"] = settings_validation
        if not settings_validation["is_valid"]:
            validation_result["is_valid"] = False
            validation_result["errors"].extend(settings_validation["errors"])

        return validation_result

    def get_configuration_summary(self) -> dict[str, Any]:
        """
        獲取配置摘要資訊

        Returns:
            Dict[str, Any]: 配置摘要
        """
        summary = {
            "config_base_path": str(self._config_base_path),
            "loaded_configs": list(self._config_cache.keys()),
            "config_file_status": {},
            "total_query_patterns": 0,
            "total_sql_templates": 0,
            "parser_count": 0,
        }

        # 檢查配置檔案狀態
        for name, path in self._config_files.items():
            summary["config_file_status"][name] = {
                "path": str(path),
                "exists": path.exists(),
                "size": path.stat().st_size if path.exists() else 0,
                "loaded": name in self._config_cache,
            }

        # 統計配置內容
        query_patterns = self.get_query_patterns()
        summary["total_query_patterns"] = len(query_patterns)

        sql_templates = self.get_sql_templates()
        summary["total_sql_templates"] = len(sql_templates)

        parser_settings = self.get_parser_settings()
        if "parser_weights" in parser_settings.get("strategy_settings", {}):
            summary["parser_count"] = len(
                parser_settings["strategy_settings"]["parser_weights"]
            )

        return summary

    def _load_environment_variables(self) -> dict[str, Any]:
        """
        載入環境變數配置

        Returns:
            Dict[str, Any]: 環境變數配置字典
        """
        env_config = {}

        # 使用統一的 settings 物件取代直接的環境變數存取
        from src.config import get_settings

        settings = get_settings()

        # NL-to-SQL 功能開關
        nl_to_sql_enabled = settings.nl_to_sql_enabled
        env_config["nl_to_sql_enabled"] = nl_to_sql_enabled

        # 組合解析器設定
        fallback_threshold = settings.composite_parser_fallback_threshold
        env_config["composite_parser_fallback_threshold"] = fallback_threshold

        # 統計功能開關
        enable_statistics = settings.enable_query_statistics
        env_config["enable_query_statistics"] = enable_statistics

        # AI 解析器超時設定 (毫秒)
        ai_timeout = settings.ai_parser_timeout
        env_config["ai_parser_timeout"] = ai_timeout

        # 規則解析器快取大小
        cache_size = settings.rule_parser_cache_size
        env_config["rule_parser_cache_size"] = cache_size

        # 配置熱更新開關
        hot_reload = settings.enable_config_hot_reload
        env_config["enable_config_hot_reload"] = hot_reload

        logger.info(
            "🌍 環境變數配置載入完成",
            enabled=nl_to_sql_enabled,
            fallback_threshold=fallback_threshold,
            enable_statistics=enable_statistics,
            ai_timeout=ai_timeout,
            cache_size=cache_size,
            hot_reload=hot_reload,
        )

        return env_config

    def _merge_environment_config(self) -> None:
        """
        合併環境變數配置到配置快取中
        環境變數優先級高於檔案配置
        """
        # 建立環境變數配置節點
        env_section = {
            "runtime_config": self._env_config,
            "feature_flags": {
                "nl_to_sql_enabled": self._env_config["nl_to_sql_enabled"],
                "enable_query_statistics": self._env_config["enable_query_statistics"],
                "enable_config_hot_reload": self._env_config[
                    "enable_config_hot_reload"
                ],
            },
            "performance_settings": {
                "ai_parser_timeout_ms": self._env_config["ai_parser_timeout"],
                "rule_parser_cache_size": self._env_config["rule_parser_cache_size"],
                "composite_parser_fallback_threshold": self._env_config[
                    "composite_parser_fallback_threshold"
                ],
            },
        }

        # 合併到解析器設定中
        if "parser_settings" not in self._config_cache:
            self._config_cache["parser_settings"] = {}

        # 環境變數覆蓋檔案配置
        if "environment_overrides" not in self._config_cache["parser_settings"]:
            self._config_cache["parser_settings"]["environment_overrides"] = {}

        self._config_cache["parser_settings"]["environment_overrides"].update(
            env_section
        )

        # 直接設定常用配置到根層級，方便快速存取
        self._config_cache["_env_runtime"] = self._env_config

        logger.info("🔄 環境變數配置已合併到設定快取")

    def get_environment_config(self) -> dict[str, Any]:
        """
        獲取環境變數配置

        Returns:
            Dict[str, Any]: 環境變數配置字典
        """
        return self._env_config.copy()

    def is_feature_enabled(self, feature_name: str) -> bool:
        """
        檢查功能是否啟用

        Args:
            feature_name: 功能名稱

        Returns:
            bool: 功能是否啟用
        """
        feature_map = {
            "nl_to_sql": self._env_config.get("nl_to_sql_enabled", True),
            "query_statistics": self._env_config.get("enable_query_statistics", True),
            "config_hot_reload": self._env_config.get(
                "enable_config_hot_reload", False
            ),
        }

        return feature_map.get(feature_name, False)

    def get_performance_setting(self, setting_name: str, default: Any = None) -> Any:
        """
        獲取效能設定值

        Args:
            setting_name: 設定名稱
            default: 預設值

        Returns:
            Any: 設定值
        """
        performance_map = {
            "ai_parser_timeout": self._env_config.get("ai_parser_timeout", 3000),
            "rule_parser_cache_size": self._env_config.get(
                "rule_parser_cache_size", 1000
            ),
            "composite_parser_fallback_threshold": self._env_config.get(
                "composite_parser_fallback_threshold", 0.5
            ),
        }

        return performance_map.get(setting_name, default)

    def get_config_value(
        self, key: str, default: Any = None, config_section: str | None = None
    ) -> Any:
        """
        獲取配置值（實現 IConfiguration 介面）

        Args:
            key: 配置鍵名
            default: 預設值
            config_section: 可選的配置段落

        Returns:
            Any: 配置值
        """
        key_path = f"{config_section}.{key}" if config_section else key

        return self.get_setting(key_path, default)

    def set_config_value(
        self, key: str, value: Any, config_section: str | None = None
    ) -> None:
        """
        設置配置值（實現 IConfiguration 介面）

        Args:
            key: 配置鍵名
            value: 配置值
            config_section: 可選的配置段落
        """
        key_path = f"{config_section}.{key}" if config_section else key

        self.set_setting(key_path, value)

    def validate_config(self) -> dict[str, Any]:
        """
        驗證配置的有效性（實現 IConfiguration 介面）

        Returns:
            Dict[str, Any]: 驗證結果
        """
        return self.validate_configuration()

    def get_config_metadata(self) -> dict[str, Any]:
        """
        獲取配置元數據（實現 IConfiguration 介面）

        Returns:
            Dict[str, Any]: 配置元數據
        """
        from datetime import datetime

        metadata = {
            "version": "1.0.0",
            "last_updated": datetime.now().isoformat(),
            "source": "yaml_files_and_environment",
            "config_base_path": str(self._config_base_path),
            "environment_variables_loaded": len(self._env_config),
            "yaml_files_loaded": len(
                [
                    name
                    for name, data in self._config_cache.items()
                    if name in self._config_files and data
                ]
            ),
            "total_config_keys": sum(
                self._count_keys(data) if isinstance(data, dict) else 1
                for data in self._config_cache.values()
            ),
            "features": {
                "nl_to_sql_enabled": self.is_feature_enabled("nl_to_sql"),
                "query_statistics_enabled": self.is_feature_enabled("query_statistics"),
                "config_hot_reload_enabled": self.is_feature_enabled(
                    "config_hot_reload"
                ),
            },
            "performance_settings": {
                "ai_parser_timeout_ms": self.get_performance_setting(
                    "ai_parser_timeout"
                ),
                "rule_parser_cache_size": self.get_performance_setting(
                    "rule_parser_cache_size"
                ),
                "composite_parser_fallback_threshold": self.get_performance_setting(
                    "composite_parser_fallback_threshold"
                ),
            },
        }

        return metadata

    def _count_keys(self, data: dict) -> int:
        """
        遞歸計算配置字典中的鍵總數

        Args:
            data: 配置字典

        Returns:
            int: 鍵的總數
        """
        count = 0
        for value in data.values():
            if isinstance(value, dict):
                count += self._count_keys(value)
            else:
                count += 1
        return count

    def _load_all_configurations(self) -> None:
        """
        載入所有配置檔案
        """
        for config_name, config_path in self._config_files.items():
            try:
                if config_path.exists():
                    with open(config_path, encoding="utf-8") as file:
                        config_data = yaml.safe_load(file)
                        self._config_cache[config_name] = config_data

                        logger.debug(
                            "📁 配置檔案載入成功",
                            config=config_name,
                            path=str(config_path),
                        )
                else:
                    # 降級為 debug 級別，因為會載入空配置作為後備
                    logger.debug(
                        "⚠️ 配置檔案不存在", config=config_name, path=str(config_path)
                    )
                    self._config_cache[config_name] = {}

            except Exception as e:
                logger.error(
                    "❌ 配置檔案載入失敗",
                    config=config_name,
                    path=str(config_path),
                    error=str(e),
                )
                self._config_cache[config_name] = {}

    def _validate_query_patterns(self) -> dict[str, Any]:
        """
        驗證查詢模式配置

        Returns:
            Dict[str, Any]: 驗證結果
        """
        result = {"is_valid": True, "errors": [], "pattern_count": 0}

        patterns = self.get_query_patterns()
        result["pattern_count"] = len(patterns)

        for pattern_name, pattern_config in patterns.items():
            if not isinstance(pattern_config, dict):
                result["errors"].append(f"查詢模式 {pattern_name} 格式錯誤")
                result["is_valid"] = False
                continue

            if "patterns" not in pattern_config:
                result["errors"].append(f"查詢模式 {pattern_name} 缺少 patterns 欄位")
                result["is_valid"] = False

            if "confidence" not in pattern_config:
                result["errors"].append(f"查詢模式 {pattern_name} 缺少 confidence 欄位")

        return result

    def _validate_sql_templates(self) -> dict[str, Any]:
        """
        驗證 SQL 模板配置

        Returns:
            Dict[str, Any]: 驗證結果
        """
        result = {"is_valid": True, "errors": [], "template_count": 0}

        templates = self.get_sql_templates()
        result["template_count"] = len(templates)

        for template_name, template_sql in templates.items():
            if not template_sql or not template_sql.strip():
                result["errors"].append(f"SQL 模板 {template_name} 為空")
                result["is_valid"] = False
                continue

            # 基本 SQL 語法檢查
            if not template_sql.strip().upper().startswith("SELECT"):
                result["errors"].append(f"SQL 模板 {template_name} 不是以 SELECT 開始")
                result["is_valid"] = False

        return result

    def _validate_parser_settings(self) -> dict[str, Any]:
        """
        驗證解析器設定

        Returns:
            Dict[str, Any]: 驗證結果
        """
        result = {"is_valid": True, "errors": [], "settings_count": 0}

        settings = self.get_parser_settings()
        result["settings_count"] = len(settings)

        # 檢查必要設定
        required_sections = ["global_parser_settings", "strategy_settings"]
        for section in required_sections:
            if section not in settings:
                result["errors"].append(f"缺少必要設定區段: {section}")
                result["is_valid"] = False

        return result

    def _get_changed_configs(self, old_cache: dict[str, Any]) -> list[str]:
        """
        獲取變更的配置列表

        Args:
            old_cache: 舊配置快取

        Returns:
            List[str]: 變更的配置名稱列表
        """
        changed = []

        for config_name in self._config_cache:
            if config_name not in old_cache:
                changed.append(f"+ {config_name}")
            elif self._config_cache[config_name] != old_cache[config_name]:
                changed.append(f"* {config_name}")

        for config_name in old_cache:
            if config_name not in self._config_cache:
                changed.append(f"- {config_name}")

        return changed
