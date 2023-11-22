import re
from contextlib import nullcontext as does_not_raise
from typing import Any

import pytest
from _pytest.python_api import RaisesContext
from geodense.lib import (
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
    geojson, expectation: Any | RaisesContext[GeodenseError], request
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
