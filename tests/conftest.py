import logging
import os

import pytest
from geodense.lib import get_geojson_obj


@pytest.fixture()
def test_dir():
    return os.path.dirname(os.path.abspath(__file__))


@pytest.fixture()
def linestring_d10_feature_gj(test_dir):
    with open(os.path.join(test_dir, "data", "linestring_feature_d10.json")) as f:
        return get_geojson_obj(f)


@pytest.fixture()
def linestring_feature_gj(test_dir):
    with open(os.path.join(test_dir, "data", "linestring_feature.json")) as f:
        return get_geojson_obj(f)


@pytest.fixture()
def linestring_3d_feature_gj(test_dir):
    with open(os.path.join(test_dir, "data", "linestring_3d_feature.json")) as f:
        return get_geojson_obj(f)


@pytest.fixture()
def linestring_feature_5000_gj(test_dir):
    with open(os.path.join(test_dir, "data", "linestring_feature_5000.json")) as f:
        return get_geojson_obj(f)


@pytest.fixture()
def geometry_collection_gj(test_dir):
    with open(os.path.join(test_dir, "data", "feature-geometry-collection.json")) as f:
        return get_geojson_obj(f)


@pytest.fixture()
def polygon_feature_with_holes_gj(test_dir):
    with open(os.path.join(test_dir, "data", "polygon_feature_with_holes.json")) as f:
        return get_geojson_obj(f)


@pytest.fixture()
def point_feature_gj(test_dir):
    with open(os.path.join(test_dir, "data", "point_feature.json")) as f:
        return get_geojson_obj(f)


@pytest.fixture()
def geometry_collection_feature_gj(test_dir):
    with open(os.path.join(test_dir, "data", "feature-geometry-collection.json")) as f:
        return get_geojson_obj(f)


@pytest.fixture()
def linestring_feature_multiple_linesegments(test_dir):
    with open(
        os.path.join(test_dir, "data", "linestring_feature_multiple_linesegments.json")
    ) as f:
        return get_geojson_obj(f)


geodense_logger = logging.getLogger("geodense")


# see https://github.com/pytest-dev/pytest/issues/14#issuecomment-521577819
# required since: "I think the issue boils down to the fact that if you set up a Stream Handler and you enable capsys the actual output stream will be a pytest stream that will be closed and thrown away at the next test in the test suite."
@pytest.fixture(autouse=True)
def _ensure_logging_framework_not_altered():
    before_handlers = list(geodense_logger.handlers)
    yield
    geodense_logger.handlers = before_handlers
