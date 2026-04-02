from typer.testing import CliRunner

from parsemux.cli.main import app

runner = CliRunner()


def test_detect_shows_helpful_error_for_unsupported_file_type(tmp_path) -> None:
    unsupported = tmp_path / "archive.zip"
    unsupported.write_bytes(b"zip data")

    result = runner.invoke(app, ["detect", str(unsupported)])

    assert result.exit_code == 1
    assert "Unsupported file type '.zip'." in result.stderr
    assert "Supported:" in result.stderr
