import os
import re
from unittest import mock
from unittest.mock import MagicMock, patch

import geodense
import pytest
from cli_test_helpers import ArgvContext
from geodense.main import check_density_cmd, main
from geodense.models import DEFAULT_MAX_SEGMENT_LENGTH, GeodenseError

USAGE_REGEX = r"^Usage: geodense (\[.+\])+ \{.*?\}"


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

    assert mock_command.call_args.kwargs["input_file"] == in_filepath
    assert mock_command.call_args.kwargs["max_segment_length"] == float(
        max_segment_length
    )  # note max_segment_length arg is parsed as int by argparse
    assert mock_command.called


def test_cli_densify_shows_outputs_error_returns_1(caplog, tmpdir, test_dir):
    with mock.patch.object(geodense.main, "densify_file") as get_mock:
        get_mock.side_effect = GeodenseError("FOOBAR")

        with pytest.raises(SystemExit) as cm, ArgvContext(
            "geodense",
            "densify",
            os.path.join(test_dir, "data", "linestrings.json"),
            os.path.join(tmpdir, "linestrings.json"),
        ):
            main()

        assert cm.type == SystemExit
        expected_exit_code = 1
        assert (
            cm.value.code == expected_exit_code
        ), f"expected densify_cmd call to exit with exit code {expected_exit_code} was {cm.value.code}"
        assert re.match(
            r"ERROR\s+geodense:main.py:.* FOOBAR\n",
            caplog.text,
        )


def test_cli_check_density_shows_outputs_error_returns_1(caplog, test_dir):
    with mock.patch.object(geodense.main, "check_density_file") as get_mock:
        get_mock.side_effect = GeodenseError("FOOBAR")

        with pytest.raises(SystemExit) as cm, ArgvContext(
            "geodense",
            "check-density",
            os.path.join(test_dir, "data", "linestrings.json"),
            "--max-segment-length",
            str(DEFAULT_MAX_SEGMENT_LENGTH),
        ):
            main()

        assert cm.type == SystemExit
        expected_exit_code = 1
        assert (
            cm.value.code == expected_exit_code
        ), f"expected check_density_cmd call to exit with exit code {expected_exit_code} was {cm.value.code}"
        assert re.match(
            r"ERROR\s+geodense:main.py:.* FOOBAR\n",
            caplog.text,
        )


def test_cli_shows_help_text_stderr_invoked_no_args(capsys):
    with pytest.raises(SystemExit), ArgvContext("geodense"):
        main()
    _, err = capsys.readouterr()
    assert re.match(USAGE_REGEX, err)


def test_cli_shows_help_text_invoked_help(capsys):
    with pytest.raises(SystemExit), ArgvContext("geodense", "--help"):
        main()
    out, _ = capsys.readouterr()
    assert re.match(USAGE_REGEX, out)
    assert "show this help message and exit" in out
