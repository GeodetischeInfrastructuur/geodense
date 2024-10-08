import json
import logging
import math
import os
import sys
import tempfile
from collections.abc import Callable, Iterable, Sequence
from enum import Enum
from functools import partial
from typing import Literal, TextIO, cast

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
from geojson_pydantic.types import LineStringCoords, Position, Position2D, Position3D
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


class InfValCoordinateError(Exception):
    pass


def densify_geojson_object(densify_config: DenseConfig, geojson_obj: GeojsonObject) -> GeojsonObject:
    validate_geom_type(geojson_obj, "densify")
    _densify_geometry = partial(densify_geometry, densify_config)
    return traverse_geojson_geometries(geojson_obj, _densify_geometry)


def densify_geometry(densify_config: DenseConfig, geometry: GeojsonGeomNoGeomCollection) -> None:
    _densify_line_segment = partial(densify_line_segment, densify_config)
    result: GeojsonCoordinates = traverse_linestrings_in_coordinates(geometry.coordinates, _densify_line_segment)
    geometry.coordinates = result


def densify_line_segment(
    densify_config: DenseConfig,
    coords: GeojsonCoordinates,
) -> None:
    linestring = cast(LineStringCoords, coords)
    added_nodes = 0
    stop = len(linestring) - 1
    for i, _ in enumerate(linestring[:stop]):
        added_nodes += _add_vertices_to_line_segment(linestring, i + added_nodes, densify_config)


def check_density_geojson_object(densify_config: DenseConfig, geojson_obj: GeojsonObject) -> CrsFeatureCollection:
    validate_geom_type(geojson_obj, "density-check")
    _check_density_geometry = partial(check_density_geometry, densify_config)
    result: Nested[ReportLineString] | None = transform_geojson_geometries(geojson_obj, _check_density_geometry)
    if result is None:
        raise ValueError("_check_density_geometry returned None")

    flat_result: list[ReportLineString] = (
        list(  # filter out None values, these occur when point geometries are part of input
            filter(lambda x: x is not None, _flatten(result))
        )
    )
    report_fc = _report_line_string_to_geojson(flat_result, ":".join(densify_config.src_crs.to_authority()))
    return report_fc


def check_density_geometry(
    densify_config: DenseConfig,
    geometry: GeojsonGeomNoGeomCollection,
) -> Nested[ReportLineString] | None:
    _check_density_linestring = partial(check_density_linestring, densify_config)
    return transform_linestrings_in_coordinates(geometry.coordinates, _check_density_linestring)


def check_density_linestring(
    densify_config: DenseConfig,
    linestring: LineStringCoords,
) -> list[ReportLineString]:
    result = []

    for k in range(0, len(linestring) - 1):
        a: Position = linestring[k]
        b: Position = linestring[k + 1]

        a_2d = cast(Position2D, a[0:2])
        b_2d = cast(Position2D, b[0:2])

        if densify_config.in_projection:
            linesegment_dist = _cartesian_distance(a_2d, b_2d)
        else:
            if densify_config.src_crs.is_projected:  # only convert to basegeographic crs if src_proj is projected
                transformer = densify_config.transformer
                if transformer is None:
                    raise GeodenseError("transformer cannot be None when src_crs.is_projected=True")
                a_t = transformer.transform(*a_2d)
                b_t = transformer.transform(*b_2d)
            else:  # src_crs is geographic do not transform
                a_t, b_t = (a_2d, b_2d)
            g = densify_config.geod

            _, _, geod_dist = g.inv(*a_t, *b_t, return_back_azimuth=True)
            if math.isnan(geod_dist):
                raise GeodenseError(
                    f"unable to calculate geodesic distance, output calculation geodesic distance: {geod_dist}, expected: floating-point number"
                )
            linesegment_dist = geod_dist
        if linesegment_dist > (densify_config.max_segment_length + 0.001):
            result.append((linesegment_dist, (a, b)))
    return result


