import json
import math
import os
import re
from collections.abc import Sequence
from typing import Union

import fiona
from pyproj import CRS, Geod, Transformer
from shapely import LineString, Point

TRANSFORM_CRS = "EPSG:4258"
ELLIPS = "GRS80"
SUPPORTED_GEOM_TYPES = [
    "LineString",
    "Polygon",
    "MultiPolygon",
    "MultiLineString",
]
DEFAULT_MAX_SEGMENT_LENGTH = 200
DEFAULT_PRECISION_GEOGRAPHIC = 9
DEFAULT_PRECISION_PROJECTED = 4


def transfrom_linestrings_in_geometry_coordinates(
    geometry_coordinates,
    transformer,
    transform_fun,
    max_segment_length: Union[int, None] = None,
    densify_in_projection: bool = False,
):
    max_segment_length = abs(max_segment_length or DEFAULT_MAX_SEGMENT_LENGTH)

    raise_e_if_point_geom(geometry_coordinates)

    if is_linestring_geom(geometry_coordinates):
        geometry_coordinates = transform_fun(
            geometry_coordinates, max_segment_length, transformer, densify_in_projection
        )
        return geometry_coordinates
    else:
        return [
            transfrom_linestrings_in_geometry_coordinates(
                e, transformer, transform_fun, max_segment_length, densify_in_projection
            )
            for e in geometry_coordinates
        ]


def is_linestring_geom(geometry_coordinates: list) -> bool:
    """Check if coordinates are of linestring geometry type.
        - Fiona linestring coordinates are of type: list[tuple[float,float,...]])
        - GeoJSON linestring coordinates are of type: list[list[float]]

        Raises exception if 3D geometry is encountered.

    Args:
        geometry_coordinates (list): Fiona or GeoJSON coordinates sequence

    Returns:
        bool: if geometry_coordinates is linestring geometry return True else False
    """
    if (
        len(geometry_coordinates) > 0
        and isinstance(geometry_coordinates[0], Sequence)
        and all(isinstance(x, float) for x in geometry_coordinates[0])
    ):
        three_dimensional = 3
        if len(geometry_coordinates[0]) == three_dimensional:
            raise ValueError("3 dimensional geometries are not supported")
        return True


def raise_e_if_point_geom(geometry_coordinates):
    if all(isinstance(x, float) for x in geometry_coordinates):
        raise ValueError(
            "received point geometry coordinates, instead of (multi)linestring"
        )


def densify_geometry_coordinates(
    coordinates,
    transformer,
    max_segment_length: Union[int, None] = None,
    densify_in_projection: bool = False,
):
    max_segment_length = abs(max_segment_length or DEFAULT_MAX_SEGMENT_LENGTH)

    return transfrom_linestrings_in_geometry_coordinates(
        coordinates,
        transformer,
        add_vertices_exceeding_max_segment_length,
        max_segment_length,
        densify_in_projection,
    )


def densify_geospatial_file(
    input_file,
    output_file,
    layer="",
    max_segment_length: Union[int, None] = None,
    densify_in_projection: bool = False,
):
    max_segment_length = abs(max_segment_length or DEFAULT_MAX_SEGMENT_LENGTH)

    layer = get_valid_layer_name(input_file, layer)
    _, output_file_ext = os.path.splitext(output_file)
    single_layer_file_ext = [".json", ".geojson"]

    with fiona.open(input_file, layer=layer) as src:
        profile = src.profile
        geom_type = profile["schema"]["geometry"]
        crs = str(profile["crs"])

        if densify_in_projection and crs_is_geographic(crs):
            raise ValueError(
                f"densify_in_projection can only be used with \
projected coordinates reference systems, crs {crs} is a geographic crs"
            )

        geom_type_check(geom_type)

        with fiona.open(
            output_file, "w", **profile, layer=layer
        ) if output_file_ext not in single_layer_file_ext else fiona.open(
            output_file, "w", **profile
        ) as dst:
            transformer = get_transformer(crs, TRANSFORM_CRS)
            for i, ft in enumerate(src):
                try:
                    coordinates_t = densify_geometry_coordinates(
                        ft.geometry.coordinates,
                        transformer,
                        max_segment_length,
                        densify_in_projection,
                    )
                    geom = fiona.Geometry(coordinates=coordinates_t, type=geom_type)
                    dst.write(fiona.Feature(geometry=geom, properties=ft.properties))
                except Exception as e:
                    raise ValueError(
                        f"Unexpected error occured while processing feature [{i}]"
                    ) from e


