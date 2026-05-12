"""Unit tests for SyncService."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from crawler.services import SyncService


class TestSyncService:
    """Test SyncService functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
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
                        "projects": [{"key": "PROJ", "name": "Test Project"}],
                    }
                ],
            },
            "output": {"base_dir": "./test-sources"},
            "sync": {"state_file": "./test-state.json"},
            "error_handling": {
                "max_retries": 3,
                "retry_delay": 1,
                "error_log": "./test-errors.log",
            },
            "performance": {
                "max_workers": 2,
                "max_results_per_page": 10,
            },
        }

    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage manager."""
        storage = Mock()
        storage.save_state = Mock()
        return storage

    @pytest.fixture
    def mock_error_handler(self):
        """Create a mock error handler."""
        handler = Mock()
        handler.generate_error_report = Mock()
        return handler

    def test_filter_sources_all(self, mock_config):
        """Test filtering sources with type='all'."""
        result = SyncService.filter_sources(
            mock_config["sources"], source_name=None, source_type="all"
        )

        assert len(result["confluence"]) == 1
        assert len(result["jira"]) == 1
        assert result["confluence"][0]["name"] == "test-confluence"
        assert result["jira"][0]["name"] == "test-jira"

    def test_filter_sources_confluence_only(self, mock_config):
        """Test filtering only Confluence sources."""
        result = SyncService.filter_sources(
            mock_config["sources"], source_name=None, source_type="confluence"
        )

        assert len(result["confluence"]) == 1
        assert len(result["jira"]) == 0

    def test_filter_sources_jira_only(self, mock_config):
        """Test filtering only Jira sources."""
        result = SyncService.filter_sources(
            mock_config["sources"], source_name=None, source_type="jira"
        )

        assert len(result["confluence"]) == 0
        assert len(result["jira"]) == 1

    def test_filter_sources_by_name(self, mock_config):
        """Test filtering sources by name."""
        result = SyncService.filter_sources(
            mock_config["sources"], source_name="test-jira", source_type="all"
        )

        assert len(result["confluence"]) == 0
        assert len(result["jira"]) == 1
        assert result["jira"][0]["name"] == "test-jira"

    def test_filter_sources_by_name_not_found(self, mock_config):
        """Test filtering with non-existent source name."""
        result = SyncService.filter_sources(
            mock_config["sources"], source_name="non-existent", source_type="all"
        )

        assert len(result["confluence"]) == 0
        assert len(result["jira"]) == 0

    def test_empty_stats(self):
        """Test _empty_stats returns correct structure."""
        stats = SyncService._empty_stats()

        assert "confluence" in stats
        assert "jira" in stats
        assert stats["confluence"]["pages"] == 0
        assert stats["confluence"]["attachments"] == 0
        assert stats["jira"]["issues"] == 0
        assert stats["jira"]["attachments"] == 0

    def test_merge_result(self):
        """Test _merge_result merges stats correctly."""
        target = {
            "stats": {
                "confluence": {"pages": 10, "attachments": 5, "skipped": 2, "total": 12},
                "jira": {"issues": 0, "attachments": 0, "skipped": 0, "total": 0},
            },
            "results": {"confluence": [], "jira": []},
            "errors": [],
        }

        source = {
            "stats": {
                "confluence": {"pages": 5, "attachments": 3, "skipped": 1, "total": 6}
            },
            "results": [{"source": "test", "target": "TEST", "stats": {}}],
            "errors": [{"source": "test", "target": "ERR", "error": "test error"}],
        }

        SyncService._merge_result(target, source, "confluence")

        # _merge_result uses update() which replaces values, not adds them
        assert target["stats"]["confluence"]["pages"] == 5
        assert target["stats"]["confluence"]["attachments"] == 3
        assert target["stats"]["confluence"]["skipped"] == 1
        assert target["stats"]["confluence"]["total"] == 6
        assert len(target["results"]["confluence"]) == 1
        assert len(target["errors"]) == 1
        assert target["errors"][0]["type"] == "confluence"

    @patch("crawler.services.sync_service.ConfluenceCrawler")
    def test_sync_confluence_space(
        self, mock_crawler_class, mock_config, mock_storage, mock_error_handler
    ):
        """Test syncing a single Confluence space."""
        # Setup mock crawler
        mock_crawler = Mock()
        mock_crawler.crawl_space = Mock(
            return_value={"pages": 10, "attachments": 5, "skipped": 2, "total": 12}
        )
        mock_crawler_class.return_value = mock_crawler

        # Create service
        service = SyncService(
            mock_config, storage=mock_storage, error_handler=mock_error_handler
        )

        # Sync space
        source = mock_config["sources"]["confluence"][0]
        space_config = source["spaces"][0]
        result = service._sync_confluence_space(source, space_config, is_cloud=True)

        # Verify
        assert result["pages"] == 10
        assert result["attachments"] == 5
        mock_crawler_class.assert_called_once()
        mock_crawler.crawl_space.assert_called_once()

    @patch("crawler.services.sync_service.JiraCrawler")
    def test_sync_jira_project(
        self, mock_crawler_class, mock_config, mock_storage, mock_error_handler
    ):
        """Test syncing a single Jira project."""
        # Setup mock crawler
        mock_crawler = Mock()
        mock_crawler.crawl_project = Mock(
            return_value={"issues": 20, "attachments": 8, "skipped": 3, "total": 23}
        )
        mock_crawler_class.return_value = mock_crawler

        # Create service
        service = SyncService(
            mock_config, storage=mock_storage, error_handler=mock_error_handler
        )

        # Sync project
        source = mock_config["sources"]["jira"][0]
        project_key = source["projects"][0]["key"]
        result = service._sync_jira_project(source, project_key, is_cloud=True)

        # Verify
        assert result["issues"] == 20
        assert result["attachments"] == 8
        mock_crawler_class.assert_called_once()
        mock_crawler.crawl_project.assert_called_once()

    @patch("crawler.services.sync_service.ConfluenceCrawler")
    def test_sync_confluence_sources(
        self, mock_crawler_class, mock_config, mock_storage, mock_error_handler
    ):
        """Test syncing multiple Confluence sources."""
        # Setup mock crawler
        mock_crawler = Mock()
        mock_crawler.crawl_space = Mock(
            return_value={"pages": 10, "attachments": 5, "skipped": 2, "total": 12}
        )
        mock_crawler_class.return_value = mock_crawler

        # Create service
        service = SyncService(
            mock_config, storage=mock_storage, error_handler=mock_error_handler
        )

        # Sync sources
        sources = mock_config["sources"]["confluence"]
        result = service.sync_confluence_sources(sources)

        # Verify
        assert result["stats"]["confluence"]["pages"] == 10
        assert result["stats"]["confluence"]["attachments"] == 5
        assert len(result["results"]) == 1
        assert len(result["errors"]) == 0

    @patch("crawler.services.sync_service.JiraCrawler")
    def test_sync_jira_sources(
        self, mock_crawler_class, mock_config, mock_storage, mock_error_handler
    ):
        """Test syncing multiple Jira sources."""
        # Setup mock crawler
        mock_crawler = Mock()
        mock_crawler.crawl_project = Mock(
            return_value={"issues": 20, "attachments": 8, "skipped": 3, "total": 23}
        )
        mock_crawler_class.return_value = mock_crawler

        # Create service
        service = SyncService(
            mock_config, storage=mock_storage, error_handler=mock_error_handler
        )

        # Sync sources
        sources = mock_config["sources"]["jira"]
        result = service.sync_jira_sources(sources)

        # Verify
        assert result["stats"]["jira"]["issues"] == 20
        assert result["stats"]["jira"]["attachments"] == 8
        assert len(result["results"]) == 1
        assert len(result["errors"]) == 0

    @patch("crawler.services.sync_service.JiraCrawler")
    @patch("crawler.services.sync_service.ConfluenceCrawler")
    def test_sync_all(
        self,
        mock_confluence_crawler,
        mock_jira_crawler,
        mock_config,
        mock_storage,
        mock_error_handler,
    ):
        """Test syncing all sources."""
        # Setup mock crawlers
        mock_conf_crawler = Mock()
        mock_conf_crawler.crawl_space = Mock(
            return_value={"pages": 10, "attachments": 5, "skipped": 2, "total": 12}
        )
        mock_confluence_crawler.return_value = mock_conf_crawler

        mock_jira_crawler_inst = Mock()
        mock_jira_crawler_inst.crawl_project = Mock(
            return_value={"issues": 20, "attachments": 8, "skipped": 3, "total": 23}
        )
        mock_jira_crawler.return_value = mock_jira_crawler_inst

        # Create service
        service = SyncService(
            mock_config, storage=mock_storage, error_handler=mock_error_handler
        )

        # Sync all
        result = service.sync_all(source_name=None, source_type="all")

        # Verify
        assert result["stats"]["confluence"]["pages"] == 10
        assert result["stats"]["jira"]["issues"] == 20
        assert len(result["results"]["confluence"]) == 1
        assert len(result["results"]["jira"]) == 1
        assert len(result["errors"]) == 0

        # Verify storage and error handler called
        mock_storage.save_state.assert_called_once()
        mock_error_handler.generate_error_report.assert_called_once()
