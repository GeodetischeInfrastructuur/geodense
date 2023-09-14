import os
import tempfile

from cli_test_helpers import ArgvContext
from unittest.mock import patch

from geodense.main import main


@patch("geodense.main.densify_cmd")
def test_cli_densify_cmd(mock_command):
    TEST_DIR = os.path.dirname(os.path.abspath(__file__))

    in_file = "linestrings.json"
    in_filepath = f"{TEST_DIR}/data/{in_file}"
    out_filepath = os.path.join(tempfile.mkdtemp(), in_file)

    max_segment_length = "5000"
    with ArgvContext(
        "geodense",
        "densify",
        in_filepath,
        out_filepath,
        "--max-segment-length",
        max_segment_length,
    ):
        main()

    # TODO: test all CLI options
    assert mock_command.call_args.args[0].input_file == in_filepath
    assert mock_command.call_args.args[0].output_file == out_filepath
    assert mock_command.call_args.args[0].max_segment_length == int(
        max_segment_length
    )  # note max_segment_length arg is parsed as int by argparse

    assert mock_command.called


@patch("geodense.main.check_density_cmd")
def test_cli_check_density_cmd(mock_command):
    TEST_DIR = os.path.dirname(os.path.abspath(__file__))

    in_file = "linestrings.json"
    in_filepath = f"{TEST_DIR}/data/{in_file}"

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
    assert mock_command.call_args.args[0].input_file == in_filepath
    assert mock_command.call_args.args[0].max_segment_length == int(
        max_segment_length
    )  # note max_segment_length arg is parsed as int by argparse

    assert mock_command.called
