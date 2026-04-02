import json

from typer.testing import CliRunner

from parsemux import __version__
from parsemux.cli.main import app

runner = CliRunner()


def test_version_command_outputs_version() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == f"parsemux {__version__}"


def test_version_flag_outputs_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == f"parsemux {__version__}"


def test_schema_output_schema_prints_parse_result_schema() -> None:
    result = runner.invoke(app, ["schema", "--output-schema"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["title"] == "ParseResult"
    assert "properties" in payload
