from geodense.lib import interpolate_src_proj


def test_interpolate_src_proj():
    points = [(0, 0), (10, 10)]  # 14.142
    points_t = interpolate_src_proj(*points, 20)
    assert points_t == points  # check if no-op
