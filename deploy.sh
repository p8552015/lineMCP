#!/bin/bash

# LINE MCP Bot 多環境部署腳本
# 使用方式: ./deploy.sh [environment] [action]
# 環境: dev/staging/prod
# 動作: up/down/restart/logs/status

set -euo pipefail

# 顏色代碼
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日誌函數
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 顯示使用說明
show_usage() {
    cat << EOF
LINE MCP Bot 多環境部署工具

使用方式:
    $0 [environment] [action] [options]

環境 (environment):
    dev       開發環境
    staging   測試環境  
    prod      生產環境

動作 (action):
    up        啟動服務
    down      停止服務
    restart   重啟服務
    logs      查看日誌
    status    查看狀態
    build     重新建構映像
    backup    執行備份
    restore   恢復備份

選項 (options):
    --force   強制執行動作
    --no-deps 不啟動依賴服務
    --scale   指定副本數量 (僅生產環境)

範例:
    $0 dev up                    # 啟動開發環境
    $0 staging logs              # 查看測試環境日誌
    $0 prod up --scale bot=3     # 啟動生產環境並設定 bot 服務 3 個副本
    $0 prod backup               # 執行生產環境備份

EOF
}

# 檢查必要工具
check_requirements() {
    local missing=()
    
    # 檢查 docker
    if ! command -v docker &> /dev/null; then
        missing+=("docker")
    fi
    
    # 檢查 docker-compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        missing+=("docker-compose")
    fi
    
    if [ ${#missing[@]} -ne 0 ]; then
        log_error "缺少必要工具: ${missing[*]}"
        log_info "請安裝缺少的工具後重試"
        exit 1
    fi
}

# 檢查環境檔案
check_env_file() {
    local environment=$1
    local env_file=".env.${environment}"
    
    if [ ! -f "$env_file" ]; then
        log_error "環境設定檔 $env_file 不存在"
        log_info "請從 .env.template 複製並設定適當的值"
        log_info "cp .env.template $env_file"
        exit 1
    fi
    
    # 檢查關鍵環境變數
    local required_vars=("LINE_CHANNEL_ACCESS_TOKEN" "LINE_CHANNEL_SECRET")
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" "$env_file" || grep -q "^${var}=your_" "$env_file"; then
            log_error "環境變數 $var 未正確設定於 $env_file"
            exit 1
        fi
    done
    
    log_success "環境設定檔 $env_file 檢查通過"
}

# 獲取 docker-compose 命令
get_compose_cmd() {
    if docker compose version &> /dev/null; then
        echo "docker compose"
    else
        echo "docker-compose"
    fi
}

# 設定環境變數
setup_environment() {
    local environment=$1
    
    # 設定 compose 檔案
    case $environment in
        dev)
            export COMPOSE_FILE="docker-compose.dev.yml"
            export COMPOSE_PROJECT_NAME="line-mcp-dev"
            ;;
        staging)
            export COMPOSE_FILE="docker-compose.staging.yml"
            export COMPOSE_PROJECT_NAME="line-mcp-staging"
            ;;
        prod)
            export COMPOSE_FILE="docker-compose.prod.yml"
            export COMPOSE_PROJECT_NAME="line-mcp-prod"
            ;;
        *)
            log_error "未知環境: $environment"
            show_usage
            exit 1
            ;;
    esac
    
    # 載入環境變數
    if [ -f ".env.${environment}" ]; then
        export $(cat ".env.${environment}" | grep -v '^#' | xargs)
    fi
    
    log_info "環境設定: $environment ($COMPOSE_FILE)"
}

# 檢查服務狀態
check_service_status() {
    local compose_cmd=$1
    
    log_info "檢查服務狀態..."
    
    # 獲取服務狀態
    local services_status
    services_status=$($compose_cmd ps --format json 2>/dev/null || echo "[]")
    
    if [ "$services_status" = "[]" ]; then
        log_warning "沒有運行中的服務"
        return 1
    fi
    
    # 解析並顯示狀態
    echo "$services_status" | python3 << 'EOF'
import json
import sys

try:
    services = json.loads(sys.stdin.read())
    if not services:
        print("沒有運行中的服務")
        sys.exit(1)
    
    print(f"{'服務名稱':<20} {'狀態':<10} {'端口':<20} {'健康狀態':<10}")
    print("-" * 70)
    
    for service in services:
        name = service.get('Service', 'N/A')
        state = service.get('State', 'N/A')
        ports = service.get('Publishers', [])
        health = service.get('Health', 'N/A')
        
        port_str = ', '.join([f"{p.get('PublishedPort', '')}:{p.get('TargetPort', '')}" for p in ports]) or 'N/A'
        
        status_icon = "🟢" if state == "running" else "🔴" if state == "exited" else "🟡"
        health_icon = "✅" if health == "healthy" else "❌" if health == "unhealthy" else "⏳"
        
        print(f"{name:<20} {status_icon} {state:<8} {port_str:<20} {health_icon} {health:<8}")

except Exception as e:
    print(f"解析服務狀態時出錯: {e}")
    sys.exit(1)
EOF
}

