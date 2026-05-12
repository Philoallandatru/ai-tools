"""CLI decorators for error handling and common functionality."""

import functools
import sys
from typing import Any, Callable
import click
from crawler.observability import get_logger, LogContext


logger = get_logger('cli.decorators')


def handle_cli_errors(func: Callable) -> Callable:
    """
    Decorator to handle common CLI errors gracefully.

    Catches exceptions and displays user-friendly error messages
    while logging the full error details.

    Args:
        func: CLI command function to wrap

    Returns:
        Wrapped function with error handling
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            with LogContext(command=func.__name__):
                return func(*args, **kwargs)
        except FileNotFoundError as e:
            click.secho(f"✗ File not found: {e}", fg='red', err=True)
            logger.error(f"File not found in {func.__name__}", extra={'error': str(e)})
            sys.exit(1)
        except PermissionError as e:
            click.secho(f"✗ Permission denied: {e}", fg='red', err=True)
            logger.error(f"Permission error in {func.__name__}", extra={'error': str(e)})
            sys.exit(1)
        except ValueError as e:
            click.secho(f"✗ Invalid value: {e}", fg='red', err=True)
            logger.error(f"Value error in {func.__name__}", extra={'error': str(e)})
            sys.exit(1)
        except KeyError as e:
            click.secho(f"✗ Missing configuration key: {e}", fg='red', err=True)
            logger.error(f"Configuration error in {func.__name__}", extra={'error': str(e)})
            sys.exit(1)
        except Exception as e:
            click.secho(f"✗ Unexpected error: {e}", fg='red', err=True)
            logger.exception(f"Unexpected error in {func.__name__}")
            sys.exit(1)

    return wrapper


def require_config(func: Callable) -> Callable:
    """
    Decorator to ensure config file exists before running command.

    Args:
        func: CLI command function to wrap

    Returns:
        Wrapped function with config validation
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        config_path = kwargs.get('config', 'config.yaml')

        from pathlib import Path
        if not Path(config_path).exists():
            click.secho(
                f"✗ Configuration file not found: {config_path}",
                fg='red',
                err=True
            )
            click.echo("Run 'crawler init' to create a default configuration file.")
            sys.exit(1)

        return func(*args, **kwargs)

    return wrapper


def with_output(func: Callable) -> Callable:
    """
    Decorator to inject CLIOutput instance into command.

    Adds 'output' parameter to the function with a CLIOutput instance
    configured based on verbose/quiet flags.

    Args:
        func: CLI command function to wrap

    Returns:
        Wrapped function with output parameter
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        from crawler.cli.output import CLIOutput

        verbose = kwargs.pop('verbose', False)
        quiet = kwargs.pop('quiet', False)

        output = CLIOutput(verbose=verbose, quiet=quiet)
        kwargs['output'] = output

        return func(*args, **kwargs)

    return wrapper
