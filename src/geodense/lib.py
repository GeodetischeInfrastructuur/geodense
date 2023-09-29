import itertools
import math
import os
import pathlib
from collections.abc import Sequence
from typing import Any, Callable, Optional, Union

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

SUPPORTED_GEOM_TYPES = [
    *SUPPORTED_GEOM_TYPES,
    *[f"3D {x}" for x in SUPPORTED_GEOM_TYPES],
]

DEFAULT_MAX_SEGMENT_LENGTH = 200
DEFAULT_PRECISION_GEOGRAPHIC = 9
DEFAULT_PRECISION_PROJECTED = 4
DEFAULT_PRECISION_DISTANCE = 4
SUPPORTED_FILE_FORMATS = {
    "ESRI Shapefile": [".shp"],
    "FlatGeobuf": [".fgb"],
    "GeoJSON": [".geojson", ".json"],
    "GML": [".gml"],
    "GPKG": [".gpkg"],
}
ERROR_MESSAGE_UNSUPPORTED_FILE_FORMAT = "Argument {arg_name} {file_path} is of an unsupported fileformat, see list-formats for list of supported file formats"
THREE_DIMENSIONAL = 3
point_type = tuple[float, ...]
report_type = list[tuple[list[int], float]]


def transfrom_linestrings_in_geometry_coordinates(
    geometry_coordinates: list[Any],
    transformer: Transformer,
    transform_fun: Callable[
        [list[point_type], float, Transformer, bool], list[point_type]
    ],
    max_segment_length: Optional[float] = None,
    densify_in_projection: bool = False,
) -> list[Any]:
    max_segment_length = abs(max_segment_length or DEFAULT_MAX_SEGMENT_LENGTH)

    _raise_e_if_point_geom(geometry_coordinates)

    if _is_linestring_geom(geometry_coordinates):
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


def check_density_linestring(
    linestring: list[point_type],
    transformer: Transformer,
    max_segment_length: float,
    indices: list[int],
) -> report_type:
    result = []
    for k in range(0, len(linestring) - 1):
        a: point_type = linestring[k]
        b: point_type = linestring[k + 1]

        a_2d = tuple(a[:2])
        b_2d = tuple(b[:2])

        a_t = transformer.transform(*a_2d)  # type: ignore
        b_t = transformer.transform(*b_2d)  # type: ignore
        g = Geod(ellps=ELLIPS)
        _, _, geod_dist = g.inv(*a_t, *b_t, return_back_azimuth=True)  # type: ignore
        if math.isnan(geod_dist):
            raise ValueError(
                f"unable to calculate geodesic distance, result: {geod_dist}, expected: floating-point number"
            )
        if geod_dist > (max_segment_length + 0.001):
            report_indices = [*indices, k]
            result.append((report_indices, geod_dist))
    return result


def check_density_geometry_coordinates(
    geometry_coordinates: list[Any],
    transformer: Transformer,
    max_segment_length: float,
    result: list,
    indices: Optional[list[int]] = None,
) -> None:
    if indices is None:
        indices = []
    _raise_e_if_point_geom(geometry_coordinates)
    if _is_linestring_geom(
        geometry_coordinates
    ):  # check if at linestring level in coordinates array - list[typle[float,float]]
        linestring_report = check_density_linestring(
            geometry_coordinates, transformer, max_segment_length, indices
        )
        result.extend(linestring_report)
    else:
        for i, e in enumerate(geometry_coordinates):
            check_density_geometry_coordinates(
                e, transformer, max_segment_length, result, [*indices, i]
            )


def check_density_file(
    input_file: str, max_segment_length: float, layer: str
) -> report_type:
    if not _file_is_supported_fileformat(input_file):
        raise ValueError(
            ERROR_MESSAGE_UNSUPPORTED_FILE_FORMAT.format(
                file_path=input_file, arg_name="input_file"
            )
        )

    layer = _get_valid_layer_name(input_file, layer)

    with fiona.open(input_file, layer=layer) as src:
        profile = src.profile
        geom_type = profile["schema"]["geometry"]
        crs = str(profile["crs"])
        _geom_type_check(geom_type)
        transformer = _get_transformer(crs, TRANSFORM_CRS)
        report: list[tuple[list[int], float]] = []
        for i, ft in enumerate(src):
            check_density_geometry_coordinates(
                ft.geometry.coordinates, transformer, max_segment_length, report, [i]
            )
    return report


