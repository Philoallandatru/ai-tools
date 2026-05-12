"""CLI output formatting and logging utilities."""

import sys
from typing import Any, Dict, List, Optional
import click
from crawler.observability import get_logger, LogContext


class CLIOutput:
    """
    CLI output manager that handles both terminal output and structured logging.

    This class provides a unified interface for CLI output, automatically
    logging to structured logs while displaying user-friendly messages in the terminal.
    """

    def __init__(self, verbose: bool = False, quiet: bool = False):
        """
        Initialize CLI output manager.

        Args:
            verbose: Enable verbose output (DEBUG level logs)
            quiet: Suppress non-error output
        """
        self.verbose = verbose
        self.quiet = quiet
        self.logger = get_logger('cli')

    def success(self, message: str, **context: Any) -> None:
        """Display success message in green."""
        if not self.quiet:
            click.secho(f"✓ {message}", fg='green')
        self.logger.info(message, extra={'status': 'success', **context})

    def error(self, message: str, **context: Any) -> None:
        """Display error message in red."""
        click.secho(f"✗ {message}", fg='red', err=True)
        self.logger.error(message, extra={'status': 'error', **context})

    def warning(self, message: str, **context: Any) -> None:
        """Display warning message in yellow."""
        if not self.quiet:
            click.secho(f"⚠ {message}", fg='yellow')
        self.logger.warning(message, extra={'status': 'warning', **context})

    def info(self, message: str, **context: Any) -> None:
        """Display info message."""
        if not self.quiet:
            click.echo(message)
        self.logger.info(message, extra=context)

    def debug(self, message: str, **context: Any) -> None:
        """Display debug message (only in verbose mode)."""
        if self.verbose:
            click.secho(f"[DEBUG] {message}", fg='cyan', dim=True)
        self.logger.debug(message, extra=context)

    def header(self, message: str) -> None:
        """Display section header."""
        if not self.quiet:
            click.echo()
            click.secho(f"=== {message} ===", bold=True)
            click.echo()

    def subheader(self, message: str) -> None:
        """Display subsection header."""
        if not self.quiet:
            click.secho(f"--- {message} ---", bold=True)

    def table(self, data: List[Dict[str, Any]], headers: Optional[List[str]] = None) -> None:
        """
        Display data as a formatted table.

        Args:
            data: List of dictionaries to display
            headers: Optional list of column headers (uses dict keys if not provided)
        """
        if self.quiet or not data:
            return

        # Determine headers
        if headers is None:
            headers = list(data[0].keys()) if data else []

        # Calculate column widths
        widths = {h: len(str(h)) for h in headers}
        for row in data:
            for header in headers:
                value = str(row.get(header, ''))
                widths[header] = max(widths[header], len(value))

        # Print header
        header_row = ' | '.join(str(h).ljust(widths[h]) for h in headers)
        click.echo(header_row)
        click.echo('-' * len(header_row))

        # Print rows
        for row in data:
            row_str = ' | '.join(str(row.get(h, '')).ljust(widths[h]) for h in headers)
            click.echo(row_str)

    def key_value(self, key: str, value: Any, indent: int = 0) -> None:
        """Display key-value pair."""
        if not self.quiet:
            prefix = '  ' * indent
            click.echo(f"{prefix}{key}: {value}")

    def list_items(self, items: List[str], bullet: str = '-', indent: int = 0) -> None:
        """Display list of items."""
        if not self.quiet:
            prefix = '  ' * indent
            for item in items:
                click.echo(f"{prefix}{bullet} {item}")

    def progress_bar(self, iterable, length: Optional[int] = None, label: str = '') -> Any:
        """
        Create a progress bar for iteration.

        Args:
            iterable: Iterable to wrap
            length: Total length (if known)
            label: Progress bar label

        Returns:
            Progress bar iterator
        """
        if self.quiet:
            return iterable
        return click.progressbar(iterable, length=length, label=label)

    def confirm(self, message: str, default: bool = False) -> bool:
        """
        Prompt user for confirmation.

        Args:
            message: Confirmation message
            default: Default value if user just presses Enter

        Returns:
            True if user confirms, False otherwise
        """
        return click.confirm(message, default=default)

    def prompt(self, message: str, default: Optional[str] = None) -> str:
        """
        Prompt user for input.

        Args:
            message: Prompt message
            default: Default value

        Returns:
            User input
        """
        return click.prompt(message, default=default)

    def json(self, data: Any) -> None:
        """Display data as formatted JSON."""
        import json
        if not self.quiet:
            click.echo(json.dumps(data, indent=2, ensure_ascii=False))

    def stats(self, stats: Dict[str, Any], title: Optional[str] = None) -> None:
        """
        Display statistics in a formatted way.

        Args:
            stats: Dictionary of statistics
            title: Optional title for the stats section
        """
        if self.quiet:
            return

        if title:
            self.subheader(title)

        for key, value in stats.items():
            if isinstance(value, dict):
                click.echo(f"{key}:")
                for sub_key, sub_value in value.items():
                    click.echo(f"  {sub_key}: {sub_value}")
            else:
                click.echo(f"{key}: {value}")

    def separator(self, char: str = '-', length: int = 80) -> None:
        """Display a separator line."""
        if not self.quiet:
            click.echo(char * length)


def create_output(verbose: bool = False, quiet: bool = False) -> CLIOutput:
    """
    Factory function to create CLIOutput instance.

    Args:
        verbose: Enable verbose output
        quiet: Suppress non-error output

    Returns:
        CLIOutput instance
    """
    return CLIOutput(verbose=verbose, quiet=quiet)
