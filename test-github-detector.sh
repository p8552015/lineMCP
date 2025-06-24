#!/bin/bash

##############################################################################
# GitHub Actions 檢測器測試腳本
# 
# 功能: 測試 github-actions-detector.sh 的各項功能
# 作者: Claude Code
# 版本: 1.0
# 日期: 2025-06-24
##############################################################################

set -euo pipefail

# 顏色定義
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly DETECTOR_SCRIPT="${SCRIPT_DIR}/github-actions-detector.sh"
readonly TEST_LOG="${SCRIPT_DIR}/test-results.log"

# 測試計數器
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0

##############################################################################
# 測試工具函數
##############################################################################

print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}🧪 GitHub Actions 檢測器測試套件${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

test_start() {
    local test_name="$1"
    echo -e "\\n${YELLOW}🧪 測試: ${test_name}${NC}"
    ((TESTS_TOTAL++))
}

test_pass() {
    local message="$1"
    echo -e "  ${GREEN}✅ PASS: ${message}${NC}"
    ((TESTS_PASSED++))
}

test_fail() {
    local message="$1"
    echo -e "  ${RED}❌ FAIL: ${message}${NC}"
    ((TESTS_FAILED++))
}

run_command() {
    local cmd="$1"
    local expected_exit_code="${2:-0}"
    
    echo "  🔧 執行: $cmd" | tee -a "$TEST_LOG"
    
    local exit_code=0
    if ! eval "$cmd" >> "$TEST_LOG" 2>&1; then
        exit_code=$?
    fi
    
    if [[ $exit_code -eq $expected_exit_code ]]; then
        test_pass "命令執行成功 (exit code: $exit_code)"
        return 0
    else
        test_fail "命令執行失敗 (expected: $expected_exit_code, got: $exit_code)"
        return 1
    fi
}

check_file_exists() {
    local file="$1"
    local description="$2"
    
    if [[ -f "$file" ]]; then
        test_pass "$description 存在: $file"
        return 0
    else
        test_fail "$description 不存在: $file"
        return 1
    fi
}

check_environment() {
    echo -e "\\n${YELLOW}🔍 檢查測試環境${NC}"
    
    # 檢查必要工具
    local tools=("curl" "jq" "git")
    for tool in "${tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            test_pass "工具可用: $tool"
        else
            test_fail "工具缺失: $tool"
        fi
    done
    
    # 檢查檢測器腳本
    check_file_exists "$DETECTOR_SCRIPT" "檢測器腳本"
    
    if [[ -x "$DETECTOR_SCRIPT" ]]; then
        test_pass "檢測器腳本有執行權限"
    else
        test_fail "檢測器腳本沒有執行權限"
    fi
    
    # 檢查 GitHub 配置
    if [[ -n "${GITHUB_TOKEN:-}" ]]; then
        test_pass "GITHUB_TOKEN 環境變數已設置"
    else
        test_fail "GITHUB_TOKEN 環境變數未設置"
        echo -e "  ${YELLOW}⚠️  某些測試將會跳過${NC}"
    fi
    
    if git rev-parse --is-inside-work-tree &>/dev/null; then
        test_pass "在 Git 倉庫中執行"
        
        local remote_url=$(git config --get remote.origin.url 2>/dev/null || echo "")
        if [[ "$remote_url" =~ github\.com ]]; then
            test_pass "GitHub 倉庫偵測成功"
        else
            test_fail "不是 GitHub 倉庫"
        fi
    else
        test_fail "不在 Git 倉庫中"
    fi
}

##############################################################################
# 功能測試
##############################################################################

test_help_function() {
    test_start "幫助功能測試"
    
    if run_command "${DETECTOR_SCRIPT} --help" 0; then
        # 檢查幫助訊息是否包含關鍵內容
        if grep -q "GitHub Actions CI/CD 自動檢測系統" "$TEST_LOG"; then
            test_pass "幫助訊息包含正確標題"
        else
            test_fail "幫助訊息格式不正確"
        fi
    fi
}

test_dependency_check() {
    test_start "依賴檢查測試"
    
    # 暫時重新命名工具來測試依賴檢查
    if command -v jq &> /dev/null; then
        local jq_path=$(command -v jq)
        local temp_name="${jq_path}.bak"
        
        # 備份 jq
        sudo mv "$jq_path" "$temp_name" 2>/dev/null || {
            test_pass "無法移動 jq，跳過依賴測試"
            return 0
        }
        
        # 測試缺少依賴的情況
        if run_command "${DETECTOR_SCRIPT}" 1; then
            test_pass "正確檢測到缺少依賴"
        fi
        
        # 恢復 jq
        sudo mv "$temp_name" "$jq_path" 2>/dev/null
    else
        test_pass "jq 已缺失，跳過依賴測試"
    fi
}

test_api_connection() {
    test_start "GitHub API 連接測試"
    
    if [[ -z "${GITHUB_TOKEN:-}" ]]; then
        test_fail "跳過 API 測試 (缺少 GITHUB_TOKEN)"
        return 0
    fi
    
    # 測試基本 API 連接
    local api_test_cmd="curl -s -H 'Authorization: token ${GITHUB_TOKEN}' -H 'Accept: application/vnd.github.v3+json' https://api.github.com/user"
    
    if eval "$api_test_cmd" >/dev/null 2>&1; then
        test_pass "GitHub API 連接成功"
    else
        test_fail "GitHub API 連接失敗"
    fi
}

test_workflow_detection() {
    test_start "Workflow 檢測測試"
    
    if [[ -z "${GITHUB_TOKEN:-}" ]]; then
        test_fail "跳過 Workflow 檢測 (缺少 GITHUB_TOKEN)"
        return 0
    fi
    
    # 檢查 .github/workflows 目錄
    local workflows_dir="${SCRIPT_DIR}/.github/workflows"
    if [[ -d "$workflows_dir" ]]; then
        local workflow_files=$(find "$workflows_dir" -name "*.yml" -o -name "*.yaml" | wc -l)
        if [[ $workflow_files -gt 0 ]]; then
            test_pass "發現 $workflow_files 個 workflow 檔案"
        else
            test_fail "未發現 workflow 檔案"
        fi
    else
        test_fail "未找到 .github/workflows 目錄"
    fi
}

test_log_generation() {
    test_start "日誌生成測試"
    
    # 執行檢測器並檢查日誌檔案
    local log_file="${SCRIPT_DIR}/github-actions-detector.log"
    rm -f "$log_file"  # 清理舊日誌
    
    if [[ -n "${GITHUB_TOKEN:-}" ]]; then
        # 執行實際檢測
        "${DETECTOR_SCRIPT}" >/dev/null 2>&1 || true
    else
        # 執行幫助功能以測試日誌生成
        "${DETECTOR_SCRIPT}" --help >/dev/null 2>&1 || true
    fi
    
    if [[ -f "$log_file" ]]; then
        test_pass "日誌檔案生成成功"
        
        if [[ -s "$log_file" ]]; then
            test_pass "日誌檔案不為空"
        else
            test_fail "日誌檔案為空"
        fi
    else
        test_fail "日誌檔案未生成"
    fi
}

test_report_generation() {
    test_start "報告生成測試"
    
    local report_file="${SCRIPT_DIR}/ci-status-report.md"
    rm -f "$report_file"  # 清理舊報告
    
    if [[ -n "${GITHUB_TOKEN:-}" ]]; then
        # 執行檢測器生成報告
        "${DETECTOR_SCRIPT}" --report >/dev/null 2>&1 || true
        
        if [[ -f "$report_file" ]]; then
            test_pass "報告檔案生成成功"
            
            # 檢查報告內容
            if grep -q "GitHub Actions CI/CD 狀態報告" "$report_file"; then
                test_pass "報告內容格式正確"
            else
                test_fail "報告內容格式不正確"
            fi
        else
            test_fail "報告檔案未生成"
        fi
    else
        test_pass "跳過報告生成測試 (缺少 GITHUB_TOKEN)"
    fi
}

test_error_handling() {
    test_start "錯誤處理測試"
    
    # 測試無效的 GitHub token
    local old_token="${GITHUB_TOKEN:-}"
    export GITHUB_TOKEN="invalid_token_12345"
    
    if run_command "${DETECTOR_SCRIPT}" 1; then
        test_pass "正確處理無效 token"
    fi
    
    # 恢復原始 token
    if [[ -n "$old_token" ]]; then
        export GITHUB_TOKEN="$old_token"
    else
        unset GITHUB_TOKEN
    fi
}

##############################################################################
# 整合測試
##############################################################################

test_full_integration() {
    test_start "完整整合測試"
    
    if [[ -z "${GITHUB_TOKEN:-}" ]]; then
        test_fail "跳過整合測試 (缺少 GITHUB_TOKEN)"
        return 0
    fi
    
    # 執行完整檢測流程
    echo "  📋 執行完整檢測流程..."
    
    local start_time=$(date +%s)
    
    if "${DETECTOR_SCRIPT}" >> "$TEST_LOG" 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        test_pass "完整檢測流程執行成功 (耗時: ${duration}秒)"
        
        # 檢查執行時間是否在合理範圍內 (< 120秒)
        if [[ $duration -lt 120 ]]; then
            test_pass "執行時間在合理範圍內"
        else
            test_fail "執行時間過長 (${duration}秒)"
        fi
        
        # 檢查生成的檔案
        check_file_exists "${SCRIPT_DIR}/github-actions-detector.log" "檢測日誌"
        check_file_exists "${SCRIPT_DIR}/ci-status-report.md" "狀態報告"
        
    else
        test_fail "完整檢測流程執行失敗"
    fi
}

##############################################################################
# 主函數
##############################################################################

main() {
    print_header
    echo "測試開始時間: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    
    # 初始化測試日誌
    > "$TEST_LOG"
    echo "# GitHub Actions 檢測器測試日誌" >> "$TEST_LOG"
    echo "# 測試時間: $(date '+%Y-%m-%d %H:%M:%S')" >> "$TEST_LOG"
    echo "" >> "$TEST_LOG"
    
    # 執行所有測試
    check_environment
    test_help_function
    test_dependency_check
    test_api_connection
    test_workflow_detection
    test_log_generation
    test_report_generation
    test_error_handling
    test_full_integration
    
    # 顯示測試結果總結
    echo -e "\\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}📊 測試結果總結${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    echo -e "總計測試: ${TESTS_TOTAL}"
    echo -e "通過: ${GREEN}${TESTS_PASSED}${NC}"
    echo -e "失敗: ${RED}${TESTS_FAILED}${NC}"
    
    local success_rate=0
    if [[ $TESTS_TOTAL -gt 0 ]]; then
        success_rate=$((TESTS_PASSED * 100 / TESTS_TOTAL))
    fi
    echo -e "成功率: ${success_rate}%"
    
    echo -e "\\n詳細日誌: ${TEST_LOG}"
    
    # 返回適當的退出碼
    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "\\n${GREEN}🎉 所有測試通過！${NC}"
        exit 0
    else
        echo -e "\\n${RED}⚠️  有 ${TESTS_FAILED} 個測試失敗${NC}"
        exit 1
    fi
}

# 執行主函數
main "$@"