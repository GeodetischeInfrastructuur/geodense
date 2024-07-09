import re
from contextlib import nullcontext as does_not_raise
from typing import Any

import pytest
from _pytest.python_api import RaisesContext
from geodense.lib import validate_geom_type
from geodense.models import GeodenseError


@pytest.mark.parametrize(
    ("geojson", "expectation"),
    [
        ("linestring_feature_gj", does_not_raise()),
        (
            "point_feature_gj",
            pytest.raises(
                GeodenseError,
                match=r"GeoJSON contains only \(Multi\)Point geometries",
            ),
        ),
        ("geometry_collection_gj", does_not_raise()),
    ],
)
def test_validate_geom_type(
    geojson, expectation: Any | RaisesContext[GeodenseError], request
):
    with expectation:
        gj_obj = request.getfixturevalue(geojson)
        validate_geom_type(gj_obj)


def test_mixed_geom_outputs_warning(geometry_collection_feature_gj, caplog):
    geojson_obj = geometry_collection_feature_gj
    validate_geom_type(geojson_obj)
    my_regex = re.compile(r"WARNING .* GeoJSON contains \(Multi\)Point geometries\n")
    assert my_regex.match(caplog.text) is not None
