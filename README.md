# geodense

[![Code
Coverage](https://img.shields.io/endpoint?url=https%3A%2F%2Fgeodetischeinfrastructuur.github.io%2Fgeodense%2Fbadge.json&style=flat-square&logo=pytest&logoColor=white)](https://geodetischeinfrastructuur.github.io/geodense/)
[![Python
3.12+](https://img.shields.io/badge/python-3.12+-teal.svg?style=flat-square)](https://www.python.org/downloads/release/python-3116/)
![License:
MIT](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)
[![PyPI
Version](https://img.shields.io/pypi/v/geodense.svg?style=flat-square)](https://pypi.python.org/pypi/geodense)

Python library and CLI tool to **check density** and **densify** geometries
using the geodesic (ellipsoidal great-circle) calculation for accurate CRS
transformations.

Implementation based on [*Eenduidige transformatie van grenzen tussen ETRS89 en
RD*](https://gnss-data.kadaster.nl/misc/docs/langelijnenadvies.pdf)

Requires Python v3.12 or higher.

Depends on:

- `pyproj ~= 3.7.0` -> [requires libproj>=9.2](https://pyproj4.github.io/pyproj/stable/installation.html)
- `shapely ~= 2.0.6` -> [requires libgeos>=3.9](https://shapely.readthedocs.io/en/stable/index.html)

Installation of binary dependencies (libproj, libgeos) is done through Python package management (`uv`, `pip`), since [PyPI](https://pypi.org/) has binary distributions available for `pyproj` and `shapely`.

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

See
[`DOCS.md`](https://github.com/GeodetischeInfrastructuur/geodense/blob/main/DOCS.md)
for usage docs; for now only containing flow-charts of the `densify` and
`check-densify` subcommands.

## Contributing

Issues (bugs/feature requests) can be reported in the [issue tracker of this
repository](https://github.com/GeodetischeInfrastructuur/geodense/issues). Pull
requests are more than welcome, but we encourage to start a discussion on the
issue tracker first.

## Development

Project uses [uv](https://docs.astral.sh/uv/) for package management. To get started install `uv` and run:

Install dev dependencies with:

```sh
uv sync
```

Enable [pre-commit](https://pre-commit.com/) hooks with:

```sh
pre-commit install
```

### Tests

Run tests:

```sh
pytest tests/
```

Check test coverage:

```sh
coverage run -p --source=src/geodense -m pytest -v tests && python3 -m coverage report --data-file $(ls -t  .coverage.* | head -1)
```

### Create release

Creating a release requires the `build` and `twine` packages, which are part of
this package's `dev` dependencies. To create a release follow these steps:

To release a new version create a new git tag and push the new tag with

```sh
git tag -a x.x.x -m "tagging x.x.x release"
git push --tags
```

Create a new build with:

```sh
rm -rf dist/* # clean dist folder before build
uv build --wheel
```

Check wheel contains expected files:

```sh
unzip dist/geodense-0.0.1a3-py3-none-any.whl -d geodense-whl
tree geodense-whl
rm -rf geodense-whl
```

See [.github/python-publish.yml](.github/python-publish.yml) for how to build an publish package on [PyPI](https://pypi.org/).

> **Note:** requires
> [`~/.pypirc`](https://packaging.python.org/en/latest/specifications/pypirc/)
> file with API token (when 2FA is enabled on [PyPI](https://pypi.org/)).
