import argparse
import logging
import os
import sys
from collections.abc import Callable
from enum import Enum
from functools import wraps
from typing import Any, Literal

from rich_argparse import RichHelpFormatter

from geodense import __version__, add_stderr_logger
from geodense.lib import (
    SUPPORTED_FILE_FORMATS,
    check_density_file,
    densify_file,
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
        except Exception as e:  # unexpected exception, show stacktrace by calling logger.exception
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
def check_density_cmd(  # noqa: PLR0913
    input_file: str,
    max_segment_length: float,
    overwrite: bool = False,
    in_projection: bool = False,
    src_crs: str | None = None,
    density_check_report_path: str | None = None,
) -> None:
    print(overwrite)

    check_status, density_check_report_path, nr_line_segments = check_density_file(
        input_file,
        max_segment_length,
        density_check_report_path,
        src_crs,
        in_projection=in_projection,
        overwrite=overwrite,
    )

    status = "OK" if check_status else "FAILED"
    status_message = f"density-check {status} for file {input_file} with max-segment-length: {max_segment_length}"

    print(status_message)  # print status message for both OK and FAILED status

    if check_status:
        sys.exit(0)
    else:
        print(
            f"{nr_line_segments} line segments in data exceed max-segment-length {max_segment_length}, line segment geometries written to GeoJSON FeatureCollection: {density_check_report_path}"
        )
        sys.exit(1)


def main() -> None:
    input_file_help = (
        "any valid GeoJSON file, accepted GeoJSON objects: FeatureCollection, Feature, Geometry and GeometryCollection "
    )
    source_crs_help = "override source CRS, if not specified then the CRS found in the GeoJSON input file will be used; format: $AUTH:$CODE; for example: EPSG:4326"
    verbose_help = "verbose output"
    max_segment_length_help = f"max allowed segment length in meters; default: {DEFAULT_MAX_SEGMENT_LENGTH}"

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
        description="Densify (multi)polygon and (multi)linestring geometries along the geodesic (ellipsoidal great-circle), in base CRS (geographic) in case of projected source CRS. Supports GeoJSON as input file format. When supplying 3D coordinates, the height is linear interpolated for both geographic CRSs with ellipsoidal height and for compound CRSs with physical height.",
    )
    densify_parser.add_argument(
        "input_file",
        type=lambda x: is_json_file_arg(parser, x, "input_file", exist_required=FileRequired.exist),
        help=input_file_help,
    )
    densify_parser.add_argument(
        "output_file",
        type=lambda x: is_json_file_arg(parser, x, "output_file", exist_required=FileRequired.either),
        help="output file path",
    )

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

    densify_parser.add_argument("-v", "--verbose", action="store_true", default=False, help=verbose_help)

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
        is FAILED the program will return with exit code 1. The density-check report is a GeoJSON FeatureCollection containing line segments exceeding the max-segment-length treshold.",
    )
    check_density_parser.add_argument(
        "input_file",
        type=lambda x: is_json_file_arg(parser, x, "input_file", exist_required=FileRequired.exist),
        help=input_file_help,
    )
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
        "--in-projection",
        "-p",
        action="store_true",
        default=False,
        help="check density using linear interpolation in source projection instead of the geodesic, not applicable when source CRS is geographic",
    )
    check_density_parser.add_argument(
        "--density-check-report-path",
        "-r",
        dest="density_check_report_path",
        required=False,
        help="density-check report path, when omitted a temp file will be used. Report is only generated when density-check fails.",
        metavar="FILE_PATH",
        type=lambda x: is_json_file_arg(parser, x, "density-check-report-path", FileRequired.either),
    )
    check_density_parser.add_argument(
        "--overwrite",
        "-o",
        action="store_true",
        default=False,
        help="overwrite density-check report if exists",
    )
    check_density_parser.add_argument("-v", "--verbose", action="store_true", default=False, help=verbose_help)
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


class FileRequired(Enum):
    exist: Literal["exist"] = "exist"
    not_exist: Literal["not_exist"] = "not_exist"
    either: Literal["either"] = "either"


def is_json_file_arg(
    parser: argparse.ArgumentParser,
    arg: str,
    arg_name: str,
    exist_required: FileRequired,
) -> str:
    _, file_ext = os.path.splitext(arg)
    unsupported_file_extension_msg = (
        "unsupported file extension of {input_file}, received: {ext}, expected one of: {supported_ext}"
    )
    if arg != "-" and file_ext not in SUPPORTED_FILE_FORMATS["GeoJSON"]:
        parser.error(
            unsupported_file_extension_msg.format(
                input_file=arg_name,
                ext=file_ext,
                supported_ext=", ".join(SUPPORTED_FILE_FORMATS["GeoJSON"]),
            )
        )
    if (
        exist_required != FileRequired.either
        and arg != "-"
        and (not os.path.isfile(arg) if exist_required == FileRequired.exist else os.path.isfile(arg))
    ):
        if exist_required:
            parser.error(f"{arg_name} {arg} does not exist")
        else:
            parser.error(f"{arg_name} {arg} exists")

    if (
        arg not in ["", "-"]
        and exist_required in [FileRequired.not_exist, FileRequired.either]
        and not os.path.exists(os.path.realpath(os.path.dirname(arg)))
    ):
        os.mkdir(os.path.realpath(os.path.dirname(arg)))
    return arg


if __name__ == "__main__":
    main()  # pragma: no cover
