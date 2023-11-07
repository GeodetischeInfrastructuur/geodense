import json
import os
from contextlib import nullcontext as does_not_raise
from unittest import mock

import pytest
from geodense.lib import (
    check_density_file,
    check_density_geometry_coordinates,
)
from geodense.models import DenseConfig
from pyproj import CRS


def test_check_density(test_dir):
    report = check_density_file(
        os.path.join(test_dir, "data/linestrings.json"), 1000, "lijnen"
    )
    assert len(report) > 0, f"expected len(report) to >0, was {len(report)}"


def test_check_density_not_pass(linestring_feature):
    feature_200 = json.loads(linestring_feature)
    result = []
    d_conf = DenseConfig(CRS.from_epsg(28992))
    check_density_geometry_coordinates(
        feature_200["geometry"]["coordinates"], d_conf, result
    )
    assert len(result) > 0


def test_check_density_pass_linestring(linestring_feature_5000):
    feature = json.loads(linestring_feature_5000)
    result = []
    d_conf = DenseConfig(CRS.from_epsg(28992), 5000)
    check_density_geometry_coordinates(
        feature["geometry"]["coordinates"], d_conf, result
    )
    assert len(result) == 0


def test_check_density_polygon_with_hole_not_pass(polygon_feature_with_holes):
    feature = json.loads(polygon_feature_with_holes)
    result = []
    d_conf = DenseConfig(CRS.from_epsg(28992), 5000)

    check_density_geometry_coordinates(
        feature["geometry"]["coordinates"], d_conf, result
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

    d_conf = DenseConfig(CRS.from_epsg(7415), 500)

    result = []

    check_density_geometry_coordinates(
        feature_t["geometry"]["coordinates"], d_conf, result
    )

    assert len(result) > 0


@mock.patch("pyproj.Geod.inv", mock.MagicMock(return_value=(None, None, float("NaN"))))
def test_densify_file_exception(linestring_3d_feature):
    feature_t = json.loads(linestring_3d_feature)

    d_conf = DenseConfig(CRS.from_epsg(7415), 500)
    result = []

    with pytest.raises(
        ValueError,
        match=r"unable to calculate geodesic distance, result: nan, expected: floating-point number",
    ):
        check_density_geometry_coordinates(
            feature_t["geometry"]["coordinates"], d_conf, result
        )
