import json

from geodense.lib import check_density_geometry_coordinates, get_cmd_result_message

# TODO: add test to test content of error message


def test_get_empty_hr_report(linestring_feature_multiple_linesegments):
    feature = json.loads(linestring_feature_multiple_linesegments)
    result = []
    max_segment_length = 20000
    check_density_geometry_coordinates(
        feature["geometry"]["coordinates"], "EPSG:28992", max_segment_length, result
    )
    cmd_output = get_cmd_result_message("my-file", result, max_segment_length)
    assert (
        cmd_output
        == f"density-check PASSED for file my-file with max-segment-length: {max_segment_length}"
    )


def test_get_hr_report(linestring_feature_multiple_linesegments):
    feature = json.loads(linestring_feature_multiple_linesegments)
    result = []
    max_segment_length = 10
    check_density_geometry_coordinates(
        feature["geometry"]["coordinates"], "EPSG:28992", max_segment_length, result
    )
    cmd_output = get_cmd_result_message("my-file", result, max_segment_length)
    assert cmd_output.startswith(
        f"density-check FAILED for file my-file with max-segment-length: {max_segment_length}"
    )
