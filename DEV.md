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

### direnv config

Repository also contains a [`.envrc`](https://direnv.net/) config file, which automatically activates the `uv` managed
virtual environment. See the [direnv wiki](https://github.com/direnv/direnv/wiki/Python#uv) for how to set this up.

## Tests

Run tests:

```sh
pytest tests/
```

Check test coverage:

```sh
coverage run -p --source=src/geodense -m pytest -v tests && coverage report --data-file $(ls -t  .coverage.* | head -1)
```

## Creating release

New releases are built and published through the GitHub Action
[_Build and Publish Release_](.github/workflows/python-publish.yaml). The workflow is triggered when a new release is
created in the GitHub repository.

The release workflow:

1. Builds the geodense wheel
2. Attaches it to the GitHub release
3. **Note:** geodense is no longer published to PyPI (as of v3) due to NSGI `pyproj` direct-URL dependency

### Manual build

Create a new build with:

```sh
rm -rf dist/* # clean dist folder before build
uv build --wheel
```

Verify the wheel contents:

```sh
unzip dist/geodense-*.whl -d geodense-whl
tree geodense-whl
rm -rf geodense-whl
```

### Distributing a release

1. Create a new release tag in GitHub (e.g., `v3.0.0`)
2. The _Build and Publish Release_ workflow automatically builds and attaches the wheel
3. Users install via: `uvx --from https://github.com/.../geodense-<version>-py3-none-any.whl geodense`
