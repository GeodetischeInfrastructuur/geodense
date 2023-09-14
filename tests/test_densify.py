import json
import os
import tempfile

import mock
import pyproj
import pytest

from geodense.lib import (densify_geometry_coordinates,
                          densify_geospatial_file,
                          get_intermediate_nr_points_and_segment_length)


# TODO: add 3D feature to test


def test_point_raises_exception(point_feature):
    feature = json.loads(point_feature)
    with pytest.raises(
        ValueError,
        match=r"received point geometry coordinates, instead of \(multi\)linestring",
    ):
        densify_geometry_coordinates(feature["geometry"]["coordinates"], "EPSG:28992")


def test_linestring_transformed(linestring_feature):
    feature = json.loads(linestring_feature)
    feature_t = json.loads(linestring_feature)
    densify_geometry_coordinates(
        feature_t["geometry"]["coordinates"], "EPSG:28992", 1000, False
    )
    assert feature != feature_t
    assert len(feature["geometry"]["coordinates"]) == 2
    assert len(feature_t["geometry"]["coordinates"]) == 12


def test_polygon_with_hole_transformed(polygon_feature_with_holes):
    feature = json.loads(polygon_feature_with_holes)
    feature_t = json.loads(polygon_feature_with_holes)
    densify_geometry_coordinates(
        feature_t["geometry"]["coordinates"], "EPSG:28992", 1000, False
    )
    test = json.dumps(feature_t, indent=4)
    print(test)
    assert feature != feature_t


def test_linestring_transformed_source_proj(linestring_feature):
    feature = json.loads(linestring_feature)
    feature_t = json.loads(linestring_feature)
    densify_geometry_coordinates(
        feature_t["geometry"]["coordinates"], "EPSG:28992", 1000, True
    )
    assert feature != feature_t
    assert len(feature["geometry"]["coordinates"]) == 2
    assert len(feature_t["geometry"]["coordinates"]) == 14


def test_maxlinesegment_param(linestring_feature):
    feature_200 = json.loads(linestring_feature)
    feature_1000 = json.loads(linestring_feature)
    densify_geometry_coordinates(
        feature_200["geometry"]["coordinates"], "EPSG:28992", 200, False
    )
    densify_geometry_coordinates(
        feature_1000["geometry"]["coordinates"], "EPSG:28992", 1000, False
    )
    assert len(feature_200["geometry"]["coordinates"]) == 53
    assert len(feature_1000["geometry"]["coordinates"]) == 12


def test_get_intermediate_nr_points_and_segment_length():
    # test distance > max_segment_length
    data = [
        [(1000, 100), (9, 100.0)],
        [(1000, 300), (3, 250.0)],
    ]
    for value in data:
        result = get_intermediate_nr_points_and_segment_length(*value[0])
        assert result == value[1]

    # test distance < max_segment_length
    with pytest.raises(
        ValueError,
        match=r"max_segment_length \(.+\) cannot be bigger or equal than dist \(.+\)",
    ):
        get_intermediate_nr_points_and_segment_length(100, 1000)

    # test distance == max_segment_length
    with pytest.raises(
        ValueError,
        match=r"max_segment_length \(.+\) cannot be bigger or equal than dist \(.+\)",
    ):
        get_intermediate_nr_points_and_segment_length(1000, 1000)


def test_densify_geospatial_file(test_dir):
    in_file = "linestrings.json"
    out_file = os.path.join(tempfile.mkdtemp(), in_file)
    densify_geospatial_file(os.path.join(test_dir, "data", in_file), out_file)
    assert os.path.exists(out_file)


def test_densify_geospatial_file_negative(test_dir):
    in_file = "linestrings.json"
    out_file = os.path.join(tempfile.mkdtemp(), in_file)
    densify_geospatial_file(
        os.path.join(test_dir, "data", in_file), out_file, "", -10000
    )
    assert os.path.exists(out_file)


def test_densify_geospatial_file_exception(test_dir):
    with mock.patch.object(pyproj.Geod, "fwd_intermediate") as get_mock:
        get_mock.side_effect = ValueError("FOOBAR")
        in_file = "linestrings.json"
        out_file = os.path.join(tempfile.mkdtemp(), in_file)
        with pytest.raises(
            ValueError,
            match=r"Unexpected error occured while processing feature \[0\]",
        ):
            densify_geospatial_file(
                os.path.join(test_dir, "data", in_file), out_file, "", 10000
            )


def test_densify_geospatial_file_in_proj_exc(test_dir):
    in_file = "linestrings-4258.json"
    out_file = os.path.join(tempfile.mkdtemp(), in_file)

    with pytest.raises(
        ValueError,
        match=(r"densify_in_projection can only be used with projected coordinates "
        r"reference systems, crs .+ is a geographic crs"),
    ):
        densify_geospatial_file(
            os.path.join(test_dir, "data", in_file), out_file, "", None, True
        )
