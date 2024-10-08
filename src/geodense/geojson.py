import re
from typing import Literal

from geojson_pydantic import FeatureCollection
from pydantic import BaseModel, Field

from geodense.models import GeodenseError


class GeoJsonCrsProp(BaseModel):
    # OGC URN scheme - 8.2 in OGC 05-103
    # urn:ogc:def:crs:{crs_auth}:{crs_version}:{crs_identifier}
    name: str = Field(pattern=r"^urn:ogc:def:crs:.*?:.*?:.*?$")


class GeoJsonCrs(BaseModel):
    properties: GeoJsonCrsProp
    type: Literal["name"] = "name"


class CrsFeatureCollection(FeatureCollection):
    crs: GeoJsonCrs | None = None
    name: str | None = None

    def set_crs_auth_code(self: "CrsFeatureCollection", crs_auth_code: str) -> None:
        crs_auth, crs_identifier = crs_auth_code.split(":")
        geojson_crs_val = f"urn:ogc:def:crs:{crs_auth}::{crs_identifier}"
        if self.crs is None:
            self.crs = GeoJsonCrs(properties=GeoJsonCrsProp(name=geojson_crs_val))
        self.crs.properties.name = geojson_crs_val

    def get_crs_auth_code(self: "CrsFeatureCollection") -> str | None:
        if self.crs is None:
            return None
        result = re.search(r"^urn:ogc:def:crs:(.*?):.*?:(.*?)$", self.crs.properties.name)
        if result is None:
            raise GeodenseError(f"unable to retrieve crs_auth_code from crs.properties.name {self.crs.properties.name}")
        return f"{result.group(1)}:{result.group(2)}"
