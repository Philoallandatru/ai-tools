"""Unit tests for AnalysisService."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from crawler.services import AnalysisService
from crawler.services.analysis_service import LLMClientInfo, JiraAnalysisResult


class TestAnalysisService:
    """Test AnalysisService functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        return {
            "llm": {
                "provider": "openai",
                "base_url": "http://127.0.0.1:1234/v1",
                "model": "test-model",
                "max_tokens": 2000,
                "temperature": 0.7,
            },
            "jira_analysis": {
                "issue_summary": {
                    "enabled": True,
                }
            },
            "custom_analyzers": [],
        }

    def test_service_initialization_with_config(self, mock_config):
        """Test service initialization with explicit config."""
        service = AnalysisService(config=mock_config)
        assert service.config == mock_config
        assert service.config_path == "config.yaml"

    def test_service_initialization_without_config(self):
        """Test service initialization with empty config dict."""
        service = AnalysisService(config={})
        assert service.config == {}
        assert service.config_path == "config.yaml"

    @patch("crawler.services.analysis_service.LLMClientFactory")
    def test_create_llm_client_mock_provider(self, mock_factory, mock_config):
        """Test creating mock LLM client."""
        mock_client = Mock()
        mock_factory.create.return_value = mock_client

        service = AnalysisService(config=mock_config)
        client, info = service.create_llm_client(provider_override="mock")

        assert client == mock_client
        assert info.provider == "mock"
        assert info.base_url is None
        assert not info.used_mock_fallback
        mock_factory.create.assert_called_once_with("mock")

    @patch("crawler.services.analysis_service.LLMClientFactory")
    def test_create_llm_client_openai_success(self, mock_factory, mock_config):
        """Test creating OpenAI client successfully."""
        mock_client = Mock()
        mock_client.generate.return_value = "test response"
        mock_factory.create_from_config.return_value = mock_client

        service = AnalysisService(config=mock_config)
        client, info = service.create_llm_client(
            provider_override="openai",
            connection_test=True
        )

        assert client == mock_client
        assert info.provider == "openai"
        assert info.base_url == "http://127.0.0.1:1234/v1"
        assert not info.used_mock_fallback
        assert info.connection_error is None
        mock_client.generate.assert_called_once_with("test", max_tokens=10, temperature=0.7)

    @patch("crawler.services.analysis_service.LLMClientFactory")
    def test_create_llm_client_connection_failure_with_fallback(self, mock_factory, mock_config):
        """Test LLM client falls back to mock on connection failure."""
        mock_openai_client = Mock()
        mock_openai_client.generate.side_effect = RuntimeError("Connection failed")
        mock_mock_client = Mock()

        mock_factory.create_from_config.return_value = mock_openai_client
        mock_factory.create.return_value = mock_mock_client

        service = AnalysisService(config=mock_config)
        client, info = service.create_llm_client(
            provider_override="openai",
            connection_test=True,
            allow_mock_fallback=True
        )

        assert client == mock_mock_client
        assert info.provider == "openai"
        assert info.used_mock_fallback is True
        assert "Connection failed" in info.connection_error
        mock_factory.create.assert_called_once_with("mock")

    @patch("crawler.services.analysis_service.LLMClientFactory")
    def test_create_llm_client_connection_failure_no_fallback(self, mock_factory, mock_config):
        """Test LLM client raises error when fallback disabled."""
        mock_client = Mock()
        mock_client.generate.side_effect = RuntimeError("Connection failed")
        mock_factory.create_from_config.return_value = mock_client

        service = AnalysisService(config=mock_config)

        with pytest.raises(RuntimeError, match="Connection failed"):
            service.create_llm_client(
                provider_override="openai",
                connection_test=True,
                allow_mock_fallback=False
            )

    @patch("crawler.services.analysis_service.JiraDeepAnalyzer")
    def test_create_jira_analyzer(self, mock_analyzer_class, mock_config):
        """Test creating Jira analyzer with standard pipeline."""
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer
        mock_llm_client = Mock()

        service = AnalysisService(config=mock_config)
        analyzer = service.create_jira_analyzer(
            source_dir="./sources",
            wiki_dir="./wiki",
            llm_client=mock_llm_client
        )

        assert analyzer == mock_analyzer
        mock_analyzer_class.assert_called_once_with(
            source_dir="./sources",
            llm_client=mock_llm_client
        )

        # Verify analyzers were registered (7 standard analyzers)
        assert mock_analyzer.register_analyzer.call_count == 7

    @patch("crawler.services.analysis_service.JiraDeepAnalyzer")
    def test_create_jira_analyzer_with_custom_analyzers(self, mock_analyzer_class, mock_config):
        """Test creating Jira analyzer with custom analyzers."""
        mock_config["custom_analyzers"] = [
            {"name": "custom1", "prompt": "test prompt 1", "enabled": True},
            {"name": "custom2", "prompt": "test prompt 2", "enabled": False},
            {"name": "custom3", "prompt": "test prompt 3", "enabled": True},
        ]

        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer
        mock_llm_client = Mock()

        service = AnalysisService(config=mock_config)
        analyzer = service.create_jira_analyzer(
            source_dir="./sources",
            wiki_dir="./wiki",
            llm_client=mock_llm_client
        )

        # 7 standard + 2 enabled custom analyzers
        assert mock_analyzer.register_analyzer.call_count == 9

    @patch("crawler.services.analysis_service.JiraDeepAnalyzer")
    def test_create_jira_analyzer_issue_summary_disabled(self, mock_analyzer_class, mock_config):
        """Test creating analyzer with issue summary disabled."""
        mock_config["jira_analysis"]["issue_summary"]["enabled"] = False

        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer
        mock_llm_client = Mock()

        service = AnalysisService(config=mock_config)
        analyzer = service.create_jira_analyzer(
            source_dir="./sources",
            wiki_dir="./wiki",
            llm_client=mock_llm_client
        )

        # 6 standard analyzers (without IssueSummaryAnalyzer)
        assert mock_analyzer.register_analyzer.call_count == 6

    @patch("crawler.services.analysis_service.JiraDeepAnalyzer")
    @patch("crawler.services.analysis_service.LLMClientFactory")
    def test_analyze_jira_success(self, mock_factory, mock_analyzer_class, mock_config):
        """Test successful Jira analysis."""
        # Setup mocks
        mock_llm_client = Mock()
        mock_llm_client.generate.return_value = "test response"
        mock_factory.create_from_config.return_value = mock_llm_client

        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = "# Analysis Report\n\nTest content"
        mock_analyzer.pipeline = [Mock(get_name=lambda: "TestAnalyzer")]
        mock_analyzer_class.return_value = mock_analyzer

        # Run analysis
        service = AnalysisService(config=mock_config)

        with tempfile.TemporaryDirectory() as tmpdir:
            result = service.analyze_jira(
                issue_key="TEST-123",
                source_dir="./sources",
                wiki_dir="./wiki",
                output_dir=tmpdir,
                llm_provider="openai",
                allow_mock_fallback=True
            )

            # Verify result
            assert isinstance(result, JiraAnalysisResult)
            assert result.issue_key == "TEST-123"
            assert result.report == "# Analysis Report\n\nTest content"
            assert result.report_file.exists()
            assert result.report_file.name.startswith("jira_analysis_TEST-123_")
            assert result.report_file.suffix == ".md"
            assert result.llm_info.provider == "openai"
            assert not result.llm_info.used_mock_fallback
            assert result.analyzers == ["TestAnalyzer"]

            # Verify file content
            with open(result.report_file, "r", encoding="utf-8") as f:
                content = f.read()
                assert content == "# Analysis Report\n\nTest content"

            # Verify analyzer was called
            mock_analyzer.analyze.assert_called_once_with("TEST-123")

    @patch("crawler.services.analysis_service.JiraDeepAnalyzer")
    @patch("crawler.services.analysis_service.LLMClientFactory")
    def test_analyze_jira_with_mock_fallback(self, mock_factory, mock_analyzer_class, mock_config):
        """Test Jira analysis with mock fallback."""
        # Setup mocks - OpenAI fails, falls back to mock
        mock_openai_client = Mock()
        mock_openai_client.generate.side_effect = RuntimeError("Connection failed")
        mock_mock_client = Mock()

        mock_factory.create_from_config.return_value = mock_openai_client
        mock_factory.create.return_value = mock_mock_client

        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = "# Mock Analysis"
        mock_analyzer.pipeline = []
        mock_analyzer_class.return_value = mock_analyzer

        # Run analysis
        service = AnalysisService(config=mock_config)

        with tempfile.TemporaryDirectory() as tmpdir:
            result = service.analyze_jira(
                issue_key="TEST-456",
                output_dir=tmpdir,
                allow_mock_fallback=True
            )

            # Verify mock fallback was used
            assert result.llm_info.used_mock_fallback is True
            assert "Connection failed" in result.llm_info.connection_error
            assert result.report == "# Mock Analysis"

    @patch("crawler.services.analysis_service.JiraDeepAnalyzer")
    @patch("crawler.services.analysis_service.LLMClientFactory")
    def test_analyze_jira_creates_output_dir(self, mock_factory, mock_analyzer_class, mock_config):
        """Test that analyze_jira creates output directory if it doesn't exist."""
        mock_llm_client = Mock()
        mock_llm_client.generate.return_value = "test"
        mock_factory.create_from_config.return_value = mock_llm_client

        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = "# Report"
        mock_analyzer.pipeline = []
        mock_analyzer_class.return_value = mock_analyzer

        service = AnalysisService(config=mock_config)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "nested" / "reports"
            assert not output_dir.exists()

            result = service.analyze_jira(
                issue_key="TEST-789",
                output_dir=str(output_dir)
            )

            # Verify directory was created
            assert output_dir.exists()
            assert result.report_file.parent == output_dir

    def test_create_llm_client_uses_config_defaults(self, mock_config):
        """Test that create_llm_client uses config defaults when no override."""
        service = AnalysisService(config=mock_config)

        with patch("crawler.services.analysis_service.LLMClientFactory") as mock_factory:
            mock_client = Mock()
            mock_client.generate.return_value = "test"
            mock_factory.create_from_config.return_value = mock_client

            client, info = service.create_llm_client(connection_test=False)

            # Verify config was used
            call_args = mock_factory.create_from_config.call_args[0][0]
            assert call_args["provider"] == "openai"
            assert call_args["base_url"] == "http://127.0.0.1:1234/v1"
            assert call_args["model"] == "test-model"
