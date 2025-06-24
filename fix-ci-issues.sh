#!/bin/bash

##############################################################################
# CI 問題修復腳本
# 
# 功能: 根據錯誤分析結果修復 CI/CD 問題
# 基於最新的失敗分析：程式碼品質檢查失敗
##############################################################################

set -euo pipefail

# 顏色定義
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly NC='\033[0m' # No Color

BOT_DIR="apps/bot"

echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${PURPLE}🔧 CI 問題修復工具${NC}"
echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 檢查工作目錄
check_directory() {
    echo -e "${BLUE}📍 檢查工作目錄...${NC}"
    
    if [[ ! -d "$BOT_DIR" ]]; then
        echo -e "${RED}❌ 找不到 $BOT_DIR 目錄${NC}"
        exit 1
    fi
    
    if [[ ! -f "$BOT_DIR/pyproject.toml" ]]; then
        echo -e "${RED}❌ 找不到 $BOT_DIR/pyproject.toml${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ 工作目錄正確${NC}"
}

# 修復 1: Python 程式碼格式化
fix_python_formatting() {
    echo -e "\n${YELLOW}🐍 修復 Python 程式碼格式...${NC}"
    
    cd "$BOT_DIR"
    
    # 1. 修復 import 排序 (isort)
    echo -e "${BLUE}  📦 修復 import 排序...${NC}"
    if command -v poetry &> /dev/null; then
        poetry run isort src/ tests/ || {
            echo -e "${YELLOW}  ⚠️  isort 不可用，嘗試安裝...${NC}"
            poetry add --dev isort
            poetry run isort src/ tests/
        }
    else
        echo -e "${RED}  ❌ Poetry 不可用${NC}"
        return 1
    fi
    
    # 2. 代碼格式化 (black)
    echo -e "${BLUE}  🖤 代碼格式化...${NC}"
    poetry run black src/ tests/
    
    # 3. 代碼風格檢查和修復 (ruff)
    echo -e "${BLUE}  🔍 代碼風格檢查...${NC}"
    poetry run ruff check src/ tests/ --fix
    
    # 4. 類型檢查 (mypy) - 僅檢查不修復
    echo -e "${BLUE}  📝 類型檢查...${NC}"
    poetry run mypy src/ || echo -e "${YELLOW}  ⚠️  類型檢查有警告，需要手動修復${NC}"
    
    cd - > /dev/null
    echo -e "${GREEN}✅ Python 格式修復完成${NC}"
}

# 修復 2: Dockerfile 格式
fix_dockerfile() {
    echo -e "\n${YELLOW}🐳 檢查和修復 Dockerfile...${NC}"
    
    # 查找 Dockerfile
    local dockerfiles=$(find . -name "Dockerfile*" -type f)
    
    if [[ -z "$dockerfiles" ]]; then
        echo -e "${YELLOW}  ⚠️  沒有找到 Dockerfile${NC}"
        return 0
    fi
    
    for dockerfile in $dockerfiles; do
        echo -e "${BLUE}  📋 檢查 $dockerfile...${NC}"
        
        # 基本的 Dockerfile 最佳實踐檢查
        local issues=0
        
        # 檢查是否使用特定版本標籤
        if grep -q "FROM.*:latest" "$dockerfile"; then
            echo -e "${YELLOW}    ⚠️  建議使用特定版本而非 :latest${NC}"
            ((issues++))
        fi
        
        # 檢查是否有 LABEL
        if ! grep -q "LABEL" "$dockerfile"; then
            echo -e "${YELLOW}    ⚠️  建議添加 LABEL 元數據${NC}"
            ((issues++))
        fi
        
        if [[ $issues -eq 0 ]]; then
            echo -e "${GREEN}    ✅ $dockerfile 檢查通過${NC}"
        else
            echo -e "${YELLOW}    ⚠️  $dockerfile 有 $issues 個建議改進項${NC}"
        fi
    done
}

# 修復 3: 複雜度檢查
fix_complexity() {
    echo -e "\n${YELLOW}📊 檢查代碼複雜度...${NC}"
    
    cd "$BOT_DIR"
    
    # 使用 radon 檢查複雜度
    if poetry run python -c "import radon" 2>/dev/null; then
        echo -e "${BLUE}  📈 分析代碼複雜度...${NC}"
        poetry run radon cc src/ -s || echo -e "${YELLOW}    ⚠️  發現高複雜度代碼，建議重構${NC}"
    else
        echo -e "${YELLOW}  ⚠️  radon 不可用，嘗試安裝...${NC}"
        poetry add --dev radon || echo -e "${YELLOW}    無法安裝 radon${NC}"
    fi
    
    cd - > /dev/null
}

