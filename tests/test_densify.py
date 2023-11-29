import json
import os
import re
import tempfile
from contextlib import nullcontext as does_not_raise
from contextlib import suppress

import pyproj
import pytest
from geodense.lib import (
    _get_geojson_obj,
    _get_geom_densify_fun,
    _get_intermediate_nr_points_and_segment_length,
    densify_file,
    densify_geojson_object,
)
from geodense.models import DenseConfig, GeodenseError
from geojson_pydantic import Feature, GeometryCollection


@pytest.mark.parametrize(
    ("geojson", "expected"),
    [
        (
            "point_feature_gj",
            pytest.raises(
                GeodenseError,
                match=r"input file contains only \(Multi\)Point geometries which cannot be densified",
            ),
        ),
        (
            "geometry_collection_gj",
            does_not_raise(),
        ),  # geom collection containing point
    ],
)
def test_only_points_raises_exception(geojson, expected, request):
    feature: Feature = request.getfixturevalue(geojson)
    c = DenseConfig(pyproj.CRS.from_epsg(28992))

    with expected:
        densify_geojson_object(feature, c)


def test_geometry_collection_transformed(geometry_collection_gj):
    gc: GeometryCollection = geometry_collection_gj
    gc_t: GeometryCollection = gc.model_copy(deep=True)

    c = DenseConfig(pyproj.CRS.from_epsg(28992), 10)
    densify_geojson_object(gc_t, c)

    assert gc_t != gc


def test_linestring_d10_transformed(linestring_d10_feature_gj):
    ft: Feature = linestring_d10_feature_gj
    ft_t: Feature = ft.model_copy(deep=True)

    c = DenseConfig(pyproj.CRS.from_epsg(28992), 10)
    geom_densify_fun = _get_geom_densify_fun(c)
    geom_densify_fun(ft_t.geometry, [], [])
    feature_coords_length = 2
    feature_t_coord_length = 3

    assert ft != ft_t
    assert len(ft.geometry.coordinates) == feature_coords_length
    assert len(ft_t.geometry.coordinates) == feature_t_coord_length


def test_linestring_d10_no_op(linestring_d10_feature_gj):
    ft: Feature = linestring_d10_feature_gj
    ft_t: Feature = ft.model_copy(deep=True)
    ft_t_in_proj: Feature = ft.model_copy(deep=True)
    ft_t.properties[
        "foo"
    ] = "bar"  # to differentiate between original ft and ft_t, to prevent we are testing the same object...

    c = DenseConfig(
        pyproj.CRS.from_epsg(28992), 15
    )  # 15 since 15> sqrt(10^2+10^2) -- see linestring_feature_d10.json -> this should result in no points added
    c_in_proj = DenseConfig(pyproj.CRS.from_epsg(28992), 15, True)

    geom_densify_fun = _get_geom_densify_fun(c)
    geom_densify_in_proj_fun = _get_geom_densify_fun(c_in_proj)

    geom_densify_fun(ft_t.geometry, [], [])
    geom_densify_in_proj_fun(ft_t_in_proj.geometry, [], [])

    feature_coords_length = 2

    assert ft != ft_t
    assert len(ft_t.geometry.coordinates) == feature_coords_length
    assert len(ft_t_in_proj.geometry.coordinates) == feature_coords_length


def test_linestring_transformed(linestring_feature_gj):
    ft: Feature = linestring_feature_gj
    ft_t: Feature = ft.model_copy(deep=True)
    c = DenseConfig(pyproj.CRS.from_epsg(28992), 1000)

    geom_densify_fun = _get_geom_densify_fun(c)
    geom_densify_fun(ft_t.geometry, [], [])

    feature_coords_length = 2
    feature_t_coord_length = 12

    assert ft != ft_t
    assert len(ft.geometry.coordinates) == feature_coords_length
    assert len(ft_t.geometry.coordinates) == feature_t_coord_length


def test_densify_3d_source_projection(linestring_3d_feature_gj):
    ft_t: Feature = linestring_3d_feature_gj
    c = DenseConfig(pyproj.CRS.from_epsg(7415), 1000, True)

    geom_densify_fun = _get_geom_densify_fun(c)
    geom_densify_fun(ft_t.geometry, [], [])

    for i, (_, _, h) in enumerate(ft_t.geometry.coordinates):
        assert h == (
            i * 10
        ), f"height is not linear interpolated with increments of 10 - height: {h}, expected height: {i*10}"


