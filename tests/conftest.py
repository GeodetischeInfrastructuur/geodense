import os

import pytest


@pytest.fixture()
def test_dir():
    return os.path.dirname(os.path.abspath(__file__))


@pytest.fixture()
def linestring_d10_feature(test_dir):
    with open(os.path.join(test_dir, "data", "linestring_feature_d10.json")) as f:
        return f.read()


@pytest.fixture()
def linestring_feature(test_dir):
    with open(os.path.join(test_dir, "data", "linestring_feature.json")) as f:
        return f.read()


@pytest.fixture()
def linestring_3d_feature(test_dir):
    with open(os.path.join(test_dir, "data", "linestring_3d_feature.json")) as f:
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


@pytest.fixture()
def geometry_collection_feature(test_dir):
    with open(os.path.join(test_dir, "data", "feature-geometry-collection.json")) as f:
        return f.read()


@pytest.fixture()
def geometry_path(test_dir):
    return os.path.join(test_dir, "data", "geometry.json")


@pytest.fixture()
def geometry_crs_path(test_dir):
    return os.path.join(test_dir, "data", "geometry-crs.json")


@pytest.fixture()
def invalid_crs_path(test_dir):
    return os.path.join(test_dir, "data", "invalid-crs.json")


@pytest.fixture()
def gemeenten_path(test_dir):
    return os.path.join(test_dir, "data", "gemeenten-40.json")


# @pytest.fixture()
# def gem100_path(test_dir, tmpdir):
#     fc = """{
#         "type": "FeatureCollection",
#         "name": "gemeentegebied",
#         "features": [],
#         "crs": {
#             "type": "name",
#             "properties": {
#                 "name": "urn:ogc:def:crs:EPSG::28992"
#             }
#         }
#     }
#     """
#     file_path = os.path.join(tmpdir, "gm100.json")
#     with open(file_path, "w") as f, open(
#         os.path.join(test_dir, "data", "feature-big.json")
#     ) as ff:
#         ft = json.load(ff)
#         fc_json = json.loads(fc)
#         fc_json["features"] = [ft] * 1000
#         json.dump(fc_json, f)
#     return file_path
