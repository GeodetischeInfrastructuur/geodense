import json
import logging
import math
import os
import sys
import tempfile
from collections.abc import Callable, Iterable, Sequence
from enum import Enum
from typing import Any, Literal, TextIO, cast

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
from geojson_pydantic.types import LineStringCoords, Position, Position2D
from pydantic import BaseModel
from pyproj import CRS
from shapely import LineString as ShpLineString
from shapely import Point as ShpPoint

from geodense.geojson import CrsFeatureCollection
from geodense.models import DEFAULT_PRECISION_METERS, DenseConfig, GeodenseError
from geodense.types import (
    GeojsonCoordinates,
    GeojsonGeomNoGeomCollection,
    GeojsonObject,
    Nested,
    ReportLineString,
    T,
)

TWO_DIMENSIONAL = 2
THREE_DIMENSIONAL = 3
DEFAULT_CRS_2D = "OGC:CRS84"
DEFAULT_CRS_3D = "OGC:CRS84h"
SUPPORTED_FILE_FORMATS = {
    "GeoJSON": [".geojson", ".json"],
}

logger = logging.getLogger("geodense")


def densify_geojson_object(geojson_obj: GeojsonObject, dc: DenseConfig) -> None:
    _geom_type_check(geojson_obj, "densify")
    geom_densify_fun = _get_geom_densify_fun(dc)
    _ = apply_function_on_geojson_geometries(geojson_obj, geom_densify_fun)


def density_check_geojson_object(
    geojson_obj: GeojsonObject, dc: DenseConfig
) -> CrsFeatureCollection:
    _geom_type_check(geojson_obj, "density-check")
    density_check_fun = get_density_check_fun(dc)
    result: Nested[ReportLineString] = apply_function_on_geojson_geometries(
        geojson_obj, density_check_fun
    )
    flat_result: list[ReportLineString] = (
        list(  # filter out None values, these occur when point geometries are part of input
            filter(lambda x: x is not None, flatten(result))
        )
    )
    report_fc = report_line_string_to_geojson(
        flat_result, ":".join(dc.src_crs.to_authority())
    )
    return report_fc


def get_density_check_fun(
    densify_config: DenseConfig,
) -> Callable:
    def density_check(
        geometry: GeojsonGeomNoGeomCollection,
    ) -> Nested[ReportLineString]:
        return check_density_geometry_coordinates(geometry.coordinates, densify_config)

    return density_check


def _validate_dependent_file_args(
    input_file_path: str,
    output_file_path: str | None = None,
    overwrite: bool = False,
) -> None:
    if output_file_path is not None and (
        input_file_path == output_file_path and input_file_path != "-"
    ):
        raise GeodenseError(
            f"input_file and output_file arguments must be different, input_file: {input_file_path}, output_file: {output_file_path}"
        )
    if output_file_path is not None and output_file_path != "-":
        if os.path.exists(output_file_path) and not overwrite:
            raise GeodenseError(f"output_file {output_file_path} already exists")
        elif os.path.exists(output_file_path) and overwrite:
            os.remove(output_file_path)


def check_density_file(  # noqa: PLR0913
    input_file_path: str,
    max_segment_length: float,
    density_check_report_path: str | None = None,
    src_crs: str | None = None,
    in_projection: bool = False,
    overwrite: bool = False,
) -> tuple[bool, str, int]:
    if density_check_report_path is None:
        density_check_report_path = os.path.join(
            tempfile.mkdtemp(), "check-density-report.json"
        )

    _validate_dependent_file_args(input_file_path, density_check_report_path, overwrite)

    with open(input_file_path) if input_file_path != "-" else sys.stdin as src:
        geojson_obj = get_geojson_obj(src)
        _geom_type_check(geojson_obj, "check-density")
        has_3d_coords: Has3D = _has_3d_coordinates(geojson_obj)
        geojson_src_crs = _get_crs_geojson(
            geojson_obj, input_file_path, src_crs, has_3d_coords
        )
        config = DenseConfig(
            CRS.from_authority(*geojson_src_crs.split(":")),
            max_segment_length,
            in_projection=in_projection,
        )
        report_fc = density_check_geojson_object(geojson_obj, config)

    failed_segment_count = len(report_fc.features)
    check_status = failed_segment_count == 0

    if not check_status:
        with open(density_check_report_path, "w") as f:
            f.write(report_fc.model_dump_json(indent=4, exclude_none=True))
    return (check_status, density_check_report_path, len(report_fc.features))


