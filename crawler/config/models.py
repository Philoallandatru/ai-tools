"""
Pydantic configuration models for type-safe config validation.

This module defines the complete configuration schema using Pydantic,
providing validation, type checking, and environment variable support.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SpaceConfig(BaseModel):
    """Confluence space configuration."""

    key: str = Field(..., description="Space key")
    name: str = Field(..., description="Space name")
    max_pages: Optional[int] = Field(None, description="Maximum pages to fetch")
    root_page_id: Optional[str] = Field(None, description="Root page ID to start from")


class ProjectConfig(BaseModel):
    """Jira project configuration."""

    key: str = Field(..., description="Project key")
    name: str = Field(..., description="Project name")


class ConfluenceSourceConfig(BaseModel):
    """Confluence source configuration."""

    name: str = Field(..., description="Source name")
    url: str = Field(..., description="Confluence URL")
    username: str = Field(..., description="Username or email")
    api_token: str = Field(..., description="API token")
    spaces: List[SpaceConfig] = Field(default_factory=list, description="Spaces to sync")
    type: str = Field(default="cloud", description="Instance type: cloud or server")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URL doesn't end with slash."""
        return v.rstrip("/")


class JiraSourceConfig(BaseModel):
    """Jira source configuration."""

    name: str = Field(..., description="Source name")
    url: str = Field(..., description="Jira URL")
    username: str = Field(..., description="Username or email")
    api_token: str = Field(..., description="API token")
    projects: List[ProjectConfig] = Field(default_factory=list, description="Projects to sync")
    type: str = Field(default="cloud", description="Instance type: cloud or server")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URL doesn't end with slash."""
        return v.rstrip("/")


class SourcesConfig(BaseModel):
    """All data sources configuration."""

    confluence: List[ConfluenceSourceConfig] = Field(default_factory=list)
    jira: List[JiraSourceConfig] = Field(default_factory=list)


class OutputConfig(BaseModel):
    """Output directory configuration."""

    base_dir: str = Field(default="./sources", description="Base output directory")


class SyncConfig(BaseModel):
    """Synchronization state configuration."""

    state_file: str = Field(
        default="./.atlassian-sync-state.json",
        description="Sync state file path",
    )


class ErrorHandlingConfig(BaseModel):
    """Error handling configuration."""

    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts")
    retry_delay: int = Field(default=5, ge=0, description="Retry delay in seconds")
    error_log: str = Field(default="./sync-errors.log", description="Error log file path")


class KnowledgeRetrievalConfig(BaseModel):
    """Knowledge retrieval performance settings."""

    max_thread_workers: int = Field(default=3, ge=1, le=10)
    wiki_query_timeout: int = Field(default=30, ge=5)
    max_keywords: int = Field(default=10, ge=1)
    min_keyword_length: int = Field(default=2, ge=1)
    max_keyword_length: int = Field(default=20, ge=5)
    max_description_length: int = Field(default=500, ge=100)
    wiki_content_preview: int = Field(default=1000, ge=100)
    keyword_extraction_max_tokens: int = Field(default=200, ge=50)
    concept_analysis_max_tokens: int = Field(default=300, ge=50)
    max_search_keywords: int = Field(default=5, ge=1)
    max_results_per_keyword: int = Field(default=3, ge=1)


class PerformanceConfig(BaseModel):
    """Performance and concurrency configuration."""

    max_results_per_page: int = Field(default=50, ge=1, le=100)
    max_workers: int = Field(default=10, ge=1, le=20)
    knowledge_retrieval: KnowledgeRetrievalConfig = Field(
        default_factory=KnowledgeRetrievalConfig
    )


class CacheConfig(BaseModel):
    """Cache configuration."""

    enabled: bool = Field(default=True)
    dir: str = Field(default="./.cache", description="Cache directory")
    ttl: int = Field(default=86400, ge=0, description="Cache TTL in seconds")


class SchedulerConfig(BaseModel):
    """Scheduler configuration."""

    enabled: bool = Field(default=True)
    sync_time: str = Field(default="02:00", description="Daily sync time (HH:MM)")
    timezone: str = Field(default="Asia/Shanghai")
    retry_on_failure: bool = Field(default=True)
    retry_interval: int = Field(default=3600, ge=0, description="Retry interval in seconds")

    @field_validator("sync_time")
    @classmethod
    def validate_sync_time(cls, v: str) -> str:
        """Validate time format HH:MM."""
        parts = v.split(":")
        if len(parts) != 2:
            raise ValueError("sync_time must be in HH:MM format")
        hour, minute = parts
        if not (0 <= int(hour) <= 23 and 0 <= int(minute) <= 59):
            raise ValueError("Invalid time values")
        return v


