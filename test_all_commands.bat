@echo off
REM 测试 README.md 中的所有 CLI 命令
REM 用于验证每次修改后所有功能是否正常工作

setlocal enabledelayedexpansion

echo ==========================================
echo 开始测试所有 CLI 命令
echo ==========================================
echo.

set TOTAL_TESTS=0
set PASSED_TESTS=0
set FAILED_TESTS=0
set SKIPPED_TESTS=0

REM ==========================================
REM 1. 搜索功能测试
REM ==========================================
echo ==========================================
echo 1. 搜索功能测试
echo ==========================================

call :run_test "基本搜索" "uv run python cli.py search NVMe"
call :run_test "搜索 Jira issues" "uv run python cli.py search 测试 --type jira"
call :run_test "正则表达式搜索" "uv run python cli.py search KAN-[0-9]+ --regex"
call :run_test "带上下文搜索" "uv run python cli.py search 测试 --context 5"
call :run_test "只显示统计信息" "uv run python cli.py search NVMe --stats-only"

REM ==========================================
REM 2. Jira 查询功能测试
REM ==========================================
echo.
echo ==========================================
echo 2. Jira 查询功能测试
echo ==========================================

call :run_test "查找特定 Jira issue" "uv run python cli.py find-jira KAN-1"
call :run_test "列出所有 Jira issues" "uv run python cli.py list-jira"
call :run_test "按状态过滤 Jira" "uv run python cli.py list-jira --status 进行中"
call :run_test "按优先级过滤 Jira" "uv run python cli.py list-jira --priority High"

REM ==========================================
REM 3. Jira 分析功能测试
REM ==========================================
echo.
echo ==========================================
echo 3. Jira 分析功能测试
echo ==========================================

call :run_test "使用 Mock LLM 分析 Jira" "uv run python cli.py analyze-jira KAN-2 --llm-provider mock"
call :run_test_skip "使用真实 LLM 分析 Jira（需要 LLM 服务）"

REM ==========================================
REM 4. 文档分析功能测试
REM ==========================================
echo.
echo ==========================================
echo 4. 文档分析功能测试
echo ==========================================

call :run_test "分析文档（dry-run 模式）" "uv run python cli.py analyze-doc sources/KAN-1.md --dry-run"
call :run_test_skip "分析文档（真实 LLM，需要 LLM 服务）"
call :run_test "分析文档（指定输出路径）" "uv run python cli.py analyze-doc sources/KAN-1.md --output reports/test_analysis.md --dry-run"

REM ==========================================
REM 5. 报告生成功能测试
REM ==========================================
echo.
echo ==========================================
echo 5. 报告生成功能测试
echo ==========================================

call :run_test "生成周报" "uv run python cli.py generate-report"
call :run_test "生成日报" "uv run python cli.py generate-report --type daily"
call :run_test "生成月报" "uv run python cli.py generate-report --type monthly"
call :run_test "生成指定时间范围报告" "uv run python cli.py generate-report --start 2026-05-01 --end 2026-05-07"
call :run_test "生成 JSON 格式报告" "uv run python cli.py generate-report --format json"

REM ==========================================
REM 6. 筛选导出功能测试
REM ==========================================
echo.
echo ==========================================
echo 6. 筛选导出功能测试
echo ==========================================

call :run_test "导出今天更新的进行中 issues" "uv run python cli.py export-filtered --today --status 进行中"
call :run_test "导出最近 7 天更新的 issues" "uv run python cli.py export-filtered --days 7 --status 待办 --status 进行中"
call :run_test "导出昨天更新的 Confluence 页面" "uv run python cli.py export-filtered --type confluence --yesterday"

REM ==========================================
REM 7. 文档拆分功能测试
REM ==========================================
echo.
echo ==========================================
echo 7. 文档拆分功能测试
echo ==========================================

if exist "test-sources\nvme.md" (
    call :run_test "拆分长文档" "uv run python cli.py split-doc test-sources/nvme.md --split-level 2 --max-chars 15000 --dry-run"
) else (
    call :run_test_skip "拆分长文档（测试文件不存在）"
)

REM ==========================================
REM 8. Wiki 功能测试
REM ==========================================
echo.
echo ==========================================
echo 8. Wiki 功能测试
echo ==========================================

where llm-wiki-compiler >nul 2>&1
if %errorlevel% equ 0 (
    call :run_test "查看 Wiki 状态" "uv run python cli.py wiki-status"
    call :run_test_skip "编译知识库（耗时较长）"
    call :run_test_skip "查询知识库（需要先编译）"
) else (
    call :run_test_skip "Wiki 功能测试（llm-wiki-compiler 未安装）"
    call :run_test_skip "编译知识库"
    call :run_test_skip "查询知识库"
)

REM ==========================================
REM 9. 同步功能测试
REM ==========================================
echo.
echo ==========================================
echo 9. 同步功能测试
echo ==========================================

call :run_test_skip "同步 Atlassian 数据（避免实际调用 API）"

REM ==========================================
REM 测试总结
REM ==========================================
echo.
echo ==========================================
echo 测试总结
echo ==========================================
echo 总测试数: %TOTAL_TESTS%
echo 通过: %PASSED_TESTS%
echo 失败: %FAILED_TESTS%
echo 跳过: %SKIPPED_TESTS%
echo.

if %FAILED_TESTS% equ 0 (
    echo [32m✓ 所有测试通过！[0m
    exit /b 0
) else (
    echo [31m✗ 有 %FAILED_TESTS% 个测试失败[0m
    exit /b 1
)

REM ==========================================
REM 函数定义
REM ==========================================

:run_test
set /a TOTAL_TESTS+=1
echo.
echo [TEST %TOTAL_TESTS%] %~1
echo 命令: %~2

%~2 >nul 2>&1
if %errorlevel% equ 0 (
    echo [32m✓ PASSED[0m
    set /a PASSED_TESTS+=1
) else (
    echo [31m✗ FAILED[0m
    set /a FAILED_TESTS+=1
)
goto :eof

:run_test_skip
set /a TOTAL_TESTS+=1
set /a SKIPPED_TESTS+=1
echo [33m[SKIP][0m %~1
goto :eof
