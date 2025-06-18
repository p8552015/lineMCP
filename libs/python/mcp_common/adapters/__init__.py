"""
協議適配器模組

提供不同協議的 MCP 適配器實作。
"""

from .legacy_adapter import LegacyMCPAdapter
from .simple_adapter import SimpleMCPAdapter

__all__ = [
    "LegacyMCPAdapter",
    "SimpleMCPAdapter",
]