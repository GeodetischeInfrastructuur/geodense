from typing import TypeAlias

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

from geodense.geojson import CrsFeatureCollection

GeojsonGeomNoGeomCollection: TypeAlias = (
    Point | MultiPoint | LineString | MultiLineString | Polygon | MultiPolygon
)

GeojsonObject: TypeAlias = (
    Feature | CrsFeatureCollection | Geometry | GeometryCollection
)