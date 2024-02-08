import re
import tempfile

import pytest
from cli_test_helpers import ArgvContext
from geodense.main import main


# @pytest.mark.usefixtures("clear_log") # see https://github.com/pytest-dev/pytest/issues/5502#issuecomment-1509988433
def test_3d_coords_2d_crs_raises_warning(test_dir, capsys):
    in_file = "linestring_3d_feature.json"
    in_filepath = f"{test_dir}/data/{in_file}"
    max_segment_length = "5000"
    with (
        ArgvContext(
            "geodense",
            "check-density",
            in_filepath,
            "--max-segment-length",
            max_segment_length,
            "--src-crs",
            "EPSG:28992",
        ),
        pytest.raises(SystemExit),
    ):
        main()
    _, err = capsys.readouterr()
    assert (
        err
        == "[WARNING] src_crs is 2D while input data contains geometries with 3D coordinates\n"
    )


@pytest.mark.parametrize(
    ("input_file", "src_crs", "expected"),
    [
        (
            "geometry-4326-no-crs.json",
            None,
            r"\[WARNING\] unable to determine source CRS for file .*, assumed CRS is OGC:CRS84\n",
        ),
        ("linestring_feature.json", "EPSG:7415", r""),
    ],
)
def test_2d_coords_3d_crs_raises_no_warning(
    test_dir, capsys, input_file, src_crs, expected
):
    in_filepath = f"{test_dir}/data/{input_file}"
    max_segment_length = "10000"
    args = [
        "geodense",
        "check-density",
        in_filepath,
        "--max-segment-length",
        max_segment_length,
    ]
    if src_crs is not None:
        args.extend(["--src-crs", src_crs])
    with ArgvContext(*args), pytest.raises(SystemExit):
        main()
    _out, err = capsys.readouterr()
    assert re.match(expected, err)


@pytest.mark.parametrize(
    ("input_file", "src_crs", "expected"),
    [
        (
            "geometry-4326-no-crs.json",
            None,
            r"\[WARNING\] unable to determine source CRS for file .*, assumed CRS is OGC:CRS84\n",
        ),
        ("linestring_feature.json", "EPSG:7415", r""),
    ],
)
def test_2d_coords_3d_crs_raises_no_warning_densify(
    test_dir, capsys, input_file, src_crs, expected
):
    in_filepath = f"{test_dir}/data/{input_file}"
    max_segment_length = "5000"
    out_dir = tempfile.mkdtemp()
    out_filepath = f"{out_dir}/{input_file}"
    args = [
        "geodense",
        "densify",
        "--max-segment-length",
        max_segment_length,
        in_filepath,
        out_filepath,
    ]
    if src_crs is not None:
        args.extend(["--src-crs", src_crs])
    with ArgvContext(*args):
        main()
    _out, err = capsys.readouterr()
    assert re.match(expected, err)
