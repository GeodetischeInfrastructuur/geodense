# geodense

[![Code Coverage](https://img.shields.io/endpoint?url=https%3A%2F%2Fgeodetischeinfrastructuur.github.io%2Fgeodense%2Fbadge.json&style=flat-square&logo=pytest&logoColor=white)](https://geodetischeinfrastructuur.github.io/geodense/) [![Python 3.11+](https://img.shields.io/badge/python-3.11+-teal.svg?style=flat-square)](https://www.python.org/downloads/release/python-3116/) ![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)

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

## Contributing

Issues (bugs/feature requests) can be reported in the [issue tracker of this repository](https://github.com/GeodetischeInfrastructuur/geodense/issues). Pull requests are more than welcome, but we encourage to start a discussion on the issue tracker first.

## Development

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


### Create release

Creating a release requires the `build` and `twine` packages, which are part of this package's `dev` dependencies. To create a release follow these steps:


1. To release a new version create a new git tag and push the new tag with:

```sh
git tag -a x.x.x -m "tagging x.x.x release"
git push --tags
```

2. Create a new build with:

```sh
rm -rf dist/* # clean dist folder before build
python -m build
```

3. Check wheel contains expected files:

```sh
unzip dist/geodense-0.0.1a3-py3-none-any.whl -d geodense-whl
tree geodense-whl
rm -rf geodense-whl
```

4. Check whether package description will render properly on PyPI:

```sh
twine check dist/*
```

5. Upload release to pypi:

```sh
twine upload -r testpypi dist/*
```

> **Note:** requires [`~/.pypirc`](https://packaging.python.org/en/latest/specifications/pypirc/) file with API token (when 2FA is enabled on PyPi).
