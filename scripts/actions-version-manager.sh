#!/bin/bash

# 🔧 GitHub Actions 版本管理腳本
# 用於檢查、更新和監控 GitHub Actions 版本

set -euo pipefail

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
WORKFLOW_DIR=".github/workflows"
BACKUP_DIR=".github/workflows.backup"
LOG_FILE="actions-version-check.log"

# 記錄函數
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

# 顯示使用方法
show_usage() {
    cat << EOF
🔧 GitHub Actions 版本管理腳本

使用方法:
  $0 [選項]

選項:
  --scan                  掃描所有 workflow 中的 Actions 版本
  --check-updates         檢查 Actions 是否有更新版本
  --security-scan         執行安全檢查
  --update [action]       更新指定 Action (可選)
  --backup                備份當前 workflows
  --restore               還原 workflows 備份
  --report                生成詳細報告
  --help                  顯示此幫助訊息

範例:
  $0 --scan --report                    # 掃描並生成報告
  $0 --security-scan                    # 執行安全檢查
  $0 --update actions/checkout          # 更新特定 Action
  $0 --check-updates --backup           # 檢查更新並備份

EOF
}

# 檢查必要工具
check_dependencies() {
    local missing_tools=()
    
    for tool in jq yq gh; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        error "缺少必要工具: ${missing_tools[*]}"
        echo "請安裝缺少的工具："
        echo "  brew install jq yq gh"
        exit 1
    fi
}

