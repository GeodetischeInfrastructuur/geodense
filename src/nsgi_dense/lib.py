import math
import os
from typing import Tuple
import fiona
from pyproj import CRS, Geod, Transformer
from shapely import LineString, Point

TRANFORM_CRS = "EPSG:4258"
ELLIPS = "GRS80"
SUPPORTED_GEOM_TYPES = [
            "LineString",
            "Polygon",
            "MultiPolygon",
            "MultiLinestring",
        ]

def transform_point(source_crs: str, target_crs: str, val: Tuple[float, float]):
    source_crs_crs = CRS.from_authority(*source_crs.split(":"))
    target_crs_crs = CRS.from_authority(*target_crs.split(":"))
    transformer = Transformer.from_crs(source_crs_crs, target_crs_crs, always_xy=True)
    return transformer.transform(*val)


def check_density_linestring(linestring_coordinates, crs: str, max_segment_length, indices):
    result = []
    for k in range(0, len(linestring_coordinates) - 1):
        a = linestring_coordinates[k]
        b = linestring_coordinates[k + 1]
        a_t = transform_point(crs, TRANFORM_CRS, a)
        b_t = transform_point(crs, TRANFORM_CRS, b)
        g = Geod(ellps=ELLIPS)
        _, _, geod_dist = g.inv(*a_t, *b_t, return_back_azimuth=True)
        if geod_dist > max_segment_length:
            report_indices = indices + [k]
            result.append((report_indices,geod_dist))
    return result


def check_density_geometry_coordinates(
    geometry_coordinates, input_crs, max_segment_length, result, indices=[],
):
    if len(geometry_coordinates) > 0 and isinstance(
        geometry_coordinates[0], tuple
    ):  # check if at linestring level in coordinates array - list[typle[float,float]]
        linestring_report = check_density_linestring(geometry_coordinates, input_crs, max_segment_length, indices)
        result.extend(linestring_report)
    else:
        [
            check_density_geometry_coordinates(
                e, input_crs, max_segment_length, result, indices + [i]
            )
            for i, e in enumerate(geometry_coordinates)
        ]