def _validate_dependent_file_args(
    input_file_path: str,
    output_file_path: str | None = None,
    overwrite: bool = False,
) -> None:
    if output_file_path is not None and (input_file_path == output_file_path and input_file_path != "-"):
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
        density_check_report_path = os.path.join(tempfile.mkdtemp(), "check-density-report.json")

    _validate_dependent_file_args(input_file_path, density_check_report_path, overwrite)

    with open(input_file_path) if input_file_path != "-" else sys.stdin as src:
        geojson_obj = textio_to_geojson(src)
        validate_geom_type(geojson_obj, "check-density")
        has_3d_coords: Has3D = _has_3d_coordinates(geojson_obj)
        geojson_src_crs = _get_crs_geojson(geojson_obj, input_file_path, src_crs, has_3d_coords)
        config = DenseConfig(
            CRS.from_authority(*geojson_src_crs.split(":")),
            max_segment_length,
            in_projection=in_projection,
        )
        report_fc = check_density_geojson_object(config, geojson_obj)

    failed_segment_count = len(report_fc.features)
    check_status = failed_segment_count == 0

    if not check_status:
        with open(density_check_report_path, "w") as f:
            f.write(report_fc.model_dump_json(indent=4, exclude_none=True))
    return (check_status, density_check_report_path, len(report_fc.features))


def _report_line_string_to_geojson(
    report: list[ReportLineString], src_crs_auth_code: str | None
) -> CrsFeatureCollection:
    features: list[Feature] = [
        Feature(
            type="Feature",
            properties={"segment_length": x[0]},
            geometry=LineString(type="LineString", coordinates=list(x[1])),
        )
        for x in report
    ]
    result = CrsFeatureCollection(features=features, type="FeatureCollection", name="density-check-report")
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
        geojson_obj = textio_to_geojson(src)
        has_3d_coords: Has3D = _has_3d_coordinates(geojson_obj)
        geojson_src_crs = _get_crs_geojson(geojson_obj, input_file_path, src_crs, has_3d_coords)
        config = DenseConfig(
            CRS.from_authority(*geojson_src_crs.split(":")),
            max_segment_length,
            densify_in_projection,
        )
        densify_geojson_object(config, geojson_obj)
        if src_crs is not None and isinstance(geojson_obj, CrsFeatureCollection):
            geojson_obj.set_crs_auth_code(src_crs)
        with open(output_file_path, "w") if output_file_path != "-" else sys.stdout as out_f:
            geojson_obj_model: BaseModel = cast(BaseModel, geojson_obj)

            out_f.write(geojson_obj_model.model_dump_json(indent=1, exclude_none=True))


def transform_linestrings_in_coordinates(
    coordinates: GeojsonCoordinates,
    callback: Callable[[GeojsonCoordinates], T],
) -> Nested | T | None:
    # when point geometry return None, since we only want to operate on linestring-like coordinates sequences
    if isinstance(coordinates, tuple):
        return None
    elif not _is_linestring_geom(coordinates):
        _self = partial(transform_linestrings_in_coordinates, callback=callback)
        return list(
            map(
                _self,
                coordinates,
            )
        )
    else:
        return callback(coordinates)


def traverse_linestrings_in_coordinates(
    coordinates: GeojsonCoordinates,
    callback: Callable[[GeojsonCoordinates], None],
) -> GeojsonCoordinates:
    """Differs from transform_linestrings_in_coordinates in that it does not transform the type of coordinates, so coordinates in > coordinates out. transform_linestrings_in_coordinates expects a callback that transforms the linestring coordinates to generic type  T."""
    #  maybe do perform mutations on copy
    if isinstance(coordinates, tuple):
        return coordinates
    elif not _is_linestring_geom(coordinates):
        _self = partial(traverse_linestrings_in_coordinates, callback=callback)
        list(
            map(
                _self,
                coordinates,
            )
        )
    else:
        callback(coordinates)
    return coordinates


