import argparse
import sys

from rich_argparse import RichHelpFormatter

from geodense.lib import check_density, densify_geospatial_file, get_hr_report


def densify_cmd(args):
    input_file = args.input_file
    output_file = args.output_file
    max_segment_length = args.max_segment_length
    layer = args.layer
    in_projection = args.in_projection
    densify_geospatial_file(
        input_file, output_file, layer, max_segment_length, in_projection
    )


def check_density_cmd(args):
    result = check_density(args.input_file, args.max_segment_length, args.layer)
    hr_report = get_hr_report(result, args.max_segment_length)
    if len(result) == 0:
        sys.exit(0)
    else:
        print(hr_report)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog="geodense",
        description="Check density of, and densify geometries \
using the geodetic great circle calculation for accurate CRS transformations",
        epilog="Created by https://www.nsgi.nl/",
        formatter_class=RichHelpFormatter,
    )

    subparsers = parser.add_subparsers()

    densify_parser = subparsers.add_parser(
        "densify",
        formatter_class=parser.formatter_class,
        description="Densify (multi)polygon and linestring geometries along the great circle using the GRS 1980 ellipsoid",
    )
    densify_parser.add_argument("input_file", type=str)
    densify_parser.add_argument("output_file", type=str)
    densify_parser.add_argument(
        "--max-segment-length",
        "-m",
        type=int,
        default=200,
        help="max allowed segment length in meters",
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
        description="Check density of (multi)polygon and linestring geometries",
    )
    check_density_parser.add_argument("input_file", type=str)
    check_density_parser.add_argument(
        "--max-segment-length",
        "-m",
        type=int,
        default=200,
        help="max allowed segment length in meters",
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

    try:
        args.func(args)
    except AttributeError:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
