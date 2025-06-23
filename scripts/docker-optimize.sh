#!/bin/bash

# ==============================================================================
# Docker 容器化優化腳本
# 實現多階段建構、快取優化、安全掃描
# ==============================================================================

set -e  # 遇到錯誤立即退出

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 項目根目錄
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BOT_DIR="$PROJECT_ROOT/apps/bot"

# 配置變數
REGISTRY=${DOCKER_REGISTRY:-"ghcr.io"}
ORGANIZATION=${DOCKER_ORG:-"your-org"}
IMAGE_NAME="line-mcp-bot"
PLATFORMS=${DOCKER_PLATFORMS:-"linux/amd64,linux/arm64"}

# 版本信息
VERSION=${1:-"latest"}
BUILD_TYPE=${2:-"production"}

echo -e "${BLUE}🐳 LINE MCP Docker 容器化優化${NC}"
echo "=============================================="
echo -e "📋 配置信息:"
echo -e "  Registry: ${CYAN}$REGISTRY${NC}"
echo -e "  Organization: ${CYAN}$ORGANIZATION${NC}"
echo -e "  Image: ${CYAN}$IMAGE_NAME${NC}"
echo -e "  Version: ${CYAN}$VERSION${NC}"
echo -e "  Build Type: ${CYAN}$BUILD_TYPE${NC}"
echo -e "  Platforms: ${CYAN}$PLATFORMS${NC}"
echo ""

# 函數：打印步驟
print_step() {
    echo -e "${YELLOW}▶ $1${NC}"
}

# 函數：打印成功
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# 函數：打印錯誤
print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 函數：打印警告
print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

# 函數：檢查依賴
check_dependencies() {
    print_step "檢查依賴環境"
    
    # 檢查 Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安裝"
        exit 1
    fi
    
    # 檢查 Docker Buildx
    if ! docker buildx version &> /dev/null; then
        print_error "Docker Buildx 未安裝或未啟用"
        exit 1
    fi
    
    # 檢查項目結構
    if [ ! -f "$BOT_DIR/Dockerfile.optimized" ]; then
        print_error "優化 Dockerfile 不存在: $BOT_DIR/Dockerfile.optimized"
        exit 1
    fi
    
    if [ ! -f "$BOT_DIR/pyproject.toml" ]; then
        print_error "pyproject.toml 不存在: $BOT_DIR/pyproject.toml"
        exit 1
    fi
    
    print_success "依賴檢查完成"
}

# 函數：設置 Docker Buildx
setup_buildx() {
    print_step "設置 Docker Buildx"
    
    # 創建並使用 buildx builder
    if ! docker buildx ls | grep -q "line-mcp-builder"; then
        docker buildx create --name line-mcp-builder --use
        print_success "已創建 buildx builder"
    else
        docker buildx use line-mcp-builder
        print_success "使用現有 buildx builder"
    fi
    
    # 啟動 builder
    docker buildx inspect --bootstrap
}

# 函數：清理 Docker 快取
clean_cache() {
    print_step "清理 Docker 快取"
    
    echo "清理未使用的映像..."
    docker image prune -f
    
    echo "清理建構快取..."
    docker buildx prune -f
    
    print_success "快取清理完成"
}

