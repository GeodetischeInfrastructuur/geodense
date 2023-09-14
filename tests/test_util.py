from contextlib import nullcontext as does_not_raise
from typing import Any, Literal, Union

import pytest
from _pytest.python_api import RaisesContext

from geodense.lib import crs_is_geographic, geom_type_check


@pytest.mark.parametrize(
    "geom_type,expectation",
    [
        ("LineString", does_not_raise()),
        ("Polygon", does_not_raise()),
        ("MultiPolygon", does_not_raise()),
        ("MultiLineString", does_not_raise()),
        ("Point", pytest.raises(ValueError)),
        ("MultiPoint", pytest.raises(ValueError)),
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
    expectation: Union[Any ,RaisesContext[ValueError]],
):
    with expectation:
        assert geom_type_check(geom_type) is None


def test_crs_is_geographic():
    data = [
        ("EPSG:28992", False),
        ("EPSG:4258", True),
    ]
    for test in data:
        result = crs_is_geographic(test[0])
        assert result == test[1]
