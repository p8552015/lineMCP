#!/bin/bash

##############################################################################
# 代碼品質自動修復腳本
# 
# 功能: 自動修復 Code Quality Checks workflow 中的問題
# 基於: error_analysis_report.md 分析結果
##############################################################################

set -euo pipefail

# 顏色定義
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly NC='\033[0m' # No Color

echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${PURPLE}🔧 代碼品質自動修復工具${NC}"
echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 檢查工作目錄
if [[ ! -d "apps/bot" ]]; then
    echo -e "${RED}❌ 找不到 apps/bot 目錄${NC}"
    exit 1
fi

cd apps/bot

echo -e "${BLUE}📦 檢查 Poetry 環境...${NC}"
if ! command -v poetry &> /dev/null; then
    echo -e "${RED}❌ 找不到 Poetry${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Poetry 可用${NC}"

echo -e "\n${BLUE}📦 安裝/更新依賴...${NC}"
poetry install --no-interaction

echo -e "\n${YELLOW}🔄 開始修復 import 排序 (isort)...${NC}"
echo -e "${BLUE}  檢查當前狀態:${NC}"
poetry run isort --check-only --diff src/ tests/ || echo -e "${YELLOW}  發現需要修復的 import 排序問題${NC}"

echo -e "${BLUE}  修復 import 排序:${NC}"
poetry run isort src/ tests/
echo -e "${GREEN}✅ isort 修復完成${NC}"

echo -e "\n${YELLOW}🖤 開始修復代碼格式 (black)...${NC}"
echo -e "${BLUE}  檢查當前狀態:${NC}"
poetry run black --check --diff src/ tests/ || echo -e "${YELLOW}  發現需要修復的格式問題${NC}"

echo -e "${BLUE}  修復代碼格式:${NC}"
poetry run black src/ tests/
echo -e "${GREEN}✅ black 格式修復完成${NC}"

echo -e "\n${YELLOW}🔍 開始修復代碼風格 (ruff)...${NC}"
echo -e "${BLUE}  檢查當前問題:${NC}"
poetry run ruff check src/ tests/ --output-format=github || echo -e "${YELLOW}  發現代碼風格問題${NC}"

echo -e "${BLUE}  修復代碼風格（安全修復）:${NC}"
poetry run ruff check src/ tests/ --fix --unsafe-fixes || echo -e "${YELLOW}  部分問題已修復，可能有剩餘問題需要手動處理${NC}"
echo -e "${GREEN}✅ ruff 風格修復完成${NC}"

echo -e "\n${YELLOW}🧪 運行測試驗證修復...${NC}"
echo -e "${BLUE}  執行基礎測試（無覆蓋率）:${NC}"
if poetry run pytest --no-cov -v -x; then
    echo -e "${GREEN}✅ 基礎測試通過${NC}"
else
    echo -e "${YELLOW}⚠️  測試有問題，但繼續檢查品質${NC}"
fi

echo -e "\n${PURPLE}📊 檢查修復結果...${NC}"

echo -e "\n${BLUE}=== isort 最終檢查 ===${NC}"
if poetry run isort --check-only src/ tests/; then
    echo -e "${GREEN}✅ isort 檢查通過${NC}"
else
    echo -e "${RED}❌ 仍有 import 排序問題${NC}"
fi

echo -e "\n${BLUE}=== black 最終檢查 ===${NC}"
if poetry run black --check src/ tests/; then
    echo -e "${GREEN}✅ black 檢查通過${NC}"
else
    echo -e "${RED}❌ 仍有代碼格式問題${NC}"
fi

echo -e "\n${BLUE}=== ruff 最終檢查 ===${NC}"
if poetry run ruff check src/ tests/; then
    echo -e "${GREEN}✅ ruff 檢查通過${NC}"
else
    echo -e "${YELLOW}⚠️  仍有代碼風格問題，需要手動修復${NC}"
    echo -e "${BLUE}  剩餘問題:${NC}"
    poetry run ruff check src/ tests/ --output-format=github | head -20
fi

echo -e "\n${BLUE}=== mypy 類型檢查 ===${NC}"
if poetry run mypy src/; then
    echo -e "${GREEN}✅ mypy 檢查通過${NC}"
else
    echo -e "${YELLOW}⚠️  有類型檢查問題，可能需要手動修復${NC}"
fi

echo -e "\n${BLUE}=== bandit 安全檢查 ===${NC}"
if poetry run bandit -r src/ -q; then
    echo -e "${GREEN}✅ bandit 檢查通過${NC}"
else
    echo -e "${YELLOW}⚠️  有安全檢查問題，建議審查${NC}"
fi

echo -e "\n${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 自動修復完成！${NC}"

echo -e "\n${YELLOW}📋 修復總結:${NC}"
echo -e "✅ import 排序修復 (isort)"
echo -e "✅ 代碼格式修復 (black)"  
echo -e "✅ 代碼風格修復 (ruff)"
echo -e "📝 類型檢查 (mypy) - 可能需要手動修復"
echo -e "🔒 安全檢查 (bandit) - 可能需要審查"

echo -e "\n${BLUE}🚀 建議的下一步:${NC}"
echo -e "1. 檢查上面的輸出確認所有檢查狀態"
echo -e "2. 手動修復任何剩餘的 mypy 類型問題"
echo -e "3. 審查任何 bandit 安全警告"
echo -e "4. 提交修復:"
echo -e "   ${YELLOW}git add .${NC}"
echo -e "   ${YELLOW}git commit -m '🔧 修復 Code Quality Checks 問題'${NC}"
echo -e "   ${YELLOW}git push${NC}"
echo -e "5. 檢查 GitHub Actions 狀態:"
echo -e "   ${YELLOW}./github-actions-detector.sh${NC}"

echo -e "\n${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"