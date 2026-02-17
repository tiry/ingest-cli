"""Main CLI entry point for ingest-cli."""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

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


def display_results(result: PipelineResult, dry_run: bool = False) -> None:
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
def cli(ctx: click.Context, verbose: bool, config: str | None) -> None:
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
def validate(ctx: click.Context, config: str | None, show_config: bool) -> None:
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
    "-c",
    "--config",
    "config_override",
    type=click.Path(exists=True),
    default=None,
    help="Path to configuration file (default: config.yaml).",
)
@click.option(
    "--auth-only",
    is_flag=True,
    default=False,
    help="Only check authentication (skip upload and ingest).",
)
@click.option(
    "--skip-ingest",
    is_flag=True,
    default=False,
    help="Skip the ingest step (only check auth and upload).",
)
@click.pass_context
def check(
    ctx: click.Context,
    config_override: str | None,
    auth_only: bool,
    skip_ingest: bool,
) -> None:
    """Test API connectivity with verbose output.

    This command performs a full connectivity check against the HxAI Ingestion API:

    1. Validates configuration
    2. Tests authentication and token retrieval
    3. Uploads a test text file via presigned URL
    4. Creates a test ingest event

    Use this command to debug setup or code issues.

    Examples:

        # Full connectivity check
        ingest check -c config.yaml

        # Only check authentication
        ingest check -c config.yaml --auth-only

        # Check auth and upload, skip ingest
        ingest check -c config.yaml --skip-ingest
    """
    import json
    import tempfile
    import time
    import uuid
    from datetime import datetime, timezone
    from pathlib import Path

    from ingest_cli.api.auth import create_auth_client
    from ingest_cli.api.ingestion import create_ingestion_client
    from ingest_cli.models.annotations import (
        CreatedByAnnotation,
        DateCreatedAnnotation,
        DateModifiedAnnotation,
        ModifiedByAnnotation,
        NameAnnotation,
        TypeAnnotation,
    )
    from ingest_cli.models.event import CreateOrUpdateEvent
    from ingest_cli.models.file import FileProperty

    # Resolve config path: command option > parent group option > default file
    config_path = config_override or ctx.obj.get("config")
    if not config_path:
        # Check if default config.yaml exists
        default_config = Path("config.yaml")
        if default_config.exists():
            config_path = str(default_config)

    verbose = ctx.obj.get("verbose", False)

    # Force verbose for check command - setup detailed logging
    if not verbose:
        setup_logging(True)  # Always verbose for check

    logger = logging.getLogger(__name__)

    click.echo()
    click.echo(click.style("=== HxAI Ingestion API Connectivity Check ===", fg="cyan", bold=True))
    click.echo()

    # Track overall status
    steps_completed = 0
    total_steps = 1 if auth_only else (2 if skip_ingest else 3)

    # ===== Step 1: Configuration =====
    step_header = click.style(f"Step 1/{total_steps}:", fg="yellow", bold=True)
    click.echo(f"{step_header} Loading configuration")
    click.echo(f"  Config file: {config_path}")

    if not config_path:
        click.echo(click.style("  ✗ No configuration file specified", fg="red"), err=True)
        click.echo("  Use --config option or set INGEST_CONFIG environment variable.", err=True)
        ctx.exit(1)

    try:
        settings = load_config(config_path)
        click.echo(click.style("  ✓ Configuration loaded successfully", fg="green"))

        # Show config summary (redacted)
        click.echo()
        click.echo("  Configuration Summary:")
        click.echo(f"    Auth endpoint:    {settings.auth_endpoint}")
        click.echo(f"    Ingest endpoint:  {settings.ingest_endpoint}")
        click.echo(f"    Environment ID:   {settings.environment_id}")
        click.echo(f"    Source ID:        {settings.source_id}")
        click.echo(f"    Client ID:        {settings.client_id[:8]}...{settings.client_id[-4:]}")
        click.echo(f"    Client secret:    {'*' * 20}")
        click.echo()

    except ConfigurationError as e:
        click.echo(click.style(f"  ✗ Configuration error: {e}", fg="red"), err=True)
        ctx.exit(1)

    # ===== Step 2: Authentication =====
    step_header = click.style(f"Step 2/{total_steps}:", fg="yellow", bold=True)
    click.echo(f"{step_header} Testing authentication")

    click.echo("  Creating auth client...")
    click.echo(f"    Token endpoint: {settings.auth_endpoint}")

    try:
        auth_client = create_auth_client(settings)
    except Exception as e:
        click.echo(click.style(f"  ✗ Failed to create auth client: {e}", fg="red"), err=True)
        logger.exception("Auth client creation failed")
        ctx.exit(1)

    click.echo(click.style("  ✓ Auth client created", fg="green"))

    click.echo("  Fetching OAuth2 token from auth server...")
    start_time = time.time()

    try:
        token = auth_client.get_token()
        elapsed = time.time() - start_time

        click.echo(click.style("  ✓ Valid OAuth2 token received!", fg="green"))
        click.echo()
        click.echo("  Token Details:")
        click.echo(f"    Token prefix:   {token[:20]}...")
        click.echo(f"    Token length:   {len(token)} characters")
        click.echo(f"    Request time:   {elapsed:.3f}s")

        # Show token expiry if available
        if auth_client._token:
            click.echo(f"    Expires at:     {auth_client._token.expires_at.isoformat()}")

        steps_completed += 1
        click.echo()
        click.echo(click.style("  Authentication: SUCCESS", fg="green", bold=True))
        click.echo()

    except Exception as e:
        elapsed = time.time() - start_time
        click.echo(click.style(f"  ✗ Token request failed ({elapsed:.3f}s)", fg="red"), err=True)
        click.echo()
        click.echo("  Error Details:")
        click.echo(f"    Type:    {type(e).__name__}")
        click.echo(f"    Message: {e}")
        logger.exception("Token request failed")
        click.echo()
        click.echo(click.style("  Authentication: FAILED", fg="red", bold=True))
        ctx.exit(1)

    if auth_only:
        click.echo()
        click.echo(click.style("=== Check Complete (auth only) ===", fg="green", bold=True))
        click.echo(f"  Steps completed: {steps_completed}/{total_steps}")
        return

    # ===== Step 3: File Upload =====
    step_header = click.style(f"Step 3/{total_steps}:", fg="yellow", bold=True)
    click.echo(f"{step_header} Testing file upload")

    try:
        click.echo("  Creating ingestion client...")
        click.echo(f"    API endpoint:    {settings.ingest_endpoint}")
        click.echo(f"    Environment ID:  {settings.environment_id}")
        click.echo(f"    Source ID:       {settings.source_id}")

        ingestion_client = create_ingestion_client(settings, auth_client)
        click.echo(click.style("  ✓ Ingestion client created", fg="green"))
        click.echo()

        # Create a temporary test file
        test_id = str(uuid.uuid4())[:8]
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            prefix="ingest-cli-test-",
            delete=False,
        ) as tmp:
            ts = datetime.now(timezone.utc).isoformat()
            test_content = f"ingest-cli connectivity test\nTest ID: {test_id}\nTimestamp: {ts}\n"
            tmp.write(test_content)
            tmp_path = Path(tmp.name)

        click.echo(f"  Created test file: {tmp_path}")
        click.echo(f"    Size: {tmp_path.stat().st_size} bytes")
        click.echo(f"    Content: {repr(test_content[:50])}...")
        click.echo()

        # Request presigned URL
        click.echo("  Requesting presigned URL...")
        start_time = time.time()

        try:
            presigned_urls = ingestion_client.get_presigned_urls(count=1)
            elapsed = time.time() - start_time

            click.echo(click.style("  ✓ Presigned URL received", fg="green"))
            presigned_url = presigned_urls[0]
            click.echo(f"    Object key: {presigned_url.object_key}")
            click.echo(f"    URL prefix: {presigned_url.url[:60]}...")
            click.echo(f"    Request time: {elapsed:.3f}s")
            click.echo()

        except Exception as e:
            elapsed = time.time() - start_time
            err_msg = f"  ✗ Presigned URL request failed ({elapsed:.3f}s)"
            click.echo(click.style(err_msg, fg="red"), err=True)
            click.echo()
            click.echo("  Error Details:")
            click.echo(f"    Type:    {type(e).__name__}")
            click.echo(f"    Message: {e}")
            logger.exception("Presigned URL request failed")
            ctx.exit(1)

        # Upload file
        click.echo("  Uploading test file...")
        start_time = time.time()

        try:
            upload_result = ingestion_client.upload_file(presigned_url, tmp_path)
            elapsed = time.time() - start_time

            click.echo(click.style("  ✓ File uploaded successfully", fg="green"))
            click.echo(f"    Object key:   {upload_result.object_key}")
            click.echo(f"    Content type: {upload_result.content_type}")
            click.echo(f"    Size:         {upload_result.size_bytes} bytes")
            click.echo(f"    Upload time:  {elapsed:.3f}s")
            click.echo()

        except Exception as e:
            elapsed = time.time() - start_time
            click.echo(click.style(f"  ✗ File upload failed ({elapsed:.3f}s)", fg="red"), err=True)
            click.echo()
            click.echo("  Error Details:")
            click.echo(f"    Type:    {type(e).__name__}")
            click.echo(f"    Message: {e}")
            logger.exception("File upload failed")
            ctx.exit(1)

        finally:
            # Cleanup temp file
            try:
                tmp_path.unlink()
                click.echo(f"  Cleaned up temp file: {tmp_path}")
            except Exception:
                pass

        steps_completed += 1

    except Exception as e:
        click.echo(click.style(f"  ✗ Upload test failed: {e}", fg="red"), err=True)
        logger.exception("Upload test failed")
        ctx.exit(1)

    if skip_ingest:
        click.echo()
        click.echo(click.style("=== Check Complete (skip ingest) ===", fg="green", bold=True))
        click.echo(f"  Steps completed: {steps_completed}/{total_steps}")
        return

    # ===== Step 4: Send Ingest Event =====
    step_header = click.style(f"Step 4/{total_steps}:", fg="yellow", bold=True)
    click.echo(f"{step_header} Testing document ingestion")

    try:
        # Build a test document event
        now = datetime.now(timezone.utc)
        timestamp_ms = int(now.timestamp() * 1000)
        test_object_id = f"ingest-cli-test-{test_id}"

        click.echo("  Building test document event...")
        click.echo(f"    Object ID:   {test_object_id}")
        click.echo(f"    Source ID:   {settings.source_id}")
        click.echo(f"    Timestamp:   {timestamp_ms}")
        click.echo()

        # Create event with required annotations and file reference
        properties: dict[str, any] = {  # type: ignore[valid-type]
            "name": NameAnnotation(value=f"Test Document {test_id}"),
            "type": TypeAnnotation(value="TestDocument"),
            "dateCreated": DateCreatedAnnotation(value=now.strftime("%Y-%m-%dT%H:%M:%S.000Z")),
            "createdBy": CreatedByAnnotation(value="ingest-cli-check"),
            "dateModified": DateModifiedAnnotation(value=now.strftime("%Y-%m-%dT%H:%M:%S.000Z")),
            "modifiedBy": ModifiedByAnnotation(value="ingest-cli-check"),
            "file": FileProperty.with_upload(
                upload_id=upload_result.object_key,
                content_type=upload_result.content_type,
                size=upload_result.size_bytes,
                name="ingest-cli-test.txt",
            ),
        }

        event = CreateOrUpdateEvent(
            objectId=test_object_id,
            sourceId=settings.source_id,
            sourceTimestamp=timestamp_ms,
            properties=properties,
        )

        # Show event JSON
        event_data = event.model_dump(by_alias=True, exclude_none=True)
        click.echo("  Event payload (truncated):")
        event_json = json.dumps(event_data, indent=2, default=str)
        # Show first 500 chars
        if len(event_json) > 500:
            click.echo(f"    {event_json[:500]}...")
        else:
            click.echo(f"    {event_json}")
        click.echo()

        # Send event
        click.echo("  Sending ingestion event...")
        start_time = time.time()

        try:
            response = ingestion_client.send_events([event])
            elapsed = time.time() - start_time

            click.echo(click.style("  ✓ Event sent successfully", fg="green"))
            click.echo(f"    Success:          {response.success}")
            click.echo(f"    Events processed: {response.events_processed}")
            click.echo(f"    Request time:     {elapsed:.3f}s")

            if response.errors:
                click.echo(click.style("    Warnings/Errors:", fg="yellow"))
                for err in response.errors:
                    click.echo(f"      - {err}")

            click.echo()

        except Exception as e:
            elapsed = time.time() - start_time
            click.echo(click.style(f"  ✗ Event send failed ({elapsed:.3f}s)", fg="red"), err=True)
            click.echo()
            click.echo("  Error Details:")
            click.echo(f"    Type:    {type(e).__name__}")
            click.echo(f"    Message: {e}")

            # Show full error details if available (EventSendError)
            if hasattr(e, "error_details") and e.error_details:
                click.echo()
                click.echo(click.style("  API Response:", fg="yellow"))
                error_details = e.error_details
                # Show raw response if available
                raw_resp = error_details.pop("_raw_response", None)
                if raw_resp:
                    click.echo(f"    Raw: {raw_resp}")
                # Show parsed details
                for key, value in error_details.items():
                    click.echo(f"    {key}: {value}")

            logger.exception("Event send failed")
            ctx.exit(1)

        steps_completed += 1

    except Exception as e:
        click.echo(click.style(f"  ✗ Ingest test failed: {e}", fg="red"), err=True)
        logger.exception("Ingest test failed")
        ctx.exit(1)

    # ===== Summary =====
    click.echo()
    click.echo(click.style("=== Check Complete ===", fg="green", bold=True))
    click.echo(f"  Steps completed: {steps_completed}/{total_steps}")
    click.echo()
    click.echo("  All API endpoints are working correctly!")
    click.echo(f"  Test document ID: {test_object_id}")
    click.echo()


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
    mapper_name: str | None,
    batch_size: int | None,
    offset: int,
    limit: int | None,
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
