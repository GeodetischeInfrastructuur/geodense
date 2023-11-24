# geodense

[![Endpoint Badge](https://img.shields.io/endpoint?url=https%3A%2F%2Fgeodetischeinfrastructuur.github.io%2Fgeodense%2Fbadge.json&style=flat-square&logo=pytest&logoColor=white)](https://geodetischeinfrastructuur.github.io/geodense/)

Python library and CLI tool to **check density** and **densify** geometries using the geodesic (ellipsoidal great-circle) calculation for accurate CRS transformations.

Implementation based on [*Eenduidige transformatie van grenzen tussen ETRS89 en RD*](https://geoforum.nl/uploads/default/original/2X/c/c0795baa683bf3845c866ae4c576a880455be02a.pdf)

Requires Python v3.11 or higher.

Depends on: 

- `pyproj ~= 3.6.0` -> [requires PROJ 9+](https://pyproj4.github.io/pyproj/stable/installation.html#installing-from-source)
- `shapely ~= 2.0.2` -> [requires GEOS >= 3.5](https://shapely.readthedocs.io/en/stable/index.html#requirements)

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

See [`DOCS.md`](https://github.com/GeodetischeInfrastructuur/geodense/blob/main/DOCS.md) for usage docs; for now only containing flow-charts of the `densify` and `check-densify` subcommands.

## Development

> **TODO**: add description how to setup dev environment with conda/miniconda and libmamba solver, and install pyproj with: `conda install -c conda-forge  pyproj==3.6.0 --solver=libmamba`

Install/uninstall geodense for development, including dev dependencies (run from root of repository):

```sh
pip install -e ".[dev]"
pip uninstall geodense
```

### Tests

Run tests:

```sh
python3 -m pytest tests/
```

Check test coverage:

```sh
python3 -m coverage run -p --source=src/geodense -m pytest -v tests && python3 -m coverage report
```
