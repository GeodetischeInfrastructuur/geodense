import json
import logging
import math
import os
import sys
from collections.abc import Callable, Iterable, Sequence
from typing import Any, TextIO, cast

from geojson_pydantic import (
    Feature,
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)
from geojson_pydantic.geometries import Geometry
from pydantic import BaseModel
from pyproj import CRS
from shapely import LineString as ShpLineString
from shapely import Point as ShpPoint

from geodense.geojson import CrsFeatureCollection
from geodense.models import DEFAULT_PRECISION_METERS, DenseConfig, GeodenseError
from geodense.types import GeojsonGeomNoGeomCollection, GeojsonObject, T

TWO_DIMENSIONAL = 2
THREE_DIMENSIONAL = 3
DEFAULT_CRS_2D = "EPSG:4326"
DEFAULT_CRS_3D = "EPSG:4979"
SUPPORTED_FILE_FORMATS = {
    "GeoJSON": [".geojson", ".json"],
}

logger = logging.getLogger("geodense")
point_type = tuple[float, ...]
report_type = list[tuple[list[int], float]]


def densify_geojson_object(geojson_obj: GeojsonObject, dc: DenseConfig) -> None:
    _geom_type_check(geojson_obj)
    geom_densify_fun = _get_geom_densify_fun(dc)
    _ = apply_function_on_geojson_geometries(geojson_obj, geom_densify_fun)


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


def get_density_check_fun(
    densify_config: DenseConfig,
) -> Callable:
    def density_check(
        geometry: GeojsonGeomNoGeomCollection,
        result: list[report_type],
        indices: list[int] | None = None,
    ) -> None:
        _check_density_geometry_coordinates(
            geometry.coordinates, densify_config, result, indices
        )

    return density_check


def check_density_file(
    input_file_path: str,
    max_segment_length: float,
    src_crs: str | None = None,
) -> report_type:
    # TODO: check if densify_in_projection missing in function args
    _validate_file_args(input_file_path)

    with open(input_file_path) if input_file_path != "-" else sys.stdin as src:
        geojson_obj = _get_geojson_obj(src)
        _geom_type_check(geojson_obj)
        has_3d_coords = _has_3d_coordinates(geojson_obj)
        geojson_src_crs = _get_crs_geojson(
            geojson_obj, input_file_path, src_crs, has_3d_coords
        )
        config = DenseConfig(
            CRS.from_authority(*geojson_src_crs.split(":")),
            max_segment_length,
        )
        density_check_fun = get_density_check_fun(config)
        result = apply_function_on_geojson_geometries(geojson_obj, density_check_fun)
        return result