def get_intermediate_nr_points_and_segment_length(
    dist, max_segment_length
) -> tuple[int, float]:
    if dist <= max_segment_length:
        raise ValueError(
            f"max_segment_length ({max_segment_length}) cannot be bigger or equal than dist ({dist})"
        )

    remainder = dist % max_segment_length
    nr_segments = int(dist // max_segment_length)
    if remainder > 0:
        nr_segments += 1
    new_max_segment_length = dist / nr_segments  # space segments evenly over delta(a,b)
    nr_points = (
        nr_segments - 1
    )  # convert nr of segments to nr of intermediate points, should be at least 1
    return nr_points, new_max_segment_length


def interpolate_src_proj(a, b, max_segment_length):
    """Interpolate intermediate points between points a and b, with segment_length < max_segment_length. Only returns intermediate points."""
    dist = math.sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)  # Pythagoras
    if dist <= max_segment_length:
        return []
    else:
        new_points = []

        (
            nr_points,
            new_max_segment_length,
        ) = get_intermediate_nr_points_and_segment_length(dist, max_segment_length)

        for i in range(0, nr_points):
            p_point: Point = LineString([a, b]).interpolate(
                new_max_segment_length * (i + 1)
            )  # type: ignore
            p = tuple(p_point.coords[0])
            new_points.append(p)
        return [
            *new_points,
        ]


def interpolate_geodesic(a, b, max_segment_length, transformer: Transformer):
    """geodesic interpolate intermediate points between points a and b, with segment_length < max_segment_length. Only returns intermediate points."""
    a_t = transformer.transform(*a)
    b_t = transformer.transform(*b)
    g = Geod(ellps=ELLIPS)
    az12, _, dist = g.inv(*a_t, *b_t, return_back_azimuth=True)  # type: ignore
    if dist <= max_segment_length:
        return []
    else:
        (
            nr_points,
            new_max_segment_length,
        ) = get_intermediate_nr_points_and_segment_length(dist, max_segment_length)
        r = g.fwd_intermediate(
            *a_t,
            az12,
            npts=nr_points,
            del_s=new_max_segment_length,
            return_back_azimuth=True,
        )  # type: ignore

        back_transformer = Transformer.from_crs(
            transformer.target_crs, transformer.source_crs, always_xy=True
        )
        return [
            back_transformer.transform(lon, lat) for lon, lat in zip(r.lons, r.lats)
        ]


def add_vertices_to_line_segment(
    ft_linesegment,
    coord_index: int,
    transformer: Transformer,
    max_segment_length: float,
    densify_in_projection: bool,
):
    a = ft_linesegment[coord_index]
    b = ft_linesegment[coord_index + 1]
    prec = get_coord_precision(transformer)
    if not densify_in_projection:
        p = round_line_segment(
            interpolate_geodesic(a, b, max_segment_length, transformer), prec
        )
    else:
        p = round_line_segment(interpolate_src_proj(a, b, max_segment_length), prec)

    result = ft_linesegment

    result[coord_index] = tuple([round(x, prec) for x in result[coord_index]])
    result[coord_index + 1] = tuple([round(x, prec) for x in result[coord_index + 1]])

    result[coord_index + 1 : coord_index + 1] = p

    return len(p)


def round_line_segment(l_segment, precision):
    return list([tuple(round(y, precision) for y in x) for x in l_segment])


def add_vertices_exceeding_max_segment_length(
    linestring,
    max_segment_length: float,
    transformer: Transformer,
    densify_in_projection: bool,
):
    added_nodes = 0
    stop = len(linestring) - 1
    for i, _ in enumerate(linestring[:stop]):
        added_nodes += add_vertices_to_line_segment(
            linestring,
            i + added_nodes,
            transformer,
            max_segment_length,
            densify_in_projection,
        )
    return linestring


def check_density_linestring(
    linestring_coordinates, transformer: Transformer, max_segment_length, indices
):
    result = []
    for k in range(0, len(linestring_coordinates) - 1):
        a = linestring_coordinates[k]
        b = linestring_coordinates[k + 1]
        a_t = transformer.transform(*a)
        b_t = transformer.transform(*b)
        g = Geod(ellps=ELLIPS)
        _, _, geod_dist = g.inv(*a_t, *b_t, return_back_azimuth=True)  # type: ignore
        if geod_dist > (max_segment_length + 0.001):
            report_indices = [*indices, k]
            result.append((report_indices, geod_dist))
    return result


