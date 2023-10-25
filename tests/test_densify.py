import json
import os
import re
import tempfile
from contextlib import nullcontext as does_not_raise
from contextlib import suppress
from unittest import mock

import pyproj
import pytest
from geodense.lib import (
    _get_intermediate_nr_points_and_segment_length,
    densify_file,
    densify_geometry_coordinates,
)
from geodense.models import DenseConfig


def test_point_raises_exception(point_feature):
    feature = json.loads(point_feature)
    c = DenseConfig(pyproj.CRS.from_epsg(28992))

    with pytest.raises(
        ValueError,
        match=r"received point geometry coordinates, instead of \(multi\)linestring",
    ):
        densify_geometry_coordinates(feature["geometry"]["coordinates"], c)


def test_linestring_d10_transformed(linestring_d10_feature):
    feature = json.loads(linestring_d10_feature)
    feature_t = json.loads(linestring_d10_feature)

    c = DenseConfig(pyproj.CRS.from_epsg(28992), 10)

    densify_geometry_coordinates(feature_t["geometry"]["coordinates"], c)

    feature_coords_length = 2
    feature_t_coord_length = 3

    assert feature != feature_t
    assert len(feature["geometry"]["coordinates"]) == feature_coords_length
    assert len(feature_t["geometry"]["coordinates"]) == feature_t_coord_length


def test_linestring_d10_no_op(linestring_d10_feature):
    feature = json.loads(linestring_d10_feature)
    feature_t = json.loads(linestring_d10_feature)
    feature_t_in_proj = json.loads(linestring_d10_feature)

    c = DenseConfig(
        pyproj.CRS.from_epsg(28992), 15
    )  # 15 since 15> sqrt(10^2+10^2) -- see linestring_feature_d10.json
    c_in_proj = DenseConfig(pyproj.CRS.from_epsg(28992), 15, True)

    densify_geometry_coordinates(feature_t["geometry"]["coordinates"], c)

    densify_geometry_coordinates(
        feature_t_in_proj["geometry"]["coordinates"], c_in_proj
    )

    feature_coords_length = 2

    assert feature != feature_t
    assert len(feature_t["geometry"]["coordinates"]) == feature_coords_length
    assert len(feature_t_in_proj["geometry"]["coordinates"]) == feature_coords_length


def test_linestring_transformed(linestring_feature):
    feature = json.loads(linestring_feature)
    feature_t = json.loads(linestring_feature)
    c = DenseConfig(pyproj.CRS.from_epsg(28992), 1000)
    densify_geometry_coordinates(feature_t["geometry"]["coordinates"], c)

    feature_coords_length = 2
    feature_t_coord_length = 12

    assert feature != feature_t
    assert len(feature["geometry"]["coordinates"]) == feature_coords_length
    assert len(feature_t["geometry"]["coordinates"]) == feature_t_coord_length


def test_densify_3d_source_projection(linestring_3d_feature):
    feature_t = json.loads(linestring_3d_feature)
    c = DenseConfig(pyproj.CRS.from_epsg(7415), 1000, True)

    result = densify_geometry_coordinates(feature_t["geometry"]["coordinates"], c)

    for i, (_, _, h) in enumerate(result):
        assert h == (
            i * 10
        ), f"height is not linear interpolated with increments of 10 - height: {h}, expected height: {i*10}"


def test_densify_3d(linestring_3d_feature):
    feature_t = json.loads(linestring_3d_feature)

    c = DenseConfig(pyproj.CRS.from_epsg(7415), 1000)

    result = densify_geometry_coordinates(feature_t["geometry"]["coordinates"], c)

    for i, (_, _, h) in enumerate(result):
        assert h == (
            i * 10
        ), f"height is not linear interpolated with increments of 10 - height: {h}, expected height: {i*10}"