def densify_file(  # noqa: PLR0913
    input_file_path: str,
    output_file_path: str,
    overwrite: bool = False,
    max_segment_length: float | None = None,
    densify_in_projection: bool = False,
    src_crs: str | None = None,
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
    _validate_file_args(input_file_path, output_file_path, overwrite)
    src: TextIO
    with open(input_file_path) if input_file_path != "-" else sys.stdin as src:
        geojson_obj = _get_geojson_obj(src)
        has_3d_coords = _has_3d_coordinates(geojson_obj)
        geojson_src_crs = _get_crs_geojson(
            geojson_obj, input_file_path, src_crs, has_3d_coords
        )
        config = DenseConfig(
            CRS.from_authority(*geojson_src_crs.split(":")),
            max_segment_length,
            densify_in_projection,
        )
        densify_geojson_object(geojson_obj, config)
        if src_crs is not None and isinstance(geojson_obj, CrsFeatureCollection):
            geojson_obj.set_crs_auth_code(src_crs)
        with open(
            output_file_path, "w"
        ) if output_file_path != "-" else sys.stdout as out_f:
            geojson_obj_model: BaseModel = cast(BaseModel, geojson_obj)

            out_f.write(geojson_obj_model.model_dump_json(indent=1))


def apply_function_on_geojson_geometries(  # noqa: C901
    body: Feature
    | CrsFeatureCollection
    | GeojsonGeomNoGeomCollection
    | GeometryCollection,
    callback: Callable[[GeojsonGeomNoGeomCollection, list[T], list[int] | None], None],
    indices: list[int] | None = None,
) -> list[T]:
    result: list[T] = []
    if isinstance(body, Feature):
        feature = cast(Feature, body)
        if isinstance(feature.geometry, GeometryCollection):
            return apply_function_on_geojson_geometries(feature.geometry, callback)
        geom = cast(GeojsonGeomNoGeomCollection, feature.geometry)
        callback(geom, result, None)
    elif isinstance(body, GeojsonGeomNoGeomCollection):  # type: ignore
        geom = cast(GeojsonGeomNoGeomCollection, body)
        callback(geom, result, indices)
    elif isinstance(body, CrsFeatureCollection):
        fc_body: CrsFeatureCollection = body
        features: Iterable[Feature] = fc_body.features
        for i, ft in enumerate(features):
            if ft.geometry is None:
                raise GeodenseError(f"feature does not have a geometry, feature: {ft}")
            if isinstance(ft.geometry, GeometryCollection):
                ft_result = apply_function_on_geojson_geometries(
                    ft.geometry, callback, [i]
                )
                result.extend(ft_result)
            else:
                callback(ft.geometry, result, [i])
    elif isinstance(body, GeometryCollection):
        gc = cast(GeometryCollection, body)
        geometries: list[Geometry] = gc.geometries
        for i, g in enumerate(geometries):
            n_indices = None
            if indices is not None:
                n_indices = indices[:]
                n_indices.append(i)
            g_no_gc = cast(
                GeojsonGeomNoGeomCollection, g
            )  # geojson prohibits nested geometrycollections - maybe throw exception if this occurs
            callback(g_no_gc, result, n_indices)
    return result


def _interpolate_geodesic(
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

    az12, _, geod_dist = g.inv(*a_t, *b_t, return_back_azimuth=True)  # type: ignore
    if math.isnan(geod_dist):
        raise GeodenseError(
            f"unable to calculate geodesic distance, output calculation geodesic distance: {geod_dist}, expected: floating-point number"
        )

    if geod_dist <= densify_config.max_segment_length:
        return []
    else:
        (
            nr_points,
            new_max_segment_length,
        ) = _get_intermediate_nr_points_and_segment_length(
            geod_dist, densify_config.max_segment_length
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
                if densify_config.back_transformer is None:
                    raise GeodenseError(
                        "back_transformer cannot be None when src_crs.is_projected=True"
                    )
                return densify_config.back_transformer.transform(lon, lat)
            return (lon, lat)

        if three_dimensional_points:
            # interpolate height for three_dimensional_points
            height_a = a[2:][0]
            height_b = b[2:][0]
            delta_height_b_a = height_b - height_a
            delta_height_per_point = delta_height_b_a * (
                new_max_segment_length / geod_dist
            )
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
                for i, (lon, lat) in enumerate(zip(r.lons, r.lats, strict=True))
            ]
        else:
            return [
                optional_back_transform(lon, lat)
                for lon, lat in zip(r.lons, r.lats, strict=True)
            ]


def _interpolate_src_proj(
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
            p_point: ShpPoint = ShpLineString([a, b]).interpolate(
                new_max_segment_length * (i + 1)
            )  # type: ignore
            p = tuple(p_point.coords[0])
            new_points.append(p)
        return [
            *new_points,
        ]


def _get_geojson_obj(src: TextIO) -> GeojsonObject:
    src_json = json.loads(src.read())
    type_map = {
        "Feature": Feature,
        "GeometryCollection": GeometryCollection,
        "FeatureCollection": CrsFeatureCollection,
        "Point": Point,
        "MultiPoint": MultiPoint,
        "Polygon": Polygon,
        "MultiPolygon": MultiPolygon,
        "LineString": LineString,
        "MultiLineString": MultiLineString,
    }
    try:  # TODO: add check for missing type field and appropriate error
        geojson_type = src_json["type"]
        constructor = type_map[geojson_type]
    except KeyError as e:
        message = f'received invalid GeoJSON file, loc: `.type`, value: `{src_json["type"]}`, expected one of: {", ".join(list(type_map.keys()))}'
        raise GeodenseError(message) from e
    geojson_obj: GeojsonObject = constructor(**src_json)
    return geojson_obj


def _check_density_geometry_coordinates(
    geometry_coordinates: list[Any] | tuple[Any, ...],
    densify_config: DenseConfig,
    result: list,
    indices: list[int] | None = None,
) -> None:
    if indices is None:
        indices = []
    _raise_e_if_point_geom(geometry_coordinates)
    if _is_linestring_geom(
        geometry_coordinates
    ):  # check if at linestring level in coordinates array - list[typle[float,float]]
        linestring_coords = cast(list[tuple[float, ...]], geometry_coordinates)
        linestring_report = _check_density_linestring(
            linestring_coords, densify_config, indices
        )
        result.extend(linestring_report)
    else:
        for i, e in enumerate(geometry_coordinates):
            _check_density_geometry_coordinates(
                e, densify_config, result, [*indices, i]
            )


def _get_crs_geojson(
    geojson_object: GeojsonObject,
    input_file_path: str,
    src_crs: str | None,
    has_3d_coords: bool,
) -> str:
    result: str | None = None
    if isinstance(geojson_object, CrsFeatureCollection):
        result = geojson_object.get_crs_auth_code()
    if (
        result is None and src_crs is None
    ):  # set default crs if not in geojson object and not overridden with src_crs
        default_crs = DEFAULT_CRS_2D
        if has_3d_coords:
            default_crs = DEFAULT_CRS_3D
        message = f"unable to determine source CRS for file {input_file_path}, assumed CRS is {default_crs}"
        logger.warning(message)
        result = default_crs
    else:
        result = (
            src_crs if src_crs is not None else result
        )  # override json_crs with src_crs if defined
    if result is None:
        raise GeodenseError("could not determin crs from GeoJSON object")
    return result


def _flatten(container: list | tuple) -> Iterable:
    for i in container:
        if isinstance(i, list | tuple):
            yield from _flatten(i)
        else:
            yield i


def _check_density_linestring(
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
            raise GeodenseError(
                f"unable to calculate geodesic distance, output calculation geodesic distance: {geod_dist}, expected: floating-point number"
            )

        if geod_dist > (densify_config.max_segment_length + 0.001):
            report_indices = [*indices, k]
            result.append((report_indices, geod_dist))
    return result


def _is_linestring_geom(geometry_coordinates: list[Any] | tuple[Any, ...]) -> bool:
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
            isinstance(x, float | int) for x in geometry_coordinates[0]
        )  # also test for int just in case...
    ):
        return True
    return False


def _raise_e_if_point_geom(geometry_coordinates: list[Any] | tuple[Any, ...]) -> None:
    if all(isinstance(x, float) for x in geometry_coordinates):
        raise GeodenseError(
            "received point geometry coordinates, instead of (multi)linestring"
        )


# TODO: fix type annotation, see type: ignore comments
def _transform_linestrings_in_geometry_coordinates(
    geometry_coordinates: list[Any],
    transform_fun: Callable[[list[point_type]], list[T]],
) -> list[T] | T:  # note should be nested type
    if all(isinstance(x, float) for x in geometry_coordinates):  # if point skip
        return tuple(geometry_coordinates)  # type: ignore
    if _is_linestring_geom(geometry_coordinates):
        return transform_fun(geometry_coordinates)
    else:
        return [
            _transform_linestrings_in_geometry_coordinates(e, transform_fun)  # type: ignore
            for e in geometry_coordinates
        ]


def _validate_file_args(
    input_file_path: str,
    output_file_path: str | None = None,
    overwrite: bool = False,
) -> None:
    _, input_file_ext = os.path.splitext(input_file_path)
    if output_file_path is not None:
        _, output_file_ext = os.path.splitext(output_file_path)

    if output_file_path is not None and (
        input_file_path == output_file_path and input_file_path != "-"
    ):
        raise GeodenseError(
            f"input_file and output_file arguments must be different, input_file: {input_file_path}, output_file: {output_file_path}"
        )
    unsupported_file_extension_msg = "unsupported file extension of {input_file}, received: {ext}, expected one of: {supported_ext}"

    if (
        input_file_path != "-"
        and input_file_ext not in SUPPORTED_FILE_FORMATS["GeoJSON"]
    ):
        raise GeodenseError(
            unsupported_file_extension_msg.format(
                input_file="input-file",
                ext=input_file_ext,
                supported_ext=", ".join(SUPPORTED_FILE_FORMATS["GeoJSON"]),
            )
        )
    if (
        output_file_path is not None
        and output_file_path != "-"
        and output_file_ext not in SUPPORTED_FILE_FORMATS["GeoJSON"]
    ):
        raise GeodenseError(
            unsupported_file_extension_msg.format(
                input_file="output-file",
                ext=output_file_ext,
                supported_ext=SUPPORTED_FILE_FORMATS["GeoJSON"],
            )
        )

    if input_file_path != "-" and not os.path.exists(input_file_path):
        raise GeodenseError(f"input_file {input_file_path} does not exist")

    if (
        output_file_path is not None
        and output_file_path != "-"
        and not os.path.exists(os.path.realpath(os.path.dirname(output_file_path)))
    ):
        raise GeodenseError(
            f"target directory of output_file {output_file_path} does not exist"
        )

    if output_file_path is not None and output_file_path != "-":
        if os.path.exists(output_file_path) and not overwrite:
            raise GeodenseError(f"output_file {output_file_path} already exists")
        elif os.path.exists(output_file_path) and overwrite:
            os.remove(output_file_path)


def _get_intermediate_nr_points_and_segment_length(
    dist: float, max_segment_length: float
) -> tuple[int, float]:
    if dist <= max_segment_length:
        raise GeodenseError(
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
                for x in _interpolate_geodesic(a, b, densify_config)
            ]
        )
    else:
        p = list(
            [
                _round_coordinates(x, prec)
                for x in _interpolate_src_proj(a, b, densify_config)
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


def _get_geometry_type(
    geometry: GeojsonGeomNoGeomCollection,
    result: list[str],
    _indices: list[int] | None = None,
) -> None:
    result.append(geometry.type)


def _geom_has_3d_coords(
    geometry: GeojsonGeomNoGeomCollection,
    result: list[list[bool] | bool],
    _indices: list[int] | bool,
) -> None:
    def _linestring_has_3d_coords(linestring: list[point_type]) -> list[bool]:
        return [len(x) == THREE_DIMENSIONAL for x in linestring]

    coords = cast(list[Any], geometry.coordinates)
    result.append(
        _transform_linestrings_in_geometry_coordinates(
            coords, _linestring_has_3d_coords
        )
    )


def _get_line_segment_densify_fun(
    densify_config: DenseConfig,
) -> Callable[[list[point_type]], list[point_type]]:
    def line_segment_densify(
        linestring: list[point_type],
    ) -> list[point_type]:
        added_nodes = 0
        stop = len(linestring) - 1
        for i, _ in enumerate(linestring[:stop]):
            added_nodes += _add_vertices_to_line_segment(
                linestring, i + added_nodes, densify_config
            )
        return linestring

    return line_segment_densify


def _get_geom_densify_fun(
    densify_config: DenseConfig,
) -> Callable[[GeojsonGeomNoGeomCollection, list[Any], list[int] | None], None]:
    def _geom_densify(
        geometry: GeojsonGeomNoGeomCollection,
        result: list[Any],
        _indices: list[int] | None,
    ) -> None:
        _add_vertices_exceeding_max_segment_length = _get_line_segment_densify_fun(
            densify_config
        )
        result = _transform_linestrings_in_geometry_coordinates(
            geometry.coordinates, _add_vertices_exceeding_max_segment_length  # type: ignore
        )
        geometry.coordinates = result  # type: ignore

    return _geom_densify


def _has_3d_coordinates(
    geojson_obj: GeojsonObject, silent: bool | None = False
) -> bool:
    has_3d_coords = apply_function_on_geojson_geometries(
        geojson_obj, _geom_has_3d_coords  # type: ignore
    )
    has_3d_coords_flat = _flatten(has_3d_coords)

    result = True  # default case all 3d
    if not all(has_3d_coords_flat) and any(has_3d_coords_flat):  # some 3d
        if not silent:
            warning_message = "geometries with mixed 2D and 3D vertices found"
            logger.warning(warning_message)
    elif all(not x for x in has_3d_coords_flat):  # none 3d
        result = False
    return result


def _geom_type_check(geojson_obj: GeojsonObject) -> None:
    geom_types = apply_function_on_geojson_geometries(
        geojson_obj, _get_geometry_type
    )  # TODO: replace with try except block - saves an JSON serialization ??

    if all(g_t in ("Point", "MultiPoint") for g_t in geom_types):
        # situation: all geoms point -> error
        error_message = (
            "input file contains only (Multi)Point geometries which cannot be densified"
        )
        raise GeodenseError(error_message)
    elif any(gt in ["Point", "MultiPoint"] for gt in geom_types):
        # sitation: some geoms point -> warning
        warning_message = (
            "input file contains (Multi)Point geometries which cannot be densified"
        )
        logger.warning(warning_message)
    else:
        # situation: no geoms point -> ok
        pass