def traverse_geojson_geometries(
    geojson: Feature | CrsFeatureCollection | Geometry,
    geometry_callback: Callable[[Geometry], None] | None = None,
    node_callback: Callable | None = None,
) -> Feature | CrsFeatureCollection | Geometry:
    _self: Callable[
        [Feature | CrsFeatureCollection | Geometry],
        Feature | CrsFeatureCollection | Geometry,
    ] = partial(
        traverse_geojson_geometries,
        geometry_callback=geometry_callback,
        node_callback=node_callback,
    )

    _geojson = geojson.model_copy(deep=True)

    if isinstance(geojson, Feature):
        feature = cast(Feature, geojson)
        _feature = cast(Feature, _geojson)
        geom = cast(GeojsonGeomNoGeomCollection, feature.geometry)
        try:
            _feature.geometry = _self(geom)
        except InfValCoordinateError as _:
            _feature.geometry = None

    elif isinstance(geojson, CrsFeatureCollection):
        _feature_collection: CrsFeatureCollection = cast(CrsFeatureCollection, _geojson)
        _feature_collection.features = list(map(_self, _feature_collection.features))
    elif isinstance(geojson, GeometryCollection):
        _geometry_collection = cast(GeometryCollection, _geojson)
        __self = cast(
            Callable[
                [Geometry],
                Geometry,
            ],
            _self,
        )  # cast to more specific type, to fix mypy error
        _geometry_collection.geometries = list(map(__self, _geometry_collection.geometries))
    elif isinstance(
        geojson,
        Point | MultiPoint | LineString | MultiLineString | Polygon | MultiPolygon,
    ):
        if geometry_callback is not None:
            _geom = cast(GeojsonGeomNoGeomCollection, _geojson)
            geometry_callback(_geom)

    if node_callback:
        node_callback(_geojson)

    return _geojson


def transform_geojson_geometries(
    geojson: (Feature | CrsFeatureCollection | GeojsonGeomNoGeomCollection | GeometryCollection),
    geometry_callback: Callable[[GeojsonGeomNoGeomCollection], T],
) -> Nested | T:
    _self = partial(transform_geojson_geometries, geometry_callback=geometry_callback)

    if isinstance(geojson, Feature):
        feature = cast(Feature, geojson)
        geom = cast(GeojsonGeomNoGeomCollection, feature.geometry)
        return _self(geom)

    elif isinstance(geojson, CrsFeatureCollection):
        feature_collection: CrsFeatureCollection = cast(CrsFeatureCollection, geojson)
        return list(map(_self, feature_collection.features))
    elif isinstance(geojson, GeometryCollection):
        geometry_collection = cast(GeometryCollection, geojson)
        return list(map(_self, geometry_collection.geometries))
    else:
        #     isinstance(
        #     geojson,
        #     Point | MultiPoint | LineString | MultiLineString | Polygon | MultiPolygon,
        # ):
        geom = cast(GeojsonGeomNoGeomCollection, geojson)
        return geometry_callback(geom)


def interpolate_geodesic(a: Position, b: Position, densify_config: DenseConfig) -> LineStringCoords:
    """geodesic interpolate intermediate points between points a and b, with segment_length < max_segment_length. Only returns intermediate points."""

    three_dimensional_points = len(a) == THREE_DIMENSIONAL and len(b) == THREE_DIMENSIONAL
    a_2d = Position2D(longitude=a.longitude, latitude=a.latitude)
    b_2d = Position2D(longitude=b.longitude, latitude=b.latitude)

    transformer = densify_config.transformer

    if densify_config.src_crs.is_projected:  # only convert to basegeographic crs if src_proj is projected
        if transformer is None:
            raise GeodenseError("transformer cannot be None when src_crs.is_projected=True")
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
        ) = _get_intermediate_nr_points_and_segment_length(geod_dist, densify_config.max_segment_length)
        r = g.fwd_intermediate(
            *a_t,
            az12,
            npts=nr_points,
            del_s=new_max_segment_length,
            return_back_azimuth=True,
        )

        def optional_back_transform(lon: float, lat: float) -> Position2D:
            """technically should be named optional_back_convert, since crs->base crs is (mostly) a conversion and not a transformation"""
            if densify_config.src_crs.is_projected:
                if densify_config.back_transformer is None:
                    raise GeodenseError("back_transformer cannot be None when src_crs.is_projected=True")
                _result = densify_config.back_transformer.transform(lon, lat)
                return Position2D(longitude=_result[0], latitude=_result[1])
            return Position2D(longitude=lon, latitude=lat)

        if three_dimensional_points:
            # interpolate height for three_dimensional_points
            a_3d = cast(Position3D, a)
            b_3d = cast(Position3D, b)
            height_a = a_3d[2:][0]
            height_b = b_3d[2:][0]
            delta_height_b_a = height_b - height_a
            delta_height_per_point = delta_height_b_a * (new_max_segment_length / geod_dist)
            return [
                Position3D(
                    *optional_back_transform(lon, lat),
                    altitude=round(
                        (height_a + ((i + 1) * delta_height_per_point)),
                        DEFAULT_PRECISION_METERS,
                    ),
                )
                for i, (lon, lat) in enumerate(zip(r.lons, r.lats, strict=True))
            ]
        else:
            return [optional_back_transform(lon, lat) for lon, lat in zip(r.lons, r.lats, strict=True)]


