import argparse
import sys

from rich_argparse import RichHelpFormatter

from geodense.lib import (
    DEFAULT_MAX_SEGMENT_LENGTH,
    check_density,
    densify_geospatial_file,
    get_cmd_result_message,
)


def densify_cmd(
    input_file: str,
    output_file: str,
    max_segment_length: float,
    layer: str,
    in_projection: bool,
):
    densify_geospatial_file(
        input_file, output_file, layer, max_segment_length, in_projection
    )


def check_density_cmd(input_file: str, max_segment_length: float, layer: str):
    result = check_density(input_file, max_segment_length, layer)
    cmd_output = get_cmd_result_message(input_file, result, max_segment_length)

    if len(result) == 0:
        print(cmd_output)
        sys.exit(0)
    else:
        print(cmd_output)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog="geodense",
        description="Check density of, and densify geometries \
using the geodesic (great-circle) calculation for accurate CRS transformations",
        epilog="Created by https://www.nsgi.nl/",
        formatter_class=RichHelpFormatter,
    )

    subparsers = parser.add_subparsers()

    densify_parser = subparsers.add_parser(
        "densify",
        formatter_class=parser.formatter_class,
        description="Densify (multi)polygon and linestring geometries along the great-circle using the GRS 1980 ellipsoid",
    )
    densify_parser.add_argument("input_file", type=str, help="foobar")
    densify_parser.add_argument("output_file", type=str)
    densify_parser.add_argument(
        "--max-segment-length",
        "-m",
        type=float,
        default=DEFAULT_MAX_SEGMENT_LENGTH,
        help=f"max allowed segment length in meters; default {DEFAULT_MAX_SEGMENT_LENGTH} meter",
    )
    densify_parser.add_argument(
        "--layer",
        "-l",
        type=str,
        help="layer to use in multi-layer geospatial input files",
        default="",
    )
    densify_parser.add_argument(
        "--in-projection",
        "-p",
        action="store_true",
        default=False,
        help="densify using source projection, not applicable when source crs is geographic",
    )

    densify_parser.set_defaults(func=densify_cmd)

    check_density_parser = subparsers.add_parser(
        "check-density",
        formatter_class=parser.formatter_class,
        description="Check density of (multi)polygon and linestring geometries. \
        When result of check is OK the program will return with exit code 0, when result \
        is FAILED the program will return with exit code 1.",
    )
    check_density_parser.add_argument("input_file", type=str)
    check_density_parser.add_argument(
        "--max-segment-length",
        "-m",
        type=float,
        default=DEFAULT_MAX_SEGMENT_LENGTH,
        help=f"max allowed segment length in meters; default {DEFAULT_MAX_SEGMENT_LENGTH} meter",
    )
    check_density_parser.add_argument(
        "--layer",
        "-l",
        type=str,
        help="layer to use in multi-layer geospatial input files",
        default="",
    )
    check_density_parser.set_defaults(func=check_density_cmd)

    parser._positionals.title = "commands"
    args = parser.parse_args()

    #     import fiona
    # >>> fiona.supported_drivers
    try:
        func = args.func
        del args.func
        func(**vars(args))
    except AttributeError:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
