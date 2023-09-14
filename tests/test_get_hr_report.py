import json

from geodense.lib import check_density_geometry_coordinates, get_hr_report



def test_get_empty_hr_report(linestring_feature_multiple_linesegments):
    feature = json.loads(linestring_feature_multiple_linesegments)
    result = []
    check_density_geometry_coordinates(
        feature["geometry"]["coordinates"], "EPSG:28992", 20000, result
    )
    report = get_hr_report(result, 20000)
    assert report == ""  # TODO: generate succes message when ok


def test_get_hr_report(linestring_feature_multiple_linesegments):
    feature = json.loads(linestring_feature_multiple_linesegments)
    result = []
    check_density_geometry_coordinates(
        feature["geometry"]["coordinates"], "EPSG:28992", 10, result
    )
    report = get_hr_report(result, 10)
    assert (
        len(report.split("\n")) == len(result) + 1
    )  # check that report contains same nr of lines as result +1