def get_cmd_result_message(
    input_file: str, report: report_type, max_segment_length: float
) -> str:
    status = "PASSED" if len(report) == 0 else "FAILED"
    status_message = f"density-check {status} for file {input_file} with max-segment-length: {max_segment_length}"

    if len(report) == 0:
        return status_message

    hr_report = (
        f"{status_message}\n\n"
        f"Feature(s) detected that contain line-segment(s) "
        f"exceeding max-segment-length ({max_segment_length}):\n"
    )
    for i, item in enumerate(report):
        ft_index, coordinates_indices = item[0][:1], item[0][1:]
        distance = round(item[1], DEFAULT_PRECISION_DISTANCE)
        ft_report = f"  - features{ft_index}.geometry.segments\
 [{', '.join([str(x) for x  in coordinates_indices])}], distance: {distance}"
        if len(report) - 1 != i:
            ft_report += "\n"
        hr_report += ft_report
    return hr_report


def densify_geometry_coordinates(
    geometry_coordinates: list[Any],
    transformer: Transformer,
    max_segment_length: Union[float, None] = None,
    densify_in_projection: bool = False,
) -> list[Any]:
    max_segment_length = abs(max_segment_length or DEFAULT_MAX_SEGMENT_LENGTH)

    return transfrom_linestrings_in_geometry_coordinates(
        geometry_coordinates,
        transformer,
        _add_vertices_exceeding_max_segment_length,
        max_segment_length,
        densify_in_projection,
    )


def densify_geospatial_file(
    input_file_path: str,
    output_file_path: str,
    layer: Optional[str] = None,
    max_segment_length: Optional[float] = None,
    densify_in_projection: bool = False,
) -> None:
    _validate_densify_geospatial_file_file_args(input_file_path, output_file_path)

    _, output_file_ext = os.path.splitext(output_file_path)

    max_segment_length = abs(max_segment_length or DEFAULT_MAX_SEGMENT_LENGTH)
    layer = _get_valid_layer_name(input_file_path, layer)
    single_layer_file_ext = [".json", ".geojson"]

    with fiona.open(input_file_path, layer=layer) as src:
        profile = src.profile
        geom_type = profile["schema"]["geometry"]
        crs = str(profile["crs"])

        if densify_in_projection and _crs_is_geographic(crs):
            raise ValueError(
                f"densify_in_projection can only be used with \
projected coordinates reference systems, crs {crs} is a geographic crs"
            )

        _geom_type_check(geom_type)

        prec = (
            DEFAULT_PRECISION_GEOGRAPHIC
            if _crs_is_geographic(crs)
            else DEFAULT_PRECISION_PROJECTED
        )

        # COORDINATE_PRECISION is only a lco (layer creation option) for OGR GeoJSON driver
        is_geojson_driver = profile["driver"] == "GeoJSON"
        fun_kwargs = {"COORDINATE_PRECISION": prec} if is_geojson_driver else {}

        with fiona.open(
            output_file_path, "w", **profile, layer=layer, **fun_kwargs
        ) if output_file_ext not in single_layer_file_ext else fiona.open(
            output_file_path, "w", **profile, **fun_kwargs
        ) as dst:
            transformer = _get_transformer(crs, TRANSFORM_CRS)
            for i, ft in enumerate(src):
                try:
                    coordinates_t = densify_geometry_coordinates(
                        ft.geometry.coordinates,
                        transformer,
                        max_segment_length,
                        densify_in_projection,
                    )
                    geom = fiona.Geometry(
                        coordinates=coordinates_t, type=geom_type.replace("3D ", "")
                    )
                    new_ft = fiona.Feature(geometry=geom, properties=ft.properties)
                    dst.write(new_ft)
                except Exception as e:
                    raise ValueError(
                        f"Unexpected error occured while processing feature [{i}]: {e}"
                    ) from e


