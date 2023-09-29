import json
import os
import tempfile
from contextlib import nullcontext as does_not_raise
from unittest import mock

import pyproj
import pytest
from geodense.lib import (
    TRANSFORM_CRS,
    _get_intermediate_nr_points_and_segment_length,
    _get_transformer,
    densify_geometry_coordinates,
    densify_geospatial_file,
)


def test_point_raises_exception(point_feature):
    feature = json.loads(point_feature)
    with pytest.raises(
        ValueError,
        match=r"received point geometry coordinates, instead of \(multi\)linestring",
    ):
        densify_geometry_coordinates(feature["geometry"]["coordinates"], "EPSG:28992")


def test_linestring_d10_transformed(linestring_d10_feature):
    feature = json.loads(linestring_d10_feature)
    feature_t = json.loads(linestring_d10_feature)
    src_crs = "EPSG:28992"
    transformer = _get_transformer(src_crs, TRANSFORM_CRS)

    densify_geometry_coordinates(
        feature_t["geometry"]["coordinates"], transformer, 10, False
    )

    feature_coords_length = 2
    feature_t_coord_length = 3

    assert feature != feature_t
    assert len(feature["geometry"]["coordinates"]) == feature_coords_length
    assert len(feature_t["geometry"]["coordinates"]) == feature_t_coord_length


def test_linestring_d10_no_op(linestring_d10_feature):
    feature = json.loads(linestring_d10_feature)
    feature_t = json.loads(linestring_d10_feature)
    feature_t_s = json.loads(linestring_d10_feature)

    src_crs = "EPSG:28992"
    transformer = _get_transformer(src_crs, TRANSFORM_CRS)

    densify_geometry_coordinates(
        feature_t["geometry"]["coordinates"], transformer, 20, False
    )

    densify_geometry_coordinates(
        feature_t["geometry"]["coordinates"], transformer, 20, True
    )

    feature_coords_length = 2

    assert feature != feature_t
    assert len(feature["geometry"]["coordinates"]) == feature_coords_length
    assert len(feature_t["geometry"]["coordinates"]) == feature_coords_length
    assert len(feature_t_s["geometry"]["coordinates"]) == feature_coords_length


def test_linestring_transformed(linestring_feature):
    feature = json.loads(linestring_feature)
    feature_t = json.loads(linestring_feature)
    src_crs = "EPSG:28992"
    transformer = _get_transformer(src_crs, TRANSFORM_CRS)
    densify_geometry_coordinates(
        feature_t["geometry"]["coordinates"], transformer, 1000, False
    )

    feature_coords_length = 2
    feature_t_coord_length = 12

    assert feature != feature_t
    assert len(feature["geometry"]["coordinates"]) == feature_coords_length
    assert len(feature_t["geometry"]["coordinates"]) == feature_t_coord_length


def test_linestring_3d_raises_exception(linestring_3d_feature):
    feature_t = json.loads(linestring_3d_feature)

    src_crs = "EPSG:7415"
    transformer = _get_transformer(src_crs, TRANSFORM_CRS)

    with pytest.raises(
        ValueError,
        match=r"3 dimensional geometries are not supported",
    ):
        densify_geometry_coordinates(
            feature_t["geometry"]["coordinates"], transformer, 1000, False
        )


def test_polygon_with_hole_transformed(polygon_feature_with_holes):
    feature = json.loads(polygon_feature_with_holes)
    feature_t = json.loads(polygon_feature_with_holes)

    src_crs = "EPSG:28992"
    transformer = _get_transformer(src_crs, TRANSFORM_CRS)

    densify_geometry_coordinates(
        feature_t["geometry"]["coordinates"], transformer, 1000, False
    )
    test = json.dumps(feature_t, indent=4)
    print(test)
    assert feature != feature_t


def test_linestring_transformed_source_proj(linestring_feature):
    feature = json.loads(linestring_feature)
    feature_t = json.loads(linestring_feature)

    src_crs = "EPSG:28992"
    transformer = _get_transformer(src_crs, TRANSFORM_CRS)

    densify_geometry_coordinates(
        feature_t["geometry"]["coordinates"], transformer, 1000, True
    )
    feature_coords_length = 2
    feature_t_coord_length = 12

    assert feature != feature_t
    assert len(feature["geometry"]["coordinates"]) == feature_coords_length
    assert len(feature_t["geometry"]["coordinates"]) == feature_t_coord_length


