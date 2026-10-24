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

Install and run the CLI with [`uv`](https://docs.astral.sh/uv/). Because geodense's `pyproj` pin is a direct wheel URL
declared in `[tool.uv.sources]`, you must supply that source when installing, otherwise `pyproj==3.7.2.post1` is looked
up on PyPI (where the NSGI build does not exist). The simplest way is to install geodense from a checkout/export of this
repository (which carries the `[tool.uv.sources]` entry), or to pass the `pyproj` URL explicitly:

```sh
# uv: run as a tool, resolving the NSGI pyproj wheel alongside geodense
# (replace <version>; use the wheel URLs from the respective release pages)
uvx \
  --with https://github.com/GeodetischeInfrastructuur/transformations/releases/download/9.7.1-post1-rc17/pyproj-3.7.2.post1-cp312-cp312-linux_x86_64.whl \
  --from https://github.com/GeodetischeInfrastructuur/geodense/releases/download/<version>/geodense-<version>-py3-none-any.whl \
  geodense
```

### Depending on geodense from another project

> **Important:** `[tool.uv.sources]` is **not** part of a built wheel's metadata. When you build your own package,
> geodense's `pyproj` source pin does **not** travel into your wheel — your `Requires-Dist` will only say
> `pyproj==3.7.2.post1`. Consumers of *your* package therefore have to resolve the NSGI `pyproj` wheel themselves.

To depend on geodense, add **both** the geodense wheel **and** the NSGI `pyproj` source to your own `pyproject.toml`,
and install with `uv` (plain `pip` does not read `[tool.uv.sources]`):

```toml
[project]
dependencies = [
    "geodense",
    # ... your other dependencies
]

[tool.uv.sources]
geodense = { url = "https://github.com/GeodetischeInfrastructuur/geodense/releases/download/<version>/geodense-<version>-py3-none-any.whl" }
# geodense pins pyproj to the NSGI build, but that source pin is not carried in
# geodense's wheel metadata, so it must be declared here as well:
pyproj = { url = "https://github.com/GeodetischeInfrastructuur/transformations/releases/download/9.7.1-post1-rc17/pyproj-3.7.2.post1-cp312-cp312-linux_x86_64.whl" }
```

If your package is in turn consumed by others, this same `[tool.uv.sources]` block has to be repeated at each level of
the dependency chain — there is currently no way to propagate it through wheel metadata.

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