def _cartesian_distance(a: Position, b: Position) -> float:
    return math.sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)  # pythagoras


def interpolate_src_proj(a: Position, b: Position, densify_config: DenseConfig) -> LineStringCoords:
    """Interpolate intermediate points between points a and b, with segment_length < max_segment_length. Only returns intermediate points."""

    all_three_dimensional = len(a) == THREE_DIMENSIONAL and len(b) == THREE_DIMENSIONAL
    # when mixed 2D/3D reduce to 2D, shapely cannot do interpolation on points with mixed dimensionality
    if not all_three_dimensional:
        a = Position2D(longitude=a.longitude, latitude=a.latitude)
        b = Position2D(longitude=b.longitude, latitude=b.latitude)

    dist = _cartesian_distance(a, b)
    if dist <= densify_config.max_segment_length:
        return []
    else:
        new_points: list[Position] = []

        (
            nr_points,
            new_max_segment_length,
        ) = _get_intermediate_nr_points_and_segment_length(dist, densify_config.max_segment_length)

        for i in range(0, nr_points):
            p_point: ShpPoint = ShpLineString([a, b]).interpolate(new_max_segment_length * (i + 1))
            p_2d = Position2D(longitude=p_point.coords[0][0], latitude=p_point.coords[0][1])
            if len(p_point.coords[0]) == THREE_DIMENSIONAL:
                p: Position = Position3D(*p_2d, altitude=p_point.coords[0][2])  # type: ignore
            else:
                p = p_2d
            new_points.append(p)
        return [
            *new_points,
        ]


def textio_to_geojson(src: TextIO) -> GeojsonObject:
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
            logger.warning("src_crs is 2D while input data contains geometries with 3D coordinates")
        result_crs = src_crs if src_crs is not None else result_crs  # override json_crs with src_crs if defined

    elif result_crs is None:
        raise GeodenseError("could not determine CRS from GeoJSON object")

    return result_crs


def _flatten(container: Nested) -> Iterable:
    if isinstance(container, tuple | str):
        raise ValueError("var container should not be of type tuple or str")

    for item in container:
        if isinstance(item, Sequence) and not isinstance(item, tuple) and not isinstance(item, str):
            yield from _flatten(item)
        else:
            yield item


def _is_linestring_geom(geometry_coordinates: GeojsonCoordinates) -> bool:
    """Check if coordinates are of linestring geometry type.

        - Fiona linestring coordinates are of type: list[tuple[float,float,...]])
        - GeoJSON linestring coordinates are of type: list[list[float]]

    Args:
        geometry_coordinates (list): Fiona or GeoJSON coordinates sequence

    Returns:
        bool: if geometry_coordinates is linestring return True else False
    """

    return (
        len(geometry_coordinates) > 0
        and isinstance(geometry_coordinates[0], Sequence)
        and all(isinstance(x, float | int) for x in geometry_coordinates[0])
    )  # also test for int just in case...


def _transform_positions_in_coordinates(
    coordinates: GeojsonCoordinates,
    callback: Callable[[GeojsonCoordinates], T],
) -> Nested | T:
    if not isinstance(coordinates, tuple):
        return list(map(lambda x: _transform_positions_in_coordinates(x, callback), coordinates))
    return callback(coordinates)


