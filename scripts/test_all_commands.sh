#!/bin/bash
# 测试 README.md 中的所有 CLI 命令
# 用于验证每次修改后所有功能是否正常工作

# 不使用 set -e，让测试继续运行并收集所有结果

echo "=========================================="
echo "开始测试所有 CLI 命令"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试计数器
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

# 测试函数
run_test() {
    local test_name="$1"
    local command="$2"
    local should_skip="${3:-false}"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [ "$should_skip" = "true" ]; then
        echo -e "${YELLOW}[SKIP]${NC} $test_name"
        SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
        return
    fi

    echo -e "\n${YELLOW}[TEST $TOTAL_TESTS]${NC} $test_name"
    echo "命令: $command"

    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASSED${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗ FAILED${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

# ==========================================
# 1. 搜索功能测试
# ==========================================
echo "=========================================="
echo "1. 搜索功能测试"
echo "=========================================="

run_test "基本搜索" \
    "uv run python cli.py search 'NVMe'"

run_test "搜索 Jira issues" \
    "uv run python cli.py search '测试' --file-type jira"

run_test "正则表达式搜索" \
    "uv run python cli.py search 'KAN-[0-9]+' --regex"

run_test "带上下文搜索" \
    "uv run python cli.py search '测试' --context-lines 5"

run_test "只显示统计信息" \
    "uv run python cli.py search 'NVMe' --stats-only"

# ==========================================
# 2. Jira 查询功能测试
# ==========================================
echo ""
echo "=========================================="
echo "2. Jira 查询功能测试"
echo "=========================================="

run_test "查找特定 Jira issue" \
    "uv run python cli.py find-jira KAN-1"

run_test "列出所有 Jira issues" \
    "uv run python cli.py list-jira"

run_test "按状态过滤 Jira" \
    "uv run python cli.py list-jira --status '进行中'"

run_test "按优先级过滤 Jira" \
    "uv run python cli.py list-jira --priority High"

# ==========================================
# 3. Jira 分析功能测试
# ==========================================
echo ""
echo "=========================================="
echo "3. Jira 分析功能测试"
echo "=========================================="

run_test "使用 Mock LLM 分析 Jira" \
    "uv run python cli.py analyze-jira KAN-2 --llm-provider mock"

# 跳过真实 LLM 测试（需要 LLM 服务运行）
run_test "使用真实 LLM 分析 Jira" \
    "uv run python cli.py analyze-jira KAN-2" \
    "true"

# ==========================================
# 4. 文档分析功能测试
# ==========================================
echo ""
echo "=========================================="
echo "4. 文档分析功能测试"
echo "=========================================="

run_test "分析文档（dry-run 模式）" \
    "uv run python cli.py analyze-doc sources/KAN-1.md --dry-run"

# 跳过需要真实 LLM 的测试
run_test "分析文档（真实 LLM）" \
    "uv run python cli.py analyze-doc sources/KAN-1.md" \
    "true"

run_test "分析文档（指定输出路径）" \
    "uv run python cli.py analyze-doc sources/KAN-1.md --output reports/test_analysis.md --dry-run"

# ==========================================
# 5. 报告生成功能测试
# ==========================================
echo ""
echo "=========================================="
echo "5. 报告生成功能测试"
echo "=========================================="

run_test "生成周报" \
    "uv run python cli.py generate-report --report-type weekly"

run_test "生成 Jira 报告（需要 Jira 配置）" \
    "uv run python cli.py generate-report --report-type jira" \
    "true"

run_test "生成指定时间范围报告" \
    "uv run python cli.py generate-report --report-type weekly --start-date 2026-05-01 --end-date 2026-05-07"

run_test "生成 JSON 格式报告" \
    "uv run python cli.py generate-report --report-type weekly --output-format json"

# ==========================================
# 6. 筛选导出功能测试
# ==========================================
echo ""
echo "=========================================="
echo "6. 筛选导出功能测试"
echo "=========================================="

run_test "导出今天更新的进行中 issues" \
    "uv run python cli.py export-filtered --today --statuses '进行中'"

run_test "导出最近 7 天更新的 issues" \
    "uv run python cli.py export-filtered --days 7 --statuses '待办,进行中'"

run_test "导出昨天更新的 Confluence 页面" \
    "uv run python cli.py export-filtered --doc-type confluence --yesterday"

# ==========================================
# 7. 文档拆分功能测试
# ==========================================
echo ""
echo "=========================================="
echo "7. 文档拆分功能测试"
echo "=========================================="

# 检查测试文件是否存在
if [ -f "test-sources/nvme.md" ]; then
    run_test "拆分长文档" \
        "uv run python cli.py split-doc test-sources/nvme.md --split-level 2 --max-chars 15000 --dry-run"
else
    run_test "拆分长文档（测试文件不存在）" \
        "echo 'Skip: test-sources/nvme.md not found'" \
        "true"
fi

# ==========================================
# 8. Wiki 功能测试（需要 Node.js）
# ==========================================
echo ""
echo "=========================================="
echo "8. Wiki 功能测试"
echo "=========================================="

# 检查是否安装了 llm-wiki-compiler
if command -v llm-wiki-compiler &> /dev/null || npx llm-wiki-compiler --version &> /dev/null 2>&1; then
    run_test "查看 Wiki 状态" \
        "uv run python cli.py wiki-status"

    # 跳过编译和查询（耗时较长）
    run_test "编译知识库" \
        "uv run python cli.py compile-wiki" \
        "true"

    run_test "查询知识库" \
        "uv run python cli.py query-wiki '什么是 NVMe？'" \
        "true"
else
    echo -e "${YELLOW}[SKIP]${NC} Wiki 功能测试（llm-wiki-compiler 未安装）"
    SKIPPED_TESTS=$((SKIPPED_TESTS + 3))
    TOTAL_TESTS=$((TOTAL_TESTS + 3))
fi

# ==========================================
# 9. 同步功能测试（跳过，避免实际调用 API）
# ==========================================
echo ""
echo "=========================================="
echo "9. 同步功能测试"
echo "=========================================="

run_test "同步 Atlassian 数据" \
    "uv run python cli.py sync" \
    "true"

# ==========================================
# 测试总结
# ==========================================
echo ""
echo "=========================================="
echo "测试总结"
echo "=========================================="
echo -e "总测试数: $TOTAL_TESTS"
echo -e "${GREEN}通过: $PASSED_TESTS${NC}"
echo -e "${RED}失败: $FAILED_TESTS${NC}"
echo -e "${YELLOW}跳过: $SKIPPED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✓ 所有测试通过！${NC}"
    exit 0
else
    echo -e "${RED}✗ 有 $FAILED_TESTS 个测试失败${NC}"
    exit 1
fi