def test_densify_3d(linestring_3d_feature_gj):
    ft_t: Feature = linestring_3d_feature_gj
    c = DenseConfig(pyproj.CRS.from_epsg(7415), 1000)

    geom_densify_fun = _get_geom_densify_fun(c)
    geom_densify_fun(ft_t.geometry, [], [])

    for i, (_, _, h) in enumerate(ft_t.geometry.coordinates):
        assert h == (
            i * 10
        ), f"height is not linear interpolated with increments of 10 - height: {h}, expected height: {i*10}"


def test_polygon_with_hole_transformed(polygon_feature_with_holes_gj):
    feature: Feature = polygon_feature_with_holes_gj
    feature_t = feature.model_copy(deep=True)

    c = DenseConfig(pyproj.CRS.from_epsg(28992), 1000)

    geom_densify_fun = _get_geom_densify_fun(c)
    geom_densify_fun(feature_t.geometry, [], [])

    assert feature != feature_t


def test_linestring_transformed_source_proj(linestring_feature_gj):
    feature: Feature = linestring_feature_gj
    feature_t = feature.model_copy(deep=True)

    c = DenseConfig(pyproj.CRS.from_epsg(28992), 1000, True)

    geom_densify_fun = _get_geom_densify_fun(c)
    geom_densify_fun(feature_t.geometry, [], [])

    feature_coords_length = 2
    feature_t_coord_length = 12

    assert feature != feature_t
    assert len(feature.geometry.coordinates) == feature_coords_length
    assert len(feature_t.geometry.coordinates) == feature_t_coord_length


def test_maxlinesegment_param(linestring_feature_gj):
    feature_200: Feature = linestring_feature_gj
    feature_1000 = feature_200.model_copy(deep=True)

    c_200 = DenseConfig(pyproj.CRS.from_epsg(28992), 200, False)
    c_1000 = DenseConfig(pyproj.CRS.from_epsg(28992), 1000, False)

    geom_densify_fun_200 = _get_geom_densify_fun(c_200)
    geom_densify_fun_1000 = _get_geom_densify_fun(c_1000)

    geom_densify_fun_200(feature_200.geometry, [], [])
    geom_densify_fun_1000(feature_1000.geometry, [], [])

    assert len(feature_200.geometry.coordinates) > len(
        feature_1000.geometry.coordinates
    )


@pytest.mark.parametrize(
    ("input_args", "expectation"),
    [((1000, 100), (9, 100.0)), ((1000, 300), (3, 250.0))],
)
def test_get_intermediate_nr_points_and_segment_length(input_args, expectation):
    # test distance > max_segment_length
    result = _get_intermediate_nr_points_and_segment_length(*input_args)
    assert result == expectation


@pytest.mark.parametrize(
    ("input_args", "expectation"),
    [
        (
            (100, 1000),
            pytest.raises(
                GeodenseError,
                match=r"max_segment_length \(.+\) cannot be bigger or equal than dist \(.+\)",
            ),
        ),
        (
            (1000, 1000),
            pytest.raises(
                GeodenseError,
                match=r"max_segment_length \(.+\) cannot be bigger or equal than dist \(.+\)",
            ),
        ),
        ((1000, 100), does_not_raise()),
    ],
)
def test_get_intermediate_nr_points_and_segment_length_raises(input_args, expectation):
    with expectation:
        _get_intermediate_nr_points_and_segment_length(*input_args)


def test_densify_file(test_dir):
    in_file = "linestrings.json"
    out_file = os.path.join(tempfile.mkdtemp(), in_file)
    densify_file(os.path.join(test_dir, "data", in_file), out_file)
    assert os.path.exists(out_file)


@pytest.mark.parametrize(
    ("input_file", "src_crs", "expectation"),
    [
        (
            "multipolygon.json",
            None,
            "urn:ogc:def:crs:EPSG::28992",
        ),
        ("geometry-4326-no-crs.json", None, None),
        ("geometry-4326-no-crs.json", "OGC:CRS84", None),
        (
            "multipolygon_wrong_crs.json",
            "EPSG:28992",
            "urn:ogc:def:crs:EPSG::28992",
        ),
    ],
)
def test_densify_file_crs_matches_input(test_dir, input_file, src_crs, expectation):
    output_file = os.path.join(tempfile.mkdtemp(), input_file)
    input_file = os.path.join(test_dir, "data", input_file)
    densify_file(input_file, output_file, src_crs=src_crs)
    with open(output_file) as f:
        geojson = json.load(f)
        crs = None
        with suppress(KeyError):
            crs = geojson["crs"]["properties"]["name"]
        assert crs == expectation


