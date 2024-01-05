import os
from unittest import mock

import pytest
from geodense.lib import (
    check_density_file,
    check_density_geometry_coordinates,
    flatten,
)
from geodense.models import DenseConfig, GeodenseError
from geodense.types import Nested, ReportLineString
from geojson_pydantic import Feature
from pyproj import CRS


def test_check_density(test_dir):
    result, _, nr_segments = check_density_file(
        os.path.join(test_dir, "data/linestrings.json"), 100
    )
    assert not result, "expected result is False"
    assert nr_segments > 0


def test_check_density_not_pass(linestring_feature_gj):
    feature: Feature = linestring_feature_gj
    result = []
    d_conf = DenseConfig(CRS.from_epsg(28992))
    result: Nested[ReportLineString] = check_density_geometry_coordinates(
        feature.geometry.coordinates, d_conf
    )
    flat_result: list[ReportLineString] = list(flatten(result))
    assert len(flat_result) > 0


def test_check_density_pass_linestring(linestring_feature_5000_gj):
    feature: Feature = linestring_feature_5000_gj
    result = []
    d_conf = DenseConfig(CRS.from_epsg(28992), 5000)
    check_density_geometry_coordinates(feature.geometry.coordinates, d_conf)
    assert len(result) == 0


def test_check_density_polygon_with_hole_not_pass(polygon_feature_with_holes_gj):
    feature: Feature = polygon_feature_with_holes_gj

    d_conf = DenseConfig(CRS.from_epsg(28992), 5000)

    result: Nested[ReportLineString] = check_density_geometry_coordinates(
        feature.geometry.coordinates, d_conf
    )
    flat_result: list[ReportLineString] = list(flatten(result))
    assert len(flat_result) > 0


def test_check_density_3d(linestring_3d_feature_gj):
    feature_t: Feature = linestring_3d_feature_gj
    d_conf = DenseConfig(CRS.from_epsg(7415), 500)
    result: Nested[ReportLineString] = check_density_geometry_coordinates(
        feature_t.geometry.coordinates, d_conf
    )
    flat_result: list[ReportLineString] = list(flatten(result))
    assert len(flat_result) > 0


@mock.patch("pyproj.Geod.inv", mock.MagicMock(return_value=(None, None, float("NaN"))))
def test_densify_file_exception(linestring_3d_feature_gj):
    feature_t: Feature = linestring_3d_feature_gj

    d_conf = DenseConfig(CRS.from_epsg(7415), 500)

    with pytest.raises(
        GeodenseError,
        match=r"unable to calculate geodesic distance, output calculation geodesic distance: nan, expected: floating-point number",
    ):
        _: Nested[ReportLineString] = check_density_geometry_coordinates(
            feature_t.geometry.coordinates, d_conf
        )
