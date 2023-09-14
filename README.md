# geodense


Eventual goal is to implement the following [document](https://geoforum.nl/uploads/default/original/2X/c/c0795baa683bf3845c866ae4c576a880455be02a.pdf) as:

- check-density - check if geometries do not contain line segments longer than the max-line-segment threshold
- densify - add vertices to line segments of geometries that exceed the max-line-segment threshold

## Development

Requires Python v3.9 or higher (due to dependency on pyproj v3.6.0).

Install/uninstall for development:

```sh
pip install -e .
pip uninstall geodense
```

Check test coverage (install `coverage` with `pip install coverage`):

```sh
coverage run --source=src/geodense -m pytest -v tests && coverage report -m
```

## Usage CLI

```sh
usage: geodense [-h] {densify,check-density} ...

Check density of, and densify geometries using the geodetic great circle calculation for
accurate CRS transformations

commands:
  {densify,check-density}

options:
  -h, --help            show this help message and exit

Created by https://www.nsgi.nl/
```


