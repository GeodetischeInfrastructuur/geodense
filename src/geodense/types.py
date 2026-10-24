from collections.abc import Sequence
from typing import Any, TypeVar

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

# A GeoJSON Feature with an arbitrary geometry and arbitrary properties. geodense
# traverses features generically and does not depend on the concrete Geom/Props.
type GeojsonFeature = Feature[Geometry, Any]

type GeojsonGeomNoGeomCollection = Point | MultiPoint | LineString | MultiLineString | Polygon | MultiPolygon

type GeojsonObject = GeojsonFeature | CrsFeatureCollection | Geometry | GeometryCollection

type GeojsonCoordinates = Position | MultiPointCoords | LineStringCoords | MultiLineStringCoords | MultiPolygonCoords


type Nested[T] = Sequence[T | "Nested[T]" | None]

ReportLineString = tuple[float, tuple[Position, Position]]
