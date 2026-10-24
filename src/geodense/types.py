from collections.abc import Sequence
from typing import TypeVar

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
from geojson_pydantic.types import (
    LineStringCoords,
    MultiLineStringCoords,
    MultiPointCoords,
    MultiPolygonCoords,
    Position,
)

from geodense.geojson import CrsFeatureCollection

T = TypeVar("T")

type GeojsonGeomNoGeomCollection = Point | MultiPoint | LineString | MultiLineString | Polygon | MultiPolygon

type GeojsonObject = Feature | CrsFeatureCollection | Geometry | GeometryCollection

type GeojsonCoordinates = Position | MultiPointCoords | LineStringCoords | MultiLineStringCoords | MultiPolygonCoords


type Nested[T] = Sequence[T | "Nested" | None]

ReportLineString = tuple[float, tuple[Position, Position]]
