from contextlib import nullcontext as does_not_raise
from typing import Any, Literal, Union

import pytest
from _pytest.python_api import RaisesContext
from geodense.lib import (
    SUPPORTED_FILE_FORMATS,
    crs_is_geographic,
    file_is_supported_fileformat,
    geom_type_check,
    get_driver_by_file_extension,
)


@pytest.mark.parametrize(
    ("geom_type", "expectation"),
    [
        ("LineString", does_not_raise()),
        ("Polygon", does_not_raise()),
        ("MultiPolygon", does_not_raise()),
        ("MultiLineString", does_not_raise()),
        (
            "Point",
            pytest.raises(
                ValueError,
                match=r"Unsupported GeometryType .+, supported GeometryTypes are: .+",
            ),
        ),
        (
            "MultiPoint",
            pytest.raises(
                ValueError,
                match=r"Unsupported GeometryType .+, supported GeometryTypes are: .+",
            ),
        ),
    ],
)
def test_geom_type_check(
    geom_type: Literal[
        "LineString",
        "Polygon",
        "MultiPolygon",
        "MultiLineString",
        "Point",
        "MultiPoint",
    ],
    expectation: Union[Any, RaisesContext[ValueError]],
):
    with expectation:
        assert geom_type_check(geom_type) is None


@pytest.mark.parametrize(
    ("crs_string", "expectation"), [("EPSG:28992", False), ("EPSG:4258", True)]
)
def test_crs_is_geographic(crs_string: str, expectation: bool):
    assert crs_is_geographic(crs_string) is expectation


@pytest.mark.parametrize(
    ("file_path", "expectation"),
    [
        ("/temp/data/bar.fgb", True),
        (
            "/temp/data/foo.gpkg",
            True,
        ),
        ("/temp/data/foo.fgdb", False),
    ],
)
def test_is_supported_fileformat(file_path, expectation):
    assert file_is_supported_fileformat(file_path) is expectation


def test_get_driver_by_file_extension_raises():
    with pytest.raises(
        ValueError,
        match=r"file extension '.foobar' not found in list of supported extensions: .shp, .fgb, .geojson, .json, .gml, .gpkg",
    ):
        get_driver_by_file_extension(".foobar")


@pytest.mark.parametrize("supported_file_format", SUPPORTED_FILE_FORMATS)
def test_get_driver_by_file_extension_all_values(supported_file_format):
    extensions = SUPPORTED_FILE_FORMATS[supported_file_format]
    for ext in extensions:
        assert get_driver_by_file_extension(ext) in SUPPORTED_FILE_FORMATS
