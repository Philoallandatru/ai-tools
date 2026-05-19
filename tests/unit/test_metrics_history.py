"""Unit tests for MetricsHistoryManager."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from crawler.metrics_history import MetricsHistoryManager


class TestMetricsHistoryManager:
    """Test MetricsHistoryManager functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a MetricsHistoryManager with a temporary storage file."""
        storage_file = temp_dir / "test_metrics.json"
        return MetricsHistoryManager(history_file=str(storage_file))

    @pytest.fixture
    def sample_report_data(self):
        """Create sample report data for testing."""
        return {
            "report_id": "weekly_2026-05-12_to_2026-05-19",
            "type": "weekly",
            "start_date": "2026-05-12",
            "end_date": "2026-05-19",
            "jira": {
                "total": 4,
                "new": 2,
                "updated": 2,
                "by_status": {
                    "Done": [{"key": "PROJ-1"}],
                    "In Progress": [{"key": "PROJ-2"}, {"key": "PROJ-3"}],
                    "To Do": [{"key": "PROJ-4"}]
                },
                "by_priority": {
                    "High": [{"key": "PROJ-1"}],
                    "Medium": [{"key": "PROJ-2"}]
                },
                "by_type": {
                    "Bug": [{"key": "PROJ-1"}],
                    "Feature": [{"key": "PROJ-2"}]
                }
            },
            "analysis": {
                "project_health": {
                    "total_score": 85,
                    "dimension_scores": {
                        "progress": {"score": 90, "weight": 0.3},
                        "quality": {"score": 85, "weight": 0.3},
                        "resource": {"score": 80, "weight": 0.2},
                        "risk": {"score": 75, "weight": 0.2}
                    }
                },
                "team_collaboration": {
                    "workload_distribution": {
                        "statistics": {
                            "total_members": 2,
                            "gini_coefficient": 0.15
                        },
                        "members": [
                            {"name": "Alice", "assigned_count": 5},
                            {"name": "Bob", "assigned_count": 3}
                        ],
                        "overloaded": [
                            {"name": "Alice", "workload": 5}
                        ],
                        "underloaded": []
                    },
                    "bottlenecks": {
                        "bottleneck_members": []
                    }
                }
            }
        }

    def test_extract_metrics(self, manager, sample_report_data):
        """Test extracting metrics from report data."""
        metrics = manager.extract_metrics(sample_report_data)

        assert metrics["report_id"] == "weekly_2026-05-12_to_2026-05-19"
        assert metrics["report_type"] == "weekly"
        assert "timestamp" in metrics

        # Check Jira metrics
        assert metrics["jira"]["total_items"] == 4
        assert metrics["jira"]["new"] == 2
        assert metrics["jira"]["updated"] == 2
        assert metrics["jira"]["by_status_counts"]["Done"] == 1
        assert metrics["jira"]["by_status_counts"]["In Progress"] == 2
        assert metrics["jira"]["by_status_counts"]["To Do"] == 1

        # Check health metrics
        assert metrics["health"]["total_score"] == 85
        assert metrics["health"]["progress_score"] == 90
        assert metrics["health"]["quality_score"] == 85
        assert metrics["health"]["resource_score"] == 80
        assert metrics["health"]["risk_score"] == 75

        # Check team metrics
        assert metrics["team"]["total_members"] == 2
        assert metrics["team"]["gini_coefficient"] == 0.15
        assert metrics["team"]["overloaded_count"] == 1
        assert metrics["team"]["underloaded_count"] == 0
        assert metrics["team"]["bottleneck_count"] == 0

    def test_save_and_load_metrics(self, manager, sample_report_data):
        """Test saving and loading metrics."""
        manager.save_metrics(sample_report_data)

        # Load the saved metrics
        history = manager.get_last_n_weeks(n=1)

        assert len(history) == 1
        assert history[0]["report_id"] == "weekly_2026-05-12_to_2026-05-19"
        assert history[0]["jira"]["by_status_counts"]["Done"] == 1

    def test_save_duplicate_report_id(self, manager, sample_report_data):
        """Test that saving the same report_id updates the existing record."""
        manager.save_metrics(sample_report_data)

        # Modify the data and save again
        sample_report_data["analysis"]["project_health"]["total_score"] = 90
        manager.save_metrics(sample_report_data)

        # Should only have one record
        history = manager.get_last_n_weeks(n=10)
        assert len(history) == 1
        assert history[0]["health"]["total_score"] == 90

    def test_get_last_n_weeks(self, manager):
        """Test retrieving last N weeks of data."""
        # Create multiple reports
        for i in range(5):
            report_data = {
                "report_id": f"weekly_2026-05-{i:02d}",
                "type": "weekly",
                "start_date": f"2026-05-{i:02d}",
                "end_date": f"2026-05-{i+7:02d}",
                "jira": {
                    "total": 0,
                    "new": 0,
                    "updated": 0,
                    "by_status": {}
                },
                "analysis": {
                    "project_health": {
                        "total_score": 80 + i,
                        "dimension_scores": {
                            "progress": {"score": 80, "weight": 0.3},
                            "quality": {"score": 80, "weight": 0.3},
                            "resource": {"score": 80, "weight": 0.2},
                            "risk": {"score": 80, "weight": 0.2}
                        }
                    },
                    "team_collaboration": {
                        "workload_distribution": {
                            "statistics": {
                                "total_members": 0,
                                "gini_coefficient": 0.1
                            },
                            "members": [],
                            "overloaded": [],
                            "underloaded": []
                        },
                        "bottlenecks": {
                            "bottleneck_members": []
                        }
                    }
                }
            }
            manager.save_metrics(report_data)

        # Get last 3 weeks
        history = manager.get_last_n_weeks(n=3)
        assert len(history) == 3
        assert history[-1]["health"]["total_score"] == 84  # Most recent

    def test_get_last_n_weeks_with_report_type_filter(self, manager):
        """Test filtering by report type."""
        # Create weekly and monthly reports
        for i in range(3):
            weekly_report = {
                "report_id": f"weekly_{i}",
                "type": "weekly",
                "start_date": f"2026-05-{i:02d}",
                "end_date": f"2026-05-{i+7:02d}",
                "jira": {
                    "total": 0,
                    "new": 0,
                    "updated": 0,
                    "by_status": {}
                },
                "analysis": {
                    "project_health": {
                        "total_score": 80,
                        "dimension_scores": {
                            "progress": {"score": 80, "weight": 0.3},
                            "quality": {"score": 80, "weight": 0.3},
                            "resource": {"score": 80, "weight": 0.2},
                            "risk": {"score": 80, "weight": 0.2}
                        }
                    },
                    "team_collaboration": {
                        "workload_distribution": {
                            "statistics": {
                                "total_members": 0,
                                "gini_coefficient": 0.1
                            },
                            "members": [],
                            "overloaded": [],
                            "underloaded": []
                        },
                        "bottlenecks": {
                            "bottleneck_members": []
                        }
                    }
                }
            }
            manager.save_metrics(weekly_report)

        monthly_report = {
            "report_id": "monthly_1",
            "type": "monthly",
            "start_date": "2026-05-01",
            "end_date": "2026-05-31",
            "jira": {
                "total": 0,
                "new": 0,
                "updated": 0,
                "by_status": {}
            },
            "analysis": {
                "project_health": {
                    "total_score": 85,
                    "dimension_scores": {
                        "progress": {"score": 85, "weight": 0.3},
                        "quality": {"score": 85, "weight": 0.3},
                        "resource": {"score": 85, "weight": 0.2},
                        "risk": {"score": 85, "weight": 0.2}
                    }
                },
                "team_collaboration": {
                    "workload_distribution": {"members": [], "gini_coefficient": 0.1},
                    "bottlenecks": {"overloaded_members": []}
                }
            }
        }
        manager.save_metrics(monthly_report)

        # Get only weekly reports
        weekly_history = manager.get_last_n_weeks(n=10, report_type="weekly")
        assert len(weekly_history) == 3
        assert all(r["report_type"] == "weekly" for r in weekly_history)

        # Get only monthly reports
        monthly_history = manager.get_last_n_weeks(n=10, report_type="monthly")
        assert len(monthly_history) == 1
        assert monthly_history[0]["report_type"] == "monthly"

    def test_cleanup_old_metrics(self, manager):
        """Test cleaning up old metrics."""
        # Create 10 reports
        for i in range(10):
            report_data = {
                "report_id": f"weekly_{i}",
                "type": "weekly",
                "start_date": f"2026-05-{i:02d}",
                "end_date": f"2026-05-{i+7:02d}",
                "jira": {
                    "total": 0,
                    "new": 0,
                    "updated": 0,
                    "by_status": {}
                },
                "analysis": {
                    "project_health": {
                        "total_score": 80,
                        "dimension_scores": {
                            "progress": {"score": 80, "weight": 0.3},
                            "quality": {"score": 80, "weight": 0.3},
                            "resource": {"score": 80, "weight": 0.2},
                            "risk": {"score": 80, "weight": 0.2}
                        }
                    },
                    "team_collaboration": {
                        "workload_distribution": {
                            "statistics": {
                                "total_members": 0,
                                "gini_coefficient": 0.1
                            },
                            "members": [],
                            "overloaded": [],
                            "underloaded": []
                        },
                        "bottlenecks": {
                            "bottleneck_members": []
                        }
                    }
                }
            }
            manager.save_metrics(report_data)

        # Cleanup, keeping only 5
        deleted_count = manager.cleanup_old_metrics(keep_weeks=5)
        assert deleted_count == 5

        # Verify only 5 remain
        history = manager.get_last_n_weeks(n=100)
        assert len(history) == 5

    def test_load_nonexistent_file(self, temp_dir):
        """Test loading from a nonexistent file."""
        storage_file = temp_dir / "nonexistent.json"
        manager = MetricsHistoryManager(history_file=str(storage_file))

        # Should return empty history without error
        history = manager.get_last_n_weeks(n=10)
        assert history == []

    def test_load_corrupted_file(self, temp_dir):
        """Test loading from a corrupted JSON file."""
        storage_file = temp_dir / "corrupted.json"
        storage_file.write_text("{ invalid json }")

        manager = MetricsHistoryManager(history_file=str(storage_file))

        # Should return empty history and log warning
        history = manager.get_last_n_weeks(n=10)
        assert history == []

    def test_extract_metrics_with_missing_fields(self, manager):
        """Test extracting metrics when some fields are missing."""
        minimal_report = {
            "report_id": "test_report",
            "type": "weekly",
            "start_date": "2026-05-12",
            "end_date": "2026-05-19",
            "jira": {
                "by_status": {}
            },
            "analysis": {
                "project_health": {
                    "total_score": 80,
                    "dimension_scores": {}
                },
                "team_collaboration": {
                    "workload_distribution": {
                        "statistics": {},
                        "members": []
                    },
                    "bottlenecks": {}
                }
            }
        }

        metrics = manager.extract_metrics(minimal_report)

        # Should handle missing fields gracefully
        assert metrics["jira"]["by_status_counts"] == {}
        assert metrics["health"]["progress_score"] == 0
        assert metrics["team"]["total_members"] == 0
        assert metrics["team"]["gini_coefficient"] == 0
        assert metrics["team"]["overloaded_count"] == 0
        assert metrics["team"]["bottleneck_count"] == 0