def test_polygon_with_hole_transformed(polygon_feature_with_holes):
    feature = json.loads(polygon_feature_with_holes)
    feature_t = json.loads(polygon_feature_with_holes)

    c = DenseConfig(pyproj.CRS.from_epsg(28992), 1000)
    densify_geometry_coordinates(feature_t["geometry"]["coordinates"], c)
    assert feature != feature_t


def test_linestring_transformed_source_proj(linestring_feature):
    feature = json.loads(linestring_feature)
    feature_t = json.loads(linestring_feature)

    c = DenseConfig(pyproj.CRS.from_epsg(28992), 1000, True)

    densify_geometry_coordinates(feature_t["geometry"]["coordinates"], c)
    feature_coords_length = 2
    feature_t_coord_length = 12

    assert feature != feature_t
    assert len(feature["geometry"]["coordinates"]) == feature_coords_length
    assert len(feature_t["geometry"]["coordinates"]) == feature_t_coord_length


def test_maxlinesegment_param(linestring_feature):
    feature_200 = json.loads(linestring_feature)
    feature_1000 = json.loads(linestring_feature)

    c_200 = DenseConfig(pyproj.CRS.from_epsg(28992), 200, False)
    c_1000 = DenseConfig(pyproj.CRS.from_epsg(28992), 1000, False)

    densify_geometry_coordinates(feature_200["geometry"]["coordinates"], c_200)
    densify_geometry_coordinates(feature_1000["geometry"]["coordinates"], c_1000)
    assert len(feature_200["geometry"]["coordinates"]) > len(
        feature_1000["geometry"]["coordinates"]
    )


def test_get_intermediate_nr_points_and_segment_length():
    # test distance > max_segment_length
    data = [
        [(1000, 100), (9, 100.0)],
        [(1000, 300), (3, 250.0)],
    ]
    for value in data:
        result = _get_intermediate_nr_points_and_segment_length(*value[0])
        assert result == value[1]

    # test distance < max_segment_length
    with pytest.raises(
        ValueError,
        match=r"max_segment_length \(.+\) cannot be bigger or equal than dist \(.+\)",
    ):
        _get_intermediate_nr_points_and_segment_length(100, 1000)

    # test distance == max_segment_length
    with pytest.raises(
        ValueError,
        match=r"max_segment_length \(.+\) cannot be bigger or equal than dist \(.+\)",
    ):
        _get_intermediate_nr_points_and_segment_length(1000, 1000)


def test_densify_file(test_dir):
    in_file = "linestrings.json"
    out_file = os.path.join(tempfile.mkdtemp(), in_file)
    densify_file(os.path.join(test_dir, "data", in_file), out_file)
    assert os.path.exists(out_file)


@pytest.mark.parametrize(
    ("input_file", "output_file", "expectation"),
    [
        (
            "linestrings.foobar",
            "linestrings_out.foobar",
            pytest.raises(
                ValueError,
                match=r"Argument input_file .*linestrings.foobar is of an unsupported fileformat, see list-formats for list of supported file formats",
            ),
        ),
        (
            "linestrings.json",
            "linestrings.gpkg",
            pytest.raises(
                ValueError,
                match=r"Extension of input_file and output_file need to match, was input_file: .json, output_file: .gpkg",
            ),
        ),
        ("linestrings.json", "linestrings.json", does_not_raise()),
    ],
)
def test_densify_file_unsupported_file_format(
    test_dir, input_file, output_file, expectation
):
    input_file = os.path.join(test_dir, "data", input_file)
    output_file = os.path.join(tempfile.mkdtemp(), output_file)
    with expectation:
        assert densify_file(input_file, output_file) is None


def test_densify_file_negative(tmpdir, test_dir):
    in_file = "linestrings.json"
    out_file = os.path.join(tmpdir, in_file)
    densify_file(os.path.join(test_dir, "data", in_file), out_file, None, -10000)
    assert os.path.exists(out_file)