# 掃描 Actions 版本
scan_actions() {
    log "🔍 掃描 GitHub Actions 版本..."
    
    if [ ! -d "$WORKFLOW_DIR" ]; then
        error "Workflows 目錄不存在: $WORKFLOW_DIR"
        return 1
    fi
    
    local actions_found=()
    local unsafe_versions=()
    
    # 掃描所有 YAML 文件
    while IFS= read -r -d '' file; do
        log "檢查檔案: $file"
        
        # 提取 uses 行
        while IFS= read -r line; do
            if [[ $line =~ uses:[[:space:]]+([^@]+)@([^[:space:]]+) ]]; then
                local action="${BASH_REMATCH[1]}"
                local version="${BASH_REMATCH[2]}"
                
                actions_found+=("$action@$version")
                
                # 檢查不安全版本
                if [[ $version =~ ^(main|master|latest)$ ]]; then
                    unsafe_versions+=("$action@$version in $file")
                fi
            fi
        done < <(grep "uses:" "$file" 2>/dev/null || true)
        
    done < <(find "$WORKFLOW_DIR" -name "*.yml" -o -name "*.yaml" -print0)
    
    # 顯示結果
    echo ""
    success "掃描完成！"
    echo ""
    echo "📋 發現的 Actions:"
    if [ ${#actions_found[@]} -gt 0 ]; then
        printf '%s\n' "${actions_found[@]}" | sort -u | while read -r action; do
            echo "  ✓ $action"
        done
    else
        echo "  (未發現 Actions)"
    fi
    
    if [ ${#unsafe_versions[@]} -gt 0 ]; then
        echo ""
        warn "🚨 發現不安全的版本標籤:"
        printf '%s\n' "${unsafe_versions[@]}" | while read -r unsafe; do
            echo "  ❌ $unsafe"
        done
    fi
    
    echo ""
    echo "📊 統計:"
    local unique_count=0
    if [ ${#actions_found[@]} -gt 0 ]; then
        unique_count=$(printf '%s\n' "${actions_found[@]}" | sort -u | wc -l)
    fi
    echo "  總 Actions 數量: $unique_count"
    echo "  不安全版本數量: ${#unsafe_versions[@]}"
}

# 檢查 Actions 更新
check_updates() {
    log "🔄 檢查 Actions 更新..."
    
    # 獲取所有 Actions
    local actions=()
    while IFS= read -r -d '' file; do
        while IFS= read -r line; do
            if [[ $line =~ uses:[[:space:]]*([^@]+)@(.+) ]]; then
                local action="${BASH_REMATCH[1]}"
                actions+=("$action")
            fi
        done < <(grep -E "^\s*uses:" "$file" 2>/dev/null || true)
    done < <(find "$WORKFLOW_DIR" -name "*.yml" -o -name "*.yaml" -print0)
    
    # 去重並檢查每個 Action
    printf '%s\n' "${actions[@]}" | sort -u | while read -r action; do
        log "檢查 $action 的最新版本..."
        
        # 跳過本地或相對路徑的 Actions
        if [[ $action == ./* ]] || [[ $action == ../* ]]; then
            continue
        fi
        
        # 獲取最新發布版本
        if latest_version=$(gh api "repos/$action/releases/latest" --jq '.tag_name' 2>/dev/null); then
            echo "  📦 $action: 最新版本 $latest_version"
        else
            warn "  ⚠️ $action: 無法獲取版本資訊"
        fi
    done
}

# 安全檢查
security_scan() {
    log "🔒 執行安全檢查..."
    
    local security_issues=()
    local recommendations=()
    
    # 檢查不安全的版本標籤
    while IFS= read -r -d '' file; do
        local line_num=0
        while IFS= read -r line; do
            ((line_num++))
            if [[ $line =~ uses:[[:space:]]*([^@]+)@(main|master|latest) ]]; then
                local action="${BASH_REMATCH[1]}"
                local version="${BASH_REMATCH[2]}"
                security_issues+=("$file:$line_num - $action@$version")
            fi
        done < "$file"
    done < <(find "$WORKFLOW_DIR" -name "*.yml" -o -name "*.yaml" -print0)
    
    # 檢查權限配置
    while IFS= read -r -d '' file; do
        if ! grep -q "permissions:" "$file"; then
            recommendations+=("$file - 建議添加明確的 permissions 配置")
        fi
    done < <(find "$WORKFLOW_DIR" -name "*.yml" -o -name "*.yaml" -print0)
    
    # 顯示結果
    echo ""
    if [ ${#security_issues[@]} -eq 0 ]; then
        success "🛡️ 未發現安全問題"
    else
        warn "🚨 發現 ${#security_issues[@]} 個安全問題:"
        printf '%s\n' "${security_issues[@]}" | while read -r issue; do
            echo "  ❌ $issue"
        done
    fi
    
    if [ ${#recommendations[@]} -gt 0 ]; then
        echo ""
        warn "💡 建議改進 (${#recommendations[@]} 項):"
        printf '%s\n' "${recommendations[@]}" | while read -r rec; do
            echo "  📝 $rec"
        done
    fi
}

# 更新特定 Action
update_action() {
    local target_action="$1"
    log "🔄 更新 Action: $target_action"
    
    # 獲取最新版本
    if ! latest_version=$(gh api "repos/$target_action/releases/latest" --jq '.tag_name' 2>/dev/null); then
        error "無法獲取 $target_action 的最新版本"
        return 1
    fi
    
    log "最新版本: $latest_version"
    
    # 在所有 workflow 文件中更新
    local updated_files=()
    while IFS= read -r -d '' file; do
        if grep -q "uses:.*$target_action@" "$file"; then
            log "更新檔案: $file"
            
            # 備份原文件
            cp "$file" "$file.backup"
            
            # 更新版本 (保留主版本標籤格式)
            if [[ $latest_version =~ ^v([0-9]+) ]]; then
                local major_version="v${BASH_REMATCH[1]}"
                sed -i.tmp "s|uses: *$target_action@[^[:space:]]*|uses: $target_action@$major_version|g" "$file"
                rm "$file.tmp"
                updated_files+=("$file")
            fi
        fi
    done < <(find "$WORKFLOW_DIR" -name "*.yml" -o -name "*.yaml" -print0)
    
    if [ ${#updated_files[@]} -eq 0 ]; then
        warn "未找到使用 $target_action 的文件"
    else
        success "已更新 ${#updated_files[@]} 個文件"
        printf '%s\n' "${updated_files[@]}" | while read -r file; do
            echo "  ✓ $file"
        done
    fi
}

# 備份 workflows
backup_workflows() {
    log "💾 備份 workflows..."
    
    if [ -d "$BACKUP_DIR" ]; then
        rm -rf "$BACKUP_DIR"
    fi
    
    cp -r "$WORKFLOW_DIR" "$BACKUP_DIR"
    success "已備份到: $BACKUP_DIR"
}

# 還原 workflows
restore_workflows() {
    log "🔄 還原 workflows..."
    
    if [ ! -d "$BACKUP_DIR" ]; then
        error "備份目錄不存在: $BACKUP_DIR"
        return 1
    fi
    
    rm -rf "$WORKFLOW_DIR"
    cp -r "$BACKUP_DIR" "$WORKFLOW_DIR"
    success "已從備份還原"
}

# 生成詳細報告
generate_report() {
    local report_file="actions-version-report-$(date +%Y%m%d-%H%M%S).md"
    
    log "📋 生成詳細報告: $report_file"
    
    cat > "$report_file" << EOF
# 🔧 GitHub Actions 版本檢查報告

**生成時間**: $(date)  
**檢查範圍**: $WORKFLOW_DIR

## 📊 總覽

EOF
    
    # 掃描並添加到報告
    local total_actions=0
    local unsafe_count=0
    
    {
        echo "## 📋 Actions 清單"
        echo ""
        echo "| Action | 版本 | 狀態 | 檔案 |"
        echo "|--------|------|------|------|"
        
        while IFS= read -r -d '' file; do
            local filename=$(basename "$file")
            while IFS= read -r line; do
                if [[ $line =~ uses:[[:space:]]*([^@]+)@(.+) ]]; then
                    local action="${BASH_REMATCH[1]}"
                    local version="${BASH_REMATCH[2]}"
                    local status="✅ 安全"
                    
                    ((total_actions++))
                    
                    if [[ $version =~ ^(main|master|latest)$ ]]; then
                        status="❌ 不安全"
                        ((unsafe_count++))
                    fi
                    
                    echo "| $action | $version | $status | $filename |"
                fi
            done < <(grep -E "^\s*uses:" "$file" 2>/dev/null || true)
        done < <(find "$WORKFLOW_DIR" -name "*.yml" -o -name "*.yaml" -print0)
        
    } >> "$report_file"
    
    # 添加統計和建議
    cat >> "$report_file" << EOF

## 📈 統計資訊

- **總 Actions 數量**: $total_actions
- **不安全版本數量**: $unsafe_count
- **安全評分**: $(( (total_actions - unsafe_count) * 100 / total_actions ))%

## 💡 改善建議

EOF
    
    if [ $unsafe_count -gt 0 ]; then
        cat >> "$report_file" << EOF
### 🚨 立即修復 (高優先級)

需要修復 $unsafe_count 個不安全的版本標籤:

\`\`\`bash
# 執行自動修復
$0 --security-scan
$0 --update <action-name>
\`\`\`

EOF
    fi
    
    cat >> "$report_file" << EOF
### 🔄 定期維護

1. **每週執行版本檢查**:
   \`\`\`bash
   $0 --scan --check-updates
   \`\`\`

2. **設定 Dependabot 自動更新**:
   - 已配置在 \`.github/dependabot.yml\`
   - 每週一自動檢查更新

3. **安全監控**:
   \`\`\`bash
   $0 --security-scan --report
   \`\`\`

---
**報告生成工具**: actions-version-manager.sh  
**最後更新**: $(date)
EOF
    
    success "報告已生成: $report_file"
}

# 主函數
main() {
    echo "🔧 GitHub Actions 版本管理腳本"
    echo "================================"
    
    # 檢查依賴
    check_dependencies
    
    # 檢查參數
    if [ $# -eq 0 ]; then
        show_usage
        exit 1
    fi
    
    # 處理參數
    while [[ $# -gt 0 ]]; do
        case $1 in
            --scan)
                scan_actions
                shift
                ;;
            --check-updates)
                check_updates
                shift
                ;;
            --security-scan)
                security_scan
                shift
                ;;
            --update)
                if [ -n "${2-}" ]; then
                    update_action "$2"
                    shift 2
                else
                    error "--update 需要指定 Action 名稱"
                    exit 1
                fi
                ;;
            --backup)
                backup_workflows
                shift
                ;;
            --restore)
                restore_workflows
                shift
                ;;
            --report)
                generate_report
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                error "未知選項: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    echo ""
    success "✅ 執行完成！"
}

# 執行主函數
main "$@"