def report_line_string_to_geojson(
    report: list[ReportLineString], src_crs_auth_code: str | None
) -> CrsFeatureCollection:
    features = [
        Feature(
            type="Feature",
            properties={"segment_length": x[0]},
            geometry=LineString(type="LineString", coordinates=list(x[1])),
        )
        for x in report
    ]
    result = CrsFeatureCollection(
        features=features, type="FeatureCollection", name="density-check-report"
    )
    if src_crs_auth_code is not None:
        result.set_crs_auth_code(src_crs_auth_code)
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
        input_file_path: assumes file exists otherwise raises FileNotFoundError
        output_file_path: assumes directory of output_file_path exists

    Keyword Arguments:
        layer -- layer name, when no specified and multilayer file, first layer will be used (default: {None})
        max_segment_length -- max segment length to use for densification (default: {None})
        densify_in_projection -- user src projection for densification (default: {False})
        src_crs -- override src crs of input file (default: {None})

    Raises:
        ValueError: application errors
        pyproj.exceptions.CRSError: when crs cannot be found by pyproj

    """
    _validate_dependent_file_args(input_file_path, output_file_path, overwrite)
    src: TextIO
    with open(input_file_path) if input_file_path != "-" else sys.stdin as src:
        geojson_obj = get_geojson_obj(src)
        has_3d_coords: Has3D = _has_3d_coordinates(geojson_obj)
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
        with (
            open(output_file_path, "w") if output_file_path != "-" else sys.stdout
        ) as out_f:
            geojson_obj_model: BaseModel = cast(BaseModel, geojson_obj)

            out_f.write(geojson_obj_model.model_dump_json(indent=1, exclude_none=True))


def apply_function_on_geojson_geometries(  # noqa: C901
    body: (
        Feature
        | CrsFeatureCollection
        | GeojsonGeomNoGeomCollection
        | GeometryCollection
    ),
    callback: Callable[[GeojsonGeomNoGeomCollection], Nested | None],
) -> Nested:
    result: Nested = []

    if isinstance(body, Feature):
        feature = cast(Feature, body)
        if isinstance(feature.geometry, GeometryCollection):
            return apply_function_on_geojson_geometries(feature.geometry, callback)
        geom = cast(GeojsonGeomNoGeomCollection, feature.geometry)
        return [callback(geom)]
    elif isinstance(
        body, Point | MultiPoint | LineString | MultiLineString | Polygon | MultiPolygon
    ):
        geom = cast(GeojsonGeomNoGeomCollection, body)
        return [callback(geom)]
    elif isinstance(body, CrsFeatureCollection):
        fc_body: CrsFeatureCollection = body
        features: Iterable[Feature] = fc_body.features

        for ft in features:
            if ft.geometry is None:
                raise GeodenseError(f"feature does not have a geometry, feature: {ft}")

            result_list = list(result)
            if isinstance(ft.geometry, GeometryCollection):
                ft_result: Nested = apply_function_on_geojson_geometries(
                    ft.geometry, callback
                )
                result_list.append(ft_result)
            else:
                result_list.append(callback(ft.geometry))
            result = result_list
        return result
    elif isinstance(body, GeometryCollection):
        gc = cast(GeometryCollection, body)
        geometries: list[Geometry] = gc.geometries

        for g in geometries:
            if isinstance(g, GeometryCollection):
                raise GeodenseError("nested GeometryCollections are not supported")
            g_no_gc = cast(
                GeojsonGeomNoGeomCollection, g
            )  # geojson prohibits nested geometrycollections - maybe throw exception if this occurs
            result_list = list(result)
            result_list.append(callback(g_no_gc))
            result = result_list
        return result
    return result


def _interpolate_geodesic(
    a: Position, b: Position, densify_config: DenseConfig
) -> LineStringCoords:
    """geodesic interpolate intermediate points between points a and b, with segment_length < max_segment_length. Only returns intermediate points."""

    three_dimensional_points = (
        len(a) == THREE_DIMENSIONAL and len(b) == THREE_DIMENSIONAL
    )
    a_2d: tuple[float, float] = tuple(a[:2])  # type: ignore
    b_2d: tuple[float, float] = tuple(b[:2])  # type: ignore

    transformer = densify_config.transformer

    if (
        densify_config.src_crs.is_projected
    ):  # only convert to basegeographic crs if src_proj is projected
        if transformer is None:
            raise GeodenseError(
                "transformer cannot be None when src_crs.is_projected=True"
            )
        # technically the following transform call is a converion and not a transformation, since crs->base-crs will be a conversion in most cases
        a_t: tuple[float, float] = transformer.transform(*a_2d)
        b_t: tuple[float, float] = transformer.transform(*b_2d)
    else:  # src_crs is geographic do not transform
        a_t, b_t = (a_2d, b_2d)

    g = densify_config.geod

    az12, _, geod_dist = g.inv(*a_t, *b_t, return_back_azimuth=True)
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
        )

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
            a_3d: tuple[float, float, float] = cast(tuple[float, float, float], a)
            b_3d: tuple[float, float, float] = cast(tuple[float, float, float], b)
            height_a = a_3d[2:][0]
            height_b = b_3d[2:][0]
            delta_height_b_a = height_b - height_a
            delta_height_per_point = delta_height_b_a * (
                new_max_segment_length / geod_dist
            )
            return [
                tuple(  # type: ignore
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
                Position2D(*optional_back_transform(lon, lat))
                for lon, lat in zip(r.lons, r.lats, strict=True)
            ]


def _get_cartesian_distance(a: Position, b: Position) -> float:
    return math.sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)  # pythagoras


def _interpolate_src_proj(
    a: Position, b: Position, densify_config: DenseConfig
) -> LineStringCoords:
    """Interpolate intermediate points between points a and b, with segment_length < max_segment_length. Only returns intermediate points."""

    three_dimensional_points = (
        len(a) == THREE_DIMENSIONAL and len(b) == THREE_DIMENSIONAL
    )
    if (
        not three_dimensional_points
    ):  # if not both three dimensional points, ensure both points are two dimensional
        a = Position2D(*a[:2])
        b = Position2D(*b[:2])

    dist = _get_cartesian_distance(a, b)
    if dist <= densify_config.max_segment_length:
        return []
    else:
        # new_points: list[tuple[float, float] | tuple[float, float, float]] = []
        new_points: LineStringCoords = []

        (
            nr_points,
            new_max_segment_length,
        ) = _get_intermediate_nr_points_and_segment_length(
            dist, densify_config.max_segment_length
        )

        for i in range(0, nr_points):
            p_point: ShpPoint = ShpLineString([a, b]).interpolate(
                new_max_segment_length * (i + 1)
            )
            p = tuple(p_point.coords[0])
            new_points.append(p)  # type: ignore
        return [
            *new_points,
        ]


def get_geojson_obj(src: TextIO) -> GeojsonObject:
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
    try:
        geojson_type = src_json["type"]
        constructor = type_map[geojson_type]
    except KeyError as e:
        message = f'received invalid GeoJSON file, loc: `.type`, value: `{src_json["type"]}`, expected one of: {", ".join(list(type_map.keys()))}'
        raise GeodenseError(message) from e
    geojson_obj: GeojsonObject = constructor(**src_json)
    return geojson_obj


def check_density_geometry_coordinates(
    geometry_coordinates: GeojsonCoordinates,
    densify_config: DenseConfig,
    # indices: list[int] | None = None,
) -> Nested[ReportLineString]:
    # if indices is None:
    #     indices = []

    if isinstance(geometry_coordinates, tuple):
        return [None]

    if _is_linestring_geom(geometry_coordinates):
        linestring_coords = cast(LineStringCoords, geometry_coordinates)
        linestring_report = _check_density_linestring(linestring_coords, densify_config)
        return linestring_report
    else:
        return [
            check_density_geometry_coordinates(e, densify_config)
            for i, e in enumerate(geometry_coordinates)
        ]


class Has3D(Enum):
    all: Literal["all"] = "all"
    some: Literal["some"] = "some"
    none: Literal["none"] = "none"


def _get_crs_geojson(
    geojson_object: GeojsonObject,
    input_file_path: str,
    src_crs: str | None,
    has_3d_coords: Has3D,
) -> str:
    result_crs: str | None = None

    is_fc = False
    if isinstance(geojson_object, CrsFeatureCollection):
        result_crs = geojson_object.get_crs_auth_code()
        is_fc = True

    # case to set default CRS if src_crs not specified and not available in GeoJSON
    if (
        result_crs is None and src_crs is None
    ):  # set default crs if not in geojson object and not overridden with src_crs
        default_crs = DEFAULT_CRS_2D
        if has_3d_coords in [Has3D.some, Has3D.all]:
            default_crs = DEFAULT_CRS_3D
        message = f"unable to determine source CRS for file {input_file_path}, assumed CRS is {default_crs}"
        logger.warning(message)
        result_crs = default_crs
        if is_fc:
            fc: CrsFeatureCollection = cast(CrsFeatureCollection, geojson_object)
            fc.set_crs_auth_code(result_crs)

    # is src_crs is set use src_crs
    elif src_crs is not None:
        src_crs_crs: CRS = CRS.from_authority(*src_crs.split(":"))
        if has_3d_coords == Has3D.all and not src_crs_crs.is_vertical:
            logger.warning(
                "src_crs is 2D while input data contains geometries with 3D coordinates"
            )
        result_crs = (
            src_crs if src_crs is not None else result_crs
        )  # override json_crs with src_crs if defined

    elif result_crs is None:
        raise GeodenseError("could not determine CRS from GeoJSON object")

    return result_crs


def flatten(container: Nested) -> Iterable:
    for i in container:
        if isinstance(i, Sequence) and not isinstance(i, tuple):
            yield from flatten(i)
        else:
            yield i


def _check_density_linestring(
    linestring: LineStringCoords,
    densify_config: DenseConfig,
    # indices: list[int],
) -> list[ReportLineString]:
    result = []

    for k in range(0, len(linestring) - 1):
        a: Position = linestring[k]
        b: Position = linestring[k + 1]

        a_2d: Position = Position2D(*a[0:2])  # type: ignore
        b_2d: Position = Position2D(*b[0:2])  # type: ignore

        a_t: Position
        b_t: Position

        if densify_config.in_projection:
            linesegment_dist = _get_cartesian_distance(a_2d, b_2d)

        else:
            if (
                densify_config.src_crs.is_projected
            ):  # only convert to basegeographic crs if src_proj is projected
                transformer = densify_config.transformer
                if transformer is None:
                    raise GeodenseError(
                        "transformer cannot be None when src_crs.is_projected=True"
                    )
                a_t = Position2D(*transformer.transform(*a_2d))
                b_t = Position2D(*transformer.transform(*b_2d))
            else:  # src_crs is geographic do not transform
                a_t, b_t = (a_2d, b_2d)
            g = densify_config.geod

            # see https://github.com/python/mypy/issues/6799
            _, _, geod_dist = g.inv(*a_t, *b_t, return_back_azimuth=True)  # type: ignore
            if math.isnan(geod_dist):
                raise GeodenseError(
                    f"unable to calculate geodesic distance, output calculation geodesic distance: {geod_dist}, expected: floating-point number"
                )
            linesegment_dist = geod_dist
        if linesegment_dist > (densify_config.max_segment_length + 0.001):
            result.append((linesegment_dist, (a, b)))
    return result


def _is_linestring_geom(geometry_coordinates: GeojsonCoordinates) -> bool:
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


def _raise_e_if_point_geom(geometry_coordinates: GeojsonCoordinates) -> None:
    if isinstance(geometry_coordinates, tuple):  # assume is point when tuple
        raise GeodenseError(
            "received point geometry coordinates, instead of (multi)linestring"
        )


def _transform_linestrings_in_geometry_coordinates(
    geometry_coordinates: GeojsonCoordinates,
    transform_fun: Callable[[LineStringCoords], Nested],
    retain_point_geoms: bool = False,
) -> Nested | None | T:
    if isinstance(geometry_coordinates, tuple):
        if retain_point_geoms:
            return geometry_coordinates
        else:
            return None
    if _is_linestring_geom(geometry_coordinates):
        linestring_coords = cast(LineStringCoords, geometry_coordinates)
        return transform_fun(linestring_coords)
    else:
        return [
            _transform_linestrings_in_geometry_coordinates(
                e, transform_fun, retain_point_geoms=retain_point_geoms
            )
            for e in geometry_coordinates
        ]


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
    linestring: LineStringCoords, coord_index: int, densify_config: DenseConfig
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

    linestring[coord_index] = _round_coordinates(linestring[coord_index], prec)  # type: ignore
    linestring[coord_index + 1] = _round_coordinates(linestring[coord_index + 1], prec)  # type: ignore
    linestring[coord_index + 1 : coord_index + 1] = p  # type: ignore
    return len(p)


def _round_coordinates(coordinates: tuple, position_precision: int) -> tuple:
    result = tuple([round(x, position_precision) for x in coordinates[:2]])
    if len(coordinates) == THREE_DIMENSIONAL:
        result = (*result, round(coordinates[2], DEFAULT_PRECISION_METERS))
    return result


def _get_geometry_type(
    geometry: GeojsonGeomNoGeomCollection,
    _indices: list[int] | None = None,
) -> str:
    return cast(str, geometry.type)


def _geom_has_3d_coords(
    geometry: GeojsonGeomNoGeomCollection,
) -> Nested[bool] | None:
    def _linestring_has_3d_coords(linestring_coords: LineStringCoords) -> Nested[bool]:
        return [len(x) == THREE_DIMENSIONAL for x in linestring_coords]

    return _transform_linestrings_in_geometry_coordinates(
        geometry.coordinates, _linestring_has_3d_coords
    )


def _get_line_segment_densify_fun(
    densify_config: DenseConfig,
) -> Callable[[LineStringCoords], LineStringCoords]:
    def line_segment_densify(
        linestring: LineStringCoords,
    ) -> LineStringCoords:
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
) -> Callable[[GeojsonGeomNoGeomCollection], GeojsonCoordinates]:
    def _geom_densify(geometry: GeojsonGeomNoGeomCollection) -> GeojsonCoordinates:
        _add_vertices_exceeding_max_segment_length = _get_line_segment_densify_fun(
            densify_config
        )
        result: GeojsonCoordinates = _transform_linestrings_in_geometry_coordinates(  # type: ignore
            geometry.coordinates,
            _add_vertices_exceeding_max_segment_length,
            retain_point_geoms=True,
        )
        geometry.coordinates = result
        return result

    return _geom_densify


def _has_3d_coordinates(
    geojson_obj: GeojsonObject, silent: bool | None = False
) -> Has3D:
    has_3d_coords: Nested[bool] = apply_function_on_geojson_geometries(
        geojson_obj, _geom_has_3d_coords
    )
    has_3d_coords_flat = list(flatten(has_3d_coords))
    if not all(has_3d_coords_flat) and any(has_3d_coords_flat):  # some 3d
        if not silent:
            warning_message = "geometries with mixed 2D and 3D vertices found"
            logger.warning(warning_message)
        return Has3D.some
    elif all(not x for x in has_3d_coords_flat):  # none 3d
        return Has3D.none
    return Has3D.all


def _geom_type_check(geojson_obj: GeojsonObject, command: str = "") -> None:
    geom_types: Nested[str] = apply_function_on_geojson_geometries(
        geojson_obj, _get_geometry_type
    )

    if all(g_t in ("Point", "MultiPoint") for g_t in geom_types):
        # situation: all geoms point -> error
        if command:
            error_message = f"cannot run {command} on GeoJSON that only contains (Multi)Point geometries"
        else:
            error_message = "GeoJSON contains only (Multi)Point geometries"
        raise GeodenseError(error_message)
    elif any(gt in ["Point", "MultiPoint"] for gt in geom_types):
        # sitation: some geoms point -> warning
        warning_message = "GeoJSON contains (Multi)Point geometries"
        if command:
            warning_message = (
                f"{warning_message}, cannot run {command} on (Multi)Point geometries"
            )

        logger.warning(warning_message)
    else:
        # situation: no geoms point -> ok
        pass
