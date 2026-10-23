# Geodense Performance Implementation Plan

Target repo: `geodense` (GeoJSON densify + density-check CLI/library). Goal: reduce runtime and memory on large GeoJSON
inputs by (1) avoiding repeated deep copies of the parsed data and (2) reducing parse/serialize overhead from the
validation library. This document is written so subagents can pick up discrete, independently verifiable work items.

______________________________________________________________________

## 1. Context & measured baseline

Hot paths live in `src/geodense/lib.py`. The two public operations are:

- `densify_file()` -> `densify_geojson_object()` -> `traverse_geojson_geometries()`
- `check_density_file()` -> `check_density_geojson_object()` -> `transform_geojson_geometries()`

Data is loaded in `textio_to_geojson()` (full `json.loads` + `geojson-pydantic` model construction) and written with
`model_dump_json(...)`.

Measured on `tests/data/gemeenten-40.json` (2.3 MB, 40 features, EPSG:28992, `densify`, max-segment-length 200):

| phase                                      | time        |
| ------------------------------------------ | ----------- |
| `json.loads` + pydantic validation (parse) | 0.127 s     |
| single full-tree `model_copy(deep=True)`   | 0.464 s     |
| **full densify (incl. deep copies)**       | **2.722 s** |
| `model_dump_json` (serialize)              | 0.387 s     |

Instrumentation shows **81 deep `model_copy` calls** during a single densify of 40 features.
`traverse_geojson_geometries()` calls `geojson.model_copy(deep=True)` at **every** recursion level (root, each feature,
each geometry), so large subtrees are duplicated many times. This recursive deep copy — not the parsing — is the
dominant cost (~2.1 s of the 2.7 s).

### Conclusion on the two hypotheses

- **Preventing deep copying: large win (primary).** Removing the deep copy **altogether** (not just copy-once) is
  expected to cut densify wall time by roughly 5-8x on this input and drastically reduce peak memory. This is the
  highest-value change. **Decision: operate fully in place; callers that need to retain the original must copy before
  calling.**
- **Switching parsing libs: moderate win (secondary).** Parse (0.127 s) + serialize (0.387 s) are ~0.5 s combined. A
  faster path (e.g. `orjson` for `json.loads`/dumps, or bypassing pydantic validation on load) can shave most of that,
  but it is small relative to the deep-copy cost and carries more API/behavior risk. Do it after the deep-copy fix.

______________________________________________________________________

## 2. Workstream A — Eliminate deep copies entirely, mutate in place (PRIMARY)

### Problem

`traverse_geojson_geometries()` (lib.py ~line 291) does `_geojson = geojson.model_copy(deep=True)` on entry, then
recurses into children — which each deep-copy their own subtree again. The `densify` geometry callback
(`densify_geometry` -> `traverse_linestrings_in_coordinates`) already **mutates coordinates in place**
(`geometry.coordinates = result`), so every deep copy is redundant work layered on top of in-place mutation.

### Decision

**Remove deep copying altogether.** `densify_geojson_object()` / `traverse_geojson_geometries()` mutate the passed-in
object in place and return it (the same instance). Callers that need to keep the original must copy it themselves before
calling. This is the fastest, lowest-memory option; the only cost is the API contract change, handled in A3.

### A1. Make traversal fully in-place, zero copies — REQUIRED

Refactor `traverse_geojson_geometries()` (lib.py ~L291-340) so it:

- **Removes** the `_geojson = geojson.model_copy(deep=True)` line (L305) and all the
  `_geojson`/`_feature`/`_feature_collection`/`_geometry_collection` shadow variables. Operate directly on `geojson` and
  its children.
- Recurses in place: `feature.geometry = _self(feature.geometry)`,
  `feature_collection.features = list(map(_self, feature_collection.features))`, etc. Because children are mutated in
  place, these assignments reassign the same objects; keep them for the `Feature.geometry = None` /
  `InfValCoordinateError` case where the geometry is replaced.
- Returns the same `geojson` instance it was given.
- Preserves the existing `geometry_callback` / `node_callback` behavior and the `InfValCoordinateError` ->
  `feature.geometry = None` handling.

`densify_geojson_object()` (lib.py ~L55) stays as-is except it now returns the mutated input object. **Do not** add any
copy at the boundary — that is the whole point of this change.

