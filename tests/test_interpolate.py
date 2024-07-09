from copy import deepcopy

import pytest
from geodense.lib import (
    THREE_DIMENSIONAL,
    _add_vertices_to_line_segment,
    densify_line_segment,
    interpolate_src_proj,
)
from geodense.models import (
    DEFAULT_PRECISION_DEGREES,
    DEFAULT_PRECISION_METERS,
    DenseConfig,
)
from geojson_pydantic.types import Position2D, Position3D
from pyproj import CRS


def tuple_2_pos(tup):
    result = Position2D(longitude=tup[0], latitude=tup[1])
    if len(tup) == THREE_DIMENSIONAL:
        result = Position3D(*result, altitude=tup[2])
    return result


def test_interpolate_src_proj_no_op():
    points = [tuple_2_pos(x) for x in [(0, 0), (10, 10)]]  # 14.142
    c = DenseConfig(CRS.from_epsg(28992), 20)
    points_t = interpolate_src_proj(*points, c)
    assert points_t == [], f"expected points_t to be empty, received: {points_t}"


def test_interpolate_src_proj():
    points = [tuple_2_pos(x) for x in [(0, 0), (10, 10)]]  # 14.142
    c = DenseConfig(CRS.from_epsg(28992), 10)
    points_t = interpolate_src_proj(*points, c)
    expected_nr_of_points = 1

    assert (
        len(points_t) == expected_nr_of_points
    ), f"expected length of points_t was {expected_nr_of_points}, acual: {len(points_t)}"


def test_add_vertices_exceeding_max_segment_length():
    linestring = [tuple_2_pos(x) for x in [(0, 0), (10, 10), (20, 20)]]
    linestring_origin = deepcopy(linestring)

    c = DenseConfig(CRS.from_epsg(28992), 10, True)

    densify_line_segment(c, linestring)

    assert linestring != linestring_origin
    assert len(linestring) == 5  # noqa: PLR2004
    assert linestring == [(0, 0), (5.0, 5.0), (10, 10), (15.0, 15.0), (20, 20)]


def test_interpolate_round_projected():
    """Note precision is only reduced by round()"""
    points_proj = [
        tuple_2_pos(x) for x in [(0.12345678, 0.12345678), (10.12345678, 10.12345678)]
    ]

    c = DenseConfig(CRS.from_epsg(28992), 10, True)
    _add_vertices_to_line_segment(points_proj, 0, c)

    assert all(
        [
            str(x)[::-1].find(".") == DEFAULT_PRECISION_METERS
            for p in points_proj
            for x in p
        ]
    )  # https://stackoverflow.com/a/26231848/1763690
    # Quick way to check the precision of the output values.
    # Do note that the slice will reverse the string [::-1]


def test_interpolate_round_geographic():
    """Note precision is only reduced by round()"""
    points_geog = [
        tuple_2_pos(x)
        for x in [
            (0.1234567891011, 0.1234567891011),
            (10.1234567891011, 10.1234567891011),
        ]
    ]

    c = DenseConfig(CRS.from_epsg(4258), 10)
    _add_vertices_to_line_segment(points_geog, 0, c)

    assert all(
        [
            str(x)[::-1].find(".")
            <= DEFAULT_PRECISION_DEGREES  # <= because Python does not force n precision, see for instance: `round(2.000000,9) -> 2.0`
            for p in points_geog
            for x in p
        ]
    )  # https://stackoverflow.com/a/26


@pytest.mark.parametrize(
    ("linestring", "in_proj", "expectation"),
    [
        (
            [(-10, -10), (0, 0, 0), (10, 10, 10), (20, 20), (30, 30)],
            False,
            [
                (-10, -10),
                (-5.0, -5.0),
                (0, 0, 0),
                (5.0, 5.0, 5.0),
                (10, 10, 10),
                (15.0, 15.0),
                (20, 20),
                (25.0, 25.0),
                (30, 30),
            ],
        ),
        (
            [(-10, -10), (0, 0, 0), (10, 10, 10), (20, 20), (30, 30)],
            True,
            [
                (-10, -10),
                (-5.0, -5.0),
                (0, 0, 0),
                (5.0, 5.0, 5.0),
                (10, 10, 10),
                (15.0, 15.0),
                (20, 20),
                (25.0, 25.0),
                (30, 30),
            ],
        ),
    ],
)
def test_interpolate_3d(linestring, in_proj, expectation):
    linestring = [tuple_2_pos(x) for x in linestring]

    c = DenseConfig(CRS.from_epsg(7415), 10, in_proj)

    densify_line_segment(c, linestring)
    assert linestring == expectation
