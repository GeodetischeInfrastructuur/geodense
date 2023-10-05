import pytest
from geodense.lib import (
    DEFAULT_PRECISION_DEGREES,
    DEFAULT_PRECISION_METERS,
    TRANSFORM_CRS,
    _add_vertices_exceeding_max_segment_length,
    _add_vertices_to_line_segment,
    _get_transformer,
    interpolate_src_proj,
)


def test_interpolate_src_proj_no_op():
    points = [(0, 0), (10, 10)]  # 14.142
    points_t = interpolate_src_proj(*points, 20)
    assert points_t == [], f"expected points_t to be empty, received: {points_t}"


def test_interpolate_src_proj():
    points = [(0, 0), (10, 10)]  # 14.142
    points_t = interpolate_src_proj(*points, 10)
    expected_nr_of_points = 1

    assert (
        len(points_t) == expected_nr_of_points
    ), f"expected length of points_t was {expected_nr_of_points}, acual: {len(points_t)}"


def test_add_vertices_exceeding_max_segment_length():
    linestring = [(0, 0), (10, 10), (20, 20)]
    linestring_t = linestring

    transformer = _get_transformer("EPSG:28992", TRANSFORM_CRS)

    _add_vertices_exceeding_max_segment_length(linestring_t, 10, transformer, True)
    assert len(linestring_t) == 5  # noqa: PLR2004
    assert linestring_t == [(0, 0), (5.0, 5.0), (10, 10), (15.0, 15.0), (20, 20)]


def test_interpolate_round_projected():
    """Note precision is only reduced by round()"""
    points_proj = [(0.12345678, 0.12345678), (10.12345678, 10.12345678)]
    transformer = _get_transformer("EPSG:28992", TRANSFORM_CRS)
    _add_vertices_to_line_segment(points_proj, 0, transformer, 10, True)

    assert all(
        [
            str(x)[::-1].find(".") == DEFAULT_PRECISION_METERS
            for p in points_proj
            for x in p
        ]
    )  # https://stackoverflow.com/a/26231848/1763690


def test_interpolate_round_geographic():
    """Note precision is only reduced by round()"""
    points_geog = [
        (0.1234567891011, 0.1234567891011),
        (10.1234567891011, 10.1234567891011),
    ]
    transformer = _get_transformer("EPSG:4258", TRANSFORM_CRS)
    _add_vertices_to_line_segment(points_geog, 0, transformer, 10, True)

    assert all(
        [
            str(x)[::-1].find(".") == DEFAULT_PRECISION_DEGREES
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
                (-5.0, -4.9999),
                (0, 0, 0),
                (5.0, 5.0001, 5.0),
                (10, 10, 10),
                (15.0, 15.0001),
                (20, 20),
                (25.0, 25.0001),
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
    linestring_t = linestring[:]  # clone list with slicing
    transformer = _get_transformer("EPSG:28992", TRANSFORM_CRS)
    _add_vertices_exceeding_max_segment_length(linestring_t, 10, transformer, in_proj)
    assert linestring_t == expectation
