from geodense.lib import interpolate_src_proj


def test_interpolate_src_proj_no_op():
    points = [(0, 0), (10, 10)]  # 14.142
    points_t = interpolate_src_proj(*points, 20)
    assert (
        points_t == points
    ), f"expected points_t and points to be equal, instead they differ: points - {points}, points_t - {points_t}"


def test_interpolate_src_proj():
    points = [(0, 0), (10, 10)]  # 14.142
    points_t = interpolate_src_proj(*points, 10)
    assert (
        points_t != points
    ), f"expected points_t and points to differ, instead they are equal: points - {points}, points_t - {points_t}"
