"""Integration tests for Service layer end-to-end workflows."""

import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from crawler.services import AnalysisService, ReportService, SyncService


class TestServiceIntegration:
    """Test end-to-end service workflows."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
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
            "output": {"base_dir": "./sources"},
            "sync": {"state_file": "./.sync-state.json"},
            "error_handling": {
                "max_retries": 3,
                "retry_delay": 5,
                "error_log": "./errors.log",
            },
            "llm": {
                "provider": "mock",
                "model": "test-model",
            },
            "reports": {
                "fixed_issues": [],
                "max_issues_per_report": 100,
            },
            "jira_analysis": {
                "issue_summary": {"enabled": True}
            },
        }

    @patch("crawler.services.sync_service.ConfluenceCrawler")
    @patch("crawler.services.sync_service.JiraCrawler")
    def test_sync_service_end_to_end(
        self, mock_jira_crawler_class, mock_confluence_crawler_class, mock_config
    ):
        """Test complete sync workflow."""
        # Setup mocks
        mock_confluence_crawler = Mock()
        mock_confluence_crawler.crawl_space.return_value = {
            "pages": 10,
            "attachments": 5,
            "errors": [],
        }
        mock_confluence_crawler_class.return_value = mock_confluence_crawler

        mock_jira_crawler = Mock()
        mock_jira_crawler.crawl_project.return_value = {
            "issues": 20,
            "attachments": 3,
            "errors": [],
        }
        mock_jira_crawler_class.return_value = mock_jira_crawler

        # Create service and run sync
        service = SyncService(config=mock_config)
        result = service.sync_all(
            source_name=None,
            source_type="all",
        )

        # Verify results
        assert result["stats"]["confluence"]["pages"] == 10
        assert result["stats"]["confluence"]["attachments"] == 5
        assert result["stats"]["jira"]["issues"] == 20
        assert len(result["errors"]) == 0

        # Verify crawlers were called
        mock_confluence_crawler.crawl_space.assert_called_once()
        mock_jira_crawler.crawl_project.assert_called_once()

    @patch("crawler.services.report_service.ReportGenerator")
    def test_report_generation_workflow(self, mock_generator_class, mock_config):
        """Test complete report generation workflow."""
        # Setup mock
        mock_generator = Mock()
        mock_report = {
            "start_date": "2026-05-01",
            "end_date": "2026-05-07",
            "summary": {
                "total_items": 15,
                "total_new": 8,
                "total_updated": 7,
            },
            "jira_items": [],
            "confluence_items": [],
        }
        mock_generator.generate_report.return_value = mock_report
        mock_generator.format_report_markdown.return_value = "# Weekly Report\n\nContent"
        mock_generator_class.return_value = mock_generator

        # Create service and generate report
        service = ReportService(config=mock_config)

        with tempfile.TemporaryDirectory() as tmpdir:
            result = service.generate(
                report_type="weekly",
                start_date=date(2026, 5, 1),
                end_date=date(2026, 5, 7),
                output_dir=tmpdir,
                source_dir="./test-sources",
                output_format="markdown",
            )

            # Verify result
            assert result.report == mock_report
            assert result.output_format == "markdown"
            assert result.output_file.exists()
            assert "周报" in result.output_file.name

            # Verify file content
            content = result.output_file.read_text(encoding="utf-8")
            assert content == "# Weekly Report\n\nContent"

    @patch("crawler.services.analysis_service.JiraDeepAnalyzer")
    @patch("crawler.services.analysis_service.LLMClientFactory")
    def test_jira_analysis_workflow(
        self, mock_factory, mock_analyzer_class, mock_config
    ):
        """Test complete Jira analysis workflow."""
        # Setup mocks
        mock_llm_client = Mock()
        mock_llm_client.generate.return_value = "test response"
        mock_factory.create.return_value = mock_llm_client

        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = "# Jira Analysis\n\n## Summary\n\nTest analysis"
        mock_analyzer.pipeline = [
            Mock(get_name=lambda: "KnowledgeRetriever"),
            Mock(get_name=lambda: "RootCauseAnalyzer"),
        ]
        mock_analyzer_class.return_value = mock_analyzer

        # Create service and run analysis
        service = AnalysisService(config=mock_config)

        with tempfile.TemporaryDirectory() as tmpdir:
            result = service.analyze_jira(
                issue_key="TEST-123",
                source_dir="./test-sources",
                wiki_dir="./test-wiki",
                output_dir=tmpdir,
                llm_provider="mock",
            )

            # Verify result
            assert result.issue_key == "TEST-123"
            assert result.report.startswith("# Jira Analysis")
            assert result.report_file.exists()
            assert "jira_analysis_TEST-123" in result.report_file.name
            assert result.llm_info.provider == "mock"
            assert len(result.analyzers) == 2

            # Verify file content
            content = result.report_file.read_text(encoding="utf-8")
            assert content == "# Jira Analysis\n\n## Summary\n\nTest analysis"

    @patch("crawler.services.sync_service.ConfluenceCrawler")
    @patch("crawler.services.report_service.ReportGenerator")
    def test_sync_then_report_workflow(
        self, mock_generator_class, mock_crawler_class, mock_config
    ):
        """Test syncing data then generating a report."""
        # Setup sync mock
        mock_crawler = Mock()
        mock_crawler.crawl_space.return_value = {
            "pages": 5,
            "attachments": 2,
            "errors": [],
        }
        mock_crawler_class.return_value = mock_crawler

        # Setup report mock
        mock_generator = Mock()
        mock_report = {
            "start_date": "2026-05-01",
            "end_date": "2026-05-07",
            "summary": {"total_items": 5},
            "confluence_items": [],
        }
        mock_generator.generate_report.return_value = mock_report
        mock_generator.format_report_markdown.return_value = "# Report"
        mock_generator_class.return_value = mock_generator

        with tempfile.TemporaryDirectory() as tmpdir:
            # Step 1: Sync data
            sync_service = SyncService(config=mock_config)
            sync_result = sync_service.sync_all(
                source_name=None,
                source_type="confluence",
            )

            assert sync_result["stats"]["confluence"]["pages"] == 5

            # Step 2: Generate report from synced data
            report_service = ReportService(config=mock_config)
            report_result = report_service.generate(
                report_type="weekly",
                output_dir=tmpdir,
                source_dir=tmpdir,
                output_format="markdown",
            )

            assert report_result.report == mock_report
            assert report_result.output_file.exists()

    def test_error_handling_in_sync(self, mock_config):
        """Test error handling during sync operations."""
        with patch("crawler.services.sync_service.ConfluenceCrawler") as mock_crawler_class:
            mock_crawler = Mock()
            mock_crawler.crawl_space.side_effect = Exception("Connection timeout")
            mock_crawler_class.return_value = mock_crawler

            service = SyncService(config=mock_config)
            result = service.sync_all(
                source_name=None,
                source_type="confluence",
            )

            # Verify error was captured
            assert len(result["errors"]) >= 1

    @patch("crawler.services.analysis_service.LLMClientFactory")
    def test_llm_fallback_in_analysis(self, mock_factory, mock_config):
        """Test LLM fallback mechanism in analysis."""
        # Setup mock to fail first, then succeed with mock client
        mock_openai_client = Mock()
        mock_openai_client.generate.side_effect = RuntimeError("LLM connection failed")

        mock_mock_client = Mock()
        mock_mock_client.generate.return_value = "mock response"

        mock_factory.create_from_config.return_value = mock_openai_client
        mock_factory.create.return_value = mock_mock_client

        # Update config to use openai (which will fail)
        mock_config["llm"]["provider"] = "openai"

        service = AnalysisService(config=mock_config)

        # Test LLM client creation with fallback
        client, info = service.create_llm_client(
            provider_override="openai",
            connection_test=True,
            allow_mock_fallback=True,
        )

        # Verify fallback was used
        assert client == mock_mock_client
        assert info.used_mock_fallback is True
        assert "LLM connection failed" in info.connection_error

    def test_service_configuration_validation(self):
        """Test that services validate configuration properly."""
        invalid_config = {
            "llm": {
                "provider": "invalid_provider",
            }
        }

        # Services should handle invalid config gracefully
        service = AnalysisService(config=invalid_config)
        assert service.config == invalid_config

        # But LLM client creation should fail
        with pytest.raises(ValueError):
            service.create_llm_client(
                provider_override="invalid_provider",
                allow_mock_fallback=False,
            )
