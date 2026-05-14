"""Synchronization service for Confluence and Jira sources."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from crawler.confluence import ConfluenceCrawler
from crawler.error_handler import ErrorHandler
from crawler.jira import JiraCrawler
from crawler.observability import LogContext, get_logger
from crawler.storage import StorageManager

logger = get_logger(__name__)


class SyncService:
    """Coordinate Jira and Confluence synchronization work."""

    def __init__(
        self,
        config: Dict[str, Any],
        storage: Optional[StorageManager] = None,
        error_handler: Optional[ErrorHandler] = None,
    ):
        self.config = config
        self.storage = storage or StorageManager(
            config["output"]["base_dir"],
            config["sync"]["state_file"],
        )
        self.error_handler = error_handler or ErrorHandler(**config["error_handling"])
        self.max_workers = min(config.get("performance", {}).get("max_workers", 10), 10)
        self.max_results_per_page = config.get("performance", {}).get(
            "max_results_per_page", 50
        )

    def sync_all(
        self,
        source_name: Optional[str] = None,
        source_type: str = "all",
    ) -> Dict[str, Any]:
        """Synchronize selected source groups and return stats plus per-task results."""
        with LogContext(operation="sync_all", source_type=source_type):
            logger.info("Starting synchronization", extra={"source_name": source_name})

            sources_to_sync = self.filter_sources(
                self.config["sources"],
                source_name,
                source_type,
            )
            result = {
                "sources": sources_to_sync,
                "stats": self._empty_stats(),
                "results": {"confluence": [], "jira": []},
                "errors": [],
            }

            if sources_to_sync["confluence"]:
                logger.info("Syncing Confluence sources", extra={"count": len(sources_to_sync["confluence"])})
                confluence_result = self.sync_confluence_sources(sources_to_sync["confluence"])
                self._merge_result(result, confluence_result, "confluence")

            if sources_to_sync["jira"]:
                logger.info("Syncing Jira sources", extra={"count": len(sources_to_sync["jira"])})
                jira_result = self.sync_jira_sources(sources_to_sync["jira"])
                self._merge_result(result, jira_result, "jira")

            self.storage.save_state()
            self.error_handler.generate_error_report()

            logger.info(
                "Synchronization completed",
                extra={
                    "confluence_pages": result["stats"]["confluence"]["pages"],
                    "jira_issues": result["stats"]["jira"]["issues"],
                    "errors": len(result["errors"]),
                }
            )
            return result

    def sync_confluence_sources(self, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Synchronize all configured Confluence spaces for the given sources."""
        tasks = []
        for source in sources:
            is_cloud = source.get("type", "cloud").lower() == "cloud"
            for space in source["spaces"]:
                tasks.append(
                    {
                        "source": source,
                        "space_config": space,
                        "is_cloud": is_cloud,
                    }
                )

        stats = self._empty_stats()["confluence"]
        results = []
        errors = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self._sync_confluence_space,
                    task["source"],
                    task["space_config"],
                    task["is_cloud"],
                ): task
                for task in tasks
            }

            for future in as_completed(futures):
                task = futures[future]
                source_name = task["source"]["name"]
                space_key = task["space_config"]["key"]
                try:
                    task_stats = future.result()
                    stats["pages"] += task_stats["pages"]
                    stats["attachments"] += task_stats["attachments"]
                    stats["skipped"] += task_stats.get("skipped", 0)
                    stats["total"] += task_stats.get("total", 0)
                    results.append(
                        {
                            "source": source_name,
                            "target": space_key,
                            "stats": task_stats,
                        }
                    )
                except Exception as exc:
                    errors.append(
                        {
                            "source": source_name,
                            "target": space_key,
                            "error": str(exc),
                        }
                    )

        return {"stats": {"confluence": stats}, "results": results, "errors": errors}

    def sync_jira_sources(self, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Synchronize all configured Jira projects for the given sources."""
        tasks = []
        for source in sources:
            is_cloud = source.get("type", "cloud").lower() == "cloud"
            for project in source["projects"]:
                tasks.append(
                    {
                        "source": source,
                        "project_key": project["key"],
                        "is_cloud": is_cloud,
                    }
                )

        stats = self._empty_stats()["jira"]
        results = []
        errors = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self._sync_jira_project,
                    task["source"],
                    task["project_key"],
                    task["is_cloud"],
                ): task
                for task in tasks
            }

            for future in as_completed(futures):
                task = futures[future]
                source_name = task["source"]["name"]
                project_key = task["project_key"]
                try:
                    task_stats = future.result()
                    stats["issues"] += task_stats["issues"]
                    stats["attachments"] += task_stats["attachments"]
                    stats["skipped"] += task_stats.get("skipped", 0)
                    stats["total"] += task_stats.get("total", 0)
                    results.append(
                        {
                            "source": source_name,
                            "target": project_key,
                            "stats": task_stats,
                        }
                    )
                except Exception as exc:
                    errors.append(
                        {
                            "source": source_name,
                            "target": project_key,
                            "error": str(exc),
                        }
                    )

        return {"stats": {"jira": stats}, "results": results, "errors": errors}

    def _sync_confluence_space(
        self,
        source: Dict[str, Any],
        space_config: Dict[str, Any],
        is_cloud: bool,
    ) -> Dict[str, int]:
        crawler = ConfluenceCrawler(
            source["url"],
            source["api_token"],
            self.error_handler,
            username=source.get("username"),
            is_cloud=is_cloud,
        )
        return crawler.crawl_space(
            source["name"],
            space_config["key"],
            self.storage,
            max_pages=space_config.get("max_pages"),
            root_page_id=space_config.get("root_page_id"),
        )

    def _sync_jira_project(
        self,
        source: Dict[str, Any],
        project_key: str,
        is_cloud: bool,
    ) -> Dict[str, int]:
        crawler = JiraCrawler(
            source["url"],
            source["api_token"],
            self.error_handler,
            username=source.get("username"),
            is_cloud=is_cloud,
            max_results_per_page=self.max_results_per_page,
        )
        return crawler.crawl_project(source["name"], project_key, self.storage)

    @staticmethod
    def filter_sources(
        sources: Dict[str, Any],
        source_name: Optional[str],
        source_type: str,
    ) -> Dict[str, list]:
        """Filter configured sources by optional name and source type."""
        result = {"confluence": [], "jira": []}

        if source_name:
            if source_type in ["confluence", "all"]:
                result["confluence"] = [
                    source
                    for source in sources.get("confluence", [])
                    if source["name"] == source_name
                ]
            if source_type in ["jira", "all"]:
                result["jira"] = [
                    source
                    for source in sources.get("jira", [])
                    if source["name"] == source_name
                ]
            return result

        if source_type in ["confluence", "all"]:
            result["confluence"] = sources.get("confluence", [])
        if source_type in ["jira", "all"]:
            result["jira"] = sources.get("jira", [])
        return result

    @staticmethod
    def _empty_stats() -> Dict[str, Dict[str, int]]:
        return {
            "confluence": {"pages": 0, "attachments": 0, "skipped": 0, "total": 0},
            "jira": {"issues": 0, "attachments": 0, "skipped": 0, "total": 0},
        }

    @staticmethod
    def _merge_result(target: Dict[str, Any], source: Dict[str, Any], source_type: str) -> None:
        # Accumulate stats instead of replacing them
        for key, value in source["stats"][source_type].items():
            target["stats"][source_type][key] += value
        target["results"][source_type].extend(source["results"])
        for error in source["errors"]:
            error["type"] = source_type
            target["errors"].append(error)