# 函數：建構映像
build_image() {
    local target=$1
    local tag_suffix=$2
    
    print_step "建構 $target 映像"
    
    # 構建標籤
    local base_tag="$REGISTRY/$ORGANIZATION/$IMAGE_NAME"
    local full_tag="$base_tag:$VERSION"
    
    if [ -n "$tag_suffix" ]; then
        full_tag="$base_tag:$VERSION-$tag_suffix"
    fi
    
    # 建構參數
    local build_args=(
        "--file" "$BOT_DIR/Dockerfile.optimized"
        "--target" "$target"
        "--platform" "$PLATFORMS"
        "--tag" "$full_tag"
        "--cache-from" "type=gha"
        "--cache-to" "type=gha,mode=max"
        "--metadata-file" "/tmp/metadata-$target.json"
    )
    
    # 添加建構時間標籤
    if [ "$VERSION" = "latest" ]; then
        local timestamp=$(date +%Y%m%d-%H%M%S)
        build_args+=("--tag" "$base_tag:$timestamp")
    fi
    
    # 生產環境推送到 Registry
    if [ "$BUILD_TYPE" = "production" ]; then
        build_args+=("--push")
    else
        build_args+=("--load")
    fi
    
    # 添加建構標籤和元數據
    build_args+=(
        "--label" "org.opencontainers.image.created=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
        "--label" "org.opencontainers.image.version=$VERSION"
        "--label" "org.opencontainers.image.revision=$(git rev-parse HEAD)"
        "--label" "org.opencontainers.image.source=$(git config --get remote.origin.url)"
        "--label" "org.opencontainers.image.title=LINE MCP Bot"
        "--label" "org.opencontainers.image.description=Production-ready LINE Bot with MCP"
        "--label" "build.target=$target"
        "--label" "build.type=$BUILD_TYPE"
    )
    
    echo "執行建構命令:"
    echo "docker buildx build ${build_args[@]} $PROJECT_ROOT"
    echo ""
    
    # 執行建構 (從專案根目錄)
    if docker buildx build "${build_args[@]}" "$PROJECT_ROOT"; then
        print_success "$target 映像建構完成: $full_tag"
        
        # 顯示映像大小
        if [ "$BUILD_TYPE" != "production" ]; then
            local size=$(docker images --format "{{.Size}}" "$full_tag")
            echo -e "  映像大小: ${CYAN}$size${NC}"
        fi
    else
        print_error "$target 映像建構失敗"
        return 1
    fi
}

# 函數：安全掃描
security_scan() {
    local image_tag="$1"
    
    print_step "執行安全掃描: $image_tag"
    
    # 檢查 Trivy 是否安裝
    if ! command -v trivy &> /dev/null; then
        print_warning "Trivy 未安裝，跳過安全掃描"
        return 0
    fi
    
    # 執行 Trivy 掃描
    local scan_output="/tmp/trivy-scan-$(date +%s).json"
    
    if trivy image --format json --output "$scan_output" "$image_tag"; then
        # 分析掃描結果
        local critical=$(jq '.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL") | length' "$scan_output" 2>/dev/null | wc -l)
        local high=$(jq '.Results[]?.Vulnerabilities[]? | select(.Severity == "HIGH") | length' "$scan_output" 2>/dev/null | wc -l)
        local medium=$(jq '.Results[]?.Vulnerabilities[]? | select(.Severity == "MEDIUM") | length' "$scan_output" 2>/dev/null | wc -l)
        
        echo -e "  安全掃描結果:"
        echo -e "    嚴重: ${RED}$critical${NC}"
        echo -e "    高危: ${YELLOW}$high${NC}"
        echo -e "    中危: ${BLUE}$medium${NC}"
        
        # 如果有嚴重漏洞，警告但不阻止
        if [ "$critical" -gt 0 ]; then
            print_warning "發現 $critical 個嚴重安全漏洞"
        fi
        
        print_success "安全掃描完成"
    else
        print_warning "安全掃描失敗，但繼續執行"
    fi
    
    # 清理掃描文件
    rm -f "$scan_output"
}

# 函數：映像優化分析
analyze_image() {
    local image_tag="$1"
    
    print_step "分析映像: $image_tag"
    
    # 檢查 dive 是否安裝
    if command -v dive &> /dev/null; then
        echo "使用 dive 分析映像層..."
        dive "$image_tag" --ci
    else
        print_warning "dive 未安裝，跳過映像分析"
    fi
    
    # 顯示映像歷史
    echo "映像層歷史:"
    docker history "$image_tag" --format "table {{.CreatedBy}}\t{{.Size}}" | head -10
}

# 函數：推送映像
push_image() {
    local image_tag="$1"
    
    print_step "推送映像: $image_tag"
    
    if [ "$BUILD_TYPE" = "production" ]; then
        echo "生產模式已自動推送映像"
        return 0
    fi
    
    if docker push "$image_tag"; then
        print_success "映像推送完成"
    else
        print_error "映像推送失敗"
        return 1
    fi
}

