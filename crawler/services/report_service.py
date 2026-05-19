"""Service layer for report generation and persistence."""

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional

from crawler.config import ConfigManager
from crawler.report_generator import ReportGenerator


@dataclass
class ReportResult:
    report: Dict[str, Any]
    output_file: Path
    content: Optional[str]
    output_format: str


class ReportService:
    """Generate daily, weekly, and monthly reports."""

    def __init__(self, config_path: str = "config.yaml", config: Optional[Dict[str, Any]] = None):
        self.config_path = config_path
        self.config = config if config is not None else self._load_optional_config(config_path)

    def generate(
        self,
        report_type: str = "weekly",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        output_dir: str = "./reports",
        source_dir: str = "./sources",
        output_format: str = "markdown",
    ) -> ReportResult:
        """Generate and save a report."""
        generator = ReportGenerator(source_dir, self.config)
        report = generator.generate_report(report_type, start_date, end_date)

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_name = {"daily": "日报", "weekly": "周报", "monthly": "月报"}[report_type]
        filename = f"{report_name}_{report['start_date']}_to_{report['end_date']}_{timestamp}"

        if output_format == "markdown":
            content = generator.format_report_markdown(report)
            output_file = output_path / f"{filename}.md"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            content = None
            output_file = output_path / f"{filename}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

        # Save metrics to history for trend analysis
        try:
            from crawler.metrics_history import MetricsHistoryManager
            history_manager = MetricsHistoryManager()
            history_manager.save_metrics(report)
        except Exception as e:
            print(f"[WARNING] 保存指标历史失败: {e}")

        return ReportResult(
            report=report,
            output_file=output_file,
            content=content,
            output_format=output_format,
        )

    @staticmethod
    def parse_date(value: Optional[str], label: str) -> Optional[date]:
        """Parse YYYY-MM-DD date strings for report commands."""
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError(f"无效的{label}日期格式: {value}，应为 YYYY-MM-DD") from exc

    @staticmethod
    def _load_optional_config(config_path: str) -> Dict[str, Any]:
        if Path(config_path).exists():
            return ConfigManager(config_path).load()
        return {}
