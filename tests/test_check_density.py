import json
import os

from geodense.lib import (
    TRANSFORM_CRS,
    check_density,
    check_density_geometry_coordinates,
    get_transformer,
)


def test_check_density(test_dir):
    report = check_density(
        os.path.join(test_dir, "data/linestrings.json"), 1000, "lijnen"
    )
    assert len(report) > 0, f"expected len(report) to >0, was {len(report)}"


def test_check_density_not_pass(linestring_feature):
    feature_200 = json.loads(linestring_feature)
    result = []
    transformer = get_transformer("EPSG:28992", TRANSFORM_CRS)
    check_density_geometry_coordinates(
        feature_200["geometry"]["coordinates"], transformer, 200, result
    )
    assert len(result) > 0


def test_check_density_pass_linestring(linestring_feature_5000):
    feature = json.loads(linestring_feature_5000)
    result = []
    transformer = get_transformer("EPSG:28992", TRANSFORM_CRS)
    check_density_geometry_coordinates(
        feature["geometry"]["coordinates"], transformer, 5000, result
    )
    assert len(result) == 0


def test_check_density_polygon_with_hole_not_pass(polygon_feature_with_holes):
    feature = json.loads(polygon_feature_with_holes)
    result = []
    transformer = get_transformer("EPSG:28992", TRANSFORM_CRS)

    check_density_geometry_coordinates(
        feature["geometry"]["coordinates"], transformer, 5000, result
    )
    assert len(result) > 0
