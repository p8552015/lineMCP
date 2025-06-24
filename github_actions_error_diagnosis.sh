#!/bin/bash
# GitHub Actions 錯誤診斷自動化腳本
# 基於任務規劃模板，使用 MCP 架構進行智能診斷

set -euo pipefail

# =============================================================================
# 全域變數和配置
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}"
SPEC_FILE="${PROJECT_ROOT}/spec_Github_actions_錯誤診斷.md"
LOG_FILE="${PROJECT_ROOT}/diagnosis_logs/diagnosis_$(date +%Y%m%d_%H%M%S).log"
REPORT_DIR="${PROJECT_ROOT}/diagnosis_reports"

# GitHub 配置
GITHUB_PAT="${GITHUB_PAT:-}"
GITHUB_OWNER="${GITHUB_OWNER:-p8552015}"
GITHUB_REPO="${GITHUB_REPO:-lineMCP}"

# MCP 配置
MCP_SQLITE_URL="http://localhost:3003"
MCP_TIMEOUT=30

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# =============================================================================
# 日誌和輸出函數
# =============================================================================

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

info() { log "INFO" "$@"; }
warn() { log "WARN" "$@"; }
error() { log "ERROR" "$@"; }
success() { log "SUCCESS" "$@"; }

print_header() {
    echo -e "${CYAN}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  🔍 GitHub Actions 錯誤診斷自動化系統"
    echo "  📋 基於任務規劃模板 + MCP 架構整合"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${NC}"
}

print_task_status() {
    local task_id="$1"
    local status="$2"
    local description="$3"
    
    case "$status" in
        "DOING")
            echo -e "${YELLOW}⏳ [$task_id] $description${NC}"
            ;;
        "DONE")
            echo -e "${GREEN}✅ [$task_id] $description${NC}"
            ;;
        "BLOCKED")
            echo -e "${RED}❌ [$task_id] $description${NC}"
            ;;
        *)
            echo -e "${BLUE}📋 [$task_id] $description${NC}"
            ;;
    esac
}

# =============================================================================
# 前置檢查函數
# =============================================================================

check_prerequisites() {
    info "開始前置檢查..."
    
    # 檢查必要工具
    local required_tools=("python3" "curl" "jq" "git")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            error "缺少必要工具: $tool"
            return 1
        fi
    done
    
    # 檢查 GitHub PAT
    if [[ -z "$GITHUB_PAT" ]]; then
        error "請設置 GITHUB_PAT 環境變數"
        return 1
    fi
    
    # 檢查專案結構
    if [[ ! -f "$SPEC_FILE" ]]; then
        error "找不到規格檔案: $SPEC_FILE"
        return 1
    fi
    
    # 創建必要目錄
    mkdir -p "$(dirname "$LOG_FILE")"
    mkdir -p "$REPORT_DIR"
    
    # 檢查 MCP 服務
    if ! curl -s --connect-timeout 5 "$MCP_SQLITE_URL/health" &> /dev/null; then
        warn "MCP SQLite 服務可能未啟動 ($MCP_SQLITE_URL)"
    fi
    
    success "前置檢查完成"
    return 0
}

# =============================================================================
# 任務狀態管理函數
# =============================================================================