def interpolate_src_proj(
    a: point_type, b: point_type, max_segment_length: float
) -> list[point_type]:
    """Interpolate intermediate points between points a and b, with segment_length < max_segment_length. Only returns intermediate points."""
    dist = math.sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)  # Pythagoras
    if dist <= max_segment_length:
        return []
    else:
        new_points = []

        (
            nr_points,
            new_max_segment_length,
        ) = _get_intermediate_nr_points_and_segment_length(dist, max_segment_length)

        for i in range(0, nr_points):
            p_point: Point = LineString([a, b]).interpolate(
                new_max_segment_length * (i + 1)
            )  # type: ignore
            p = tuple(p_point.coords[0])
            new_points.append(p)
        return [
            *new_points,
        ]


def interpolate_geodesic(
    a: point_type, b: point_type, max_segment_length: float, transformer: Transformer
) -> list[point_type]:
    """geodesic interpolate intermediate points between points a and b, with segment_length < max_segment_length. Only returns intermediate points."""

    three_dimensional_points = (
        len(a) == THREE_DIMENSIONAL and len(b) == THREE_DIMENSIONAL
    )
    a_2d = tuple(a[:2])
    b_2d = tuple(b[:2])

    a_t = transformer.transform(*a_2d)  # type: ignore
    b_t = transformer.transform(*b_2d)  # type: ignore
    g = Geod(ellps=ELLIPS)
    az12, _, dist = g.inv(*a_t, *b_t, return_back_azimuth=True)  # type: ignore
    if dist <= max_segment_length:
        return []
    else:
        (
            nr_points,
            new_max_segment_length,
        ) = _get_intermediate_nr_points_and_segment_length(dist, max_segment_length)
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

        if three_dimensional_points:
            # interpolate height for three_dimensional_points
            height_a = a[2:][0]
            height_b = b[2:][0]
            delta_height_b_a = height_b - height_a
            delta_height_per_point = delta_height_b_a * (new_max_segment_length / dist)
            return [
                tuple(
                    (
                        *back_transformer.transform(lon, lat),
                        (height_a + ((i + 1) * delta_height_per_point)),
                    )
                )
                for i, (lon, lat) in enumerate(zip(r.lons, r.lats))
            ]
        else:
            return [
                back_transformer.transform(lon, lat) for lon, lat in zip(r.lons, r.lats)
            ]


def _is_linestring_geom(geometry_coordinates: list[Any]) -> bool:
    """Check if coordinates are of linestring geometry type.

        - Fiona linestring coordinates are of type: list[tuple[float,float,...]])
        - GeoJSON linestring coordinates are of type: list[list[float]]

    Args:
        geometry_coordinates (list): Fiona or GeoJSON coordinates sequence

    Returns:
        bool: if geometry_coordinates is linestring return True else False
    """
    if (
        len(geometry_coordinates) > 0
        and isinstance(geometry_coordinates[0], Sequence)
        and all(
            isinstance(x, (float, int)) for x in geometry_coordinates[0]
        )  # also test for int just in case...
    ):
        return True
    return False


def _raise_e_if_point_geom(geometry_coordinates: list[Any]) -> None:
    if all(isinstance(x, float) for x in geometry_coordinates):
        raise ValueError(
            "received point geometry coordinates, instead of (multi)linestring"
        )


def _validate_densify_geospatial_file_file_args(
    input_file_path: str, output_file_path: str
) -> None:
    _, input_file_ext = os.path.splitext(input_file_path)
    _, output_file_ext = os.path.splitext(output_file_path)

    if input_file_path == output_file_path:
        raise ValueError(
            f"input_file and output_file arguments must be different, input_file: {input_file_path}, output_file: {output_file_path}"
        )

    if input_file_ext != output_file_ext:
        raise ValueError(
            f"Extension of input_file and output_file need to match, was input_file: {input_file_ext}, output_file: {output_file_ext}"
        )

    if not _file_is_supported_fileformat(input_file_path):
        raise ValueError(
            ERROR_MESSAGE_UNSUPPORTED_FILE_FORMAT.format(
                file_path=input_file_path, arg_name="input_file"
            )
        )
    # no need for check if output_file file format is supported, since check for equality of file format of input_file and output_file is done before file_is_supported_fileformat(input_file) check

    if not os.path.exists(input_file_path):
        raise ValueError(f"input_file {input_file_path} does not exist")

    if not os.path.exists(os.path.realpath(os.path.dirname(output_file_path))):
        raise ValueError(
            f"target directory of output_file {output_file_path} does not exist"
        )

    if os.path.exists(output_file_path):
        raise ValueError(f"output_file {output_file_path} already exists")


