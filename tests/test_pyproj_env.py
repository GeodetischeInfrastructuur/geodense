from pyproj.network import is_network_enabled


def test_pyproj_network_enabled():
    assert is_network_enabled() is True
