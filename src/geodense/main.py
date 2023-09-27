import argparse
import sys

from fiona import supported_drivers
from rich_argparse import RichHelpFormatter

from geodense.lib import (
    DEFAULT_MAX_SEGMENT_LENGTH,
    SUPPORTED_FILE_FORMATS,
    check_density,
    densify_geospatial_file,
    get_cmd_result_message,
)

CLI_ERROR_MESSAGE_TEMPLATE = "ERROR: {message}"


def list_formats_cmd():
    # check if SUPPORTED_FILE_FORMATS are in fiona.supported_drivers
    try:
        unsupported_formats = []
        for key in SUPPORTED_FILE_FORMATS:
            if key not in supported_drivers:
                unsupported_formats.append(key)
        if len(unsupported_formats) > 0:
            supported_formats_string = ", ".join(unsupported_formats)
            raise ValueError(
                f"The following format(s) are not supported by your fiona installation: {supported_formats_string}"
            )

        column_name_length = 15  # max_length + 2 padding
        column_ext_length = 15  # max_length + 2 padding

        print(
            f"{'Name' : <{column_name_length}} | {'Extension' : <{column_ext_length}}"
        )
        print(
            f"{'-'*(column_ext_length + column_name_length + 3)}"
        )  # +3 to account for " | " seperator
        for format in SUPPORTED_FILE_FORMATS:
            print(
                f"{format : <{column_name_length}} | {' ,'.join(SUPPORTED_FILE_FORMATS[format]) : <{column_ext_length}}"
            )
        sys.exit(0)
    except ValueError as e:
        exception_message = str(e)
        error_message = CLI_ERROR_MESSAGE_TEMPLATE.format(message=exception_message)
        print(error_message, file=sys.stderr)
        sys.exit(1)


def densify_cmd(
    input_file: str,
    output_file: str,
    max_segment_length: float,
    layer: str,
    in_projection: bool,
):
    try:
        densify_geospatial_file(
            input_file, output_file, layer, max_segment_length, in_projection
        )
    except ValueError as e:
        print(CLI_ERROR_MESSAGE_TEMPLATE.format(message=str(e)), file=sys.stderr)
        sys.exit(1)


def check_density_cmd(input_file: str, max_segment_length: float, layer: str):
    try:
        result = check_density(input_file, max_segment_length, layer)
        cmd_output = get_cmd_result_message(input_file, result, max_segment_length)

        if len(result) == 0:
            print(cmd_output)
            sys.exit(0)
        else:
            print(cmd_output)
            sys.exit(1)

    except ValueError as e:
        print(CLI_ERROR_MESSAGE_TEMPLATE.format(message=str(e)), file=sys.stderr)
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

    list_formats_parser = subparsers.add_parser(
        "list-formats",
        formatter_class=parser.formatter_class,
        description="List supported file formats for reading and writing. File format is determined based on the extension of the input_file and output_file.",
    )
    list_formats_parser.set_defaults(func=list_formats_cmd)

    densify_parser = subparsers.add_parser(
        "densify",
        formatter_class=parser.formatter_class,
        description="Densify (multi)polygon and (multi)linestring geometries along the great-circle using the GRS 1980 ellipsoid. See the list-formats command for a list of supported file formats. File format of input_file and output_file should match.",
    )
    densify_parser.add_argument("input_file", type=str)
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
        description="Check density of (multi)polygon and (multi)linestring geometries. \
        When result of check is OK the program will return with exit code 0, when result \
        is FAILED the program will return with exit code 1. See the list-formats command for a list of supported file formats.",
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

    try:
        func = args.func
        del args.func
        func(**vars(args))
    except AttributeError:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()  # pragma: no cover
