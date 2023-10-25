from contextlib import nullcontext as does_not_raise
from typing import Any, Literal, Union

import pytest
from _pytest.python_api import RaisesContext
from geodense.lib import (
    _crs_is_geographic,
    _file_is_supported_fileformat,
    _geom_type_check,
    get_crs_json,
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
        assert _geom_type_check(geom_type) is None


@pytest.mark.parametrize(
    ("crs_string", "expectation"), [("EPSG:28992", False), ("EPSG:4258", True)]
)
def test_crs_is_geographic(crs_string: str, expectation: bool):
    assert _crs_is_geographic(crs_string) is expectation


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
    assert _file_is_supported_fileformat(file_path) is expectation


# using fixtures by referencing fixture as string in @pytest.mark.parametrize
# and calling request.getfixturevalue
@pytest.mark.parametrize(
    ("file_path", "expectation"),
    [
        ("geometry_path", None),
        ("geometry_crs_path", "EPSG:28992"),
        ("invalid_crs_path", None),
        ("gemeenten_path", "EPSG:28992"),
    ],
)
def test_get_crs_json(file_path, expectation, request):
    file_path_val = request.getfixturevalue(file_path)
    crs = get_crs_json(file_path_val)
    assert crs == expectation
