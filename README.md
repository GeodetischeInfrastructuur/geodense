# geodense

[![Endpoint Badge](https://img.shields.io/endpoint?url=https%3A%2F%2Fgeodetischeinfrastructuur.github.io%2Fgeodense%2Fbadge.json&style=flat-square&logo=pytest&logoColor=white)](https://geodetischeinfrastructuur.github.io/geodense/)

Python library and CLI tool to **check density** and **densify** linestring and polygon geometries using the geodesic (ellipsoidal great-circle) calculation.

Implementation based on [*Eenduidige transformatie van grenzen tussen ETRS89 en RD*](https://geoforum.nl/uploads/default/original/2X/c/c0795baa683bf3845c866ae4c576a880455be02a.pdf)

See the following flowchart for a highlevel schematic overview of the `densify` functionality of `geodense`:

```mermaid
flowchart
    input([fa:fa-database input data]) --> p_1[get input-crs]
    p_1 --> d_1{input-crs<br>type and<br>densification method}
    d_1 -->|geographic and linear| output_error([fa:fa-exclamation-triangle error: cannot do linear densification<br> on data in a geographic crs])
    d_1 -->|geographic and geodesic| p_3
    d_1 -->|projected and linear| p_4[linear densify in input-crs]
    d_1 -->|projected and geodesic| p_2    
    p_4-->d_4
    p_3["geodesic densify with<br>ellipse of input-crs or base-geographic-crs"]
    p_2[convert to LatLon in<br>base-geographic-crs<br> of input-crs]
    p_2 --> p_3
    p_3-->d_4{input-crs<br>type and<br>densification method}
    d_4 -->|projected and geodesic| p_5[convert back to input-crs]
    p_5 -->output
    d_4 -->|geographic and geodesic| output([fa:fa-database output data])
    d_4 -->|projected and linear| output
    style output_error stroke: red,stroke-width:2px
    style output stroke: green,stroke-width:2px
```

## Installation

To install from source check out this repository and run from the root:

```sh
pip install .
```

## Development

> **TODO**: add description how to setup dev environment with conda/miniconda and libmamba solver, and install pyproj with: `conda install -c conda-forge  pyproj==3.6.0 --solver=libmamba`


Requires Python v3.9 or higher (due to dependency on [pyproj](https://pyproj4.github.io/pyproj/stable/) v3.6.0).

Install/uninstall for development:

```sh
pip install -e .
pip uninstall geodense
```

Install dev dependencies with:

```sh
pip install ".[dev]"
```

Check test coverage (install `coverage` with `pip install coverage` ):

```sh
python -m coverage run -p --source=src/geodense -m pytest -v tests && python -m  coverage report -m
```

## Usage CLI

Use either `geodense` or the short `gden` alias:

```txt
$ geodense --help

Usage: geodense [-h] {list-formats,densify,check-density} ...

Check density of, and densify geometries using the geodesic (ellipsoidal great-circle)
calculation for accurate CRS transformations

Commands:
  {list-formats,densify,check-density}

Options:
  -h, --help            show this help message and exit

Created by https://www.nsgi.nl/
```