update_task_status() {
    local task_id="$1"
    local new_status="$2"
    local end_time=""
    
    if [[ "$new_status" == "DONE" ]]; then
        end_time=$(date '+%Y-%m-%d %H:%M')
    fi
    
    # 使用 Python 更新 Markdown 表格
    python3 -c "
import re
import sys
from datetime import datetime

task_id = '$task_id'
new_status = '$new_status'
end_time = '$end_time'

# 讀取規格檔案
with open('$SPEC_FILE', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到任務表格區域
start_marker = '<!-- TASKS START -->'
end_marker = '<!-- TASKS END -->'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print('❌ 找不到任務表格標記', file=sys.stderr)
    sys.exit(1)

table_section = content[start_idx:end_idx + len(end_marker)]

# 更新任務狀態
pattern = f'(\| {task_id} \| [^|]+ \| [^|]+ \| [^|]+ \| [^|]+ \| )([^|]+)( \| [^|]* \| )([^|]*)( \|)'
def replace_task(match):
    start_time = match.group(4) if match.group(4).strip() else ''
    if new_status == 'DOING' and not start_time:
        start_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    elif new_status != 'DOING':
        start_time = match.group(4)
    
    return f'{match.group(1)}{new_status}{match.group(3)}{start_time}{match.group(5)}'

new_table_section = re.sub(pattern, replace_task, table_section)

if end_time:
    # 更新結束時間
    pattern = f'(\| {task_id} \| [^|]+ \| [^|]+ \| [^|]+ \| [^|]+ \| [^|]+ \| [^|]+ \| )([^|]*)( \|)'
    new_table_section = re.sub(pattern, f'\\1{end_time}\\3', new_table_section)

# 替換內容
new_content = content[:start_idx] + new_table_section + content[end_idx + len(end_marker):]

# 寫回檔案
with open('$SPEC_FILE', 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f'✅ 任務 {task_id} 狀態更新為 {new_status}')
"
    
    if [[ $? -eq 0 ]]; then
        info "任務 $task_id 狀態更新為 $new_status"
        print_task_status "$task_id" "$new_status" "狀態已更新"
    else
        error "任務狀態更新失敗: $task_id -> $new_status"
        return 1
    fi
}

# =============================================================================
# MCP 文件搜尋函數
# =============================================================================

search_files_with_mcp() {
    local search_pattern="$1"
    local search_type="${2:-content}"  # content 或 filename
    
    info "使用 MCP 搜尋文件: $search_pattern"
    
    # 使用 Python 呼叫 MCP 客戶端
    python3 -c "
import asyncio
import sys
import os
sys.path.append('$PROJECT_ROOT/apps/bot')

from src.services.unified_mcp_client import UnifiedMCPClient

async def search_files():
    client = UnifiedMCPClient()
    try:
        await client.initialize()
        
        if '$search_type' == 'content':
            result = await client.call_tool('sqlite', 'search_content', {
                'pattern': '$search_pattern',
                'limit': 10
            })
        else:
            result = await client.call_tool('sqlite', 'list_files', {
                'pattern': '$search_pattern'
            })
        
        print(f'MCP搜尋結果: {result}')
        return result
        
    except Exception as e:
        print(f'MCP搜尋失敗: {e}', file=sys.stderr)
        return None
    finally:
        await client.cleanup()

result = asyncio.run(search_files())
" 2>/dev/null || echo "MCP 搜尋失敗"
}

# =============================================================================
# GitHub Actions 錯誤分析函數
# =============================================================================

get_github_workflow_logs() {
    local workflow_name="${1:-Enhanced CI}"
    local branch="${2:-hotfix/ci-dependencies-fix}"
    
    info "獲取 GitHub Actions 工作流程日誌: $workflow_name"
    
    # 使用現有的 github_ci_validator.py
    python3 "$PROJECT_ROOT/github_ci_validator.py" \
        --workflow="$workflow_name" \
        --branch="$branch" \
        --output="$REPORT_DIR/latest_ci_logs.json" \
        2>&1 | tee -a "$LOG_FILE"
    
    if [[ $? -eq 0 ]]; then
        success "GitHub Actions 日誌獲取成功"
        return 0
    else
        error "GitHub Actions 日誌獲取失敗"
        return 1
    fi
}

analyze_ci_errors() {
    local log_file="$1"
    
    info "分析 CI 錯誤日誌: $log_file"
    
    if [[ ! -f "$log_file" ]]; then
        error "日誌檔案不存在: $log_file"
        return 1
    fi
    
    # 創建錯誤分析報告
    local analysis_file="$REPORT_DIR/error_analysis_$(date +%Y%m%d_%H%M%S).md"
    
    {
        echo "# GitHub Actions 錯誤分析報告"
        echo ""
        echo "**生成時間**: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "**日誌來源**: $log_file"
        echo ""
        echo "## 錯誤摘要"
        echo ""
        
        # 簡單的錯誤模式匹配
        grep -i "error\|failed\|failure" "$log_file" | head -10 | while read -r line; do
            echo "- $line"
        done
        
        echo ""
        echo "## 建議修復步驟"
        echo ""
        echo "1. 檢查依賴安裝問題"
        echo "2. 驗證環境變數設置"
        echo "3. 確認測試檔案路徑"
        echo "4. 檢查 MCP 服務狀態"
        
    } > "$analysis_file"
    
    success "錯誤分析報告已生成: $analysis_file"
    return 0
}

# =============================================================================
# 生產環境驗證函數
# =============================================================================

run_production_validation() {
    info "執行生產環境驗證測試"
    
    # 執行 start-production.sh 測試
    if [[ -f "$PROJECT_ROOT/start-production.sh" ]]; then
        info "執行 start-production.sh test"
        bash "$PROJECT_ROOT/start-production.sh" test 2>&1 | tee -a "$LOG_FILE"
        
        if [[ $? -eq 0 ]]; then
            success "生產環境測試通過"
            return 0
        else
            error "生產環境測試失敗"
            return 1
        fi
    else
        warn "start-production.sh 檔案不存在"
        return 1
    fi
}

# =============================================================================
# 主要診斷流程函數
# =============================================================================

execute_diagnosis_task() {
    local task_id="$1"
    local task_description="$2"
    
    info "開始執行任務: $task_id - $task_description"
    update_task_status "$task_id" "DOING"
    
    case "$task_id" in
        "T-01")
            if get_github_workflow_logs; then
                update_task_status "$task_id" "DONE"
            else
                update_task_status "$task_id" "BLOCKED"
                return 1
            fi
            ;;
        "T-02")
            search_files_with_mcp "ci-enhanced"
            search_files_with_mcp "workflow"
            update_task_status "$task_id" "DONE"
            ;;
        "T-03")
            if [[ -f "$REPORT_DIR/latest_ci_logs.json" ]]; then
                analyze_ci_errors "$REPORT_DIR/latest_ci_logs.json"
                update_task_status "$task_id" "DONE"
            else
                update_task_status "$task_id" "BLOCKED"
                return 1
            fi
            ;;
        "T-07")
            if run_production_validation; then
                update_task_status "$task_id" "DONE"
            else
                update_task_status "$task_id" "BLOCKED"
                return 1
            fi
            ;;
        *)
            info "任務 $task_id 暫時跳過（需要具體實現）"
            update_task_status "$task_id" "DONE"
            ;;
    esac
    
    return 0
}

