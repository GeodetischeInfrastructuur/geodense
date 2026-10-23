"""End-to-end performance benchmark for the densify / check-density hot paths.

Purpose
-------
Provide a reproducible before/after measurement for the performance work described
in ``PERFORMANCE_PLAN.md`` (primarily: removing deep copies from
``traverse_geojson_geometries``).

These tests are **opt-in** and skipped by default so they never slow down or flake
the normal CI suite. Enable them with::

    GEODENSE_BENCH=1 uv run pytest tests/test_benchmark.py -s -v

The ``-s`` flag is recommended so the printed timing tables are visible.

What it measures
----------------
Using the largest fixture (``gemeenten-40.json``, ~2.3 MB) it times, separately:

    parse (json.loads + pydantic validation)
    single full-tree model_copy(deep=True)   -- the cost we are removing
    densify_geojson_object                    -- end-to-end hot path
    check_density_geojson_object              -- read-only hot path
    model_dump_json                           -- serialization

It also asserts the **copy-prevention invariant** that backs the optimization:
``densify_geojson_object`` must not trigger deep ``model_copy`` calls once the plan
is implemented. Before the change this assertion is expected to FAIL (it counts the
deep copies and prints them); after the change it must pass with zero deep copies.
This gives a single test that visibly flips from red to green, verifying the win.

Baseline (pre-optimization, local reference run on gemeenten-40.json)::

    parse ~0.13s | single deep copy ~0.46s | densify ~2.72s | dump ~0.39s
    deep model_copy calls during densify: 81
"""

import os
import time
from collections.abc import Callable
from typing import Any

import pyproj
import pytest
from pydantic import BaseModel

from geodense.geojson import CrsFeatureCollection
from geodense.lib import (
    _get_crs_geojson,
    _has_3d_coordinates,
    check_density_geojson_object,
    densify_geojson_object,
    textio_to_geojson,
)
from geodense.models import DenseConfig

BENCH_ENABLED = os.environ.get("GEODENSE_BENCH") == "1"
BENCH_FILE = "gemeenten-40.json"
MAX_SEGMENT_LENGTH = 200

pytestmark = pytest.mark.skipif(
    not BENCH_ENABLED,
    reason="performance benchmark; set GEODENSE_BENCH=1 to enable",
)


def _timeit(label: str, fn: Callable[[], Any], repeat: int = 3) -> tuple[float, Any]:
    """Run ``fn`` ``repeat`` times, return (best_seconds, last_result)."""
    best = float("inf")
    result = None
    for _ in range(repeat):
        start = time.perf_counter()
        result = fn()
        best = min(best, time.perf_counter() - start)
    print(f"  {label:<34} {best * 1000:9.1f} ms")
    return best, result


def _load(test_dir: str):
    with open(os.path.join(test_dir, "data", BENCH_FILE)) as f:
        obj = textio_to_geojson(f)
    crs = _get_crs_geojson(obj, BENCH_FILE, None, _has_3d_coordinates(obj, silent=True))
    config = DenseConfig(pyproj.CRS.from_authority(*crs.split(":")), MAX_SEGMENT_LENGTH)
    return obj, config


def _fresh_obj(test_dir: str):
    with open(os.path.join(test_dir, "data", BENCH_FILE)) as f:
        return textio_to_geojson(f)


class _DeepCopyCounter:
    """Context manager that counts deep ``BaseModel.model_copy`` calls."""

    def __init__(self) -> None:
        self.count = 0
        self._original = BaseModel.model_copy

    def __enter__(self) -> "_DeepCopyCounter":
        counter = self

        def patched(self_model: BaseModel, *args: Any, **kwargs: Any) -> BaseModel:
            if kwargs.get("deep"):
                counter.count += 1
            return counter._original(self_model, *args, **kwargs)

        BaseModel.model_copy = patched  # type: ignore[method-assign]
        return self

    def __exit__(self, *exc: Any) -> None:
        BaseModel.model_copy = self._original  # type: ignore[method-assign]


def test_benchmark_phases(test_dir):
    """Print a per-phase timing table for the hot paths (informational)."""
    print(f"\n[benchmark] file={BENCH_FILE} max_segment_length={MAX_SEGMENT_LENGTH}")

    _timeit("parse (json + validation)", lambda: _fresh_obj(test_dir))

    obj, config = _load(test_dir)
    _timeit("single full-tree deep copy", lambda: obj.model_copy(deep=True))

    # densify mutates/returns, so reload a fresh object each repeat for a fair number
    def _densify_fresh():
        fresh, cfg = _load(test_dir)
        return densify_geojson_object(cfg, fresh)

    _, densified = _timeit("densify_geojson_object", _densify_fresh)

    obj2, config2 = _load(test_dir)
    _timeit(
        "check_density_geojson_object",
        lambda: check_density_geojson_object(config2, obj2),
    )

    model = densified if isinstance(densified, BaseModel) else None
    if model is not None:
        _timeit(
            "model_dump_json",
            lambda: model.model_dump_json(indent=1, exclude_none=True),
        )


def test_densify_performs_no_deep_copies(test_dir):
    """Copy-prevention invariant.

    Before the optimization this FAILS and reports the deep-copy count (baseline:
    81 on gemeenten-40.json). After removing the deep copies from
    ``traverse_geojson_geometries`` it must pass with zero deep copies.
    """
    obj, config = _load(test_dir)

    with _DeepCopyCounter() as counter:
        densify_geojson_object(config, obj)

    print(f"\n[benchmark] deep model_copy calls during densify: {counter.count}")
    assert counter.count == 0, (
        f"expected zero deep copies after the optimization, got {counter.count}; "
        "see PERFORMANCE_PLAN.md workstream A"
    )


def test_densify_mutates_input_in_place(test_dir):
    """Pin the in-place contract: densify returns the same instance it was given.

    Before the optimization densify returns a deep copy (different identity), so
    this FAILS; after the change it returns the mutated input and passes.
    """
    obj, config = _load(test_dir)
    result = densify_geojson_object(config, obj)
    assert result is obj, "densify_geojson_object must mutate and return the same input instance"


@pytest.mark.skipif(
    os.environ.get("GEODENSE_BENCH_LARGE") != "1",
    reason="large-input benchmark; set GEODENSE_BENCH_LARGE=1 to enable",
)
def test_benchmark_large_input(test_dir):
    """Amplify the signal on a synthetic larger input (features replicated ~25x)."""
    with open(os.path.join(test_dir, "data", BENCH_FILE)) as f:
        base = textio_to_geojson(f)
    assert isinstance(base, CrsFeatureCollection)

    multiplier = 25
    crs = _get_crs_geojson(base, BENCH_FILE, None, _has_3d_coordinates(base, silent=True))
    config = DenseConfig(pyproj.CRS.from_authority(*crs.split(":")), MAX_SEGMENT_LENGTH)

    def _build():
        obj = base.model_copy(deep=True)
        obj.features = [feat.model_copy(deep=True) for _ in range(multiplier) for feat in base.features]
        return obj

    print(f"\n[benchmark] large input: {multiplier}x {BENCH_FILE} "
          f"(~{multiplier * len(base.features)} features)")

    obj = _build()
    _timeit("densify_geojson_object (large)", lambda: densify_geojson_object(config, _build()), repeat=1)
    check_obj = _build()
    _timeit(
        "check_density_geojson_object (large)",
        lambda: check_density_geojson_object(config, check_obj),
        repeat=1,
    )