@pytest.mark.parametrize(
    ("input_file", "output_file", "expectation"),
    [
        (
            "linestrings.foobar",
            "linestrings_out.foobar",
            pytest.raises(
                GeodenseError,
                match=r"unsupported file extension of input-file, received: .foobar, expected one of: .geojson, .json",
            ),
        ),
        ("linestrings.json", "linestrings.geojson", does_not_raise()),
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


def test_densify_file_in_proj_exc(tmpdir, test_dir):
    in_file = "linestrings-4258.json"
    out_file = os.path.join(tmpdir, in_file)
    in_file = os.path.join(test_dir, "data", in_file)
    with pytest.raises(
        GeodenseError,
        match=(
            r"densify_in_projection can only be used with projected coordinates "
            r"reference systems, crs .+ is a geographic crs"
        ),
    ):
        densify_file(in_file, out_file, densify_in_projection=True)


def test_densify_file_input_file_does_not_exist(tmpdir, test_dir):
    input_file = os.path.join(test_dir, "foobar.json")
    output_file = os.path.join(tmpdir, "foobar.json")

    with pytest.raises(
        GeodenseError,
        match=(r"input_file .*foobar.json does not exist"),
    ):
        assert isinstance(densify_file(input_file, output_file))


def test_densify_file_output_dir_does_not_exist_raises(test_dir):
    input_file = os.path.join(test_dir, "data", "linestrings.json")
    output_file = os.path.join(test_dir, "foobar", "foobar.json")

    with pytest.raises(
        GeodenseError,
        match=(r"target directory of output_file .*foobar.json does not exist"),
    ):
        assert isinstance(densify_file(input_file, output_file))


def test_densify_file_input_and_output_equal_raises(test_dir):
    input_file = os.path.join(test_dir, "data", "linestrings.json")
    output_file = os.path.join(test_dir, "data", "linestrings.json")

    with pytest.raises(
        GeodenseError,
        match=(
            r"input_file and output_file arguments must be different, input_file: .*linestrings.json, output_file: .*linestrings.json"
        ),
    ):
        assert isinstance(densify_file(input_file, output_file))


@pytest.mark.parametrize(
    ("overwrite", "expectation"),
    [
        (
            False,
            pytest.raises(
                GeodenseError,
                match=r"output_file .*\.json already exists",
            ),
        ),
        (True, does_not_raise()),
    ],
)
def test_densify_file_output_file_exists_raises(test_dir, overwrite, expectation):
    input_file = os.path.join(test_dir, "data", "linestrings.json")
    with tempfile.NamedTemporaryFile(suffix=".json") as tmp_file, expectation:
        densify_file(input_file, tmp_file.name, overwrite=overwrite)


@pytest.mark.parametrize(
    ("crs", "expectation"),
    [
        (
            "EPSG:999999928992",
            pytest.raises(
                pyproj.exceptions.CRSError,
                match=r"Invalid projection: EPSG:999999928992: \(Internal Proj Error: proj_create: crs not found\)",
            ),
        ),
        ("EPSG:28992", does_not_raise()),
    ],
)
def test_densify_file_invalid_crs_raises(test_dir, tmpdir, crs, expectation):
    input_file = os.path.join(test_dir, "data", "feature-geometry-collection.json")
    output_file = os.path.join(tmpdir, "geometry.json")
    with expectation:
        assert densify_file(input_file, output_file, src_crs=crs) is None


def test_point_raises_warning_and_noop(test_dir, tmpdir, caplog):
    input_file = os.path.join(test_dir, "data", "feature-geometry-collection.json")
    output_file = os.path.join(tmpdir, "geometry.json")
    densify_file(input_file, output_file, src_crs="EPSG:28992")
    output = caplog.text
    expected_warning = r"WARNING .* input file contains \(Multi\)Point geometries which cannot be densified"
    assert re.match(
        expected_warning, output
    ), f"stderr expected message is: {expected_warning}, actual message was: {output}"

    with open(input_file) as in_f, open(output_file) as out_f:
        ft_gc: Feature = _get_geojson_obj(in_f)
        ft_gc_t: Feature = _get_geojson_obj(out_f)
        assert (
            ft_gc.geometry.geometries[0].coordinates
            == ft_gc_t.geometry.geometries[0].coordinates
        )  # assert point geom coords the same


def test_densify_file_json_no_crs_outputs_message_stderr(caplog, test_dir, tmpdir):
    input_file = os.path.join(test_dir, "data", "geometry-4326-no-crs.json")
    output_file = os.path.join(tmpdir, "geometry.json")
    densify_file(input_file, output_file)
    output = caplog.text
    expected_warning = r"WARNING .* unable to determine source CRS for file .*geometry-4326-no-crs.json, assumed CRS is EPSG:4326\n"
    assert re.match(
        expected_warning, output
    ), f"stderr expected message is: {expected_warning}, actual message was: {output}"