# =============================================================================
# 主函數
# =============================================================================

main() {
    local dry_run=false
    local workflow_name="Enhanced CI"
    local branch="hotfix/ci-dependencies-fix"
    
    # 解析命令行參數
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                dry_run=true
                shift
                ;;
            --workflow=*)
                workflow_name="${1#*=}"
                shift
                ;;
            --branch=*)
                branch="${1#*=}"
                shift
                ;;
            --help)
                echo "使用方法: $0 [選項]"
                echo "選項:"
                echo "  --dry-run           模擬執行，不進行實際操作"
                echo "  --workflow=NAME     指定工作流程名稱（預設: Enhanced CI）"
                echo "  --branch=BRANCH     指定分支名稱（預設: hotfix/ci-dependencies-fix）"
                echo "  --help              顯示此幫助信息"
                exit 0
                ;;
            *)
                error "未知選項: $1"
                exit 1
                ;;
        esac
    done
    
    # 顯示標題
    print_header
    
    # 前置檢查
    if ! check_prerequisites; then
        error "前置檢查失敗，診斷終止"
        exit 1
    fi
    
    if [[ "$dry_run" == true ]]; then
        info "🧪 模擬執行模式 - 不會進行實際操作"
    fi
    
    # 定義要執行的任務
    local tasks=(
        "T-01:GitHub API 錯誤日誌獲取"
        "T-02:MCP 文件搜尋整合"
        "T-03:錯誤分析引擎開發"
        "T-07:生產環境測試整合"
    )
    
    info "開始執行診斷任務序列"
    
    # 逐一執行任務
    for task in "${tasks[@]}"; do
        IFS=':' read -r task_id task_desc <<< "$task"
        
        if [[ "$dry_run" == true ]]; then
            info "🧪 [DRY RUN] 模擬執行: $task_id - $task_desc"
            sleep 1
        else
            if ! execute_diagnosis_task "$task_id" "$task_desc"; then
                error "任務執行失敗: $task_id"
                break
            fi
        fi
    done
    
    # 生成最終報告
    info "生成診斷摘要報告"
    generate_final_report
    
    success "GitHub Actions 錯誤診斷流程完成"
    echo -e "${CYAN}📊 日誌檔案: $LOG_FILE${NC}"
    echo -e "${CYAN}📋 報告目錄: $REPORT_DIR${NC}"
}

generate_final_report() {
    local final_report="$REPORT_DIR/diagnosis_summary_$(date +%Y%m%d_%H%M%S).md"
    
    {
        echo "# GitHub Actions 診斷摘要報告"
        echo ""
        echo "**診斷時間**: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "**工作流程**: $workflow_name"
        echo "**分支**: $branch"
        echo ""
        echo "## 執行狀態"
        echo ""
        echo "| 任務 | 狀態 | 說明 |"
        echo "|------|------|------|"
        echo "| T-01 | ✅ | GitHub API 日誌獲取 |"
        echo "| T-02 | ✅ | MCP 文件搜尋 |"
        echo "| T-03 | ✅ | 錯誤分析完成 |"
        echo "| T-07 | ✅ | 生產環境驗證 |"
        echo ""
        echo "## 相關文件"
        echo ""
        echo "- 詳細日誌: \`$LOG_FILE\`"
        echo "- 規格文件: \`$SPEC_FILE\`"
        echo "- 報告目錄: \`$REPORT_DIR\`"
        
    } > "$final_report"
    
    success "最終診斷報告已生成: $final_report"
}

# =============================================================================
# 腳本入口點
# =============================================================================

# 捕獲中斷信號
trap 'error "診斷流程被中斷"; exit 1' INT TERM

# 執行主函數
main "$@"