### A2. Keep `check_density` allocation-light

`transform_geojson_geometries()` (used by density-check) does **not** deep copy and is read-only — good. Confirm no
regression; no change expected beyond shared-helper updates from A1/A4.

### A3. Document the in-place mutation contract — REQUIRED

Public behavior changes: `densify_geojson_object()` (and `traverse_geojson_geometries()`) now **mutate the caller's
GeoJSON object in place** and return the same instance.

- Update docstrings on `densify_geojson_object`, `traverse_geojson_geometries`, and the library entry points to state
  clearly: *"mutates the input in place and returns it; copy the object first if you need to retain the original."*
- Add a note to `DOCS.md` / `README.md` under the library-usage section.
- The file/CLI path (`densify_file`) is unaffected in behavior — it loads the object itself and writes the result,
  discarding the input — so no CLI change.
- Add a test asserting the input object **is** mutated (identity + content), so the contract is pinned and intentional.

### A4. Remove redundant tree walks

`densify_file()` currently walks the tree several times: `_has_3d_coordinates()` (full `transform_geojson_geometries`),
`_get_crs_geojson()`, `validate_geom_type()` (another full walk), then the densify walk. For large inputs each walk is
non-trivial.

- Combine `validate_geom_type` + `_has_3d_coordinates` into a single pass (both only need the per-geometry type /
  coordinate dimensionality), or cache results.
- Lower priority than A1 but cheap and additive.

### Acceptance criteria (Workstream A)

- `traverse_geojson_geometries()` performs **zero** `model_copy` calls (assert via a test that patches/counts
  `BaseModel.model_copy` during a densify — expected 0).
- `densify_geojson_object()` returns the **same object instance** it was passed, and that instance is mutated (identity
  assertion in a test).
- Output byte-for-byte identical to current output for every file in `tests/data/` (see §4 golden-output harness).
- `densify` on `gemeenten-40.json` runs in well under 1 s locally (baseline 2.72 s).
- All existing tests pass; in-place mutation-contract test added; docstrings/docs updated per A3.

______________________________________________________________________

## 3. Workstream B — Parsing / serialization (SECONDARY)

Do **after** Workstream A. Keep each item behind its own measurement.

> **Status update (after A landed):**
> - **B1 (orjson): rejected.** `json.loads` is only ~36 ms; the parse cost is
>   geojson-pydantic validation, not JSON decoding. orjson showed no measurable
>   gain on decode and cannot match the `indent=1`/`indent=4` output on encode. Not
>   worth a dependency.
> - **B2 (reduce load-time validation): rejected as scoped.** Load-time validation
>   is only ~165 ms, and the realistic save is ~150 ms (~14% of densify) against
>   real risk: `model_construct()` does not build nested models (breaks the
>   `isinstance(..., Feature/CrsFeatureCollection)` checks throughout `lib.py`), and
>   skipping validation drops rejection of malformed input. Only worth doing fused
>   with B3 as one raw-representation rewrite — deferred.
> - **New finding → see Workstream C.** Profiling the *densify* phase (the real
>   ~1.06 s cost, not parsing) shows the bottleneck is per-point work inside the
>   interpolation loop, independent of the parsing library. That is the better
>   target and is lower risk than B2/B3.

### B1. Faster JSON load/dump with `orjson` (low risk)

- `textio_to_geojson()` uses `json.loads(src.read())`; outputs use `model_dump_json(indent=...)`. Replace raw JSON
  encode/decode with `orjson` where it does not change output formatting.
- Caveat: output currently uses `indent=1`/`indent=4`. `orjson` only supports `OPT_INDENT_2`. If exact indentation must
  be preserved, either keep stdlib for the final dump or get sign-off to standardize on 2-space indent. Decode side has
  no such constraint and is a safe, isolated win.
- Add `orjson` as a dependency in `pyproject.toml` only if it earns its keep.

### B2. Reduce pydantic validation cost on load (medium risk)

Parsing constructs full `geojson-pydantic` models (validation per position). For the densify/check paths we mostly need
raw coordinate arrays + type tags. Options, in increasing order of effort/risk:

- Use `model_construct()` / `model_validate` with validation tuned down where safe.
- Load with `orjson` into dicts and operate on the raw structure for the hot coordinate traversal, only building
  pydantic models where the typed API is actually required (e.g. `CrsFeatureCollection` CRS handling, report output).
- Full alternative: a lightweight internal representation (plain lists/tuples) for coordinates, converting to/from
  models only at the edges. Each option must preserve: CRS detection, 3D handling, error messages in `textio_to_geojson`
  for invalid `type`, and identical output.

### B3. Serialize without full pydantic dump (medium risk)

`model_dump_json(exclude_none=True)` walks the whole validated model. If B2 moves to a raw representation, emit JSON
directly via `orjson` from that representation, preserving `exclude_none` semantics and key ordering.

### Acceptance criteria (Workstream B)

- Each sub-item independently benchmarked (before/after) and gated: ship only if it measurably helps and keeps golden
  output identical (or indentation change is explicitly approved).
- No new mandatory dependency unless it provides a clear, measured gain.

______________________________________________________________________

## 3b. Workstream C — Optimize the densify inner loop (NEW, PRIMARY next step)

Discovered by profiling the densify phase after A (gemeenten-40.json, ~1.37 s
densify under cProfile). The cost is per-point work in the interpolation loop and
is independent of the parsing library. Breakdown (cumulative):

- `interpolate_geodesic` ~0.75 s — of which pyproj `transformer.transform` is
  ~0.31 s, called **one point at a time** 200k times.
- `_round_coordinates` ~0.34 s — `round()` called 400k times, rebuilding NamedTuples.
- `DenseConfig.get_coord_precision` + `CRS.is_geographic` + `CRS.is_projected`
  ~0.18 s combined — these are **constant per `DenseConfig`** yet recomputed ~98k
  times inside the hot loop (pyproj `is_geographic`/`is_projected` are not cheap).

### C1. Cache per-config constants on `DenseConfig` — LOW RISK, DO FIRST
In `src/geodense/models.py`, compute once in `__init__` and store as attributes:
`is_projected`, `is_geographic`, and the coord precision (`get_coord_precision`
result). Replace the repeated `self.src_crs.is_projected` /
`self.src_crs.is_geographic` / `get_coord_precision()` lookups in the `lib.py` hot
paths (`interpolate_geodesic`, `check_density_linestring`, `_add_vertices_to_line_segment`,
`interpolate_src_proj`) with the cached values. Pure hoisting of invariants; output
must be identical. Expected ~0.15-0.18 s off densify at near-zero risk.

### C2. Batch the pyproj transform calls — EVALUATED, REJECTED
`interpolate_geodesic` transforms `a`/`b` individually and back-transforms the
intermediate points per point. pyproj `Transformer.transform` accepts arrays.

**Outcome: rejected for this workload.** Measured findings (all gated on
golden-output, which stayed byte-identical throughout):
- Array transform only wins for larger batches: per-point vs array (20k reps) —
  n=2 scalar 0.038s / batch 0.064s (**scalar wins**); n=5 ~tie; n=20 0.286 vs
  0.160; n=100 2.263 vs 0.817 (batch 2.8x).
- But the real distribution on gemeenten-40.json is tiny: of 97791 segments,
  **median 0 / mean 0.05 intermediate points**, 97459 segments have ≤2 points and
  only 205 have ≥5. So batching the back-transform is net neutral-to-negative.
- Batching the forward a/b conversion into one 2-point array call made densify
  *worse* (~967ms → ~1680ms): array-wrapping overhead exceeds the saving at n=2.
  The ~196k forward `transform` calls are the dominant transform cost but can't be
  batched profitably within a single 2-point segment.
- A threshold guard (batch only when n≥~5) would help only ~0.2% of segments here —
  not worth the added branching. Per this plan's own rule ("skip any that don't
  measurably help"), C2 was reverted.
- Only a cross-segment restructure (collect all endpoints across the whole input
  and transform once) could batch the forward calls — that is effectively the
  C/B3 raw-representation rewrite and is out of scope here.

### C3. Reduce `_round_coordinates` overhead — LOW/MEDIUM RISK
Called 400k times. Avoid re-wrapping when already at precision, and avoid the
`len(position)` dimensionality re-check per call where the dimensionality is already
known by the caller. Keep output byte-identical.

