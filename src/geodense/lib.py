import itertools
import math
import os
import pathlib
import re
import sys
from collections.abc import Sequence
from typing import Any, Callable, Optional

import fiona
from pyproj import CRS, Transformer
from shapely import LineString, Point

from .models import DEFAULT_PRECISION_METERS, DenseConfig

SUPPORTED_GEOM_TYPES = [
    "LineString",
    "Polygon",
    "MultiPolygon",
    "MultiLineString",
    "GeometryCollection",
]

SUPPORTED_GEOM_TYPES = [
    *SUPPORTED_GEOM_TYPES,
    *[f"3D {x}" for x in SUPPORTED_GEOM_TYPES],
]


SUPPORTED_FILE_FORMATS = {
    "ESRI Shapefile": [".shp"],
    "FlatGeobuf": [".fgb"],
    "GeoJSON": [".geojson", ".json"],
    "GML": [".gml"],
    "GPKG": [".gpkg"],
}


SINGLE_LAYER_EXTENSIONS = [".json", ".geojson", ".shp", ".fgb"]

ERROR_MESSAGE_UNSUPPORTED_FILE_FORMAT = "Argument {arg_name} {file_path} is of an unsupported fileformat, see list-formats for list of supported file formats"
THREE_DIMENSIONAL = 3
point_type = tuple[float, ...]
report_type = list[tuple[list[int], float]]


def transform_linestrings_in_geometry_coordinates(
    geometry_coordinates: list[Any],
    transform_fun: Callable[[list[point_type], DenseConfig], list[point_type]],
    densify_config: DenseConfig,
) -> list[Any]:
    _raise_e_if_point_geom(geometry_coordinates)

    if _is_linestring_geom(geometry_coordinates):
        geometry_coordinates = transform_fun(geometry_coordinates, densify_config)
        return geometry_coordinates
    else:
        return [
            transform_linestrings_in_geometry_coordinates(
                e, transform_fun, densify_config
            )
            for e in geometry_coordinates
        ]


def check_density_linestring(
    linestring: list[point_type],
    densify_config: DenseConfig,
    indices: list[int],
) -> report_type:
    result = []

    for k in range(0, len(linestring) - 1):
        a: point_type = linestring[k]
        b: point_type = linestring[k + 1]

        a_2d = tuple(a[:2])
        b_2d = tuple(b[:2])

        transformer = densify_config.transformer

        if (
            densify_config.src_crs.is_projected
        ):  # only convert to basegeographic crs if src_proj is projected
            a_t = transformer.transform(*a_2d)  # type: ignore
            b_t = transformer.transform(*b_2d)  # type: ignore
        else:  # src_crs is geographic do not transform
            a_t, b_t = (a_2d, b_2d)

        g = densify_config.geod

        _, _, geod_dist = g.inv(*a_t, *b_t, return_back_azimuth=True)  # type: ignore
        if math.isnan(geod_dist):
            raise ValueError(
                f"unable to calculate geodesic distance, result: {geod_dist}, expected: floating-point number"
            )
        if geod_dist > (densify_config.max_segment_length + 0.001):
            report_indices = [*indices, k]
            result.append((report_indices, geod_dist))
    return result


def check_density_geometry_coordinates(
    geometry_coordinates: list[Any],
    densify_config: DenseConfig,
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
            geometry_coordinates, densify_config, indices
        )
        result.extend(linestring_report)
    else:
        for i, e in enumerate(geometry_coordinates):
            check_density_geometry_coordinates(e, densify_config, result, [*indices, i])