def check_density_geometry_coordinates(
    geometry_coordinates,
    transformer: Transformer,
    max_segment_length: float,
    result: list,
    indices=None,
):
    if indices is None:
        indices = []
    raise_e_if_point_geom(geometry_coordinates)
    if is_linestring_geom(
        geometry_coordinates
    ):  # check if at linestring level in coordinates array - list[typle[float,float]]
        linestring_report = check_density_linestring(
            geometry_coordinates, transformer, max_segment_length, indices
        )
        result.extend(linestring_report)
    else:
        [
            check_density_geometry_coordinates(
                e, transformer, max_segment_length, result, [*indices, i]
            )
            for i, e in enumerate(geometry_coordinates)
        ]


def check_density(input_file, max_segment_length, layer):
    layer = get_valid_layer_name(input_file, layer)

    with fiona.open(input_file, layer=layer) as src:
        profile = src.profile
        geom_type = profile["schema"]["geometry"]
        crs = str(profile["crs"])
        geom_type_check(geom_type)
        transformer = get_transformer(crs, TRANSFORM_CRS)
        report = []
        for i, ft in enumerate(src):
            check_density_geometry_coordinates(
                ft.geometry.coordinates, transformer, max_segment_length, report, [i]
            )
    return report


def get_cmd_result_message(
    input_file: str, report: list[tuple[list[int], float]], max_segment_length
) -> str:
    status = "PASSED" if len(report) == 0 else "FAILED"
    status_message = f"density-check {status} for file {input_file} with max-segment-length: {max_segment_length}"

    if len(report) == 0:
        return status_message

    hr_report = (
        f"{status_message}\n\n"
        f"Feature(s) detected which contain line-segments(s) "
        f"exceed max-segment-length ({max_segment_length}):\n"
    )
    for i, item in enumerate(report):
        ft_index, coordinates_indices = item[0][:1], item[0][1:]
        distance = item[1]
        ft_report = f"  - features{ft_index}.geometry.segments\
 [{', '.join([str(x) for x  in coordinates_indices])}], distance: {distance}"
        if len(report) - 1 != i:
            ft_report += "\n"
        hr_report += ft_report
    return hr_report


def get_valid_layer_name(input_file, layer_name=""):
    """
    Check if layer_name exists in input_file, or when layer_name is empty get layer_name from only layer in input_file.

    Args:
        input_file (str): filepath to geospatial file
        layer_name (str, optional): layer_name to check, when left empty function
                                    checks if there is only 1 layer in the file.
                                    Defaults to "".

    Raises:
        ValueError: raised in the following conditions:
            - layer_name == "" and len(input_file.layers) == 0
            - layer_name == "" and len(input_file.layers) > 1
            - layer_name != "" and layer_name not in input_file.layers.name

    Returns:
        str: layer_name that is garantueed to exist in input_file
    """
    layers = fiona.listlayers(input_file)
    if layer_name == "":
        if len(layers) == 1:
            return layers[0]
        elif len(layers) > 1:
            raise ValueError(
                f"input_file {input_file} contains more than 1 layer: \
{layers}, specify which layer to use with optional layer argument"
            )  # case len(layers) == 0 not possible, results in fiona.DriverError
    elif layer_name in layers:
        return layer_name
    else:
        raise ValueError(
            f"layer_name {layer_name} not found in file {input_file}, layers: {', '.join(layers)}"
        )


def geom_type_check(geom_type):
    if geom_type not in SUPPORTED_GEOM_TYPES:
        raise ValueError(
            f"Unsupported GeometryType {geom_type}, supported GeometryTypes are: {', '.join(SUPPORTED_GEOM_TYPES)}"
        )


def crs_is_geographic(crs_string: str) -> bool:
    if re.match(r"\{'init'\:\s'.*'\}", crs_string):
        crs_string = json.loads(crs_string.replace("'", '"'))["init"].upper()

    crs = CRS.from_authority(*crs_string.split(":"))
    return crs.is_geographic


def get_coord_precision(transformer: Transformer):
    is_geographic = transformer.source_crs.is_geographic
    coord_precision = DEFAULT_PRECISION_PROJECTED
    if is_geographic:
        coord_precision = DEFAULT_PRECISION_GEOGRAPHIC
    return coord_precision


def get_transformer(source_crs: str, target_crs: str):
    source_crs_crs = CRS.from_authority(*source_crs.split(":"))
    target_crs_crs = CRS.from_authority(*target_crs.split(":"))
    return Transformer.from_crs(source_crs_crs, target_crs_crs, always_xy=True)
