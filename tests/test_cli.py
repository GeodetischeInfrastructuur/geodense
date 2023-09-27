import os
import re
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from cli_test_helpers import ArgvContext
from geodense.main import check_density_cmd, densify_cmd, list_formats_cmd, main


@patch("geodense.main.list_formats_cmd")
def test_cli_list_formats_cmd(mock_command):
    with ArgvContext("geodense", "list-formats"):
        main()

    assert mock_command.called


def test_cli_list_formats_cmd_shows_list(capsys):
    with ArgvContext("geodense", "list-formats"), pytest.raises(SystemExit):
        main()
    out, _ = capsys.readouterr()
    message = "No tabular output detected for list-formats command"
    assert re.match(r"^Name\s+\|\sExtension", out), message


@patch("geodense.main.SUPPORTED_FILE_FORMATS", {"FOOBAR": ".foo"})
def test_cli_list_formats_raises_exception():
    with pytest.raises(
        KeyError,
        match=r"The following format\(s\) are not supported by your fiona installation: FOOBAR",
    ):
        list_formats_cmd()


@patch("geodense.main.densify_cmd")
def test_cli_densify_cmd(mock_command, test_dir):
    in_file = "linestrings.json"
    in_filepath = f"{test_dir}/data/{in_file}"
    out_filepath = os.path.join(tempfile.mkdtemp(), in_file)

    max_segment_length = "5000"
    with ArgvContext(
        "geodense",
        "densify",
        in_filepath,
        out_filepath,
        "--max-segment-length",
        max_segment_length,
        "--in-projection",
    ):
        main()

    # TODO: test all CLI options
    assert mock_command.call_args.kwargs["input_file"] == in_filepath
    assert mock_command.call_args.kwargs["output_file"] == out_filepath
    assert mock_command.call_args.kwargs["max_segment_length"] == float(
        max_segment_length
    )  # note max_segment_length arg is parsed as int by argparse
    assert mock_command.call_args.kwargs["in_projection"] is True
    assert mock_command.called


@patch("geodense.main.check_density", MagicMock(return_value=[]))
def test_check_density_cmd_exit_0(test_dir):
    input_file = os.path.join(test_dir, "data", "polygons.json")
    with pytest.raises(SystemExit) as cm:
        check_density_cmd(input_file, 20000, "")
    assert cm.type == SystemExit
    expected_exit_code = 0
    assert (
        cm.value.code == expected_exit_code
    ), f"expected check_density_cmd call to exit with exit code {expected_exit_code} was {cm.value.code}"


@patch("geodense.main.check_density", MagicMock(return_value=[([0, 1], 100.1239123)]))
def test_check_density_cmd_exit_1(test_dir):
    input_file = os.path.join(test_dir, "data", "polygons.json")
    with pytest.raises(SystemExit) as cm:
        check_density_cmd(input_file, 20000, "")
    assert cm.type == SystemExit
    expected_exit_code = 1
    assert (
        cm.value.code == expected_exit_code
    ), f"expected check_density_cmd call to exit with exit code {expected_exit_code} was {cm.value.code}"


@patch("geodense.main.check_density_cmd")
def test_cli_check_density_cmd(mock_command, test_dir):
    in_file = "linestrings.json"
    in_filepath = f"{test_dir}/data/{in_file}"

    max_segment_length = "5000"
    with ArgvContext(
        "geodense",
        "check-density",
        in_filepath,
        "--max-segment-length",
        max_segment_length,
    ):
        main()

    # TODO: test all CLI options
    assert mock_command.call_args.kwargs["input_file"] == in_filepath
    assert mock_command.call_args.kwargs["max_segment_length"] == float(
        max_segment_length
    )  # note max_segment_length arg is parsed as int by argparse
    assert mock_command.called


def test_cli_densify_raises_exception(test_dir):
    with pytest.raises(
        ValueError,
        match=r"Unsupported GeometryType .+, supported GeometryTypes are: .+",
    ):
        densify_cmd(
            os.path.join(test_dir, "data", "linestrings_3d.json"),
            os.path.join(test_dir, "data-out", "linestrings_3d.json"),
            1000,
            "",
            False,
        )


USAGE_STRING = "Usage: geodense [-h] {list-formats,densify,check-density} ..."


def test_cli_shows_help_text_invoked_no_args(capsys):
    sys.argv = [""]
    with pytest.raises(SystemExit):
        main()
    out, _ = capsys.readouterr()
    assert out.startswith(USAGE_STRING)
    assert "show this help message and exit" in out


def test_cli_shows_help_text_invoked_help(capsys):
    sys.argv = ["--help"]
    with pytest.raises(SystemExit):
        main()
    out, _ = capsys.readouterr()
    assert out.startswith(USAGE_STRING)
    assert "show this help message and exit" in out
