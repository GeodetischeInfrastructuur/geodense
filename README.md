# geodense

[![Code Coverage](https://img.shields.io/endpoint?url=https%3A%2F%2Fgeodetischeinfrastructuur.github.io%2Fgeodense%2Fbadge.json&style=flat-square&logo=pytest&logoColor=white)](https://geodetischeinfrastructuur.github.io/geodense/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-teal.svg?style=flat-square)](https://www.python.org/downloads/release/python-3127/)
![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)
[![PyPI Version](https://img.shields.io/pypi/v/geodense.svg?style=flat-square)](https://pypi.python.org/pypi/geodense)

Python library and CLI tool to **check density** and **densify** geometries using the geodesic (ellipsoidal
great-circle) calculation for accurate CRS transformations.

Implementation based on
[*Eenduidige transformatie van grenzen tussen ETRS89 en RD*](https://gnss-data.kadaster.nl/misc/docs/langelijnenadvies.pdf)

Depends on the following Python packages with binary dependencies (installed through [`uv`](https://docs.astral.sh/uv/)
or [`pip`](https://pypi.org/project/pip/)):

- [`pyproj`](https://pyproj4.github.io/pyproj/stable/installation.html): requires libproj
- [`shapely`](https://shapely.readthedocs.io/en/stable/index.html): requires libgeos

## Installation

Install with either [`uv`](https://docs.astral.sh/uv/) or [`pip`](https://pypi.org/project/pip/):

```sh
# pip
pip install geodense

# uv: run as cli tool
uvx geodense

# uv: add as dependency to project
uv add geodense
```

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

See [`DOCS.md`](https://github.com/GeodetischeInfrastructuur/geodense/blob/main/DOCS.md) for usage docs; for now only
containing flow-charts of the `densify` and `check-densify` subcommands.

## Developer Docs

See [`DEV.md`](https://github.com/GeodetischeInfrastructuur/geodense/blob/main/DEV.md) for developer docs.

## Contributing

Issues (bugs/feature requests) can be reported in the
[issue tracker of this repository](https://github.com/GeodetischeInfrastructuur/geodense/issues). Pull requests are more
than welcome, but we encourage to start a discussion on the issue tracker first.
