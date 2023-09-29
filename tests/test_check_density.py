import json
import os
from contextlib import nullcontext as does_not_raise
from unittest import mock

import pytest
from geodense.lib import (
    TRANSFORM_CRS,
    _get_transformer,
    check_density_file,
    check_density_geometry_coordinates,
)


def test_check_density(test_dir):
    report = check_density_file(
        os.path.join(test_dir, "data/linestrings.json"), 1000, "lijnen"
    )
    assert len(report) > 0, f"expected len(report) to >0, was {len(report)}"


def test_check_density_not_pass(linestring_feature):
    feature_200 = json.loads(linestring_feature)
    result = []
    transformer = _get_transformer("EPSG:28992", TRANSFORM_CRS)
    check_density_geometry_coordinates(
        feature_200["geometry"]["coordinates"], transformer, 200, result
    )
    assert len(result) > 0


def test_check_density_pass_linestring(linestring_feature_5000):
    feature = json.loads(linestring_feature_5000)
    result = []
    transformer = _get_transformer("EPSG:28992", TRANSFORM_CRS)
    check_density_geometry_coordinates(
        feature["geometry"]["coordinates"], transformer, 5000, result
    )
    assert len(result) == 0


def test_check_density_polygon_with_hole_not_pass(polygon_feature_with_holes):
    feature = json.loads(polygon_feature_with_holes)
    result = []
    transformer = _get_transformer("EPSG:28992", TRANSFORM_CRS)

    check_density_geometry_coordinates(
        feature["geometry"]["coordinates"], transformer, 5000, result
    )
    assert len(result) > 0


@pytest.mark.parametrize(
    ("input_file", "expectation"),
    [
        (
            "linestrings.foobar",
            pytest.raises(
                ValueError,
                match=r"Argument input_file .*linestrings.foobar is of an unsupported fileformat, see list-formats for list of supported file formats",
            ),
        ),
        ("linestrings.json", does_not_raise()),
    ],
)
def test_density_check_geospatial_file_unsupported_file_format(
    test_dir, input_file, expectation
):
    input_file = os.path.join(test_dir, "data", input_file)
    with expectation:
        assert isinstance(check_density_file(input_file, 1000, "lijnen"), list)


def test_check_density_3d(linestring_3d_feature):
    feature_t = json.loads(linestring_3d_feature)

    src_crs = "EPSG:7415"
    transformer = _get_transformer(src_crs, TRANSFORM_CRS)
    result = []

    check_density_geometry_coordinates(
        feature_t["geometry"]["coordinates"], transformer, 500, result
    )

    assert len(result) > 0


@mock.patch("pyproj.Geod.inv", mock.MagicMock(return_value=(None, None, float("NaN"))))
def test_densify_geospatial_file_exception(linestring_3d_feature):
    feature_t = json.loads(linestring_3d_feature)

    src_crs = "EPSG:7415"
    transformer = _get_transformer(src_crs, TRANSFORM_CRS)
    result = []

    with pytest.raises(
        ValueError,
        match=r"unable to calculate geodesic distance, result: nan, expected: floating-point number",
    ):
        check_density_geometry_coordinates(
            feature_t["geometry"]["coordinates"], transformer, 500, result
        )
