from pyproj import CRS as ProjCrs  # noqa: N811
from pyproj import Transformer

DEFAULT_MAX_SEGMENT_LENGTH = 200
DEFAULT_PRECISION_DEGREES = 9  # digits
DEFAULT_PRECISION_METERS = 4  # digits


class GeodenseError(Exception):
    pass


class DenseConfig:
    geod_empty_exc_message = "DenseConfig.geod is None, cannot perform geodetic calculations without pyproj.Geod object"

    def __init__(
        self: "DenseConfig",
        src_crs: ProjCrs,
        max_segment_length: float | None = None,
        in_projection: bool = False,
    ) -> None:
        self.src_crs = src_crs

        if self.src_crs.is_geographic and in_projection:
            raise GeodenseError(
                f"in_projection can only be used with \
projected coordinate reference systems, crs {self.src_crs} is a geographic crs"
            )
        self.back_transformer = None
        if self.src_crs.is_geographic:
            _geod = self.src_crs.get_geod()
            self.transformer = None
        elif self.src_crs.is_projected:
            base_crs = self._get_base_crs()
            self.transformer = Transformer.from_crs(src_crs, base_crs, always_xy=True)
            _geod = self.src_crs.get_geod()
            self.back_transformer = Transformer.from_crs(base_crs, src_crs, always_xy=True)
        else:
            raise GeodenseError("unexpected crs encountered, crs is neither geographic nor projected")
        if _geod is None:
            raise GeodenseError(self.geod_empty_exc_message)
        self.geod = _geod

        self.in_projection = in_projection
        self.max_segment_length = abs(
            max_segment_length or DEFAULT_MAX_SEGMENT_LENGTH
        )  # when max_segment_length == None -> DEFAULT_MAX_SEGMENT_LENGTH

    def _get_base_crs(self: "DenseConfig") -> ProjCrs:
        if self.src_crs is None:
            raise GeodenseError("field src_proj is None")

        if self.src_crs.is_geographic:
            raise GeodenseError("cannot get base_crs for geographic crs")

        crs_dict = self.src_crs.to_json_dict()
        if crs_dict["type"] == "ProjectedCRS":
            base_crs_id = self.src_crs.to_json_dict()["base_crs"]["id"]
        elif crs_dict["type"] == "CompoundCRS":
            projected_crs = next(x for x in crs_dict["components"] if x["type"] == "ProjectedCRS")
            base_crs_id = projected_crs["base_crs"]["id"]
        return ProjCrs.from_authority(base_crs_id["authority"], base_crs_id["code"])

    def get_coord_precision(self: "DenseConfig") -> int:
        if self.src_crs is None:
            raise GeodenseError("DensifyConfig.source_crs is None")
        return DEFAULT_PRECISION_DEGREES if self.src_crs.is_geographic else DEFAULT_PRECISION_METERS
