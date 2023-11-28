import argparse
import logging
import sys
from collections.abc import Callable
from functools import wraps
from typing import Any

from rich_argparse import RichHelpFormatter

from geodense import __version__, add_stderr_logger
from geodense.lib import (
    check_density_file,
    densify_file,
    get_cmd_result_message,
)
from geodense.models import DEFAULT_MAX_SEGMENT_LENGTH, GeodenseError

logger = logging.getLogger("geodense")


def cli_exception_handler(f: Callable) -> Callable:
    @wraps(f)
    def decorated(*args, **kwargs) -> Any:  # noqa: ANN002, ANN003, ANN401
        try:
            return f(*args, **kwargs)
        except GeodenseError as e:
            logger.error(e)
            sys.exit(1)
        except (
            Exception
        ) as e:  # unexpected exception, show stacktrace by calling logger.exception
            logger.exception(e)
            sys.exit(1)

    return decorated


@cli_exception_handler
def densify_cmd(  # noqa: PLR0913
    input_file: str,
    output_file: str,
    overwrite: bool = False,
    max_segment_length: float | None = None,
    in_projection: bool = False,
    src_crs: str | None = None,
) -> None:
    densify_file(
        input_file,
        output_file,
        overwrite,
        max_segment_length,
        in_projection,
        src_crs,
    )


@cli_exception_handler
def check_density_cmd(
    input_file: str,
    max_segment_length: float,
    src_crs: str | None = None,
) -> None:
    result = check_density_file(input_file, max_segment_length, src_crs)
    cmd_output = get_cmd_result_message(input_file, result, max_segment_length)

    if len(result) == 0:
        print(cmd_output)
        sys.exit(0)
    else:
        print(cmd_output)
        sys.exit(1)


def main() -> None:
    source_crs_help = "override source CRS, if not specified then the CRS found in the input layer will be used; format: $AUTH:$CODE; for example: EPSG:4326"
    verbose_help = "verbose output"
    max_segment_length_help = (
        f"max allowed segment length in meters; default: {DEFAULT_MAX_SEGMENT_LENGTH}"
    )

    parser = argparse.ArgumentParser(
        prog="geodense",
        description="Check density and densify geometries using the geodesic (ellipsoidal great-circle) calculation for accurate CRS transformations",
        epilog="Created by https://www.nsgi.nl/",
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument("-v", "--version", action="version", version=__version__)
    subparsers = parser.add_subparsers()

    densify_parser = subparsers.add_parser(
        "densify",
        formatter_class=parser.formatter_class,
        description="Densify (multi)polygon and (multi)linestring geometries along the geodesic (ellipsoidal great-circle), in base CRS (geographic) in case of projected source CRS.Supports GeoJSON as input file format. When supplying 3D coordinates, the height is linear interpolated for both geographic CRSs with ellipsoidal height and for compound CRSs with physical height.",
    )
    densify_parser.add_argument("input_file", type=str)
    densify_parser.add_argument("output_file", type=str)

    densify_parser.add_argument(
        "--max-segment-length",
        "-m",
        type=float,
        default=DEFAULT_MAX_SEGMENT_LENGTH,
        help=max_segment_length_help,
    )

    densify_parser.add_argument(
        "--in-projection",
        "-p",
        action="store_true",
        default=False,
        help="densify using linear interpolation in source projection instead of the geodesic, not applicable when source CRS is geographic",
    )
    densify_parser.add_argument(
        "--overwrite",
        "-o",
        action="store_true",
        default=False,
        help="overwrite output file if exists",
    )

    densify_parser.add_argument(
        "-v", "--verbose", action="store_true", default=False, help=verbose_help
    )

    densify_parser.add_argument(
        "--src-crs",
        "-s",
        type=str,
        help=source_crs_help,
        default=None,
    )

    densify_parser.set_defaults(func=densify_cmd)

    check_density_parser = subparsers.add_parser(
        "check-density",
        formatter_class=parser.formatter_class,
        description="Check density of (multi)polygon and (multi)linestring geometries based on geodesic (ellipsoidal great-circle) distance, in base CRS (geographic) in case of projected source CRS. \
        When result of check is OK the program will return with exit code 0, when result \
        is FAILED the program will return with exit code 1.",
    )
    check_density_parser.add_argument("input_file", type=str)
    check_density_parser.add_argument(
        "--max-segment-length",
        "-m",
        type=float,
        default=DEFAULT_MAX_SEGMENT_LENGTH,
        help=max_segment_length_help,
    )
    check_density_parser.add_argument(
        "--src-crs",
        "-s",
        type=str,
        help=source_crs_help,
        default=None,
    )

    check_density_parser.add_argument(
        "-v", "--verbose", action="store_true", default=False, help=verbose_help
    )
    check_density_parser.set_defaults(func=check_density_cmd)

    parser._positionals.title = "commands"
    args = parser.parse_args()

    try:
        add_stderr_logger(args.verbose)
        del args.verbose
        func = args.func
        del args.func
        func(**vars(args))
    except AttributeError as _:
        parser.print_help(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()  # pragma: no cover
