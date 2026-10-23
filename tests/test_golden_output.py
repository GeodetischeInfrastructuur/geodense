import os
import tempfile

import pytest

from geodense.lib import check_density_file, densify_file

DATA = os.path.join(os.path.dirname(__file__), "data")
GOLDEN = os.path.join(DATA, "golden")

DENSIFY_CASES = [
    ("linestrings.json", None, 10, False),
    ("linestrings.json", None, 200, True),
    ("linestrings_4326.json", None, 1000, False),
    ("linestrings_3d.json", None, 10, False),
    ("linestring_feature.json", "EPSG:28992", 10, False),
    ("polygons.json", None, 50, False),
    ("polygon_feature_with_holes.json", "EPSG:28992", 20, False),
    ("multipolygon.json", None, 100, False),
    ("multipolygon_wrong_crs.json", "EPSG:28992", 100, False),
    ("geometry-4326-no-crs.json", "EPSG:4326", 1000, False),
    ("fc-geometry-collection.json", None, 10, False),
    ("feature-geometry-collection.json", "EPSG:28992", 10, False),
    ("gemeenten-40.json", None, 200, False),
]

CHECK_CASES = [
    ("linestrings.json", None, 10, False),
    ("linestrings_4326.json", None, 1000, False),
    ("linestrings_3d.json", None, 10, False),
    ("polygons.json", None, 50, False),
    ("multipolygon.json", None, 100, False),
    ("fc-geometry-collection.json", None, 10, False),
    ("gemeenten-40.json", None, 200, False),
]


def _name(kind, case):
    f, crs, msl, proj = case
    return f"{kind}__{f[:-5]}__{(crs or 'nocrs').replace(':', '')}__{msl}__{'proj' if proj else 'geod'}.json"


def _check(actual_path, name):
    golden_path = os.path.join(GOLDEN, name)
    if os.environ.get("GEODENSE_UPDATE_GOLDEN"):
        with open(actual_path, "rb") as a, open(golden_path, "wb") as g:
            g.write(a.read())
    with open(actual_path, "rb") as a, open(golden_path, "rb") as g:
        assert a.read() == g.read()


@pytest.mark.parametrize("case", DENSIFY_CASES, ids=lambda c: _name("densify", c))
def test_golden_densify(case):
    f, crs, msl, proj = case
    out = os.path.join(tempfile.mkdtemp(), "out.json")
    densify_file(os.path.join(DATA, f), out, max_segment_length=msl, densify_in_projection=proj, src_crs=crs)
    _check(out, _name("densify", case))


@pytest.mark.parametrize("case", CHECK_CASES, ids=lambda c: _name("check", c))
def test_golden_check_density(case):
    f, crs, msl, proj = case
    report = os.path.join(tempfile.mkdtemp(), "report.json")
    ok, path, _ = check_density_file(os.path.join(DATA, f), msl, report, crs, in_projection=proj)
    if ok:
        pytest.skip("no report produced")
    _check(path, _name("check", case))