def interpolate_src_proj(a, b, max_segment_length):
    dist = math.sqrt((b[0]-a[0])**2 + (b[1]-a[1])**2) # Pythagoras
    if dist <= max_segment_length:
        return [a, b]
    else:
        npts = int(dist // max_segment_length)
        new_segment_length = dist/npts # spread points evenly over distance
        new_points = []
        for i in range(0, npts):
            p_point: Point= LineString([a, b]).interpolate(new_segment_length*(i+1))
            p = tuple(p_point.coords[0])
            new_points.append(p)
        return [
            a,
            *new_points,
            b,
        ]

def interpolate_geodetic(a, b, max_segment_length, input_crs: str):
    a_t = transform_point(input_crs, TRANFORM_CRS, a)
    b_t = transform_point(input_crs, TRANFORM_CRS, b)
    g = Geod(ellps=ELLIPS)
    az12, _, dist = g.inv(*a_t, *b_t, return_back_azimuth=True)
    if dist <= max_segment_length:
        return [a, b]
    else:
        npts = dist // max_segment_length
        r = g.fwd_intermediate(*a_t, az12, npts=npts, del_s=max_segment_length, return_back_azimuth=True)
        return [
            transform_point(TRANFORM_CRS, input_crs, (lon, lat))
            for lon, lat in zip(r.lons, r.lats)
        ]


def add_vertices_to_line_segment(
    ft_linesegment, coord_index: int, treshold: float, input_crs: str, densify_in_projection:bool
):
    a = ft_linesegment[coord_index]
    b = ft_linesegment[coord_index + 1]

    if not densify_in_projection:
        p = interpolate_geodetic(a, b, treshold, input_crs)
    else:
        p = interpolate_src_proj(a, b, treshold)

    result = ft_linesegment
    result[coord_index + 1 : coord_index + 1] = p
    return len(p)


def add_vertices_exceeding_max_segment_length(
    linestring,
    max_segment_length: float,
    input_crs: str,
    densify_in_projection: bool
):
    added_nodes = 0
    stop = len(linestring) - 1
    for i, _ in enumerate(linestring[:stop]):
        added_nodes += add_vertices_to_line_segment(
            linestring, i + added_nodes, max_segment_length, input_crs,densify_in_projection
        )
    return linestring


def transfrom_linestrings_in_geometry_coordinates(
    geometry_coordinates, input_crs, max_segment_length, transform_fun, densify_in_projection:bool=False
):
    if len(geometry_coordinates) > 0 and isinstance(
        geometry_coordinates[0], tuple
    ):  # check if at linestring level in coordinates array - list[typle[float,float]] - TODO: improve on checking on generic type
        geometry_coordinates = transform_fun(
            geometry_coordinates, max_segment_length, input_crs, densify_in_projection
        )
        return geometry_coordinates
    else:
        return [
            transfrom_linestrings_in_geometry_coordinates(
                e, input_crs, max_segment_length, transform_fun, densify_in_projection
            )
            for e in geometry_coordinates
        ]

def get_layer_name(input_file, layer):
    layers = fiona.listlayers(input_file)
    if len(layers) > 1 and layer == "":
        raise ValueError(
            f"input_file {input_file} contains more than 1 layers: {layers}, specifiy which layer to use with optional layer argument"
        )
    if layer is None:  # input_file contains one layer
        layer = layers[0]
    return layer

def geom_type_check(profile, geom_type):
    if geom_type not in SUPPORTED_GEOM_TYPES:
        raise ValueError(
                f"Unsupported GeometryType  {profile['schema']['geometry']}, supported GeometryTypes are: {' '.join(SUPPORTED_GEOM_TYPES)}"
            )


def check_density(input_file, max_segment_length, layer):
    layer = get_layer_name(input_file, layer)

    with fiona.open(input_file, layer=layer) as src:
        profile = src.profile
        geom_type = profile["schema"]["geometry"]
        crs = str(profile["crs"])
        geom_type_check(profile, geom_type)

        report = []
        for i, ft in enumerate(src):
            check_density_geometry_coordinates(ft.geometry.coordinates,crs, max_segment_length,report, [i] )
    return report


def get_hr_report(report: list[tuple[list[int], float]], max_segment_length):
    if len(report) == 0:
        return ""

    hr_report = f"feature(s) detected which contain line-segments(s) exceed max-segment-length ({max_segment_length}):\n\n"
    for item in report:
        ft_index, coordinates_indices = item[0][:1], item[0][1:]
        distance = item[1]
        ft_report = f"features{ft_index}.geometry.segments[{', '.join([str(x) for x  in coordinates_indices])}], distance: {distance}\n"
        hr_report += ft_report
    return hr_report


def crs_is_geographic(crs_string: str) -> bool:
    crs = CRS.from_authority(*crs_string.split(":"))
    return crs.is_geographic



def densify_geospatial_file(input_file, output_file, max_segment_length, layer="", densify_in_projection=False):
    layer = get_layer_name(input_file, layer)
    _, output_file_ext = os.path.splitext(output_file)
    single_layer_file_ext = [".json", ".geojson"]

    with fiona.open(input_file, layer=layer) as src:
        profile = src.profile
        geom_type = profile["schema"]["geometry"]
        crs = str(profile["crs"])

        if densify_in_projection and crs_is_geographic(crs):
            raise ValueError(f"densify_in_projection can only be used with projected coordinates reference systems, crs {crs} is a geographic crs")

        geom_type_check(profile, geom_type)

        with fiona.open(
            output_file, "w", **profile, layer=layer
        ) if output_file_ext not in single_layer_file_ext else fiona.open(
            output_file, "w", **profile
        ) as dst:
            for i, ft in enumerate(src):
                try:
                    coordinates_t = transfrom_linestrings_in_geometry_coordinates(
                        ft.geometry.coordinates,
                        crs,
                        max_segment_length,
                        add_vertices_exceeding_max_segment_length,
                        densify_in_projection
                    )
                    geom = fiona.Geometry(coordinates=coordinates_t, type=geom_type)
                    dst.write(fiona.Feature(geometry=geom, properties=ft.properties))
                except Exception as e:
                    raise ValueError(
                        f"Unexpected error occured while processing feature [{i}]"
                    ) from e


