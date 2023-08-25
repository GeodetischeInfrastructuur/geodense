# lange-lijnstukken-advies-lib

Eventual goal is to implement the following [document](https://geoforum.nl/uploads/default/original/2X/c/c0795baa683bf3845c866ae4c576a880455be02a.pdf) as:

- validator - check if geometries do not contain line segments longer than threshold
- geometry-fixer - fix geometries with line segments longer than threshold

## Development

Install/uninstall for development:


```sh
pip install -e .

pip uninstall lange-lijnstukken-advies
```


## Usage CLI

```sh
lla --help
usage: lange-lijnstukken-advies (lla) [-h] input_file output_file

Geometrie controle en reparatie tbv CRS transformatie van ETRS89 en RD

positional arguments:
  input_file
  output_file

options:
  -h, --help   show this help message and exit
```


