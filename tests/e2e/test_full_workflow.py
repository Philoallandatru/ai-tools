"""完整的端到端测试，使用本地 LLM 进行真实测试。

这个测试套件覆盖所有主要功能：
1. Confluence 同步
2. Jira 同步
3. 报告生成
4. Jira 问题分析
5. 错误处理和边界情况

测试使用真实的本地 LLM（如果可用），否则跳过。
"""

import json
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Any

import pytest

from crawler.config import ConfigManager
from crawler.llm_client import LLMClient
from crawler.services import AnalysisService, ReportService, SyncService


# 检查本地 LLM 是否可用
def check_local_llm_available() -> bool:
    """检查本地 LLM 是否可用。"""
    try:
        client = LLMClient(
            provider="openai",
            model="qwen2.5-coder:7b",
            base_url="http://localhost:11434/v1",
            api_key="dummy",
        )
        response = client.generate("test", max_tokens=10)
        return bool(response)
    except Exception:
        return False


# 标记需要本地 LLM 的测试
requires_local_llm = pytest.mark.skipif(
    not check_local_llm_available(),
    reason="本地 LLM 不可用。请启动 Ollama 并确保 qwen2.5-coder:7b 模型可用。",
)


@pytest.fixture
def temp_workspace():
    """创建临时工作空间。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # 创建必要的目录结构
        sources_dir = workspace / "sources"
        sources_dir.mkdir()

        reports_dir = workspace / "reports"
        reports_dir.mkdir()

        yield {
            "workspace": workspace,
            "sources_dir": sources_dir,
            "reports_dir": reports_dir,
            "state_file": workspace / ".sync-state.json",
            "error_log": workspace / "errors.log",
        }


@pytest.fixture
def e2e_config(temp_workspace) -> Dict[str, Any]:
    """创建端到端测试配置。"""
    return {
        "sources": {
            "confluence": [
                {
                    "name": "test-confluence",
                    "url": "https://test.atlassian.net",
                    "username": "test@example.com",
                    "api_token": "test-token",
                    "spaces": [{"key": "TEST", "name": "Test Space"}],
                }
            ],
            "jira": [
                {
                    "name": "test-jira",
                    "url": "https://test.atlassian.net",
                    "username": "test@example.com",
                    "api_token": "test-token",
                    "projects": [{"key": "TEST", "name": "Test Project"}],
                }
            ],
        },
        "output": {"base_dir": str(temp_workspace["sources_dir"])},
        "sync": {"state_file": str(temp_workspace["state_file"])},
        "error_handling": {
            "max_retries": 3,
            "retry_delay": 1,
            "error_log": str(temp_workspace["error_log"]),
        },
        "llm": {
            "provider": "openai",
            "model": "qwen2.5-coder:7b",
            "base_url": "http://localhost:11434/v1",
            "api_key": "dummy",
            "timeout": 120,
        },
    }


@pytest.fixture
def mock_confluence_data():
    """模拟 Confluence 数据。"""
    return {
        "space": {
            "key": "TEST",
            "name": "Test Space",
            "description": "A test space for E2E testing",
        },
        "pages": [
            {
                "id": "123",
                "title": "Architecture Overview",
                "content": """
                # System Architecture

                Our system consists of three main components:

                ## Frontend
                - React-based SPA
                - Material-UI components
                - Redux for state management

                ## Backend
                - Python FastAPI
                - PostgreSQL database
                - Redis cache

                ## Infrastructure
                - Docker containers
                - Kubernetes orchestration
                - AWS cloud hosting
                """,
                "version": 1,
                "created": "2024-01-01T10:00:00Z",
                "modified": "2024-01-15T14:30:00Z",
            },
            {
                "id": "124",
                "title": "API Documentation",
                "content": """
                # REST API Endpoints

                ## User Management
                - GET /api/users - List all users
                - POST /api/users - Create new user
                - GET /api/users/{id} - Get user details
                - PUT /api/users/{id} - Update user
                - DELETE /api/users/{id} - Delete user

                ## Authentication
                - POST /api/auth/login - User login
                - POST /api/auth/logout - User logout
                - POST /api/auth/refresh - Refresh token
                """,
                "version": 2,
                "created": "2024-01-02T09:00:00Z",
                "modified": "2024-01-20T11:00:00Z",
            },
        ],
    }


@pytest.fixture
def mock_jira_data():
    """模拟 Jira 数据。"""
    return {
        "project": {
            "key": "TEST",
            "name": "Test Project",
            "description": "A test project for E2E testing",
        },
        "issues": [
            {
                "key": "TEST-1",
                "summary": "Implement user authentication",
                "description": """
                We need to implement a secure user authentication system.

                Requirements:
                - JWT-based authentication
                - Password hashing with bcrypt
                - Session management
                - Remember me functionality

                Acceptance Criteria:
                - Users can register with email/password
                - Users can login and receive JWT token
                - Token expires after 24 hours
                - Refresh token mechanism works
                """,
                "status": "In Progress",
                "priority": "High",
                "assignee": "john.doe@example.com",
                "created": "2024-01-05T10:00:00Z",
                "updated": "2024-01-25T15:30:00Z",
                "comments": [
                    {
                        "author": "jane.smith@example.com",
                        "body": "I suggest using Auth0 for this instead of rolling our own.",
                        "created": "2024-01-06T11:00:00Z",
                    },
                    {
                        "author": "john.doe@example.com",
                        "body": "Good point, but we need full control for compliance reasons.",
                        "created": "2024-01-06T14:00:00Z",
                    },
                ],
            },
            {
                "key": "TEST-2",
                "summary": "Fix memory leak in data processing",
                "description": """
                The data processing service is experiencing memory leaks.

                Symptoms:
                - Memory usage grows over time
                - Eventually causes OOM errors
                - Happens during large batch processing

                Investigation:
                - Profiled with memory_profiler
                - Found unclosed database connections
                - Also found large objects not being garbage collected
                """,
                "status": "Done",
                "priority": "Critical",
                "assignee": "alice.wang@example.com",
                "created": "2024-01-10T09:00:00Z",
                "updated": "2024-01-28T16:00:00Z",
                "resolution": "Fixed",
                "comments": [
                    {
                        "author": "alice.wang@example.com",
                        "body": "Fixed by implementing proper connection pooling and adding explicit cleanup.",
                        "created": "2024-01-28T16:00:00Z",
                    },
                ],
            },
        ],
    }


class TestConfluenceE2E:
    """Confluence 端到端测试。"""

    def test_confluence_sync_workflow(self, e2e_config, temp_workspace, mock_confluence_data, mocker):
        """测试完整的 Confluence 同步流程。"""
        # Mock Confluence API 调用
        mock_crawler = mocker.patch("crawler.services.sync_service.ConfluenceCrawler")
        mock_instance = mock_crawler.return_value
        mock_instance.crawl_space.return_value = {
            "space_key": "TEST",
            "space_name": "Test Space",
            "pages": mock_confluence_data["pages"],
            "total_pages": len(mock_confluence_data["pages"]),
        }

        # 创建 SyncService
        service = SyncService(e2e_config)

        # 执行同步
        result = service.sync_confluence_space("test-confluence", "TEST")

        # 验证结果
        assert result["status"] == "success"
        assert result["space_key"] == "TEST"
        assert result["total_pages"] == 2

        # 验证文件已创建
        space_dir = temp_workspace["sources_dir"] / "confluence" / "test-confluence" / "TEST"
        assert space_dir.exists()

        # 验证页面文件
        pages_dir = space_dir / "pages"
        assert pages_dir.exists()
        assert len(list(pages_dir.glob("*.md"))) == 2

        # 验证状态文件
        assert temp_workspace["state_file"].exists()
        state = json.loads(temp_workspace["state_file"].read_text())
        assert "confluence" in state
        assert "test-confluence" in state["confluence"]


class TestJiraE2E:
    """Jira 端到端测试。"""

    def test_jira_sync_workflow(self, e2e_config, temp_workspace, mock_jira_data, mocker):
        """测试完整的 Jira 同步流程。"""
        # Mock Jira API 调用
        mock_crawler = mocker.patch("crawler.services.sync_service.JiraCrawler")
        mock_instance = mock_crawler.return_value
        mock_instance.crawl_project.return_value = {
            "project_key": "TEST",
            "project_name": "Test Project",
            "issues": mock_jira_data["issues"],
            "total_issues": len(mock_jira_data["issues"]),
        }

        # 创建 SyncService
        service = SyncService(e2e_config)

        # 执行同步
        result = service.sync_jira_project("test-jira", "TEST")

        # 验证结果
        assert result["status"] == "success"
        assert result["project_key"] == "TEST"
        assert result["total_issues"] == 2

        # 验证文件已创建
        project_dir = temp_workspace["sources_dir"] / "jira" / "test-jira" / "TEST"
        assert project_dir.exists()

        # 验证问题文件
        issues_dir = project_dir / "issues"
        assert issues_dir.exists()
        assert len(list(issues_dir.glob("*.md"))) == 2


@requires_local_llm
class TestReportGenerationE2E:
    """报告生成端到端测试（需要本地 LLM）。"""

    def test_weekly_report_generation(self, e2e_config, temp_workspace, mock_jira_data, mocker):
        """测试周报生成流程。"""
        # 准备测试数据
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()

        # Mock Jira 数据获取
        mock_crawler = mocker.patch("crawler.services.sync_service.JiraCrawler")
        mock_instance = mock_crawler.return_value
        mock_instance.crawl_project.return_value = {
            "project_key": "TEST",
            "issues": mock_jira_data["issues"],
        }

        # 先同步数据
        sync_service = SyncService(e2e_config)
        sync_service.sync_jira_project("test-jira", "TEST")

        # 生成报告
        report_service = ReportService(e2e_config)
        report_path = report_service.generate_weekly_report(
            start_date=start_date,
            end_date=end_date,
            output_dir=str(temp_workspace["reports_dir"]),
        )

        # 验证报告文件
        assert Path(report_path).exists()
        report_content = Path(report_path).read_text(encoding="utf-8")

        # 验证报告内容包含关键部分
        assert "# 周报" in report_content or "# Weekly Report" in report_content
        assert str(start_date) in report_content or start_date.strftime("%Y-%m-%d") in report_content
        assert str(end_date) in report_content or end_date.strftime("%Y-%m-%d") in report_content

        # 报告应该包含一些分析内容（由 LLM 生成）
        assert len(report_content) > 500  # 至少有一定长度的内容

    def test_monthly_report_generation(self, e2e_config, temp_workspace, mock_jira_data, mocker):
        """测试月报生成流程。"""
        # 准备测试数据
        start_date = date.today().replace(day=1)
        end_date = date.today()

        # Mock Jira 数据
        mock_crawler = mocker.patch("crawler.services.sync_service.JiraCrawler")
        mock_instance = mock_crawler.return_value
        mock_instance.crawl_project.return_value = {
            "project_key": "TEST",
            "issues": mock_jira_data["issues"],
        }

        # 同步并生成报告
        sync_service = SyncService(e2e_config)
        sync_service.sync_jira_project("test-jira", "TEST")

        report_service = ReportService(e2e_config)
        report_path = report_service.generate_monthly_report(
            year=start_date.year,
            month=start_date.month,
            output_dir=str(temp_workspace["reports_dir"]),
        )

        # 验证报告
        assert Path(report_path).exists()
        report_content = Path(report_path).read_text(encoding="utf-8")
        assert "# 月报" in report_content or "# Monthly Report" in report_content


@requires_local_llm
class TestJiraAnalysisE2E:
    """Jira 分析端到端测试（需要本地 LLM）。"""

    def test_jira_issue_analysis(self, e2e_config, temp_workspace, mock_jira_data, mocker):
        """测试 Jira 问题分析流程。"""
        # Mock Jira API
        mock_crawler = mocker.patch("crawler.services.sync_service.JiraCrawler")
        mock_instance = mock_crawler.return_value
        mock_instance.get_issue.return_value = mock_jira_data["issues"][0]

        # 先同步数据
        sync_service = SyncService(e2e_config)
        sync_service.sync_jira_project("test-jira", "TEST")

        # 执行分析
        analysis_service = AnalysisService(e2e_config)
        result = analysis_service.analyze_jira(
            issue_key="TEST-1",
            output_dir=str(temp_workspace["reports_dir"]),
        )

        # 验证分析结果
        assert result["status"] == "success"
        assert "report_path" in result

        # 验证报告文件
        report_path = Path(result["report_path"])
        assert report_path.exists()

        report_content = report_path.read_text(encoding="utf-8")

        # 验证报告包含关键信息
        assert "TEST-1" in report_content
        assert "user authentication" in report_content.lower()

        # 验证 LLM 分析内容存在
        assert len(report_content) > 1000  # 应该有详细的分析内容

    def test_multiple_issues_analysis(self, e2e_config, temp_workspace, mock_jira_data, mocker):
        """测试批量分析多个 Jira 问题。"""
        # Mock Jira API
        mock_crawler = mocker.patch("crawler.services.sync_service.JiraCrawler")
        mock_instance = mock_crawler.return_value

        def get_issue_side_effect(issue_key):
            for issue in mock_jira_data["issues"]:
                if issue["key"] == issue_key:
                    return issue
            return None

        mock_instance.get_issue.side_effect = get_issue_side_effect

        # 同步数据
        sync_service = SyncService(e2e_config)
        sync_service.sync_jira_project("test-jira", "TEST")

        # 分析多个问题
        analysis_service = AnalysisService(e2e_config)

        results = []
        for issue in mock_jira_data["issues"]:
            result = analysis_service.analyze_jira(
                issue_key=issue["key"],
                output_dir=str(temp_workspace["reports_dir"]),
            )
            results.append(result)

        # 验证所有分析都成功
        assert len(results) == 2
        assert all(r["status"] == "success" for r in results)

        # 验证所有报告文件都存在
        for result in results:
            assert Path(result["report_path"]).exists()


class TestErrorHandlingE2E:
    """错误处理端到端测试。"""

    def test_network_error_retry(self, e2e_config, temp_workspace, mocker):
        """测试网络错误重试机制。"""
        # Mock 网络错误
        mock_crawler = mocker.patch("crawler.services.sync_service.ConfluenceCrawler")
        mock_instance = mock_crawler.return_value

        # 前两次失败，第三次成功
        mock_instance.crawl_space.side_effect = [
            Exception("Network timeout"),
            Exception("Connection refused"),
            {
                "space_key": "TEST",
                "pages": [],
                "total_pages": 0,
            },
        ]

        # 创建 SyncService
        service = SyncService(e2e_config)

        # 执行同步（应该重试并最终成功）
        result = service.sync_confluence_space("test-confluence", "TEST")

        # 验证重试成功
        assert result["status"] == "success"
        assert mock_instance.crawl_space.call_count == 3

    def test_invalid_config_handling(self, temp_workspace):
        """测试无效配置处理。"""
        invalid_config = {
            "sources": {},  # 空的 sources
            "output": {"base_dir": str(temp_workspace["sources_dir"])},
        }

        # 应该抛出配置错误
        with pytest.raises((ValueError, KeyError)):
            SyncService(invalid_config)

    @requires_local_llm
    def test_llm_timeout_handling(self, e2e_config, temp_workspace, mocker):
        """测试 LLM 超时处理。"""
        # 修改配置，设置很短的超时
        e2e_config["llm"]["timeout"] = 1

        # Mock 一个很慢的 LLM 响应
        mock_client = mocker.patch("crawler.llm_client.LLMClient.generate")
        mock_client.side_effect = TimeoutError("LLM request timeout")

        # 创建 AnalysisService
        service = AnalysisService(e2e_config)

        # 执行分析（应该处理超时错误）
        with pytest.raises(TimeoutError):
            service.analyze_jira(
                issue_key="TEST-1",
                output_dir=str(temp_workspace["reports_dir"]),
            )


class TestFullWorkflowE2E:
    """完整工作流端到端测试。"""

    @requires_local_llm
    def test_complete_workflow(
        self, e2e_config, temp_workspace, mock_confluence_data, mock_jira_data, mocker
    ):
        """测试完整的工作流：同步 -> 分析 -> 生成报告。"""
        # 1. Mock 所有外部 API
        mock_confluence = mocker.patch("crawler.services.sync_service.ConfluenceCrawler")
        mock_confluence.return_value.crawl_space.return_value = {
            "space_key": "TEST",
            "pages": mock_confluence_data["pages"],
            "total_pages": len(mock_confluence_data["pages"]),
        }

        mock_jira = mocker.patch("crawler.services.sync_service.JiraCrawler")
        mock_jira.return_value.crawl_project.return_value = {
            "project_key": "TEST",
            "issues": mock_jira_data["issues"],
            "total_issues": len(mock_jira_data["issues"]),
        }

        def get_issue_side_effect(issue_key):
            for issue in mock_jira_data["issues"]:
                if issue["key"] == issue_key:
                    return issue
            return None

        mock_jira.return_value.get_issue.side_effect = get_issue_side_effect

        # 2. 同步 Confluence 和 Jira 数据
        sync_service = SyncService(e2e_config)

        confluence_result = sync_service.sync_confluence_space("test-confluence", "TEST")
        assert confluence_result["status"] == "success"

        jira_result = sync_service.sync_jira_project("test-jira", "TEST")
        assert jira_result["status"] == "success"

        # 3. 分析 Jira 问题
        analysis_service = AnalysisService(e2e_config)

        analysis_result = analysis_service.analyze_jira(
            issue_key="TEST-1",
            output_dir=str(temp_workspace["reports_dir"]),
        )
        assert analysis_result["status"] == "success"

        # 4. 生成周报
        report_service = ReportService(e2e_config)

        start_date = date.today() - timedelta(days=7)
        end_date = date.today()

        report_path = report_service.generate_weekly_report(
            start_date=start_date,
            end_date=end_date,
            output_dir=str(temp_workspace["reports_dir"]),
        )
        assert Path(report_path).exists()

        # 5. 验证所有生成的文件
        # Confluence 文件
        confluence_dir = temp_workspace["sources_dir"] / "confluence" / "test-confluence" / "TEST"
        assert confluence_dir.exists()
        assert len(list((confluence_dir / "pages").glob("*.md"))) == 2

        # Jira 文件
        jira_dir = temp_workspace["sources_dir"] / "jira" / "test-jira" / "TEST"
        assert jira_dir.exists()
        assert len(list((jira_dir / "issues").glob("*.md"))) == 2

        # 分析报告
        assert Path(analysis_result["report_path"]).exists()

        # 周报
        assert Path(report_path).exists()

        # 6. 验证状态文件
        state_file = temp_workspace["state_file"]
        assert state_file.exists()

        state = json.loads(state_file.read_text())
        assert "confluence" in state
        assert "jira" in state
        assert "test-confluence" in state["confluence"]
        assert "test-jira" in state["jira"]


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
