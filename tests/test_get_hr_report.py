from geodense.lib import (
    check_density_geometry_coordinates,
    flatten,
    get_cmd_result_message,
)
from geodense.models import DenseConfig
from geodense.types import Nested, ReportLineString
from geojson_pydantic import Feature
from pyproj import CRS


def test_get_empty_hr_report(linestring_feature_multiple_linesegments):
    feature: Feature = linestring_feature_multiple_linesegments
    result = []
    max_segment_length = 20000

    c = DenseConfig(CRS.from_epsg(28992), max_segment_length)
    check_density_geometry_coordinates(feature.geometry.coordinates, c, result)
    cmd_output = get_cmd_result_message("my-file", result, max_segment_length)
    assert (
        cmd_output
        == f"density-check PASSED for file my-file with max-segment-length: {max_segment_length}"
    )


def test_get_hr_report(linestring_feature_multiple_linesegments):
    feature: Feature = linestring_feature_multiple_linesegments

    max_segment_length = 10
    c = DenseConfig(CRS.from_epsg(28992), max_segment_length)
    result: Nested[ReportLineString] = check_density_geometry_coordinates(
        feature.geometry.coordinates, c
    )
    flat_result: list[ReportLineString] = list(flatten(result))

    cmd_output = get_cmd_result_message("my-file", flat_result, max_segment_length)
    assert cmd_output.startswith(
        f"density-check FAILED for file my-file with max-segment-length: {max_segment_length}"
    )
