import re
from contextlib import nullcontext as does_not_raise
from typing import Any, Union

import pytest
from _pytest.python_api import RaisesContext
from geodense.lib import (
    _crs_is_geographic,
    _file_is_supported_fileformat,
    _geom_type_check,
)
from geodense.models import GeodenseError


@pytest.mark.parametrize(
    ("geojson", "expectation"),
    [
        ("linestring_feature_gj", does_not_raise()),
        (
            "point_feature_gj",
            pytest.raises(
                GeodenseError,
                match=r"input file contains only \(Multi\)Point geometries which cannot be densified",
            ),
        ),
        ("geometry_collection_gj", does_not_raise()),
    ],
)
def test_geom_type_check(
    geojson, expectation: Union[Any, RaisesContext[GeodenseError]], request
):
    with expectation:
        gj_obj = request.getfixturevalue(geojson)
        _geom_type_check(gj_obj)


def test_mixed_geom_outputs_warning(geometry_collection_feature_gj, caplog):
    geojson_obj = geometry_collection_feature_gj
    _geom_type_check(geojson_obj)
    my_regex = re.compile(
        r"WARNING.*input file contains \(Multi\)Point geometries which cannot be densified"
    )
    assert my_regex.match(caplog.text) is not None


@pytest.mark.parametrize(
    ("crs_string", "expectation"), [("EPSG:28992", False), ("EPSG:4258", True)]
)
def test_crs_is_geographic(crs_string: str, expectation: bool):
    assert _crs_is_geographic(crs_string) is expectation


@pytest.mark.parametrize(
    ("file_path", "expectation"),
    [
        ("/temp/data/bar.fgb", False),
        (
            "/temp/data/foo.gpkg",
            False,
        ),
        ("/temp/data/foo.geojson", True),
    ],
)
def test_is_supported_fileformat(file_path, expectation):
    assert _file_is_supported_fileformat(file_path) is expectation
