import re
from contextlib import nullcontext as does_not_raise
from typing import Any

import pytest
from _pytest.python_api import RaisesContext
from geodense.lib import _geom_type_check, _raise_e_if_point_geom
from geodense.models import GeodenseError
from geojson_pydantic import Feature


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
def test_geom_type_check(
    geojson, expectation: Any | RaisesContext[GeodenseError], request
):
    with expectation:
        gj_obj = request.getfixturevalue(geojson)
        _geom_type_check(gj_obj)


def test_mixed_geom_outputs_warning(geometry_collection_feature_gj, caplog):
    geojson_obj = geometry_collection_feature_gj
    _geom_type_check(geojson_obj)
    my_regex = re.compile(r"WARNING .* GeoJSON contains \(Multi\)Point geometries\n")
    assert my_regex.match(caplog.text) is not None


@pytest.mark.parametrize(
    ("feature_fixture", "expected"),
    [
        (
            "point_feature_gj",
            pytest.raises(
                GeodenseError,
                match=r"received point geometry coordinates, instead of \(multi\)linestring",
            ),
        ),
        ("polygon_feature_with_holes_gj", does_not_raise()),
    ],
)
def test_raise_if_point(feature_fixture, expected, request):
    feature: Feature = request.getfixturevalue(feature_fixture)

    with expected:
        _raise_e_if_point_geom(feature.geometry.coordinates)