# 等待服務健康
wait_for_health() {
    local compose_cmd=$1
    local timeout=${2:-300}  # 預設 5 分鐘
    local interval=10
    local elapsed=0
    
    log_info "等待服務健康檢查通過 (超時: ${timeout}s)..."
    
    while [ $elapsed -lt $timeout ]; do
        local unhealthy_services
        unhealthy_services=$($compose_cmd ps --filter "health=unhealthy" --format "table {{.Service}}" | tail -n +2)
        
        if [ -z "$unhealthy_services" ]; then
            log_success "所有服務健康檢查通過"
            return 0
        fi
        
        log_info "等待服務健康: $unhealthy_services (${elapsed}/${timeout}s)"
        sleep $interval
        elapsed=$((elapsed + interval))
    done
    
    log_error "服務健康檢查超時"
    return 1
}

# 執行備份
perform_backup() {
    local environment=$1
    local compose_cmd=$2
    
    log_info "執行 $environment 環境備份..."
    
    # 建立備份目錄
    local backup_dir="backups/$(date +%Y%m%d_%H%M%S)_${environment}"
    mkdir -p "$backup_dir"
    
    # 備份資料庫
    if $compose_cmd ps postgres-primary &> /dev/null; then
        log_info "備份 PostgreSQL..."
        $compose_cmd exec -T postgres-primary pg_dump -U line_mcp line_mcp_${environment} > "${backup_dir}/postgres.sql"
    fi
    
    # 備份 Redis
    if $compose_cmd ps redis &> /dev/null; then
        log_info "備份 Redis..."
        $compose_cmd exec -T redis redis-cli BGSAVE
        $compose_cmd cp redis:/data/dump.rdb "${backup_dir}/redis.rdb"
    fi
    
    # 備份 SQLite
    if [ -f "data/sqlite/${environment}.db" ]; then
        log_info "備份 SQLite..."
        cp "data/sqlite/${environment}.db" "${backup_dir}/sqlite.db"
    fi
    
    # 建立備份資訊檔案
    cat > "${backup_dir}/backup_info.json" << EOF
{
    "environment": "$environment",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "git_commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "git_branch": "$(git branch --show-current 2>/dev/null || echo 'unknown')"
}
EOF
    
    log_success "備份完成: $backup_dir"
}

# 主要邏輯
main() {
    local environment=${1:-}
    local action=${2:-}
    shift 2 2>/dev/null || true
    local extra_args=("$@")
    
    # 檢查參數
    if [ -z "$environment" ] || [ -z "$action" ]; then
        show_usage
        exit 1
    fi
    
    # 檢查必要工具
    check_requirements
    
    # 設定環境
    setup_environment "$environment"
    
    # 檢查環境檔案
    check_env_file "$environment"
    
    # 獲取 compose 命令
    local compose_cmd
    compose_cmd=$(get_compose_cmd)
    
    # 執行動作
    case $action in
        up)
            log_info "啟動 $environment 環境..."
            
            # 建構映像 (如果需要)
            $compose_cmd build
            
            # 啟動服務
            $compose_cmd up -d "${extra_args[@]}"
            
            # 等待健康檢查
            if [ "$environment" != "dev" ]; then
                wait_for_health "$compose_cmd"
            fi
            
            # 顯示狀態
            check_service_status "$compose_cmd"
            
            log_success "$environment 環境啟動完成"
            ;;
            
        down)
            log_info "停止 $environment 環境..."
            $compose_cmd down "${extra_args[@]}"
            log_success "$environment 環境已停止"
            ;;
            
        restart)
            log_info "重啟 $environment 環境..."
            $compose_cmd restart "${extra_args[@]}"
            
            if [ "$environment" != "dev" ]; then
                wait_for_health "$compose_cmd"
            fi
            
            log_success "$environment 環境重啟完成"
            ;;
            
        logs)
            log_info "顯示 $environment 環境日誌..."
            $compose_cmd logs -f "${extra_args[@]}"
            ;;
            
        status)
            check_service_status "$compose_cmd"
            ;;
            
        build)
            log_info "重新建構 $environment 環境映像..."
            $compose_cmd build --no-cache "${extra_args[@]}"
            log_success "映像建構完成"
            ;;
            
        backup)
            perform_backup "$environment" "$compose_cmd"
            ;;
            
        restore)
            log_error "還原功能尚未實作"
            exit 1
            ;;
            
        *)
            log_error "未知動作: $action"
            show_usage
            exit 1
            ;;
    esac
}

# 執行主程式
main "$@"