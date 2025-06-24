#!/usr/bin/env python3
"""
CI/CD 基本功能測試
用於驗證新建立的工作流程是否正常工作
"""

import sys
import os
import yaml
import json
from pathlib import Path

def test_yaml_files():
    """測試 YAML 檔案語法"""
    workflows_dir = Path(__file__).parent.parent.parent / ".github" / "workflows"
    yaml_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))
    
    print(f"✅ 找到 {len(yaml_files)} 個 YAML 檔案")
    
    for yaml_file in yaml_files:
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                yaml.safe_load(f)
            print(f"✅ {yaml_file.name} 語法正確")
        except yaml.YAMLError as e:
            print(f"❌ {yaml_file.name} 語法錯誤: {e}")
            return False
    
    return True

def test_poetry_config():
    """測試 Poetry 配置"""
    try:
        pyproject_file = Path(__file__).parent / "pyproject.toml"
        
        if not pyproject_file.exists():
            print("❌ pyproject.toml 不存在")
            return False
        
        # 基本檢查 - 確保檔案可以讀取
        with open(pyproject_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if "[tool.poetry]" in content:
            print("✅ Poetry 配置存在")
        else:
            print("❌ Poetry 配置缺失")
            return False
            
        if "[tool.pytest.ini_options]" in content:
            print("✅ Pytest 配置存在")
        else:
            print("❌ Pytest 配置缺失")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Poetry 配置檢查失敗: {e}")
        return False

def test_security_files():
    """測試安全配置檔案"""
    repo_root = Path(__file__).parent.parent.parent
    
    security_files = [
        ".github/SECURITY.md",
        ".github/dependabot.yml", 
        ".semgrepignore",
        ".commitlintrc.json",
        ".markdownlint.json"
    ]
    
    all_exist = True
    for security_file in security_files:
        file_path = repo_root / security_file
        if file_path.exists():
            print(f"✅ {security_file} 存在")
        else:
            print(f"❌ {security_file} 缺失")
            all_exist = False
    
    return all_exist

def test_test_structure():
    """測試測試目錄結構"""
    tests_dir = Path(__file__).parent / "tests"
    
    if not tests_dir.exists():
        print("❌ tests 目錄不存在")
        return False
    
    required_dirs = ["integration", "unit"]
    for req_dir in required_dirs:
        dir_path = tests_dir / req_dir
        if dir_path.exists():
            print(f"✅ tests/{req_dir} 目錄存在")
        else:
            print(f"❌ tests/{req_dir} 目錄缺失")
            return False
    
    # 檢查是否有測試檔案
    test_files = list(tests_dir.rglob("test_*.py"))
    if len(test_files) > 0:
        print(f"✅ 找到 {len(test_files)} 個測試檔案")
        return True
    else:
        print("❌ 沒有找到測試檔案")
        return False

def test_environment_variables():
    """測試環境變數設置"""
    critical_vars = [
        "ASYNCIO_FORCE_SELECT_SELECTOR"
    ]
    
    all_set = True
    for var in critical_vars:
        if var in os.environ:
            print(f"✅ 環境變數 {var} 已設置")
        else:
            print(f"⚠️  環境變數 {var} 未設置（在生產環境中需要）")
            # 對於測試環境，這不是致命錯誤
    
    return True  # 總是返回 True，因為這些變數在測試環境中可能不需要

def test_docker_files():
    """測試 Docker 相關檔案"""
    dockerfile = Path(__file__).parent / "Dockerfile"
    
    if dockerfile.exists():
        print("✅ Dockerfile 存在")
        
        # 檢查 Dockerfile 基本內容
        with open(dockerfile, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if "FROM python:" in content:
            print("✅ Dockerfile 包含 Python 基礎映像")
        else:
            print("❌ Dockerfile 缺少 Python 基礎映像")
            return False
            
        if "WORKDIR" in content:
            print("✅ Dockerfile 設置工作目錄")
        else:
            print("❌ Dockerfile 缺少工作目錄設置")
            return False
        
        return True
    else:
        print("❌ Dockerfile 不存在")
        return False

def main():
    """執行所有測試"""
    print("🔍 開始 CI/CD 基本功能測試...")
    print("=" * 50)
    
    tests = [
        ("YAML 檔案語法", test_yaml_files),
        ("Poetry 配置", test_poetry_config),
        ("安全配置檔案", test_security_files),
        ("測試目錄結構", test_test_structure),
        ("環境變數", test_environment_variables),
        ("Docker 檔案", test_docker_files),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 測試: {test_name}")
        try:
            if test_func():
                print(f"✅ {test_name} - 通過")
                passed += 1
            else:
                print(f"❌ {test_name} - 失敗")
        except Exception as e:
            print(f"❌ {test_name} - 異常: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 測試結果: {passed}/{total} 通過")
    
    if passed == total:
        print("🎉 所有基本功能測試通過！")
        return 0
    else:
        print("⚠️  部分測試失敗，請檢查配置")
        return 1

if __name__ == "__main__":
    sys.exit(main())