"""Main CLI entry point for ingest-cli."""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Optional

import click

if TYPE_CHECKING:
    from ingest_cli.pipeline import PipelineResult

from ingest_cli import __version__
from ingest_cli.config import (
    ConfigurationError,
    get_config_summary,
    load_config,
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


def display_results(result: "PipelineResult", dry_run: bool = False) -> None:
    """Display pipeline execution results.

    Args:
        result: Pipeline execution result.
        dry_run: Whether this was a dry-run.
    """
    click.echo()
    if dry_run:
        click.echo(click.style("=== DRY RUN Results ===", fg="cyan", bold=True))
    else:
        click.echo(click.style("=== Pipeline Results ===", fg="cyan", bold=True))

    click.echo(f"Documents read:    {result.total_read}")
    click.echo(f"Documents mapped:  {result.total_mapped}")
    click.echo(f"Files uploaded:    {result.total_uploaded}")
    click.echo(f"Events sent:       {result.total_sent}")
    click.echo(f"Failed:            {result.failed}")
    click.echo(f"Skipped (offset):  {result.skipped}")
    click.echo(f"Duration:          {result.duration_seconds:.2f}s")

    # Show errors if any
    if result.errors:
        click.echo()
        click.echo(click.style("Errors:", fg="red"))
        for error in result.errors[:10]:  # Show first 10 errors
            click.echo(f"  - Document {error.document_index}: [{error.stage}] {error.message}")
        if len(result.errors) > 10:
            click.echo(f"  ... and {len(result.errors) - 10} more errors")

    click.echo()
    if result.success:
        click.echo(click.style("Status: ✅ Success", fg="green", bold=True))
    else:
        click.echo(
            click.style(f"Status: ❌ Completed with {result.failed} errors", fg="red", bold=True)
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
@click.pass_context
def mappers(ctx: click.Context) -> None:
    """List available mappers."""
    from ingest_cli.mappers import get_mapper_info

    mapper_info = get_mapper_info()  # type: ignore[call-arg]

    click.echo("\nAvailable mappers:")
    click.echo()

    # Find max name length for alignment
    max_name_len = max(len(m["name"]) for m in mapper_info) if mapper_info else 10  # type: ignore[index]

    for mapper in mapper_info:
        name = mapper["name"].ljust(max_name_len)  # type: ignore[index]
        desc = mapper["description"]  # type: ignore[index]
        click.echo(f"  {click.style(name, fg='cyan')}  {desc}")

    click.echo()
    click.echo("Use 'ingest run --mapper <name>' to apply transformation.")


@cli.command()
@click.option(
    "-i",
    "--input",
    "input_source",
    type=str,
    required=True,
    help="Input source path (file or directory).",
)
@click.option(
    "-r",
    "--reader",
    "reader_name",
    type=str,
    default="csv",
    help="Reader to use (default: csv).",
)
@click.option(
    "-m",
    "--mapper",
    "mapper_name",
    type=str,
    default=None,
    help="Mapper to use (default: identity).",
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
    "-l",
    "--limit",
    type=int,
    default=None,
    help="Maximum documents to process.",
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
    input_source: str,
    reader_name: str,
    mapper_name: Optional[str],
    batch_size: Optional[int],
    offset: int,
    limit: Optional[int],
    dry_run: bool,
) -> None:
    """Execute the document ingestion pipeline.

    Read documents from INPUT source, optionally transform them with a MAPPER,
    and send them to the HxAI Ingestion API.

    Examples:

        # Dry run with CSV file
        ingest run -c config.yaml -i documents.csv --dry-run

        # Process first 100 documents
        ingest run -c config.yaml -i documents.csv --limit 100

        # Resume from document 500
        ingest run -c config.yaml -i documents.csv --offset 500

        # Use custom mapper
        ingest run -c config.yaml -i documents.csv --mapper field-mapper
    """
    from ingest_cli.api import AuthClient, IngestionClient
    from ingest_cli.mappers import create_mapper
    from ingest_cli.pipeline import create_pipeline
    from ingest_cli.readers import create_reader

    config_path = ctx.obj.get("config")
    logger = logging.getLogger(__name__)

    # Validate config path
    if not config_path:
        click.echo("Error: No configuration file specified.", err=True)
        click.echo("Use --config option or set INGEST_CONFIG environment variable.", err=True)
        ctx.exit(1)

    # Display header
    if dry_run:
        click.echo(click.style("=== DRY RUN MODE ===", fg="yellow", bold=True))
    else:
        click.echo(click.style("=== Starting Ingestion Pipeline ===", fg="cyan", bold=True))

    click.echo()

    # Load configuration
    try:
        click.echo(f"Loading configuration: {config_path}")
        settings = load_config(config_path)
        click.echo(click.style("  ✓ Configuration loaded", fg="green"))
    except ConfigurationError as e:
        click.echo(click.style(f"  ✗ Configuration error: {e}", fg="red"), err=True)
        ctx.exit(1)

    # Create reader
    try:
        click.echo(f"Creating reader: {reader_name}")
        reader = create_reader(reader_name)
        click.echo(click.style(f"  ✓ Reader '{reader_name}' created", fg="green"))
    except ValueError as e:
        click.echo(click.style(f"  ✗ Reader error: {e}", fg="red"), err=True)
        ctx.exit(1)

    # Validate input source
    if not reader.validate_source(input_source):
        click.echo(
            click.style(f"  ✗ Invalid source for reader '{reader_name}': {input_source}", fg="red"),
            err=True,
        )
        ctx.exit(1)
    click.echo(f"  ✓ Input source valid: {input_source}")

    # Create mapper
    try:
        mapper_name_to_use = mapper_name or "identity"
        click.echo(f"Creating mapper: {mapper_name_to_use}")
        mapper = create_mapper(mapper_name_to_use)
        click.echo(click.style(f"  ✓ Mapper '{mapper_name_to_use}' created", fg="green"))
    except ValueError as e:
        click.echo(click.style(f"  ✗ Mapper error: {e}", fg="red"), err=True)
        ctx.exit(1)

    # Create API clients (unless dry-run)
    ingestion_client = None
    if not dry_run:
        try:
            click.echo("Creating API clients...")
            auth_client = AuthClient(settings)  # type: ignore[call-arg, arg-type]
            ingestion_client = IngestionClient(settings, auth_client)  # type: ignore[call-arg, arg-type]
            click.echo(click.style("  ✓ API clients created", fg="green"))
        except Exception as e:
            click.echo(click.style(f"  ✗ API client error: {e}", fg="red"), err=True)
            ctx.exit(1)

    # Display pipeline configuration
    click.echo()
    click.echo("Pipeline configuration:")
    click.echo(f"  Reader:     {reader_name}")
    click.echo(f"  Mapper:     {mapper_name_to_use}")
    click.echo(f"  Source:     {input_source}")
    click.echo(f"  Batch size: {batch_size or settings.batch_size}")
    if offset > 0:
        click.echo(f"  Offset:     {offset}")
    if limit:
        click.echo(f"  Limit:      {limit}")
    click.echo(f"  Dry run:    {dry_run}")
    click.echo()

    # Run pipeline
    click.echo("Running pipeline...")
    try:
        pipeline = create_pipeline(
            settings=settings,
            reader=reader,
            source=input_source,
            ingestion_client=ingestion_client,
            mapper=mapper,
            dry_run=dry_run,
            batch_size=batch_size,
            offset=offset,
            limit=limit,
        )

        result = pipeline.run()

        # Display results
        display_results(result, dry_run=dry_run)

        # Exit with error code if failures
        if not result.success:
            ctx.exit(1)

    except Exception as e:
        logger.exception("Pipeline execution failed")
        click.echo(click.style(f"\nPipeline error: {e}", fg="red"), err=True)
        ctx.exit(1)


def main() -> None:
    """Main entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