class LLMConfig(BaseModel):
    """LLM provider configuration."""

    provider: str = Field(default="openai", description="LLM provider: openai or mock")
    base_url: str = Field(
        default="http://127.0.0.1:1234/v1",
        description="OpenAI-compatible API base URL",
    )
    model: str = Field(default="qwen3.5-4b", description="Model name")
    max_tokens: int = Field(default=2000, ge=1, description="Maximum tokens per request")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate provider is supported."""
        if v not in ["openai", "mock"]:
            raise ValueError("provider must be 'openai' or 'mock'")
        return v


class ReportsConfig(BaseModel):
    """Reports configuration."""

    fixed_issues: List[str] = Field(default_factory=list, description="Fixed tracked issues")
    max_issues_per_report: int = Field(default=100, ge=1)
    group_by: str = Field(default="status", description="Grouping method")
    include_attachments: bool = Field(default=True)

    @field_validator("group_by")
    @classmethod
    def validate_group_by(cls, v: str) -> str:
        """Validate grouping method."""
        valid_methods = ["status", "priority", "assignee", "type"]
        if v not in valid_methods:
            raise ValueError(f"group_by must be one of {valid_methods}")
        return v


class AnalyzerConfig(BaseModel):
    """Generic analyzer configuration."""

    enabled: bool = Field(default=True)
    max_tokens: Optional[int] = Field(None, ge=1)
    max_items: Optional[int] = Field(None, ge=1)


class RiskThresholdsConfig(BaseModel):
    """Risk analysis thresholds."""

    stalled_days: int = Field(default=7, ge=1)
    overload_issues: int = Field(default=5, ge=1)


class RiskAnalyzerConfig(BaseModel):
    """Risk analyzer configuration."""

    enabled: bool = Field(default=True)
    dimensions: List[str] = Field(default_factory=lambda: ["progress", "priority", "resource"])
    thresholds: RiskThresholdsConfig = Field(default_factory=RiskThresholdsConfig)
    max_tokens: int = Field(default=600, ge=1)


class ReportAnalysisConfig(BaseModel):
    """Report analysis configuration."""

    enabled: bool = Field(default=True)
    analyzers: Dict[str, Any] = Field(default_factory=dict)
    llm: Optional[LLMConfig] = Field(None, description="Override LLM config for analysis")


class CodeCoverageConfig(BaseModel):
    """Code coverage check configuration."""

    enabled: bool = Field(default=True)
    source_dir: str = Field(default="./sources")
    max_results: int = Field(default=5, ge=1)


class IssueSummaryConfig(BaseModel):
    """Issue summary configuration."""

    enabled: bool = Field(default=True)
    use_llm: bool = Field(default=True)
    max_tokens: int = Field(default=1000, ge=1)
    code_coverage: CodeCoverageConfig = Field(default_factory=CodeCoverageConfig)


class JiraAnalysisConfig(BaseModel):
    """Jira analysis configuration."""

    issue_summary: IssueSummaryConfig = Field(default_factory=IssueSummaryConfig)


class CustomAnalyzerContextConfig(BaseModel):
    """Custom analyzer context configuration."""

    include_knowledge: bool = Field(default=True)
    include_root_cause: bool = Field(default=False)
    include_similar_jira: bool = Field(default=False)
    include_comments: bool = Field(default=False)


class CustomAnalyzerConfig(BaseModel):
    """Custom analyzer configuration."""

    name: str = Field(..., description="Analyzer name")
    enabled: bool = Field(default=True)
    prompt: str = Field(..., description="Analysis prompt template")
    context: CustomAnalyzerContextConfig = Field(default_factory=CustomAnalyzerContextConfig)
    max_tokens: int = Field(default=1000, ge=1)


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Log level")
    format: str = Field(default="json", description="Log format: json or text")
    output_file: Optional[str] = Field(None, description="Optional log file path")

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"level must be one of {valid_levels}")
        return v_upper

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Validate log format."""
        if v not in ["json", "text"]:
            raise ValueError("format must be 'json' or 'text'")
        return v


class MetricsConfig(BaseModel):
    """Metrics collection configuration."""

    enabled: bool = Field(default=False)
    port: int = Field(default=9090, ge=1024, le=65535)


class TracingConfig(BaseModel):
    """Distributed tracing configuration."""

    enabled: bool = Field(default=False)
    service_name: str = Field(default="crawler")
    otlp_endpoint: Optional[str] = Field(default=None)
    console_export: bool = Field(default=False)


class ObservabilityConfig(BaseModel):
    """Observability configuration."""

    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    tracing: TracingConfig = Field(default_factory=TracingConfig)


class AppConfig(BaseModel):
    """Root application configuration."""

    model_config = ConfigDict(
        extra="allow",  # Allow extra fields for forward compatibility
        validate_assignment=True,  # Validate on assignment
    )

    sources: SourcesConfig = Field(default_factory=SourcesConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    sync: SyncConfig = Field(default_factory=SyncConfig)
    error_handling: ErrorHandlingConfig = Field(default_factory=ErrorHandlingConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    reports: ReportsConfig = Field(default_factory=ReportsConfig)
    report_analysis: ReportAnalysisConfig = Field(default_factory=ReportAnalysisConfig)
    jira_analysis: JiraAnalysisConfig = Field(default_factory=JiraAnalysisConfig)
    custom_analyzers: List[CustomAnalyzerConfig] = Field(default_factory=list)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