def check_density_file(
    input_file: str,
    max_segment_length: float,
    layer: str,
    src_crs: Optional[str] = None,
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

        override_src_crs(src_crs, profile)
        geom_type = profile["schema"]["geometry"]
        src_crs = str(profile["crs"])
        _geom_type_check(geom_type)

        c = DenseConfig(CRS.from_authority(*src_crs.split(":")), max_segment_length)

        report: list[tuple[list[int], float]] = []
        for i, ft in enumerate(src):
            check_density_geometry_coordinates(ft.geometry.coordinates, c, report, [i])
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
        distance = round(item[1], DEFAULT_PRECISION_METERS)
        ft_report = f"  - features{ft_index}.geometry.segments\
 [{', '.join([str(x) for x  in coordinates_indices])}], distance: {distance}"
        if len(report) - 1 != i:
            ft_report += "\n"
        hr_report += ft_report
    return hr_report


def densify_geometry_coordinates(
    geometry_coordinates: list[Any], densify_config: DenseConfig
) -> list[Any]:
    return transform_linestrings_in_geometry_coordinates(
        geometry_coordinates, _add_vertices_exceeding_max_segment_length, densify_config
    )


def search_file_streaming(
    input_file: str,
    search_string: str,
    s_from: Optional[int] = None,
    start: bool = True,
) -> Optional[int]:
    chunk_size = 1024**2  # 1MB
    with open(input_file, "rb") as f:
        prev_chunk = None
        bytes_read = 0
        if s_from is not None:
            f.seek(s_from)
            bytes_read = s_from
        for chunk in iter(lambda: f.read(chunk_size), b""):
            new_chunk = chunk
            if prev_chunk:
                new_chunk = prev_chunk + chunk
            if search_string in new_chunk.decode("utf-8"):
                if not start:
                    return bytes_read + chunk_size
                return bytes_read
            prev_chunk = chunk
            bytes_read += chunk_size
        return None


def get_crs_json(input_file: str) -> Optional[str]:
    """Get CRS identifier string (format: `$authority:$idenifier`) from JSON. Streaming search with chunksize of 1MB, to prevent loading full file in memory.

    Arguments:
        input_file -- GeoJSON file to retrieve CRS identifier string for

    Returns:
        CRS identifier string (format: `$authority:$idenifier`), None if no CRS found
    """
    with open(input_file, "rb") as f:
        f.seek(0, os.SEEK_END)
        f_size = f.tell()
        start: Optional[int] = 0
        while True:  # loop until urn found or start/end returns None
            start = search_file_streaming(input_file, '"crs"', start)
            if start is None:
                break  # loop exit
            end = search_file_streaming(input_file, "}", start, False)
            if end is None:  # in case of invalid json
                break  # loop exit
            if end > f_size:
                end = f_size
            f.seek(start)
            crs_json_string = f.read(end)
            r1 = re.findall(
                r'"urn:ogc:def:crs:.+:.*:.+"', crs_json_string.decode("utf-8")
            )
            if len(r1) != 1:
                # increment start bytes
                start += 1024**2
                continue
            else:
                urn_crs_str = r1[0].replace('"', "")
                m2 = re.match(
                    r"^urn:ogc:def:crs:(.*?):.*?:(.*?)$", urn_crs_str
                )  # extract auth:identifier crs_str, match is ensured
                # type ignore since regex will return result, because of earlier match (r1)
                return f"{m2[1]}:{m2[2]}"  # type: ignore
    return None


def densify_file(  # noqa: PLR0913
    input_file_path: str,
    output_file_path: str,
    layer: Optional[str] = None,
    max_segment_length: Optional[float] = None,
    densify_in_projection: bool = False,
    overwrite: bool = False,
    src_crs: Optional[str] = None,
) -> None:
    """_summary_

    Arguments:
        input_file_path
        output_file_path

    Keyword Arguments:
        layer -- layer name, when no specified and multilayer file, first layer will be used (default: {None})
        max_segment_length -- max segment length to use for densification (default: {None})
        densify_in_projection -- user src projection for densification (default: {False})
        src_crs -- override src crs of input file (default: {None})

    Raises:
        ValueError: application errors
        pyproj.exceptions.CRSError: when crs cannot be found by pyproj

    """
    _validate_densify_file_file_args(input_file_path, output_file_path, overwrite)

    _, output_file_ext = os.path.splitext(output_file_path)

    layer = _get_valid_layer_name(input_file_path, layer)

    with fiona.open(input_file_path, layer=layer) as src:
        profile = src.profile
        geom_type = profile["schema"]["geometry"]
        _geom_type_check(geom_type)

        is_geojson_driver = profile["driver"] == "GeoJSON"
        if is_geojson_driver:
            check_crs_geojson_defined(input_file_path, src_crs, profile)

        # override crs if supplied in src_crs argument
        override_src_crs(src_crs, profile)

        src_crs_str = str(profile["crs"])
        den_config = DenseConfig(
            CRS.from_authority(*src_crs_str.split(":")),
            max_segment_length,
            densify_in_projection,
        )

        # COORDINATE_PRECISION is only a lco (layer creation option) for OGR GeoJSON driver
        is_geojson_driver = profile["driver"] == "GeoJSON"
        fun_kwargs: dict = (
            {"COORDINATE_PRECISION": den_config.get_coord_precision()}
            if is_geojson_driver
            else {}
        )

        if output_file_ext not in SINGLE_LAYER_EXTENSIONS:
            fun_kwargs["layer"] = layer

        with fiona.open(output_file_path, "w", **profile, **fun_kwargs) as dst:
            for i, ft in enumerate(src):
                try:
                    if ft.geometry.type == "GeometryCollection":
                        new_geoms = []
                        for geom in ft.geometry.geometries:
                            coordinates_t = densify_geometry_coordinates(
                                geom.coordinates, den_config
                            )
                            new_geom = fiona.Geometry(
                                coordinates=coordinates_t, type=geom.type
                            )
                            new_geoms.append(new_geom)
                        geom = fiona.Geometry(
                            geometries=new_geoms, type="GeometryCollection"
                        )
                    else:
                        coordinates_t = densify_geometry_coordinates(
                            ft.geometry.coordinates, den_config
                        )
                        geom = fiona.Geometry(
                            coordinates=coordinates_t, type=ft.geometry.type
                        )
                    new_ft = fiona.Feature(geometry=geom, properties=ft.properties)
                    dst.write(new_ft)
                except Exception as e:
                    raise ValueError(
                        f"Unexpected error occured while processing feature [{i}]: {e}"
                    ) from e


def override_src_crs(src_crs: Optional[str], profile: dict) -> None:
    if src_crs:
        crs_obj = CRS.from_authority(*src_crs.split(":"))
        profile["crs"] = crs_obj
        profile["crs_wkt"] = crs_obj.to_wkt()


def check_crs_geojson_defined(
    input_file_path: str, src_crs: Optional[str], profile: dict
) -> None:
    """Check if GeoJSON has CRS defined. Required since fiona/ogr allows opening files containing only a feature or geometry (which cannot contain CRS by spec).

    Arguments:
        input_file_path -- _description_
        src_crs -- _description_
        profile -- _description_
    """
    json_crs = get_crs_json(input_file_path)
    if json_crs is None and src_crs is None:
        message = f"WARNING: unable to determine source CRS for file {input_file_path}, assumed CRS is {profile['crs']}"
        print(message, file=sys.stderr)


def interpolate_src_proj(
    a: point_type, b: point_type, densify_config: DenseConfig
) -> list[point_type]:
    """Interpolate intermediate points between points a and b, with segment_length < max_segment_length. Only returns intermediate points."""

    three_dimensional_points = (
        len(a) == THREE_DIMENSIONAL and len(b) == THREE_DIMENSIONAL
    )
    if (
        not three_dimensional_points
    ):  # if not both three dimensional points, ensure both points are two dimensional
        a = a[:2]
        b = b[:2]

    dist = math.sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)  # Pythagoras
    if dist <= densify_config.max_segment_length:
        return []
    else:
        new_points = []

        (
            nr_points,
            new_max_segment_length,
        ) = _get_intermediate_nr_points_and_segment_length(
            dist, densify_config.max_segment_length
        )

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
    a: point_type, b: point_type, densify_config: DenseConfig
) -> list[point_type]:
    """geodesic interpolate intermediate points between points a and b, with segment_length < max_segment_length. Only returns intermediate points."""

    three_dimensional_points = (
        len(a) == THREE_DIMENSIONAL and len(b) == THREE_DIMENSIONAL
    )
    a_2d = tuple(a[:2])
    b_2d = tuple(b[:2])

    transformer = densify_config.transformer

    if (
        densify_config.src_crs.is_projected
    ):  # only convert to basegeographic crs if src_proj is projected
        a_t = transformer.transform(*a_2d)  # type: ignore
        b_t = transformer.transform(*b_2d)  # type: ignore
    else:  # src_crs is geographic do not transform
        a_t, b_t = (a_2d, b_2d)

    g = densify_config.geod

    az12, _, dist = g.inv(*a_t, *b_t, return_back_azimuth=True)  # type: ignore
    if dist <= densify_config.max_segment_length:
        return []
    else:
        (
            nr_points,
            new_max_segment_length,
        ) = _get_intermediate_nr_points_and_segment_length(
            dist, densify_config.max_segment_length
        )
        r = g.fwd_intermediate(
            *a_t,
            az12,
            npts=nr_points,
            del_s=new_max_segment_length,
            return_back_azimuth=True,
        )  # type: ignore

        def optional_back_transform(lon: float, lat: float) -> tuple[Any, Any]:
            """technically should be named optional_back_convert, since crs->base crs is (mostly) a conversion and not a transformation"""
            if densify_config.src_crs.is_projected:
                if transformer is None:
                    raise ValueError(
                        "transformer cannot be None when src_crs.is_projected=True"
                    )
                back_transformer = Transformer.from_crs(
                    transformer.target_crs, transformer.source_crs, always_xy=True
                )
                return back_transformer.transform(lon, lat)
            return (lon, lat)

        if three_dimensional_points:
            # interpolate height for three_dimensional_points
            height_a = a[2:][0]
            height_b = b[2:][0]
            delta_height_b_a = height_b - height_a
            delta_height_per_point = delta_height_b_a * (new_max_segment_length / dist)
            return [
                tuple(
                    (
                        *optional_back_transform(lon, lat),
                        round(
                            (height_a + ((i + 1) * delta_height_per_point)),
                            DEFAULT_PRECISION_METERS,
                        ),
                    )
                )
                for i, (lon, lat) in enumerate(zip(r.lons, r.lats))
            ]
        else:
            return [
                optional_back_transform(lon, lat) for lon, lat in zip(r.lons, r.lats)
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


def _validate_densify_file_file_args(
    input_file_path: str,
    output_file_path: str,
    overwrite: bool = False,
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

    if os.path.exists(output_file_path) and not overwrite:
        raise ValueError(f"output_file {output_file_path} already exists")
    elif os.path.exists(output_file_path) and overwrite:
        os.remove(output_file_path)


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
    linestring: list[point_type], coord_index: int, densify_config: DenseConfig
) -> int:
    """Adds vertices to linestring in place, and returns number of vertices added to linestring.

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

    prec = densify_config.get_coord_precision()

    if not densify_config.in_projection:
        p = list(
            [
                _round_coordinates(x, prec)
                for x in interpolate_geodesic(a, b, densify_config)
            ]
        )
    else:
        p = list(
            [
                _round_coordinates(x, prec)
                for x in interpolate_src_proj(a, b, densify_config)
            ]
        )

    linestring[coord_index] = _round_coordinates(linestring[coord_index], prec)
    linestring[coord_index + 1] = _round_coordinates(linestring[coord_index + 1], prec)
    linestring[coord_index + 1 : coord_index + 1] = p
    return len(p)


def _round_coordinates(coordinates: tuple, position_precision: int) -> tuple:
    result = tuple([round(x, position_precision) for x in coordinates[:2]])
    if len(coordinates) == THREE_DIMENSIONAL:
        result = (*result, round(coordinates[2], DEFAULT_PRECISION_METERS))
    return result


def _add_vertices_exceeding_max_segment_length(
    linestring: list[point_type], densify_config: DenseConfig
) -> list[point_type]:
    added_nodes = 0
    stop = len(linestring) - 1
    for i, _ in enumerate(linestring[:stop]):
        added_nodes += _add_vertices_to_line_segment(
            linestring, i + added_nodes, densify_config
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


def _get_supported_extensions() -> list[str]:
    return list(itertools.chain.from_iterable(SUPPORTED_FILE_FORMATS.values()))


def _file_is_supported_fileformat(filepath: str) -> bool:
    ext = pathlib.Path(filepath).suffix
    # flatten list of get_driver_by_file_extensionlists
    return ext in _get_supported_extensions()
