# geodense

[![Endpoint Badge](https://img.shields.io/endpoint?url=https%3A%2F%2Fgeodetischeinfrastructuur.github.io%2Fgeodense%2Fbadge.json&style=flat-square&logo=pytest&logoColor=white)](https://geodetischeinfrastructuur.github.io/geodense/)

Python library and CLI tool to **check density** and **densify** linestring and polygon geometries using the geodesic great-circle calculation.

Implementation based on [*Eenduidige transformatie van grenzen tussen ETRS89 en RD*](https://geoforum.nl/uploads/default/original/2X/c/c0795baa683bf3845c866ae4c576a880455be02a.pdf)

## Installation

To install from source check out this repository and run from the root:

```sh
pip install .
```

## Development

Requires Python v3.9 or higher (due to dependency on [pyproj](https://pyproj4.github.io/pyproj/stable/) v3.6.0).

Install/uninstall for development:

```sh
pip install -e .
pip uninstall geodense
```

Check test coverage (install `coverage` with `pip install coverage` ):

```sh
coverage run --source=src/geodense -m pytest -v tests && coverage report -m
```

## Usage CLI

Use either `geodense` or the short `gden` alias:


```txt
$ geodense --help

Usage: geodense [-h] {densify,check-density} ...

Check density of, and densify geometries using the geodesic (great-circle)
calculation for accurate CRS transformations

Commands:
  {densify,check-density}

Options:
  -h, --help            show this help message and exit

Created by https://www.nsgi.nl/
```
