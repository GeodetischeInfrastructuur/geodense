import os

import pytest


@pytest.fixture()
def test_dir():
    return os.path.dirname(os.path.abspath(__file__))


@pytest.fixture()
def linestring_feature(test_dir):
    with open(os.path.join(test_dir, "data", "linestring_feature.json")) as f:
        return f.read()


@pytest.fixture()
def linestring_feature_5000(test_dir):
    with open(os.path.join(test_dir, "data", "linestring_feature_5000.json")) as f:
        return f.read()


@pytest.fixture()
def linestring_feature_multiple_linesegments(test_dir):
    with open(
        os.path.join(test_dir, "data", "linestring_feature_multiple_linesegments.json")
    ) as f:
        return f.read()


@pytest.fixture()
def polygon_feature_with_holes(test_dir):
    with open(os.path.join(test_dir, "data", "polygon_feature_with_holes.json")) as f:
        return f.read()


@pytest.fixture()
def point_feature(test_dir):
    with open(os.path.join(test_dir, "data", "point_feature.json")) as f:
        return f.read()
