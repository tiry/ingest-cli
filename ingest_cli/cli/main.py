"""Main CLI entry point for ingest-cli."""

import logging
import sys
from typing import Optional

import click

from ingest_cli import __version__
from ingest_cli.config import (
    ConfigurationError,
    get_config_summary,
    validate_config_file,
)


def setup_logging(verbose: bool) -> None:
    """Configure logging based on verbosity level.

    Args:
        verbose: If True, set DEBUG level; otherwise, INFO level.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


@click.group()
@click.version_option(version=__version__, prog_name="ingest")
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    envvar="INGEST_VERBOSE",
    help="Enable verbose output.",
)
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True),
    envvar="INGEST_CONFIG",
    help="Path to configuration file.",
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool, config: Optional[str]) -> None:
    """Ingest CLI - Import documents to HxAI Ingestion API.

    A command-line tool for importing documents (files + metadata) from a local
    filesystem to the HxAI Ingestion REST API.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Store options in context for subcommands
    ctx.obj["verbose"] = verbose
    ctx.obj["config"] = config

    # Setup logging
    setup_logging(verbose)


@cli.command()
@click.pass_context
def version(ctx: click.Context) -> None:
    """Display version information."""
    click.echo(f"ingest-cli version {__version__}")


@cli.command()
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True),
    help="Path to configuration file to validate.",
)
@click.option(
    "--show-config",
    is_flag=True,
    default=False,
    help="Display configuration values (secrets redacted).",
)
@click.pass_context
def validate(ctx: click.Context, config: Optional[str], show_config: bool) -> None:
    """Validate configuration file."""
    config_path = config or ctx.obj.get("config")
    if not config_path:
        click.echo("Error: No configuration file specified.", err=True)
        click.echo("Use --config option or set INGEST_CONFIG environment variable.", err=True)
        ctx.exit(1)

    click.echo(f"Validating configuration: {config_path}")

    try:
        settings, warnings = validate_config_file(config_path)
        click.echo(click.style("✅ Configuration is valid!", fg="green"))

        # Show warnings if any
        for warning in warnings:
            click.echo(click.style(f"⚠️  {warning}", fg="yellow"))

        # Optionally show configuration
        if show_config:
            click.echo("\nConfiguration values:")
            summary = get_config_summary(settings)
            for key, value in summary.items():
                click.echo(f"  {key}: {value}")

    except ConfigurationError as e:
        click.echo(click.style(f"❌ Configuration error: {e}", fg="red"), err=True)
        ctx.exit(1)


@cli.command()
@click.pass_context
def readers(ctx: click.Context) -> None:
    """List available document readers."""
    from ingest_cli.readers import get_reader_info

    reader_info = get_reader_info()

    click.echo("\nAvailable readers:")
    click.echo()

    # Find max name length for alignment
    max_name_len = max(len(r["name"]) for r in reader_info) if reader_info else 10

    for reader in reader_info:
        name = reader["name"].ljust(max_name_len)
        desc = reader["description"]
        click.echo(f"  {click.style(name, fg='cyan')}  {desc}")

    click.echo()
    click.echo("Use 'ingest run --reader <name> --input <source>' to process documents.")


@cli.command()
@click.option(
    "-i",
    "--input",
    "input_file",
    type=click.Path(exists=True),
    required=True,
    help="Path to input file.",
)
@click.option(
    "-r",
    "--reader",
    type=str,
    default="csv",
    help="Reader to use (default: csv).",
)
@click.option(
    "-m",
    "--mapper",
    type=str,
    default=None,
    help="Python module path for custom mapper.",
)
@click.option(
    "-b",
    "--batch-size",
    type=int,
    default=None,
    help="Batch size for processing (overrides config).",
)
@click.option(
    "-o",
    "--offset",
    type=int,
    default=0,
    help="Skip first N documents (for resume).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Validate without sending to API.",
)
@click.pass_context
def run(
    ctx: click.Context,
    input_file: str,
    reader: str,
    mapper: Optional[str],
    batch_size: Optional[int],
    offset: int,
    dry_run: bool,
) -> None:
    """Execute the document ingestion pipeline.

    Read documents from INPUT file, optionally transform them with a MAPPER,
    and send them to the HxAI Ingestion API.
    """
    config_path = ctx.obj.get("config")
    _verbose = ctx.obj.get("verbose", False)  # Will be used when pipeline is implemented

    if not config_path:
        click.echo("Error: No configuration file specified.", err=True)
        click.echo("Use --config option or set INGEST_CONFIG environment variable.", err=True)
        ctx.exit(1)

    logger = logging.getLogger(__name__)

    if dry_run:
        click.echo("=== DRY RUN MODE ===")

    logger.info(f"Configuration: {config_path}")
    logger.info(f"Input file: {input_file}")
    logger.info(f"Reader: {reader}")
    if mapper:
        logger.info(f"Mapper: {mapper}")
    if batch_size:
        logger.info(f"Batch size (override): {batch_size}")
    if offset > 0:
        logger.info(f"Offset (skip): {offset}")

    # TODO: Implement the actual pipeline in later steps
    click.echo("Pipeline execution not yet implemented.")
    click.echo("This will be completed in Steps 4-9 of the implementation plan.")


def main() -> None:
    """Main entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
