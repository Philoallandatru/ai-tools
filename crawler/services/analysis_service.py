"""Service layer for Jira deep analysis."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from crawler.analyzers.action_recommender import ActionRecommender
from crawler.analyzers.closed_loop_checker import ClosedLoopChecker
from crawler.analyzers.comment_analyzer import CommentAnalyzer
from crawler.analyzers.custom_analyzer import CustomAnalyzer
from crawler.analyzers.issue_summary_analyzer import IssueSummaryAnalyzer
from crawler.analyzers.knowledge_retriever import KnowledgeRetriever
from crawler.analyzers.root_cause_analyzer import RootCauseAnalyzer
from crawler.analyzers.similar_jira_finder import SimilarJiraFinder
from crawler.config import ConfigManager
from crawler.jira_analyzer import JiraDeepAnalyzer
from crawler.llm_client import BaseLLMClient, LLMClientFactory


@dataclass
class LLMClientInfo:
    provider: str
    base_url: Optional[str]
    used_mock_fallback: bool = False
    connection_error: Optional[str] = None


@dataclass
class JiraAnalysisResult:
    issue_key: str
    report: str
    report_file: Path
    llm_info: LLMClientInfo
    analyzers: List[str]


class AnalysisService:
    """Build and run Jira analysis pipelines."""

    def __init__(self, config_path: str = "config.yaml", config: Optional[Dict[str, Any]] = None):
        self.config_path = config_path
        self.config = config if config is not None else ConfigManager(config_path).load()

    def analyze_jira(
        self,
        issue_key: str,
        source_dir: str = "./sources",
        wiki_dir: str = "./wiki",
        output_dir: str = "./reports",
        llm_provider: Optional[str] = None,
        allow_mock_fallback: bool = True,
    ) -> JiraAnalysisResult:
        """Run Jira deep analysis and persist the markdown report."""
        llm_client, llm_info = self.create_llm_client(
            provider_override=llm_provider,
            allow_mock_fallback=allow_mock_fallback,
            connection_test=True,
        )
        analyzer = self.create_jira_analyzer(source_dir, wiki_dir, llm_client)
        report = analyzer.analyze(issue_key)

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = output_path / f"jira_analysis_{issue_key}_{timestamp}.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)

        return JiraAnalysisResult(
            issue_key=issue_key,
            report=report,
            report_file=report_file,
            llm_info=llm_info,
            analyzers=[analyzer.get_name() for analyzer in analyzer.pipeline],
        )

    def create_llm_client(
        self,
        provider_override: Optional[str] = None,
        allow_mock_fallback: bool = True,
        connection_test: bool = False,
    ) -> Tuple[BaseLLMClient, LLMClientInfo]:
        """Create the configured LLM client, optionally testing connectivity."""
        llm_config = dict(self.config.get("llm", {}))
        provider = provider_override or llm_config.get("provider", "openai")
        llm_config["provider"] = "openai" if provider == "openai" else provider

        if provider == "mock":
            return (
                LLMClientFactory.create("mock"),
                LLMClientInfo(provider="mock", base_url=None),
            )

        base_url = llm_config.get("base_url", "http://127.0.0.1:1234/v1")
        info = LLMClientInfo(provider="openai", base_url=base_url)

        try:
            client = LLMClientFactory.create_from_config(llm_config)
            if connection_test:
                client.generate("test", max_tokens=10, temperature=0.7)
            return client, info
        except Exception as exc:
            if not allow_mock_fallback:
                raise
            info.used_mock_fallback = True
            info.connection_error = str(exc)
            return LLMClientFactory.create("mock"), info

    def create_jira_analyzer(
        self,
        source_dir: str,
        wiki_dir: str,
        llm_client: BaseLLMClient,
    ) -> JiraDeepAnalyzer:
        """Create and register the standard Jira analysis pipeline."""
        analyzer = JiraDeepAnalyzer(source_dir=source_dir, llm_client=llm_client)
        analyzer.register_analyzer(
            KnowledgeRetriever(
                source_dir=source_dir,
                wiki_dir=wiki_dir,
                llm_client=llm_client,
                config=self.config,
            )
        )
        analyzer.register_analyzer(RootCauseAnalyzer(llm_client))

        similar_jira_config = self.config.get("jira_analysis", {}).get("similar_jira", {})
        analyzer.register_analyzer(
            SimilarJiraFinder(
                source_dir=source_dir,
                top_k=3,
                llm_client=llm_client,
                config=similar_jira_config
            )
        )
        analyzer.register_analyzer(ClosedLoopChecker(llm_client))
        analyzer.register_analyzer(CommentAnalyzer(llm_client))
        analyzer.register_analyzer(ActionRecommender(llm_client))

        issue_summary_config = self.config.get("jira_analysis", {}).get("issue_summary", {})
        if issue_summary_config.get("enabled", True):
            analyzer.register_analyzer(
                IssueSummaryAnalyzer(llm_client, config=issue_summary_config)
            )

        for custom_config in self.config.get("custom_analyzers", []):
            if custom_config.get("enabled", True):
                analyzer.register_analyzer(CustomAnalyzer(custom_config, llm_client))

        return analyzer
