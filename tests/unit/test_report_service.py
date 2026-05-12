"""Unit tests for ReportService."""

import tempfile
from datetime import date, datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from crawler.services import ReportService


class TestReportService:
    """Test ReportService functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        return {
            "reports": {
                "fixed_issues": ["KAN-1", "KAN-2"],
                "max_issues_per_report": 100,
                "group_by": "status",
                "include_attachments": True,
            }
        }

    @pytest.fixture
    def mock_report(self):
        """Create a mock report."""
        return {
            "start_date": "2026-05-01",
            "end_date": "2026-05-07",
            "summary": {
                "total_items": 10,
                "total_new": 5,
                "total_updated": 5,
                "jira_summary": {
                    "total": 8,
                    "new": 4,
                    "updated": 4,
                },
                "confluence_summary": {
                    "total": 2,
                    "new": 1,
                    "updated": 1,
                },
            },
            "jira_items": [
                {
                    "key": "KAN-1",
                    "title": "Test Issue 1",
                    "status": "In Progress",
                    "is_new": True,
                }
            ],
            "confluence_items": [],
        }

    def test_parse_date_valid(self):
        """Test parsing valid date string."""
        result = ReportService.parse_date("2026-05-01", "test")
        assert result == date(2026, 5, 1)

    def test_parse_date_none(self):
        """Test parsing None returns None."""
        result = ReportService.parse_date(None, "test")
        assert result is None

    def test_parse_date_invalid(self):
        """Test parsing invalid date raises ValueError."""
        with pytest.raises(ValueError, match="无效的test日期格式"):
            ReportService.parse_date("invalid-date", "test")

    @patch("crawler.services.report_service.ReportGenerator")
    def test_generate_markdown(self, mock_generator_class, mock_config, mock_report):
        """Test generating markdown report."""
        # Setup mock generator
        mock_generator = Mock()
        mock_generator.generate_report = Mock(return_value=mock_report)
        mock_generator.format_report_markdown = Mock(return_value="# Test Report\n\nContent")
        mock_generator_class.return_value = mock_generator

        # Create service
        service = ReportService(config=mock_config)

        # Generate report
        with tempfile.TemporaryDirectory() as tmpdir:
            result = service.generate(
                report_type="weekly",
                start_date=date(2026, 5, 1),
                end_date=date(2026, 5, 7),
                output_dir=tmpdir,
                source_dir="./test-sources",
                output_format="markdown",
            )

            # Verify
            assert result.report == mock_report
            assert result.output_format == "markdown"
            assert result.content == "# Test Report\n\nContent"
            assert result.output_file.exists()
            assert result.output_file.suffix == ".md"

            # Verify file content
            with open(result.output_file, "r", encoding="utf-8") as f:
                content = f.read()
                assert content == "# Test Report\n\nContent"

    @patch("crawler.services.report_service.ReportGenerator")
    def test_generate_json(self, mock_generator_class, mock_config, mock_report):
        """Test generating JSON report."""
        # Setup mock generator
        mock_generator = Mock()
        mock_generator.generate_report = Mock(return_value=mock_report)
        mock_generator_class.return_value = mock_generator

        # Create service
        service = ReportService(config=mock_config)

        # Generate report
        with tempfile.TemporaryDirectory() as tmpdir:
            result = service.generate(
                report_type="daily",
                start_date=date(2026, 5, 1),
                end_date=date(2026, 5, 1),
                output_dir=tmpdir,
                source_dir="./test-sources",
                output_format="json",
            )

            # Verify
            assert result.report == mock_report
            assert result.output_format == "json"
            assert result.content is None
            assert result.output_file.exists()
            assert result.output_file.suffix == ".json"

            # Verify file is valid JSON
            import json

            with open(result.output_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                assert data == mock_report

    @patch("crawler.services.report_service.ReportGenerator")
    def test_generate_creates_output_dir(self, mock_generator_class, mock_config, mock_report):
        """Test that generate creates output directory if it doesn't exist."""
        # Setup mock generator
        mock_generator = Mock()
        mock_generator.generate_report = Mock(return_value=mock_report)
        mock_generator.format_report_markdown = Mock(return_value="# Report")
        mock_generator_class.return_value = mock_generator

        # Create service
        service = ReportService(config=mock_config)

        # Generate report with non-existent directory
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "reports" / "nested"
            assert not output_dir.exists()

            result = service.generate(
                report_type="weekly",
                output_dir=str(output_dir),
                output_format="markdown",
            )

            # Verify directory was created
            assert output_dir.exists()
            assert result.output_file.parent == output_dir

    @patch("crawler.services.report_service.ReportGenerator")
    def test_generate_with_none_dates(self, mock_generator_class, mock_config, mock_report):
        """Test generating report with None dates (uses defaults)."""
        # Setup mock generator
        mock_generator = Mock()
        mock_generator.generate_report = Mock(return_value=mock_report)
        mock_generator.format_report_markdown = Mock(return_value="# Report")
        mock_generator_class.return_value = mock_generator

        # Create service
        service = ReportService(config=mock_config)

        # Generate report
        with tempfile.TemporaryDirectory() as tmpdir:
            result = service.generate(
                report_type="weekly",
                start_date=None,
                end_date=None,
                output_dir=tmpdir,
                output_format="markdown",
            )

            # Verify generator was called with None dates
            mock_generator.generate_report.assert_called_once_with("weekly", None, None)

    def test_service_without_config_file(self):
        """Test service works without config file."""
        service = ReportService(config_path="non-existent-config.yaml")
        assert service.config == {}

    def test_service_with_explicit_config(self, mock_config):
        """Test service with explicitly provided config."""
        service = ReportService(config=mock_config)
        assert service.config == mock_config

    @patch("crawler.services.report_service.ReportGenerator")
    def test_report_filename_format(self, mock_generator_class, mock_config, mock_report):
        """Test report filename includes correct format."""
        # Setup mock generator
        mock_generator = Mock()
        mock_generator.generate_report = Mock(return_value=mock_report)
        mock_generator.format_report_markdown = Mock(return_value="# Report")
        mock_generator_class.return_value = mock_generator

        # Create service
        service = ReportService(config=mock_config)

        # Generate report
        with tempfile.TemporaryDirectory() as tmpdir:
            result = service.generate(
                report_type="monthly",
                output_dir=tmpdir,
                output_format="markdown",
            )

            # Verify filename format: 月报_start_to_end_timestamp.md
            filename = result.output_file.name
            assert filename.startswith("月报_")
            assert "_to_" in filename
            assert filename.endswith(".md")