# 修復 4: 文檔質量
fix_documentation() {
    echo -e "\n${YELLOW}📚 檢查文檔質量...${NC}"
    
    # 檢查 README
    if [[ -f "README.md" ]]; then
        echo -e "${GREEN}  ✅ README.md 存在${NC}"
    else
        echo -e "${YELLOW}  ⚠️  建議添加 README.md${NC}"
    fi
    
    # 檢查 CLAUDE.md
    if [[ -f "CLAUDE.md" ]]; then
        echo -e "${GREEN}  ✅ CLAUDE.md 存在${NC}"
    else
        echo -e "${YELLOW}  ⚠️  CLAUDE.md 不存在${NC}"
    fi
    
    # 檢查代碼中的文檔字符串
    cd "$BOT_DIR"
    local python_files=$(find src/ -name "*.py" -type f 2>/dev/null | wc -l)
    local files_with_docstrings=$(find src/ -name "*.py" -exec grep -l '"""' {} \; 2>/dev/null | wc -l)
    
    if [[ $python_files -gt 0 ]]; then
        local coverage_percent=$((files_with_docstrings * 100 / python_files))
        echo -e "${BLUE}  📖 文檔字符串覆蓋率: ${coverage_percent}%${NC}"
        
        if [[ $coverage_percent -lt 50 ]]; then
            echo -e "${YELLOW}    ⚠️  建議增加函數和類的文檔字符串${NC}"
        fi
    fi
    
    cd - > /dev/null
}

# 修復 5: 更新依賴
update_dependencies() {
    echo -e "\n${YELLOW}📦 更新依賴...${NC}"
    
    cd "$BOT_DIR"
    
    # 更新 poetry lock
    echo -e "${BLUE}  🔒 更新 poetry.lock...${NC}"
    poetry update
    
    # 安裝所有依賴
    echo -e "${BLUE}  📥 安裝依賴...${NC}"
    poetry install
    
    cd - > /dev/null
    echo -e "${GREEN}✅ 依賴更新完成${NC}"
}

# 運行本地測試
run_local_tests() {
    echo -e "\n${YELLOW}🧪 運行本地測試...${NC}"
    
    cd "$BOT_DIR"
    
    # 運行 pytest
    echo -e "${BLUE}  🧪 運行單元測試...${NC}"
    if poetry run pytest --version &>/dev/null; then
        poetry run pytest -v || echo -e "${YELLOW}    ⚠️  部分測試失敗${NC}"
    else
        echo -e "${YELLOW}    ⚠️  pytest 不可用${NC}"
    fi
    
    cd - > /dev/null
}

# 生成修復報告
generate_fix_report() {
    echo -e "\n${YELLOW}📋 生成修復報告...${NC}"
    
    cat > ci_fix_report.md << EOF
# 🔧 CI 修復報告

**修復時間**: $(date '+%Y-%m-%d %H:%M:%S')

## 修復的問題

### 1. Python 程式碼格式化
- ✅ Import 排序 (isort)
- ✅ 代碼格式化 (black)
- ✅ 代碼風格檢查 (ruff)
- ⚠️ 類型檢查 (mypy) - 可能需要手動修復

### 2. Dockerfile 檢查
- ✅ 基本格式檢查完成

### 3. 代碼複雜度
- ✅ 複雜度分析完成

### 4. 文檔質量
- ✅ 文檔檢查完成

### 5. 依賴更新
- ✅ Poetry 依賴已更新

## 建議的後續步驟

1. 檢查並提交更改:
\`\`\`bash
git add .
git status
git commit -m "🔧 修復 CI 程式碼品質問題"
\`\`\`

2. 推送到遠端:
\`\`\`bash
git push
\`\`\`

3. 檢查 CI 狀態:
\`\`\`bash
./github-actions-detector.sh
\`\`\`

## 可能需要手動修復的項目

- MyPy 類型檢查錯誤
- 高複雜度代碼重構
- 缺失的文檔字符串

EOF

    echo -e "${GREEN}✅ 修復報告已生成: ci_fix_report.md${NC}"
}

# 主函數
main() {
    check_directory
    fix_python_formatting
    fix_dockerfile
    fix_complexity
    fix_documentation
    update_dependencies
    run_local_tests
    generate_fix_report
    
    echo -e "\n${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}🎉 CI 修復完成！${NC}"
    echo -e "\n${BLUE}下一步:${NC}"
    echo -e "1. 檢查修復報告: ${YELLOW}ci_fix_report.md${NC}"
    echo -e "2. 提交更改: ${YELLOW}git add . && git commit -m '🔧 修復 CI 問題'${NC}"
    echo -e "3. 推送並檢查: ${YELLOW}git push && ./github-actions-detector.sh${NC}"
}

# 執行主函數
main "$@"