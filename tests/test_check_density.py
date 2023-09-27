import json
import os
from contextlib import nullcontext as does_not_raise

import pytest
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
        assert isinstance(check_density(input_file, 1000, "lijnen"), list)