# 函數：生成建構報告
generate_report() {
    print_step "生成建構報告"
    
    local report_file="$PROJECT_ROOT/build-report-$(date +%Y%m%d-%H%M%S).md"
    
    cat > "$report_file" << EOF
# Docker 建構報告

## 建構信息
- **時間**: $(date)
- **版本**: $VERSION
- **建構類型**: $BUILD_TYPE
- **平台**: $PLATFORMS
- **Git 提交**: $(git rev-parse HEAD)

## 建構結果
EOF
    
    # 添加映像信息
    if [ "$BUILD_TYPE" != "production" ]; then
        echo "" >> "$report_file"
        echo "## 映像列表" >> "$report_file"
        docker images | grep "$IMAGE_NAME" | grep "$VERSION" >> "$report_file"
    fi
    
    # 添加安全掃描結果
    if [ -f "/tmp/trivy-scan-*.json" ]; then
        echo "" >> "$report_file"
        echo "## 安全掃描結果" >> "$report_file"
        echo "請查看 Trivy 掃描報告。" >> "$report_file"
    fi
    
    print_success "建構報告已生成: $report_file"
}

# 函數：顯示使用方法
show_usage() {
    echo "使用方法:"
    echo "  $0 [VERSION] [BUILD_TYPE]"
    echo ""
    echo "參數:"
    echo "  VERSION     映像版本 (預設: latest)"
    echo "  BUILD_TYPE  建構類型 (預設: production)"
    echo ""
    echo "建構類型:"
    echo "  production  生產建構 (推送到 Registry)"
    echo "  development 開發建構 (本地建構)"
    echo "  testing     測試建構 (本地建構)"
    echo ""
    echo "環境變數:"
    echo "  DOCKER_REGISTRY    Docker Registry (預設: ghcr.io)"
    echo "  DOCKER_ORG         組織名稱 (預設: your-org)"
    echo "  DOCKER_PLATFORMS   建構平台 (預設: linux/amd64,linux/arm64)"
    echo ""
    echo "範例:"
    echo "  $0 v1.0.0 production"
    echo "  $0 latest development"
    echo "  DOCKER_ORG=myorg $0 v2.0.0"
}

# 主執行流程
main() {
    # 檢查幫助參數
    if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        show_usage
        exit 0
    fi
    
    echo -e "${PURPLE}🚀 開始 Docker 容器化優化流程${NC}"
    echo ""
    
    # 檢查依賴
    check_dependencies
    
    # 設置 buildx
    setup_buildx
    
    # 根據建構類型決定要建構的目標
    case "$BUILD_TYPE" in
        "production")
            print_step "建構生產環境映像"
            build_image "production" ""
            security_scan "$REGISTRY/$ORGANIZATION/$IMAGE_NAME:$VERSION"
            ;;
        "development")
            print_step "建構開發環境映像"
            build_image "development" "dev"
            local dev_tag="$REGISTRY/$ORGANIZATION/$IMAGE_NAME:$VERSION-dev"
            security_scan "$dev_tag"
            analyze_image "$dev_tag"
            ;;
        "testing")
            print_step "建構測試環境映像"
            build_image "testing" "test"
            ;;
        "all")
            print_step "建構所有環境映像"
            build_image "production" ""
            build_image "development" "dev"
            build_image "testing" "test"
            ;;
        *)
            print_error "未知的建構類型: $BUILD_TYPE"
            show_usage
            exit 1
            ;;
    esac
    
    # 生成報告
    generate_report
    
    echo ""
    print_success "🎉 Docker 容器化優化完成！"
    
    # 顯示下一步建議
    echo ""
    echo -e "${BLUE}💡 下一步建議:${NC}"
    echo "1. 測試映像: docker run --rm -p 8000:8000 $REGISTRY/$ORGANIZATION/$IMAGE_NAME:$VERSION"
    echo "2. 部署服務: docker-compose -f docker-compose.optimized.yml up"
    echo "3. 檢查日誌: docker logs line-mcp-bot-prod"
}

# 錯誤處理
trap 'print_error "腳本執行過程中發生錯誤"' ERR

# 執行主流程
main "$@"