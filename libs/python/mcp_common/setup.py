"""
MCP Common Library Setup Script
"""

from setuptools import setup, find_packages

setup(
    name="mcp_common",
    version="0.1.0",
    description="統一的 MCP 客戶端函式庫",
    author="LINE MCP Team", 
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "pydantic>=2.0.0",
        "aiohttp>=3.8.0",
        "websockets>=10.0",
        "asyncio-mqtt>=0.11.0",
        "prometheus-client>=0.14.0",
        "opentelemetry-api>=1.15.0",
        "opentelemetry-sdk>=1.15.0",
        "opentelemetry-exporter-otlp>=1.15.0",
        "pyyaml>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.20.0",
            "pytest-cov>=4.0.0",
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
) 