import json
import os

from geodense.lib import check_density, check_density_geometry_coordinates


def test_check_density(test_dir):
    report = check_density(
        os.path.join(test_dir, "data/linestrings.json"), 1000, "lijnen"
    )
    assert len(report) > 0


def test_check_density_not_pass(linestring_feature):
    feature_200 = json.loads(linestring_feature)
    result = []
    check_density_geometry_coordinates(
        feature_200["geometry"]["coordinates"], "EPSG:28992", 200, result
    )
    assert len(result) > 0


def test_check_density_pass_linestring(linestring_feature_5000):
    feature = json.loads(linestring_feature_5000)
    result = []
    check_density_geometry_coordinates(
        feature["geometry"]["coordinates"], "EPSG:28992", 5000, result
    )
    assert len(result) == 0


def test_check_density_polygon_with_hole_not_pass(polygon_feature_with_holes):
    feature = json.loads(polygon_feature_with_holes)
    result = []
    check_density_geometry_coordinates(
        feature["geometry"]["coordinates"], "EPSG:28992", 5000, result
    )
    assert len(result) > 0
