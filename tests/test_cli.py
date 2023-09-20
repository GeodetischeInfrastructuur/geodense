import os
import tempfile
from unittest.mock import patch

import pytest
from cli_test_helpers import ArgvContext
from geodense.main import densify_cmd, main


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
