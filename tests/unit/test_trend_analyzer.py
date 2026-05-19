"""Unit tests for TrendAnalyzer."""

from unittest.mock import Mock, patch

import pytest

from crawler.analyzers.trend_analyzer import TrendAnalyzer


class TestTrendAnalyzer:
    """Test TrendAnalyzer functionality."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        return Mock()

    @pytest.fixture
    def mock_history_manager(self):
        """Create a mock MetricsHistoryManager."""
        manager = Mock()
        manager.get_last_n_weeks = Mock()
        return manager

    @pytest.fixture
    def analyzer(self, mock_llm_client, mock_history_manager):
        """Create a TrendAnalyzer with mocked dependencies."""
        config = {
            'enabled': True,
            'lookback_weeks': 4,
            'min_data_points': 2,
            'trend_threshold': 0.1
        }
        with patch('crawler.analyzers.trend_analyzer.MetricsHistoryManager', return_value=mock_history_manager):
            return TrendAnalyzer(llm_client=mock_llm_client, config=config)

    @pytest.fixture
    def sample_history_data(self):
        """Create sample historical data."""
        return [
            {
                "report_id": "weekly_2026-04-21",
                "timestamp": "2026-04-21T00:00:00",
                "start_date": "2026-04-21",
                "end_date": "2026-04-28",
                "jira": {
                    "total_items": 30,
                    "new": 5,
                    "updated": 10,
                    "by_status_counts": {"Done": 5, "In Progress": 10, "To Do": 15}
                },
                "health": {
                    "total_score": 75,
                    "progress_score": 70,
                    "quality_score": 75,
                    "resource_score": 80,
                    "risk_score": 75
                },
                "team": {
                    "total_members": 5,
                    "gini_coefficient": 0.2,
                    "overloaded_count": 1,
                    "bottleneck_count": 0
                }
            },
            {
                "report_id": "weekly_2026-04-28",
                "timestamp": "2026-04-28T00:00:00",
                "start_date": "2026-04-28",
                "end_date": "2026-05-05",
                "jira": {
                    "total_items": 32,
                    "new": 7,
                    "updated": 12,
                    "by_status_counts": {"Done": 7, "In Progress": 12, "To Do": 13}
                },
                "health": {
                    "total_score": 78,
                    "progress_score": 75,
                    "quality_score": 78,
                    "resource_score": 82,
                    "risk_score": 77
                },
                "team": {
                    "total_members": 5,
                    "gini_coefficient": 0.18,
                    "overloaded_count": 1,
                    "bottleneck_count": 0
                }
            },
            {
                "report_id": "weekly_2026-05-05",
                "timestamp": "2026-05-05T00:00:00",
                "start_date": "2026-05-05",
                "end_date": "2026-05-12",
                "jira": {
                    "total_items": 35,
                    "new": 10,
                    "updated": 14,
                    "by_status_counts": {"Done": 10, "In Progress": 14, "To Do": 11}
                },
                "health": {
                    "total_score": 82,
                    "progress_score": 80,
                    "quality_score": 82,
                    "resource_score": 85,
                    "risk_score": 80
                },
                "team": {
                    "total_members": 5,
                    "gini_coefficient": 0.15,
                    "overloaded_count": 0,
                    "bottleneck_count": 0
                }
            },
            {
                "report_id": "weekly_2026-05-12",
                "timestamp": "2026-05-12T00:00:00",
                "start_date": "2026-05-12",
                "end_date": "2026-05-19",
                "jira": {
                    "total_items": 37,
                    "new": 12,
                    "updated": 15,
                    "by_status_counts": {"Done": 12, "In Progress": 15, "To Do": 10}
                },
                "health": {
                    "total_score": 85,
                    "progress_score": 85,
                    "quality_score": 85,
                    "resource_score": 87,
                    "risk_score": 83
                },
                "team": {
                    "total_members": 5,
                    "gini_coefficient": 0.12,
                    "overloaded_count": 0,
                    "bottleneck_count": 0
                }
            }
        ]

    def test_analyze_with_sufficient_data(self, analyzer, mock_history_manager, sample_history_data):
        """Test trend analysis with sufficient historical data."""
        mock_history_manager.get_last_n_weeks.return_value = sample_history_data

        report_data = {"type": "weekly"}
        context = {}

        result = analyzer.analyze(report_data, context)

        assert result["success"] is True
        assert result["data_points"] == 4
        assert "trends" in result
        assert "health" in result["trends"]
        assert "team" in result["trends"]
        assert "issues" in result["trends"]
        assert "insights" in result
        assert "recommendations" in result

    def test_analyze_with_insufficient_data(self, analyzer, mock_history_manager):
        """Test trend analysis with insufficient historical data."""
        # Only one data point
        mock_history_manager.get_last_n_weeks.return_value = [
            {
                "report_id": "weekly_2026-05-12",
                "timestamp": "2026-05-12T00:00:00",
                "jira": {"total_items": 5},
                "health": {"total_score": 80},
                "team": {"total_members": 5}
            }
        ]

        report_data = {"type": "weekly"}
        context = {}

        result = analyzer.analyze(report_data, context)

        assert result["success"] is False
        assert "message" in result
        assert result["available_weeks"] == 1

    def test_analyze_with_empty_history(self, analyzer, mock_history_manager):
        """Test analysis with empty history."""
        mock_history_manager.get_last_n_weeks.return_value = []

        report_data = {"type": "weekly"}
        context = {}

        result = analyzer.analyze(report_data, context)

        assert result["success"] is False
        assert result["available_weeks"] == 0

    def test_health_trends_structure(self, analyzer, mock_history_manager, sample_history_data):
        """Test that health trends have the expected structure."""
        mock_history_manager.get_last_n_weeks.return_value = sample_history_data

        result = analyzer.analyze({"type": "weekly"}, {})

        health = result["trends"]["health"]
        assert "total" in health
        assert "dimensions" in health

        # Check total structure
        assert "trend" in health["total"]
        assert "change" in health["total"]
        assert "current" in health["total"]
        assert "previous" in health["total"]

        # Check dimensions
        for dim in ["progress", "quality", "resource", "risk"]:
            assert dim in health["dimensions"]
            assert "trend" in health["dimensions"][dim]
            assert "change" in health["dimensions"][dim]

    def test_team_trends_structure(self, analyzer, mock_history_manager, sample_history_data):
        """Test that team trends have the expected structure."""
        mock_history_manager.get_last_n_weeks.return_value = sample_history_data

        result = analyzer.analyze({"type": "weekly"}, {})

        team = result["trends"]["team"]
        assert "load_balance" in team
        assert "bottlenecks" in team
        assert "overloaded" in team
        assert "team_size" in team

    def test_issues_trends_structure(self, analyzer, mock_history_manager, sample_history_data):
        """Test that issues trends have the expected structure."""
        mock_history_manager.get_last_n_weeks.return_value = sample_history_data

        result = analyzer.analyze({"type": "weekly"}, {})

        issues = result["trends"]["issues"]
        assert "total" in issues
        assert "new" in issues
        assert "updated" in issues

    def test_lookback_weeks_configuration(self, mock_llm_client, mock_history_manager):
        """Test that lookback_weeks configuration is respected."""
        config = {
            'enabled': True,
            'lookback_weeks': 8,
            'min_data_points': 3,
            'trend_threshold': 0.15
        }
        with patch('crawler.analyzers.trend_analyzer.MetricsHistoryManager', return_value=mock_history_manager):
            analyzer = TrendAnalyzer(llm_client=mock_llm_client, config=config)

            mock_history_manager.get_last_n_weeks.return_value = []
            analyzer.analyze({"type": "weekly"}, {})

            # Verify it requested the correct number of weeks
            mock_history_manager.get_last_n_weeks.assert_called_once_with(8, "weekly")

    def test_min_data_points_configuration(self, mock_llm_client, mock_history_manager):
        """Test that min_data_points configuration is respected."""
        config = {
            'enabled': True,
            'lookback_weeks': 4,
            'min_data_points': 3,
            'trend_threshold': 0.1
        }
        with patch('crawler.analyzers.trend_analyzer.MetricsHistoryManager', return_value=mock_history_manager):
            analyzer = TrendAnalyzer(llm_client=mock_llm_client, config=config)

            # Provide exactly 2 data points (less than min_data_points)
            mock_history_manager.get_last_n_weeks.return_value = [
                {"report_id": "1", "jira": {}, "health": {}, "team": {}},
                {"report_id": "2", "jira": {}, "health": {}, "team": {}}
            ]

            result = analyzer.analyze({"type": "weekly"}, {})

            # Should fail due to insufficient data
            assert result["success"] is False

    def test_disabled_analyzer(self, mock_llm_client, mock_history_manager):
        """Test that disabled analyzer returns empty result."""
        config = {
            'enabled': False,
            'lookback_weeks': 4,
            'min_data_points': 2
        }
        with patch('crawler.analyzers.trend_analyzer.MetricsHistoryManager', return_value=mock_history_manager):
            analyzer = TrendAnalyzer(llm_client=mock_llm_client, config=config)

            result = analyzer.analyze({"type": "weekly"}, {})

            assert result == {}
