"""Tests for the main CLI module."""

from click.testing import CliRunner

from ingest_cli import __version__
from ingest_cli.cli.main import cli


class TestCli:
    """Test suite for CLI entry point."""

    def test_cli_help(self) -> None:
        """Test that --help displays usage information."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Ingest CLI" in result.output
        assert "Import documents to HxAI Ingestion API" in result.output

    def test_cli_version(self) -> None:
        """Test that --version displays version information."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_version_command(self) -> None:
        """Test the version command."""
        runner = CliRunner()
        result = runner.invoke(cli, ["version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_readers_command(self) -> None:
        """Test the readers command lists available readers."""
        runner = CliRunner()
        result = runner.invoke(cli, ["readers"])
        assert result.exit_code == 0
        assert "Available readers:" in result.output
        assert "csv" in result.output

    def test_validate_command_no_config(self) -> None:
        """Test validate command without config file shows error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["validate"])
        assert result.exit_code == 1
        assert "No configuration file specified" in result.output

    def test_run_command_no_config(self) -> None:
        """Test run command without config file shows error."""
        runner = CliRunner()
        # Create a temporary file for input
        with runner.isolated_filesystem():
            with open("test.csv", "w") as f:
                f.write("col1,col2\nval1,val2\n")
            result = runner.invoke(cli, ["run", "-i", "test.csv"])
        assert result.exit_code == 1
        assert "No configuration file specified" in result.output

    def test_cli_verbose_flag(self) -> None:
        """Test that verbose flag is accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["-v", "--help"])
        assert result.exit_code == 0


class TestCliRunCommand:
    """Test suite for the run command."""

    def test_run_requires_input(self) -> None:
        """Test that run command requires input file."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_run_dry_run_flag(self) -> None:
        """Test that --dry-run flag is accepted."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create a valid config with all required fields (use valid UUIDs)
            config_content = """
environment_id: hxai-84fe439b-e9a0-44d0-84da-07235736707e
source_id: a52878a6-b459-4a13-bdd9-7d086f591d58
system_integration_id: 7c9e6679-7425-40de-944b-e07fc1f90ae7
client_id: test-client-id
client_secret: test-client-secret
ingest_endpoint: https://api.example.com/
auth_endpoint: https://auth.example.com/token
batch_size: 50
"""
            with open("config.yaml", "w") as f:
                f.write(config_content)
            with open("test.csv", "w") as f:
                f.write("name,file_path\ndoc1,/path/to/file1.txt\n")
            result = runner.invoke(cli, ["-c", "config.yaml", "run", "-i", "test.csv", "--dry-run"])
        assert result.exit_code == 0, f"Output: {result.output}"
        assert "DRY RUN MODE" in result.output
