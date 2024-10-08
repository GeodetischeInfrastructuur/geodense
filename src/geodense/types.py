from collections.abc import Sequence
from typing import TypeAlias, TypeVar

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

GeojsonGeomNoGeomCollection: TypeAlias = Point | MultiPoint | LineString | MultiLineString | Polygon | MultiPolygon  # noqa: UP040

GeojsonObject: TypeAlias = Feature | CrsFeatureCollection | Geometry | GeometryCollection  # noqa: UP040

GeojsonCoordinates: TypeAlias = (  # noqa: UP040
    Position | MultiPointCoords | LineStringCoords | MultiLineStringCoords | MultiPolygonCoords
)


Nested: TypeAlias = Sequence[T | None | "Nested"]  # noqa: UP040

ReportLineString = tuple[float, tuple[Position, Position]]
