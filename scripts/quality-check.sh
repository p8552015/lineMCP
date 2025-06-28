#!/bin/bash
# Pre-commit 品質檢查自動化腳本
# 建立於: 2025-06-28 
# 作者: Claude Code

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 計數器
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

echo -e "${BLUE}🔍 執行完整程式碼品質檢查...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📅 檢查時間: $(date '+%Y-%m-%d %H:%M:%S')"
echo "📁 專案路徑: $(pwd)"
echo ""

# 檢查是否在正確目錄
if [ ! -f "apps/bot/pyproject.toml" ]; then
    echo -e "${RED}❌ 錯誤: 請在專案根目錄執行此腳本${NC}"
    exit 1
fi

cd apps/bot

# 函數：執行檢查
run_check() {
    local name="$1"
    local command="$2"
    local description="$3"
    
    echo -e "${BLUE}📋 Step $((++TOTAL_CHECKS)): $name${NC}"
    echo "   $description"
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "   ${GREEN}✅ 通過${NC}"
        ((++PASSED_CHECKS))
    else
        echo -e "   ${RED}❌ 失敗${NC}"
        echo -e "   ${YELLOW}執行詳細檢查...${NC}"
        eval "$command"
        ((++FAILED_CHECKS))
    fi
    echo ""
}

# 函數：計算統計
show_stats() {
    local command="$1"
    local type="$2"
    
    local result=$(eval "$command" 2>/dev/null | grep -c ":" || echo "0")
    echo -e "   ${YELLOW}$type: $result 個問題${NC}"
}

echo -e "${BLUE}🎯 基礎工具檢查${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Ruff 檢查與自動修復
run_check "Ruff 程式碼檢查" \
    "poetry run ruff check src/" \
    "檢查程式碼風格、語法問題和潛在錯誤"

show_stats "poetry run ruff check src/ --select E501" "行長度問題"
show_stats "poetry run ruff check src/ --select F" "語法錯誤"
show_stats "poetry run ruff check src/ --select E" "風格問題"

# 2. Black 格式化檢查  
run_check "Black 格式化檢查" \
    "poetry run black src/ --check --diff" \
    "檢查程式碼格式是否符合標準"

# 3. MyPy 類型檢查
run_check "MyPy 類型檢查" \
    "poetry run mypy src/ --ignore-missing-imports" \
    "檢查型別註解和型別安全"

echo -e "${BLUE}🔧 Pre-commit 整合檢查${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 4. Pre-commit hooks 完整檢查
cd ..
run_check "Pre-commit Hooks" \
    "pre-commit run --all-files" \
    "執行所有 pre-commit hooks 檢查"

echo -e "${BLUE}🚀 系統功能驗證${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 5. 系統啟動測試
if [ -f "start-production.sh" ]; then
    run_check "系統啟動測試" \
        "./start-production.sh test" \
        "驗證系統核心功能和服務啟動"
else
    echo -e "${YELLOW}⚠️ start-production.sh 不存在，跳過系統測試${NC}"
    echo ""
fi

echo -e "${BLUE}📊 檢查結果統計${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "總檢查項目: ${BLUE}$TOTAL_CHECKS${NC}"
echo -e "通過項目: ${GREEN}$PASSED_CHECKS${NC}"
echo -e "失敗項目: ${RED}$FAILED_CHECKS${NC}"

if [ $FAILED_CHECKS -eq 0 ]; then
    echo ""
    echo -e "${GREEN}🎉 恭喜！所有品質檢查都通過了！${NC}"
    echo -e "${GREEN}✨ 程式碼品質達到企業級標準${NC}"
    exit 0
else
    echo ""
    echo -e "${YELLOW}⚠️ 發現 $FAILED_CHECKS 個問題需要修復${NC}"
    echo ""
    echo -e "${BLUE}🔧 建議修復步驟:${NC}"
    
    if [ $FAILED_CHECKS -gt 0 ]; then
        echo -e "1. 執行自動修復: ${YELLOW}cd apps/bot && poetry run ruff check src/ --fix${NC}"
        echo -e "2. 格式化程式碼: ${YELLOW}cd apps/bot && poetry run black src/${NC}"  
        echo -e "3. 重新執行檢查: ${YELLOW}./scripts/quality-check.sh${NC}"
        echo -e "4. 查看詳細錯誤: 檢查上方的錯誤訊息"
    fi
    
    echo ""
    echo -e "${BLUE}📚 相關文檔:${NC}"
    echo -e "• 程式碼品質最佳實踐: ${YELLOW}docs/architecture/code-quality-best-practices.md${NC}"
    echo -e "• Pre-commit 設定指南: ${YELLOW}.pre-commit-config.yaml${NC}"
    echo -e "• 專案規格文件: ${YELLOW}task/任務規劃書/spec_pre-commit品質修復.md${NC}"
    
    exit 1
fi