def test_densify_file_exception(tmpdir, test_dir):
    with mock.patch.object(pyproj.Geod, "fwd_intermediate") as get_mock:
        get_mock.side_effect = ValueError("FOOBAR")
        in_file = "linestrings.json"
        out_file = os.path.join(tmpdir, in_file)
        with pytest.raises(
            ValueError,
            match=r"Unexpected error occured while processing feature \[0\]",
        ):
            densify_file(os.path.join(test_dir, "data", in_file), out_file, None, 10000)


def test_densify_file_in_proj_exc(tmpdir, test_dir):
    in_file = "linestrings-4258.json"
    out_file = os.path.join(tmpdir, in_file)

    with pytest.raises(
        ValueError,
        match=(
            r"densify_in_projection can only be used with projected coordinates "
            r"reference systems, crs .+ is a geographic crs"
        ),
    ):
        densify_file(
            os.path.join(test_dir, "data", in_file), out_file, None, None, True
        )


def test_densify_file_input_file_does_not_exist(tmpdir, test_dir):
    input_file = os.path.join(test_dir, "foobar.json")
    output_file = os.path.join(tmpdir, "foobar.json")

    with pytest.raises(
        ValueError,
        match=(r"input_file .*foobar.json does not exist"),
    ):
        assert isinstance(densify_file(input_file, output_file))


def test_densify_file_output_dir_does_not_exist_raises(test_dir):
    input_file = os.path.join(test_dir, "data", "linestrings.json")
    output_file = os.path.join(test_dir, "foobar", "foobar.json")

    with pytest.raises(
        ValueError,
        match=(r"target directory of output_file .*foobar.json does not exist"),
    ):
        assert isinstance(densify_file(input_file, output_file))


def test_densify_file_input_and_output_equal_raises(test_dir):
    input_file = os.path.join(test_dir, "data", "linestrings.json")
    output_file = os.path.join(test_dir, "data", "linestrings.json")

    with pytest.raises(
        ValueError,
        match=(
            r"input_file and output_file arguments must be different, input_file: .*linestrings.json, output_file: .*linestrings.json"
        ),
    ):
        assert isinstance(densify_file(input_file, output_file))


def test_densify_file_output_file_exists_raises(test_dir):
    input_file = os.path.join(test_dir, "data", "linestrings.json")
    output_file = os.path.join(
        test_dir, "data", "linestrings-4258.json"
    )  # use existing file to check if exception is raised

    with pytest.raises(
        ValueError,
        match=(r"output_file .*linestrings-4258.json already exists"),
    ):
        densify_file(input_file, output_file)


def test_support_geometry_collection(tmpdir, test_dir):
    input_file = os.path.join(test_dir, "data", "feature-geometry-collection.json")
    output_file = os.path.join(tmpdir, "geometry.json")
    densify_file(input_file, output_file, None, None, False, False, "EPSG:28992")


def test_densify_file_invalid_crs_raises(test_dir, tmpdir):
    input_file = os.path.join(test_dir, "data", "feature-geometry-collection.json")
    output_file = os.path.join(tmpdir, "geometry.json")
    with pytest.raises(
        pyproj.exceptions.CRSError,
        match=(
            r"Invalid projection: EPSG:9999999: \(Internal Proj Error: proj_create: crs not found\)"
        ),
    ):
        densify_file(input_file, output_file, None, None, False, False, "EPSG:9999999")


def test_densify_file_json_no_crs_outputs_message_stderr(capsys, test_dir, tmpdir):
    input_file = os.path.join(test_dir, "data", "geometry.json")
    output_file = os.path.join(tmpdir, "geometry.json")
    with suppress(ValueError):
        densify_file(input_file, output_file)
    _, err = capsys.readouterr()
    expected_message_std_err = r"WARNING: unable to determine source CRS for file .*geometry.json, assumed CRS is EPSG:4326\n"
    assert re.match(
        expected_message_std_err, err
    ), f"stderr expected message is: {expected_message_std_err}, actual message was: {err}"