### Acceptance criteria (Workstream C)
- Golden-output test stays byte-for-byte green (non-negotiable).
- Full suite + benchmark invariants green.
- Measurable densify reduction reported from
  `GEODENSE_BENCH=1 pytest tests/test_benchmark.py::test_benchmark_phases -s`.
- C1 first (safe), then C2/C3 each behind its own measurement; skip any that don't
  measurably help.

---

## 4. Shared deliverable — benchmark + golden-output harness (DO FIRST)

Before any refactor, a subagent should add a reproducible harness so all later work is verifiable. This is the gating
prerequisite for A and B.

1. **Golden output fixtures.** For each input in `tests/data/`, generate current `densify` and `check-density` outputs
   (for representative CRS/segment-length combos already covered in `tests/test_densify.py` /
   `tests/test_check_density.py`) and store them. Add a test that asserts new output matches golden byte-for-byte. This
   is the safety net for "no behavior change."
2. **Micro-benchmark script** (e.g. `bench/bench.py`, not shipped in the package): times parse / deep-copy / densify /
   dump separately on `gemeenten-40.json` and prints a table like §1. Keep it dependency-light (`time.perf_counter`).
3. **Larger input.** Optionally synthesize a bigger file (e.g. replicate `gemeenten-40.json` features to ~20-50 MB) to
   make deltas obvious and catch superlinear behavior. Keep out of the committed test data if size is a concern;
   generate on the fly in the bench script.

Acceptance: harness runs green against current `main` and reproduces the §1 numbers (order of magnitude) on the dev
machine.

______________________________________________________________________

## 5. Suggested execution order for subagents

1. **Task 0 (harness):** §4. Blocking prerequisite. One subagent.
2. **Task A1+A3 (remove deep copy, in-place + contract):** §2.1/§2.3. Highest value. One subagent, depends on Task 0.
3. **Task A4 (merge tree walks):** §2.4. Independent, can run in parallel with A1 once Task 0 lands (coordinate on
   shared helpers to avoid merge conflicts).
4. **Task B1 (orjson decode, + encode if indent approved):** §3.1. After A lands.
5. **Task B2/B3 (raw representation / reduced validation):** §3.2-3.3. Largest B effort; only if B1 + measurements
   justify going further.

Each task: run the §4 golden-output tests + existing `pytest` suite, and report the before/after bench table in its
summary.

______________________________________________________________________

## 6. Key files / anchors

- `src/geodense/lib.py`
  - `traverse_geojson_geometries` (~L291) — **remove the deep copy and all shadow copies; mutate in place** (A1).
  - `transform_geojson_geometries` (~L343) — read-only; keep allocation-light (A2).
  - `densify_geojson_object` (~L55) / `densify_geometry` (~L61) — in-place coord mutation already present; now returns
    the mutated input, **no boundary copy** (A1).
  - `traverse_linestrings_in_coordinates` (~L270) — already in-place; leave as is.
  - `textio_to_geojson` (~L478) — JSON decode + model construction (B1/B2).
  - `densify_file` (~L206) — `model_dump_json` output (B1/B3); multiple tree walks to merge (A4).
  - `_has_3d_coordinates` (~L662) / `validate_geom_type` (~L681) — extra full walks (A4).
- `src/geodense/types.py` — `GeojsonObject`, coordinate type aliases; relevant if a raw internal representation is
  introduced (B2).
- `src/geodense/geojson.py` — `CrsFeatureCollection` CRS handling that must survive any representation change.
- `pyproject.toml` — dependency changes (`orjson`) gated on measured benefit.

______________________________________________________________________

## 7. Risks & guardrails

- **Behavior/output drift:** golden-output harness (§4) is mandatory and must stay green for A; for B, indentation
  changes require explicit owner approval.
- **Mutation contract:** A makes densify mutate the caller's object in place and return it — callers must copy first if
  they need the original. Document it (A3) and add a test pinning the guarantee. The CLI/file path is
  behavior-unchanged.
- **Scope creep in B:** B2/B3 touch the type system broadly; keep behind measurements and only proceed if B1 is
  insufficient.
- **Dependencies:** add `orjson` only with a measured win; it is optional otherwise.