def _get_intermediate_nr_points_and_segment_length(
    dist: float, max_segment_length: float
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


def _add_vertices_to_line_segment(
    linestring: list[point_type],
    coord_index: int,
    transformer: Transformer,
    max_segment_length: float,
    densify_in_projection: bool = False,
) -> int:
    """Adds vertices to line segment in place, and returns number of vertices added.

    Args:
        ft_linesegment (_type_): line segment to add vertices
        coord_index (int): coordinate index of line segment to add vertices for
        transformer (Transformer): pyproj transformer
        max_segment_length (float): max segment length, if exceeded vertices will be added
        densify_in_projection (bool): whether to use source projection to densify (not use great-circle distance)

    Returns:
        int: number of added vertices
    """
    a = linestring[coord_index]
    b = linestring[coord_index + 1]
    prec = _get_coord_precision(transformer)
    if not densify_in_projection:
        p = _round_line_segment(
            interpolate_geodesic(a, b, max_segment_length, transformer), prec
        )
    else:
        p = _round_line_segment(interpolate_src_proj(a, b, max_segment_length), prec)

    result = linestring

    result[coord_index] = tuple([round(x, prec) for x in result[coord_index]])
    result[coord_index + 1] = tuple([round(x, prec) for x in result[coord_index + 1]])

    result[coord_index + 1 : coord_index + 1] = p

    return len(p)


def _round_line_segment(
    l_segment: list[point_type], precision: int
) -> list[point_type]:
    return list([tuple(round(y, precision) for y in x) for x in l_segment])


def _add_vertices_exceeding_max_segment_length(
    linestring: list[point_type],
    max_segment_length: float,
    transformer: Transformer,
    densify_in_projection: bool,
) -> list[point_type]:
    added_nodes = 0
    stop = len(linestring) - 1
    for i, _ in enumerate(linestring[:stop]):
        added_nodes += _add_vertices_to_line_segment(
            linestring,
            i + added_nodes,
            transformer,
            max_segment_length,
            densify_in_projection,
        )
    return linestring


def _get_valid_layer_name(input_file: str, layer_name: Optional[str] = None) -> str:  # type: ignore[return]
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
    layers: list[str] = fiona.listlayers(input_file)
    if layer_name is None:
        if len(layers) == 1:
            return layers[0]
        elif len(layers) > 1:
            raise ValueError(
                f"input_file {input_file} contains more than 1 layer: \
{layers}, specify which layer to use with optional layer argument"
            )
        # else: # case len(layers) == 0 not possible, results in fiona.DriverError - so not testable - see # type: ignore[return] on function def
    elif layer_name in layers:
        return layer_name
    else:
        raise ValueError(
            f"layer_name '{layer_name}' not found in file {input_file}, layers: {', '.join(layers)}"
        )


def _geom_type_check(geom_type: str) -> None:
    if geom_type not in SUPPORTED_GEOM_TYPES:
        raise ValueError(
            f"Unsupported GeometryType {geom_type}, supported GeometryTypes are: {', '.join(SUPPORTED_GEOM_TYPES)}"
        )


def _crs_is_geographic(crs_string: str) -> bool:
    crs = CRS.from_authority(*crs_string.split(":"))
    return crs.is_geographic


def _get_coord_precision(transformer: Transformer) -> int:
    if transformer.source_crs is None:
        raise ValueError("transformer.source_crs is None")
    is_geographic = transformer.source_crs.is_geographic
    coord_precision = DEFAULT_PRECISION_PROJECTED
    if is_geographic:
        coord_precision = DEFAULT_PRECISION_GEOGRAPHIC
    return coord_precision


def _get_transformer(source_crs: str, target_crs: str) -> Transformer:
    source_crs_crs = CRS.from_authority(*source_crs.split(":"))
    target_crs_crs = CRS.from_authority(*target_crs.split(":"))
    return Transformer.from_crs(source_crs_crs, target_crs_crs, always_xy=True)


def _get_supported_extensions() -> list[str]:
    return list(itertools.chain.from_iterable(SUPPORTED_FILE_FORMATS.values()))


def _file_is_supported_fileformat(filepath: str) -> bool:
    ext = pathlib.Path(filepath).suffix
    # flatten list of get_driver_by_file_extensionlists
    return ext in _get_supported_extensions()
