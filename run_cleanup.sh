#!/bin/bash

# 程式碼清理執行腳本
# 基於 spec_code_cleanup.md 的安全清理流程

set -e  # 遇到錯誤立即退出

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPEC_FILE="$PROJECT_ROOT/spec_code_cleanup.md"
TASK_EXECUTOR="$PROJECT_ROOT/task_executor.py"
SAFETY_CHECKER="$PROJECT_ROOT/cleanup_safety_checker.py"

echo -e "${PURPLE}=============================================${NC}"
echo -e "${PURPLE}🧹 LINE MCP 程式碼清理執行器 v1.0${NC}"
echo -e "${PURPLE}=============================================${NC}"

# 函數：檢查必要檔案
check_prerequisites() {
    echo -e "${BLUE}🔍 檢查執行前提條件...${NC}"
    
    local missing_files=()
    
    if [[ ! -f "$SPEC_FILE" ]]; then
        missing_files+=("規格檔: $SPEC_FILE")
    fi
    
    if [[ ! -f "$TASK_EXECUTOR" ]]; then
        missing_files+=("任務執行器: $TASK_EXECUTOR")
    fi
    
    if [[ ! -f "$SAFETY_CHECKER" ]]; then
        missing_files+=("安全檢查器: $SAFETY_CHECKER")
    fi
    
    if [[ ${#missing_files[@]} -gt 0 ]]; then
        echo -e "${RED}❌ 缺少必要檔案:${NC}"
        for file in "${missing_files[@]}"; do
            echo -e "${RED}  - $file${NC}"
        done
        return 1
    fi
    
    echo -e "${GREEN}✅ 所有必要檔案存在${NC}"
    return 0
}

# 函數：執行安全檢查
run_safety_check() {
    echo -e "\n${BLUE}🛡️ 執行安全檢查...${NC}"
    
    cd "$PROJECT_ROOT"
    python3 "$SAFETY_CHECKER"
    
    if [[ $? -ne 0 ]]; then
        echo -e "${RED}❌ 安全檢查失敗${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✅ 安全檢查完成${NC}"
    return 0
}

# 函數：備份當前狀態
create_backup() {
    echo -e "\n${BLUE}💾 創建系統備份...${NC}"
    
    local backup_dir="$PROJECT_ROOT/backups/pre-cleanup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"
    
    # 備份關鍵目錄
    echo -e "${YELLOW}📂 備份源碼目錄...${NC}"
    cp -r "$PROJECT_ROOT/apps/bot/src" "$backup_dir/"
    
    # 備份配置檔案
    echo -e "${YELLOW}📄 備份配置檔案...${NC}"
    cp "$PROJECT_ROOT/start-production.sh" "$backup_dir/" 2>/dev/null || true
    cp "$PROJECT_ROOT/quick-start.sh" "$backup_dir/" 2>/dev/null || true
    
    # 創建 Git 標記點
    echo -e "${YELLOW}🏷️ 創建 Git 標記點...${NC}"
    cd "$PROJECT_ROOT"
    git tag "pre-cleanup-backup-$(date +%Y%m%d-%H%M%S)" 2>/dev/null || true
    
    echo -e "${GREEN}✅ 備份完成: $backup_dir${NC}"
    echo "$backup_dir" > "$PROJECT_ROOT/.last_backup"
    return 0
}

# 函數：執行任務
run_tasks() {
    echo -e "\n${BLUE}🚀 開始執行清理任務...${NC}"
    
    cd "$PROJECT_ROOT"
    python3 "$TASK_EXECUTOR" "$SPEC_FILE"
    
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        echo -e "${GREEN}✅ 所有任務執行完成${NC}"
    else
        echo -e "${RED}❌ 任務執行失敗 (退出碼: $exit_code)${NC}"
    fi
    
    return $exit_code
}

# 函數：執行驗證測試
run_verification() {
    echo -e "\n${BLUE}🧪 執行驗證測試...${NC}"
    
    cd "$PROJECT_ROOT"
    
    # 1. 基本測試套件
    echo -e "${YELLOW}📋 執行基本測試套件...${NC}"
    cd apps/bot
    poetry run pytest -v --tb=short
    
    if [[ $? -ne 0 ]]; then
        echo -e "${RED}❌ 基本測試失敗${NC}"
        return 1
    fi
    
    # 2. 整合測試
    echo -e "${YELLOW}🔗 執行整合測試...${NC}"
    cd "$PROJECT_ROOT"
    ./start-production.sh test
    
    if [[ $? -ne 0 ]]; then
        echo -e "${RED}❌ 整合測試失敗${NC}"
        return 1
    fi
    
    # 3. 生產環境驗證 (M001 機台查詢)
    echo -e "${YELLOW}🏭 執行生產環境驗證...${NC}"
    timeout 30s ./start-production.sh > /tmp/production_test.log 2>&1 &
    local prod_pid=$!
    
    sleep 10  # 等待系統啟動
    
    # 這裡可以添加實際的 M001 查詢測試
    # 目前只檢查進程是否正常運行
    if kill -0 $prod_pid 2>/dev/null; then
        kill $prod_pid 2>/dev/null || true
        wait $prod_pid 2>/dev/null || true
        echo -e "${GREEN}✅ 生產環境驗證通過${NC}"
    else
        echo -e "${RED}❌ 生產環境驗證失敗${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✅ 所有驗證測試通過${NC}"
    return 0
}

# 函數：回滾操作
rollback() {
    echo -e "\n${YELLOW}🔄 執行回滾操作...${NC}"
    
    if [[ -f "$PROJECT_ROOT/.last_backup" ]]; then
        local backup_dir=$(cat "$PROJECT_ROOT/.last_backup")
        
        if [[ -d "$backup_dir" ]]; then
            echo -e "${YELLOW}📂 從備份恢復: $backup_dir${NC}"
            
            # 恢復源碼
            if [[ -d "$backup_dir/src" ]]; then
                rm -rf "$PROJECT_ROOT/apps/bot/src"
                cp -r "$backup_dir/src" "$PROJECT_ROOT/apps/bot/"
                echo -e "${GREEN}✅ 源碼已恢復${NC}"
            fi
            
            # 恢復腳本
            if [[ -f "$backup_dir/start-production.sh" ]]; then
                cp "$backup_dir/start-production.sh" "$PROJECT_ROOT/"
                chmod +x "$PROJECT_ROOT/start-production.sh"
                echo -e "${GREEN}✅ 啟動腳本已恢復${NC}"
            fi
            
            echo -e "${GREEN}✅ 回滾操作完成${NC}"
            return 0
        fi
    fi
    
    echo -e "${RED}❌ 找不到備份資料，嘗試 Git 回滾${NC}"
    
    # 嘗試 Git 回滾
    cd "$PROJECT_ROOT"
    local latest_tag=$(git tag -l "pre-cleanup-backup-*" | sort -V | tail -1)
    
    if [[ -n "$latest_tag" ]]; then
        echo -e "${YELLOW}🏷️ 回滾到標記: $latest_tag${NC}"
        git checkout "$latest_tag"
        echo -e "${GREEN}✅ Git 回滾完成${NC}"
        return 0
    fi
    
    echo -e "${RED}❌ 無法執行回滾操作${NC}"
    return 1
}

# 函數：顯示幫助
show_help() {
    echo -e "${BLUE}用法: $0 [選項]${NC}"
    echo ""
    echo -e "${YELLOW}選項:${NC}"
    echo "  run        執行完整清理流程 (預設)"
    echo "  check      僅執行安全檢查"
    echo "  backup     僅創建備份"
    echo "  test       僅執行驗證測試"
    echo "  rollback   執行回滾操作"
    echo "  help       顯示此幫助訊息"
    echo ""
    echo -e "${YELLOW}範例:${NC}"
    echo "  $0              # 執行完整清理流程"
    echo "  $0 check        # 僅執行安全檢查"
    echo "  $0 rollback     # 回滾到清理前狀態"
}

# 主執行邏輯
main() {
    local action="${1:-run}"
    
    case "$action" in
        "run")
            check_prerequisites || exit 1
            create_backup || exit 1
            run_safety_check || exit 1
            
            echo -e "\n${YELLOW}⚠️ 即將開始清理操作，是否繼續？(y/N):${NC} "
            read -r response
            if [[ "$response" != "y" && "$response" != "Y" ]]; then
                echo -e "${YELLOW}❌ 操作已取消${NC}"
                exit 0
            fi
            
            if run_tasks; then
                echo -e "\n${GREEN}🎉 清理任務完成，開始驗證...${NC}"
                if run_verification; then
                    echo -e "\n${GREEN}✅ 程式碼清理流程成功完成！${NC}"
                    exit 0
                else
                    echo -e "\n${RED}❌ 驗證失敗，建議檢查或回滾${NC}"
                    echo -e "${YELLOW}執行回滾: $0 rollback${NC}"
                    exit 1
                fi
            else
                echo -e "\n${RED}❌ 清理任務失敗${NC}"
                echo -e "${YELLOW}執行回滾: $0 rollback${NC}"
                exit 1
            fi
            ;;
        "check")
            check_prerequisites || exit 1
            run_safety_check
            ;;
        "backup")
            create_backup
            ;;
        "test")
            run_verification
            ;;
        "rollback")
            rollback
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            echo -e "${RED}❌ 未知選項: $action${NC}"
            show_help
            exit 1
            ;;
    esac
}

# 捕獲中斷信號
trap 'echo -e "\n${YELLOW}⚠️ 操作被中斷${NC}"; exit 130' INT TERM

# 執行主邏輯
main "$@"