def _get_intermediate_nr_points_and_segment_length(dist: float, max_segment_length: float) -> tuple[int, float]:
    if dist <= max_segment_length:
        raise GeodenseError(f"max_segment_length ({max_segment_length}) cannot be bigger or equal than dist ({dist})")
    remainder = dist % max_segment_length
    nr_segments = int(dist // max_segment_length)
    if remainder > 0:
        nr_segments += 1
    new_max_segment_length = dist / nr_segments  # space segments evenly over delta(a,b)
    nr_points = nr_segments - 1  # convert nr of segments to nr of intermediate points, should be at least 1
    return nr_points, new_max_segment_length


def _add_vertices_to_line_segment(linestring: LineStringCoords, coord_index: int, densify_config: DenseConfig) -> int:
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
        linestring_coords = interpolate_geodesic(a, b, densify_config)
    else:
        linestring_coords = interpolate_src_proj(a, b, densify_config)

    p = list(map(lambda x: _round_coordinates(x, prec), linestring_coords))

    linestring[coord_index] = _round_coordinates(linestring[coord_index], prec)
    linestring[coord_index + 1] = _round_coordinates(linestring[coord_index + 1], prec)
    linestring[coord_index + 1 : coord_index + 1] = p
    return len(p)


def _round_coordinates(position: Position, precision: int) -> Position:
    result: Position = Position2D(
        longitude=round(position.longitude, precision),
        latitude=round(position.latitude, precision),
    )

    if len(position) == THREE_DIMENSIONAL:
        position_3d = cast(Position3D, position)
        result = Position3D(
            longitude=result.longitude,
            latitude=result.latitude,
            altitude=round(position_3d.altitude, DEFAULT_PRECISION_METERS),
        )
    return result


def _get_geometry_type(
    geometry: GeojsonGeomNoGeomCollection,
) -> str:
    return cast(str, geometry.type)


def _geom_has_3d_coords(
    geometry: GeojsonGeomNoGeomCollection,
) -> Nested[bool] | bool:
    def _position_is_3d(position: GeojsonCoordinates) -> bool:
        return len(position) == THREE_DIMENSIONAL

    return _transform_positions_in_coordinates(geometry.coordinates, _position_is_3d)


def _has_3d_coordinates(geojson_obj: GeojsonObject, silent: bool | None = False) -> Has3D:
    has_3d_coords: Nested[bool] | bool = transform_geojson_geometries(geojson_obj, _geom_has_3d_coords)

    # in case only value returned from transform_geojson_geometries
    if isinstance(has_3d_coords, bool):  # noqa: SIM108
        has_3d_coords_flat = [has_3d_coords]
    else:
        has_3d_coords_flat = list(_flatten(has_3d_coords))

    if not all(has_3d_coords_flat) and any(has_3d_coords_flat):  # some 3d
        if not silent:
            warning_message = "geometries with mixed 2D and 3D vertices found"
            logger.warning(warning_message)
        return Has3D.some
    elif all(not x for x in has_3d_coords_flat):  # none 3d
        return Has3D.none
    return Has3D.all


def validate_geom_type(geojson_obj: GeojsonObject, command: str = "") -> None:
    geom_types: Nested[str] | str = transform_geojson_geometries(geojson_obj, _get_geometry_type)
    geom_types = [geom_types] if isinstance(geom_types, str) else geom_types
    geom_types_flat = list(_flatten(geom_types))
    if all(g_t in ("Point", "MultiPoint") for g_t in geom_types_flat):
        # situation: all geoms point -> error
        if command:
            error_message = f"cannot run {command} on GeoJSON that only contains (Multi)Point geometries"
        else:
            error_message = "GeoJSON contains only (Multi)Point geometries"
        raise GeodenseError(error_message)
    elif any(gt in ["Point", "MultiPoint"] for gt in geom_types_flat):
        # sitation: some geoms point -> warning
        warning_message = "GeoJSON contains (Multi)Point geometries"
        if command:
            warning_message = f"{warning_message}, cannot run {command} on (Multi)Point geometries"

        logger.warning(warning_message)
    else:
        # situation: no geoms point -> ok
        pass
