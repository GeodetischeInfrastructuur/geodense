# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## \[3.0.0\] - 2026-10-24

### Changed

- **BREAKING (library):** `densify_geojson_object` (and `traverse_geojson_geometries`) now **mutate their input GeoJSON
  object in place** and return the **same instance**; previously a copy was returned. Library users who need to keep the
  original must copy it first, e.g. with `copy.deepcopy`.
- **BREAKING:** Python support narrowed to 3.12 only (`requires-python = ">=3.12,<3.13"`); previously 3.10+.
- **BREAKING:** `pyproj` is pinned to the NSGI build `3.7.2.post1` via `[tool.uv.sources]` (GitHub-release wheel, cp312
  only).
- `geojson-pydantic` dependency tightened to `>=2,<3` (was `>=1,<3`).
- `shapely` range widened to `>=2.0.6,<2.3.0` (was `<2.2.0`); verified against shapely 2.2.
- Distribution: geodense is now published as a wheel on the GitHub releases page instead of PyPI.

### Performance

- Removed the per-node deep copy in `densify`, cached CRS constants on `DenseConfig`, and sped up `_round_coordinates`.
  Densifying `gemeenten-40.json` went from ~2777 ms to ~980 ms; output is byte-for-byte identical.

### Removed

- Stray debug `print` in the `check-density` CLI command.

## \[2.2.0rc2\] - Pre-release

Release candidates (`2.1.0-rc.1`, `2.2.0rc1`, `2.2.0rc2`) preceding 3.0.0; details not itemised here.

## \[2.0.2\] / \[2.0.1\] / \[2.0.0\]

- 2.0.0: major release; the codebase was refactored to separate transformation and traversal methods.
- 2.0.1 and 2.0.2: maintenance releases (dependency updates and fixes).

## \[1.0.0\] and earlier

- 1.0.0 / 1.0.1-alpha: first stable release line.
- 0.0.1 alpha releases: initial development.
