# geodense Developer docs

## Setup Dev Env

Project uses [uv](https://docs.astral.sh/uv/) for package management. To get started install `uv` and install dev
dependencies with:

```sh
uv sync
```

Enable [pre-commit](https://pre-commit.com/) hooks with:

```sh
pre-commit install
```

## direnv config

Repository also contains a [`.direnv`](https://direnv.net/) config file, which automatically activates the `uv` managed
virtual environment. See the [direnv wiki](https://github.com/direnv/direnv/wiki/Python#uv) for how to set this up.

## Tests

Run tests:

```sh
pytest tests/
```

Check test coverage:

```sh
coverage run -p --source=src/geodense -m pytest -v tests && python3 -m coverage report --data-file $(ls -t  .coverage.* | head -1)
```

## Creating release

New releases are build and published through the Github Action
[_Build and Publish to PyPI_](.github/workflows/python-publish.yaml). Workflow is triggered when a new release is
created in this Github repository.

### Manual build

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
