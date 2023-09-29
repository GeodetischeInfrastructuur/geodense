import os
import re
import sys
from unittest import mock
from unittest.mock import MagicMock, patch

import geodense
import pytest
from cli_test_helpers import ArgvContext
from geodense.lib import DEFAULT_MAX_SEGMENT_LENGTH
from geodense.main import check_density_cmd, densify_cmd, list_formats_cmd, main

USAGE_STRING = "Usage: geodense [-h] {list-formats,densify,check-density} ..."


@patch("geodense.main.list_formats_cmd")
def test_cli_list_formats_cmd(mock_command):
    """Tests if main.list_formats_cmd is called when invoking `geodense list-formats`"""
    with ArgvContext("geodense", "list-formats"):
        main()
    assert mock_command.called


def test_cli_list_formats_cmd_shows_list(capsys):
    """Tests if `geodense list-formats` is outputting tabular list of supported file formats and their extensions"""
    with ArgvContext("geodense", "list-formats"), pytest.raises(SystemExit):
        main()
    out, _ = capsys.readouterr()
    message = "No tabular output detected for list-formats command"
    assert re.match(r"^Name\s+\|\sExtension", out), message


@patch("geodense.main.SUPPORTED_FILE_FORMATS", {"FOOBAR": ".foo"})
def test_cli_list_formats_shows_error_message(capsys):
    """Tests if `geodense list-formats` shows an error message in case supported file formats of fiona do not match with geodense"""
    with pytest.raises(SystemExit) as cm:
        list_formats_cmd()
    assert cm.type == SystemExit
    expected_exit_code = 1
    _, err = capsys.readouterr()
    assert (
        cm.value.code == expected_exit_code
    ), f"expected list_formats_cmd call to exit with exit code {expected_exit_code} was {cm.value.code}"
    assert re.match(
        r"ERROR: The following format\(s\) are not supported by your fiona installation: FOOBAR",
        err,
    )


@patch("geodense.main.densify_cmd")
def test_cli_densify_cmd(mock_command, tmpdir, test_dir):
    in_file = "linestrings.json"
    in_filepath = f"{test_dir}/data/{in_file}"
    out_filepath = os.path.join(tmpdir, in_file)

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


@patch("geodense.main.check_density_file", MagicMock(return_value=[]))
def test_check_density_cmd_exit_0(test_dir):
    input_file = os.path.join(test_dir, "data", "polygons.json")
    with pytest.raises(SystemExit) as cm:
        check_density_cmd(input_file, 20000, "")
    assert cm.type == SystemExit
    expected_exit_code = 0
    assert (
        cm.value.code == expected_exit_code
    ), f"expected check_density_cmd call to exit with exit code {expected_exit_code} was {cm.value.code}"


@patch(
    "geodense.main.check_density_file", MagicMock(return_value=[([0, 1], 100.1239123)])
)
def test_check_density_cmd_exit_1_when_result_not_ok(test_dir):
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


def test_cli_densify_shows_outputs_error_returns_1(capsys, tmpdir, test_dir):
    with mock.patch.object(geodense.main, "densify_geospatial_file") as get_mock:
        get_mock.side_effect = ValueError("FOOBAR")

        with pytest.raises(SystemExit) as cm:
            densify_cmd(
                os.path.join(test_dir, "data", "linestrings.json"),
                os.path.join(tmpdir, "linestrings.json"),
            )
        assert cm.type == SystemExit
        expected_exit_code = 1
        _, err = capsys.readouterr()
        assert (
            cm.value.code == expected_exit_code
        ), f"expected densify_cmd call to exit with exit code {expected_exit_code} was {cm.value.code}"
        assert re.match(
            r"ERROR: FOOBAR\n",
            err,
        )


def test_cli_check_density_shows_outputs_error_returns_1(capsys, test_dir):
    with mock.patch.object(geodense.main, "check_density_file") as get_mock:
        get_mock.side_effect = ValueError("FOOBAR")

        with pytest.raises(SystemExit) as cm:
            check_density_cmd(
                os.path.join(test_dir, "data", "linestrings.json"),
                DEFAULT_MAX_SEGMENT_LENGTH,
                "",
            )
        assert cm.type == SystemExit
        expected_exit_code = 1
        _, err = capsys.readouterr()
        assert (
            cm.value.code == expected_exit_code
        ), f"expected check_density_cmd call to exit with exit code {expected_exit_code} was {cm.value.code}"
        assert re.match(
            r"ERROR: FOOBAR\n",
            err,
        )


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
