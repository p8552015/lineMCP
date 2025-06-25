"""
MCP 安全驗證器
實施零信任安全模型，防止任意代碼執行和注入攻擊
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()


@dataclass
class SecureServerConfig:
    """安全的服務器配置"""
    name: str
    command: str
    args: List[str]
    allowed_params: Set[str]
    working_directory: Optional[str] = None
    environment_vars: Optional[Dict[str, str]] = None
    max_memory_mb: int = 512
    max_cpu_percent: float = 50.0


class MCPSecurityValidator:
    """MCP 安全驗證器 - 零信任安全模型"""
    
    # 白名單：允許執行的 MCP 服務器
    ALLOWED_MCP_SERVERS: Dict[str, SecureServerConfig] = {
        "postgres": SecureServerConfig(
            name="postgres",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-postgres"],
            allowed_params={"connection_string"},
            max_memory_mb=512,
            max_cpu_percent=30.0,
            environment_vars={"NODE_ENV": "production"}
        ),
        "filesystem": SecureServerConfig(
            name="filesystem", 
            command="python",
            args=["-m", "mcp_server_filesystem"],
            allowed_params={"--root-path", "--read-only"},
            max_memory_mb=128,
            max_cpu_percent=15.0
        )
    }
    
    # 危險的命令模式（絕對禁止）
    FORBIDDEN_PATTERNS = [
        r'rm\s+-rf',
        r'sudo\s+',
        r'curl\s+.*\|\s*sh',
        r'wget\s+.*\|\s*sh',
        r'eval\s*\(',
        r'exec\s*\(',
        r'__import__',
        r'subprocess\.',
        r'os\.system',
        r'os\.popen',
    ]
    
    # 允許的路徑前綴
    ALLOWED_PATH_PREFIXES = [
        "/usr/local/bin/python",
        "/usr/bin/python",
        "/opt/homebrew/bin/python",
        str(Path.cwd()),  # 當前專案目錄
    ]
    
    def __init__(self):
        self.validation_cache: Dict[str, bool] = {}
        logger.info("🛡️ MCP 安全驗證器已初始化")
    
    def validate_server_config(self, server_name: str, command: str, 
                             args: List[str], params: Dict[str, str] = None) -> bool:
        """
        驗證服務器配置的安全性
        
        Args:
            server_name: 服務器名稱
            command: 執行命令
            args: 命令參數
            params: 額外參數
            
        Returns:
            bool: 是否通過安全驗證
        """
        try:
            # 生成驗證快取鍵
            cache_key = f"{server_name}:{command}:{':'.join(args)}"
            if cache_key in self.validation_cache:
                return self.validation_cache[cache_key]
            
            # 第一步：檢查是否在白名單中
            if not self._validate_whitelist(server_name):
                logger.error(f"❌ 服務器 '{server_name}' 不在白名單中")
                return False
            
            # 第二步：驗證命令安全性
            if not self._validate_command_safety(command, args):
                logger.error(f"❌ 命令 '{command}' 未通過安全檢查")
                return False
            
            # 第三步：驗證參數安全性
            if params and not self._validate_params_safety(server_name, params):
                logger.error(f"❌ 參數未通過安全檢查: {params}")
                return False
            
            # 第四步：驗證路徑安全性
            if not self._validate_path_safety(command):
                logger.error(f"❌ 路徑 '{command}' 未通過安全檢查")
                return False
            
            # 快取結果
            self.validation_cache[cache_key] = True
            logger.info(f"✅ 服務器配置通過安全驗證: {server_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 安全驗證過程中發生錯誤: {e}")
            return False
    
    def _validate_whitelist(self, server_name: str) -> bool:
        """檢查服務器是否在白名單中"""
        return server_name in self.ALLOWED_MCP_SERVERS
    
    def _validate_command_safety(self, command: str, args: List[str]) -> bool:
        """驗證命令和參數的安全性"""
        full_command = f"{command} {' '.join(args)}"
        
        # 檢查危險模式
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, full_command, re.IGNORECASE):
                logger.error(f"❌ 檢測到危險模式: {pattern}")
                return False
        
        # 檢查特殊字符
        dangerous_chars = [';', '|', '&', '`', '$', '(', ')', '{', '}']
        for char in dangerous_chars:
            if char in full_command:
                logger.error(f"❌ 檢測到危險字符: {char}")
                return False
        
        return True
    
    def _validate_params_safety(self, server_name: str, params: Dict[str, str]) -> bool:
        """驗證參數安全性"""
        config = self.ALLOWED_MCP_SERVERS.get(server_name)
        if not config:
            return False
        
        # 檢查參數是否在允許列表中
        for param_key in params.keys():
            if param_key not in config.allowed_params:
                logger.error(f"❌ 不允許的參數: {param_key}")
                return False
        
        # 檢查參數值安全性
        for param_value in params.values():
            if not self._validate_param_value(param_value):
                logger.error(f"❌ 參數值不安全: {param_value}")
                return False
        
        return True
    
    def _validate_param_value(self, value: str) -> bool:
        """驗證單個參數值的安全性"""
        # 檢查路徑注入
        if '..' in value or value.startswith('/'):
            if not self._is_safe_absolute_path(value):
                return False
        
        # 檢查命令注入
        dangerous_chars = [';', '|', '&', '`', '$']
        for char in dangerous_chars:
            if char in value:
                return False
        
        return True
    
    def _validate_path_safety(self, command: str) -> bool:
        """驗證路徑安全性"""
        # 檢查是否使用相對路徑的 python
        if command in ['python', 'python3']:
            return True
        
        # 檢查絕對路徑是否在允許的前綴中
        if os.path.isabs(command):
            return any(command.startswith(prefix) for prefix in self.ALLOWED_PATH_PREFIXES)
        
        return True
    
    def _is_safe_absolute_path(self, path: str) -> bool:
        """檢查絕對路徑是否安全"""
        try:
            resolved_path = Path(path).resolve()
            return any(
                str(resolved_path).startswith(prefix) 
                for prefix in self.ALLOWED_PATH_PREFIXES
            )
        except Exception:
            return False
    
    def get_secure_config(self, server_name: str) -> Optional[SecureServerConfig]:
        """獲取安全配置"""
        return self.ALLOWED_MCP_SERVERS.get(server_name)
    
    def add_allowed_server(self, config: SecureServerConfig) -> bool:
        """動態添加允許的服務器（僅限管理員操作）"""
        try:
            if self.validate_server_config(
                config.name, config.command, config.args
            ):
                self.ALLOWED_MCP_SERVERS[config.name] = config
                logger.info(f"✅ 已添加安全服務器配置: {config.name}")
                return True
            else:
                logger.error(f"❌ 服務器配置未通過安全驗證: {config.name}")
                return False
        except Exception as e:
            logger.error(f"❌ 添加服務器配置時發生錯誤: {e}")
            return False
    
    def clear_cache(self):
        """清除驗證快取"""
        self.validation_cache.clear()
        logger.info("🗑️ 安全驗證快取已清除")