def test_maxlinesegment_param(linestring_feature):
    feature_200 = json.loads(linestring_feature)
    feature_1000 = json.loads(linestring_feature)

    src_crs = "EPSG:28992"
    transformer = _get_transformer(src_crs, TRANSFORM_CRS)

    densify_geometry_coordinates(
        feature_200["geometry"]["coordinates"], transformer, 200, False
    )
    densify_geometry_coordinates(
        feature_1000["geometry"]["coordinates"], transformer, 1000, False
    )
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


def test_densify_geospatial_file(test_dir):
    in_file = "linestrings.json"
    out_file = os.path.join(tempfile.mkdtemp(), in_file)
    densify_geospatial_file(os.path.join(test_dir, "data", in_file), out_file)
    assert os.path.exists(out_file)


# TODO: test conversion from geojson to geopackage...
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
def test_densify_geospatial_file_unsupported_file_format(
    test_dir, input_file, output_file, expectation
):
    input_file = os.path.join(test_dir, "data", input_file)
    output_file = os.path.join(tempfile.mkdtemp(), output_file)
    with expectation:
        assert densify_geospatial_file(input_file, output_file) is None


def test_densify_geospatial_file_negative(tmpdir, test_dir):
    in_file = "linestrings.json"
    out_file = os.path.join(tmpdir, in_file)
    densify_geospatial_file(
        os.path.join(test_dir, "data", in_file), out_file, None, -10000
    )
    assert os.path.exists(out_file)


def test_densify_geospatial_file_exception(tmpdir, test_dir):
    with mock.patch.object(pyproj.Geod, "fwd_intermediate") as get_mock:
        get_mock.side_effect = ValueError("FOOBAR")
        in_file = "linestrings.json"
        out_file = os.path.join(tmpdir, in_file)
        with pytest.raises(
            ValueError,
            match=r"Unexpected error occured while processing feature \[0\]",
        ):
            densify_geospatial_file(
                os.path.join(test_dir, "data", in_file), out_file, None, 10000
            )


def test_densify_geospatial_file_in_proj_exc(tmpdir, test_dir):
    in_file = "linestrings-4258.json"
    out_file = os.path.join(tmpdir, in_file)

    with pytest.raises(
        ValueError,
        match=(
            r"densify_in_projection can only be used with projected coordinates "
            r"reference systems, crs .+ is a geographic crs"
        ),
    ):
        densify_geospatial_file(
            os.path.join(test_dir, "data", in_file), out_file, None, None, True
        )


def test_densify_geospatial_file_input_file_does_not_exist(tmpdir, test_dir):
    input_file = os.path.join(test_dir, "foobar.json")
    output_file = os.path.join(tmpdir, "foobar.json")

    with pytest.raises(
        ValueError,
        match=(r"input_file .*foobar.json does not exist"),
    ):
        assert isinstance(densify_geospatial_file(input_file, output_file))


def test_densify_geospatial_file_output_dir_does_not_exist_raises(test_dir):
    input_file = os.path.join(test_dir, "data", "linestrings.json")
    output_file = os.path.join(test_dir, "foobar", "foobar.json")

    with pytest.raises(
        ValueError,
        match=(r"target directory of output_file .*foobar.json does not exist"),
    ):
        assert isinstance(densify_geospatial_file(input_file, output_file))


def test_densify_geospatial_file_input_and_output_equal_raises(test_dir):
    input_file = os.path.join(test_dir, "data", "linestrings.json")
    output_file = os.path.join(test_dir, "data", "linestrings.json")

    with pytest.raises(
        ValueError,
        match=(
            r"input_file and output_file arguments must be different, input_file: .*linestrings.json, output_file: .*linestrings.json"
        ),
    ):
        assert isinstance(densify_geospatial_file(input_file, output_file))


def test_densify_geospatial_file_output_file_exists_raises(test_dir):
    input_file = os.path.join(test_dir, "data", "linestrings.json")
    output_file = os.path.join(test_dir, "data", "linestrings-4258.json")

    with pytest.raises(
        ValueError,
        match=(r"output_file .*linestrings-4258.json already exists"),
    ):
        assert isinstance(densify_geospatial_file(input_file, output_file))
