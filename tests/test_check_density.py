import os
from contextlib import nullcontext as does_not_raise
from unittest import mock

import pytest
from geodense.lib import (
    _check_density_geometry_coordinates,
    check_density_file,
)
from geodense.models import DenseConfig, GeodenseError
from geojson_pydantic import Feature
from pyproj import CRS


def test_check_density(test_dir):
    report = check_density_file(os.path.join(test_dir, "data/linestrings.json"), 1000)
    assert len(report) > 0, f"expected len(report) to >0, was {len(report)}"


def test_check_density_not_pass(linestring_feature_gj):
    feature: Feature = linestring_feature_gj
    result = []
    d_conf = DenseConfig(CRS.from_epsg(28992))
    _check_density_geometry_coordinates(feature.geometry.coordinates, d_conf, result)
    assert len(result) > 0


def test_check_density_pass_linestring(linestring_feature_5000_gj):
    feature: Feature = linestring_feature_5000_gj
    result = []
    d_conf = DenseConfig(CRS.from_epsg(28992), 5000)
    _check_density_geometry_coordinates(feature.geometry.coordinates, d_conf, result)
    assert len(result) == 0


def test_check_density_polygon_with_hole_not_pass(polygon_feature_with_holes_gj):
    feature: Feature = polygon_feature_with_holes_gj
    result = []
    d_conf = DenseConfig(CRS.from_epsg(28992), 5000)

    _check_density_geometry_coordinates(feature.geometry.coordinates, d_conf, result)
    assert len(result) > 0


@pytest.mark.parametrize(
    ("input_file", "expectation"),
    [
        (
            "linestrings.foobar",
            pytest.raises(
                GeodenseError,
                match=r"unsupported file extension of input-file, received: .foobar, expected one of: .geojson, .json",
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
        assert isinstance(check_density_file(input_file, 1000), list)


def test_check_density_3d(linestring_3d_feature_gj):
    feature_t: Feature = linestring_3d_feature_gj

    d_conf = DenseConfig(CRS.from_epsg(7415), 500)

    result = []

    _check_density_geometry_coordinates(feature_t.geometry.coordinates, d_conf, result)

    assert len(result) > 0


@mock.patch("pyproj.Geod.inv", mock.MagicMock(return_value=(None, None, float("NaN"))))
def test_densify_file_exception(linestring_3d_feature_gj):
    feature_t: Feature = linestring_3d_feature_gj

    d_conf = DenseConfig(CRS.from_epsg(7415), 500)
    result = []

    with pytest.raises(
        GeodenseError,
        match=r"unable to calculate geodesic distance, output calculation geodesic distance: nan, expected: floating-point number",
    ):
        _check_density_geometry_coordinates(
            feature_t.geometry.coordinates, d_conf, result
        )
