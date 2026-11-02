# geodense

[![Code Coverage](https://img.shields.io/endpoint?url=https%3A%2F%2Fgeodetischeinfrastructuur.github.io%2Fgeodense%2Fbadge.json&style=flat-square&logo=pytest&logoColor=white)](https://geodetischeinfrastructuur.github.io/geodense/)
[![Python 3.12](https://img.shields.io/badge/python-3.12-teal.svg?style=flat-square)](https://www.python.org/downloads/release/python-3120/)
![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)

Python library and CLI tool to **check density** and **densify** geometries using the geodesic (ellipsoidal
great-circle) calculation for accurate CRS transformations.

Implementation based on
[*Eenduidige transformatie van grenzen tussen ETRS89 en RD*](https://gnss-data.kadaster.nl/misc/docs/langelijnenadvies.pdf)

Depends on the following Python packages with binary dependencies (installed through
[`uv`](https://docs.astral.sh/uv/)):

- [`pyproj`](https://pyproj4.github.io/pyproj/stable/installation.html): requires libproj (NSGI build, see
  [Installation](#installation))
- [`shapely`](https://shapely.readthedocs.io/en/stable/index.html): requires libgeos

## Installation

As of v3, geodense is **no longer published on PyPI**. It depends on the NSGI build of `pyproj` (see
[NSGI transformations](DOCS.md#nsgi-transformations)), which is only available from GitHub releases, so geodense is
distributed as a wheel attached to the
[GitHub releases page](https://github.com/GeodetischeInfrastructuur/geodense/releases).

The NSGI `pyproj` wheel is only built for CPython 3.12 on Linux x86_64 (`cp312`, `linux_x86_64`).

### Running the CLI

Install and run the CLI with [`uv`](https://docs.astral.sh/uv/). The NSGI `pyproj` wheel is declared as a direct-URL
dependency in geodense's project metadata, so installers resolve it from GitHub rather than looking up the version on
PyPI. You only need to provide the geodense wheel URL:

```sh
# uv: run as a tool; geodense metadata selects the NSGI pyproj wheel
# (replace <version>; use the wheel URLs from the respective release pages)
uvx \
  --from https://github.com/GeodetischeInfrastructuur/geodense/releases/download/<version>/geodense-<version>-py3-none-any.whl \
  geodense
```

### Depending on geodense from another project

The geodense wheel metadata includes the direct URL for the NSGI `pyproj` wheel. It is a transitive dependency, so
consumers do not need to repeat the `pyproj` URL or add a `[tool.uv.sources]` entry for `pyproj`.

For a uv application, add the geodense wheel and the NSGI `pyproj` wheel to your project configuration:

```toml
[project]
dependencies = [
    "geodense",
    # ... your other dependencies
]

[tool.uv.sources]
geodense = { url = "https://github.com/GeodetischeInfrastructuur/geodense/releases/download/<version>/geodense-<version>-py3-none-any.whl" }
```

The current NSGI wheel is for CPython 3.12 on Linux x86_64. The direct-URL dependency is guarded by environment markers;
outside that environment, it does not select a stock `pyproj` fallback. If NSGI wheels become available for more Python
versions or platforms, add a direct-URL dependency for each supported wheel with matching environment markers.

## Usage CLI

Use either `geodense` or the short `gden` alias:

```txt
$ geodense --help

Usage: geodense [-h] [-v] {densify,check-density} ...

Check density of, and densify geometries using the geodesic (ellipsoidal great-circle) calculation for accurate CRS transformations

Commands:
  {densify,check-density}

Options:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit

Created by https://www.nsgi.nl/
```

## Usage Docs

See [`DOCS.md`](https://github.com/GeodetischeInfrastructuur/geodense/blob/main/DOCS.md) for usage docs: a flow-chart of
the `densify` subcommand, NSGI transformation requirements and library usage notes.

## Developer Docs

See [`DEV.md`](https://github.com/GeodetischeInfrastructuur/geodense/blob/main/DEV.md) for developer docs.

## Contributing

Issues (bugs/feature requests) can be reported in the
[issue tracker of this repository](https://github.com/GeodetischeInfrastructuur/geodense/issues). Pull requests are more
than welcome, but we encourage to start a discussion on the issue tracker first.
