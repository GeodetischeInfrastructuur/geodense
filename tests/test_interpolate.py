from geodense.lib import (
    DEFAULT_PRECISION_GEOGRAPHIC,
    DEFAULT_PRECISION_PROJECTED,
    add_vertices_exceeding_max_segment_length,
    add_vertices_to_line_segment,
    interpolate_src_proj,
)


def test_interpolate_src_proj_no_op():
    points = [(0, 0), (10, 10)]  # 14.142
    points_t = interpolate_src_proj(*points, 20)
    assert (
        points_t == points
    ), f"expected points_t and points to be equal, instead they differ: points - {points}, points_t - {points_t}"


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
    add_vertices_exceeding_max_segment_length(linestring_t, 10, "EPSG:28992", True)
    assert len(linestring_t) == 5  # noqa: PLR2004
    assert linestring_t == [(0, 0), (5.0, 5.0), (10, 10), (15.0, 15.0), (20, 20)]


def test_interpolate_round_projected():
    """Note precision is only reduced by round()"""
    points_proj = [(0.12345678, 0.12345678), (10.12345678, 10.12345678)]
    add_vertices_to_line_segment(points_proj, 0, "EPSG:28992", 10, True)

    assert all(
        [
            str(x)[::-1].find(".") == DEFAULT_PRECISION_PROJECTED
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
    add_vertices_to_line_segment(points_geog, 0, "EPSG:4258", 10, True)

    assert all(
        [
            str(x)[::-1].find(".") == DEFAULT_PRECISION_GEOGRAPHIC
            for p in points_geog
            for x in p
        ]
    )  # https://stackoverflow.com/a/26
