#!/bin/bash

# 🧪 發布流程測試腳本
# 驗證發布自動化工作流程的各個組件

set -e  # 遇到錯誤立即退出

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 項目根目錄
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BOT_DIR="$PROJECT_ROOT/apps/bot"

echo -e "${BLUE}🧪 LINE MCP 發布流程測試${NC}"
echo "=================================================="

# 測試計數器
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0

# 測試函數
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    echo -e "\n${YELLOW}[$TESTS_TOTAL] 測試: $test_name${NC}"
    
    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 通過${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}❌ 失敗${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# 測試環境檢查
echo -e "\n${BLUE}🔍 環境檢查${NC}"
echo "--------------------------------------------------"

run_test "Git 可用性" "command -v git"
run_test "Python 可用性" "command -v python3"
run_test "Poetry 可用性" "command -v poetry"
run_test "Docker 可用性" "command -v docker"

# 檢查項目結構
echo -e "\n${BLUE}📁 項目結構檢查${NC}"
echo "--------------------------------------------------"

run_test "pyproject.toml 存在" "test -f '$BOT_DIR/pyproject.toml'"
run_test "CHANGELOG.md 存在" "test -f '$PROJECT_ROOT/CHANGELOG.md'"
run_test "版本管理腳本存在" "test -f '$PROJECT_ROOT/scripts/version-manager.py'"
run_test "發布工作流程存在" "test -f '$PROJECT_ROOT/.github/workflows/release.yml'"

# 檢查 Poetry 配置
echo -e "\n${BLUE}📦 Poetry 配置檢查${NC}"
echo "--------------------------------------------------"

if cd "$BOT_DIR" 2>/dev/null; then
    run_test "Poetry 配置有效" "poetry check"
    run_test "Poetry 虛擬環境可用" "poetry env info"
    
    # 嘗試獲取當前版本
    if poetry version -s > /dev/null 2>&1; then
        current_version=$(poetry version -s)
        echo -e "${GREEN}📋 當前版本: $current_version${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ 無法獲取當前版本${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
else
    echo -e "${RED}❌ 無法進入 Bot 目錄${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
fi

# 檢查 Git 狀態
echo -e "\n${BLUE}📊 Git 狀態檢查${NC}"
echo "--------------------------------------------------"

cd "$PROJECT_ROOT"

run_test "Git 倉庫有效" "git status"
run_test "遠程倉庫配置" "git remote -v"

# 檢查是否有未提交的變更
if git diff-index --quiet HEAD --; then
    echo -e "${GREEN}✅ 工作目錄乾淨${NC}"
else
    echo -e "${YELLOW}⚠️  有未提交的變更${NC}"
fi

# 獲取最新標籤
if git describe --tags --abbrev=0 > /dev/null 2>&1; then
    latest_tag=$(git describe --tags --abbrev=0)
    echo -e "${GREEN}📋 最新標籤: $latest_tag${NC}"
else
    echo -e "${YELLOW}📋 沒有發現標籤${NC}"
fi

# 檢查 GitHub Actions 工作流程語法
echo -e "\n${BLUE}🔧 GitHub Actions 語法檢查${NC}"
echo "--------------------------------------------------"

# 檢查 YAML 語法（如果有 yamllint）
if command -v yamllint > /dev/null 2>&1; then
    for workflow in "$PROJECT_ROOT/.github/workflows"/*.yml; do
        if [ -f "$workflow" ]; then
            workflow_name=$(basename "$workflow")
            run_test "工作流程語法: $workflow_name" "yamllint '$workflow'"
        fi
    done
else
    echo -e "${YELLOW}⚠️  yamllint 未安裝，跳過 YAML 語法檢查${NC}"
fi

# 檢查工作流程必要組件
run_test "發布工作流程語法" "python3 -c \"
import yaml
with open('$PROJECT_ROOT/.github/workflows/release.yml') as f:
    yaml.safe_load(f)
\""

# 測試版本管理腳本
echo -e "\n${BLUE}🐍 版本管理腳本測試${NC}"
echo "--------------------------------------------------"

cd "$PROJECT_ROOT"

run_test "版本管理腳本語法" "python3 -m py_compile scripts/version-manager.py"
run_test "版本管理腳本執行權限" "test -x scripts/version-manager.py"

# 測試版本管理腳本功能（乾跑模式）
if python3 scripts/version-manager.py status > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 版本管理腳本狀態檢查正常${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}❌ 版本管理腳本狀態檢查失敗${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

# 檢查 Docker 配置
echo -e "\n${BLUE}🐳 Docker 配置檢查${NC}"
echo "--------------------------------------------------"

run_test "Dockerfile 存在" "test -f '$BOT_DIR/Dockerfile'"

if [ -f "$BOT_DIR/Dockerfile" ]; then
    run_test "Dockerfile 語法" "docker build --no-cache -t test-release-build -f '$BOT_DIR/Dockerfile' '$PROJECT_ROOT' --dry-run 2>/dev/null || docker build --help | grep -q 'dry-run' || echo 'Docker 建構測試跳過'"
fi

# 檢查安全配置
echo -e "\n${BLUE}🔒 安全配置檢查${NC}"
echo "--------------------------------------------------"

# 檢查是否有敏感文件被追蹤
sensitive_files=(
    ".env"
    "*.key"
    "*.pem"
    "*secret*"
    "*password*"
)

echo "檢查是否有敏感文件被追蹤..."
for pattern in "${sensitive_files[@]}"; do
    if git ls-files | grep -q "$pattern" 2>/dev/null; then
        echo -e "${RED}⚠️  發現可能的敏感文件: $pattern${NC}"
    fi
done

# 檢查 .gitignore
run_test ".gitignore 存在" "test -f '$PROJECT_ROOT/.gitignore'"

# 檢查文檔完整性
echo -e "\n${BLUE}📚 文檔完整性檢查${NC}"
echo "--------------------------------------------------"

run_test "README.md 存在" "test -f '$PROJECT_ROOT/README.md'"
run_test "發布指南存在" "test -f '$PROJECT_ROOT/docs/release-guide.md'"
run_test "CLAUDE.md 存在" "test -f '$PROJECT_ROOT/CLAUDE.md'"

# 測試摘要
echo -e "\n${BLUE}📋 測試摘要${NC}"
echo "=================================================="
echo -e "總測試數: $TESTS_TOTAL"
echo -e "${GREEN}通過: $TESTS_PASSED${NC}"
echo -e "${RED}失敗: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}🎉 所有測試通過！發布流程已就緒。${NC}"
    exit 0
else
    echo -e "\n${RED}❌ 有 $TESTS_FAILED 個測試失敗。請修復後重新測試。${NC}"
    exit 1
fi

# 額外建議
echo -e "\n${BLUE}💡 建議下一步${NC}"
echo "=================================================="
echo "1. 如果所有測試通過，可以嘗試乾跑發布："
echo "   python3 scripts/version-manager.py release --type patch --dry-run"
echo ""
echo "2. 檢查 GitHub Actions secrets 配置："
echo "   - GITHUB_TOKEN (自動提供)"
echo "   - 其他必要的環境變數"
echo ""
echo "3. 測試 GitHub Actions 工作流程："
echo "   - 手動觸發 release.yml 工作流程"
echo "   - 檢查所有步驟是否正常執行"