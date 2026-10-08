"""Service for Coordinate Reference System (CRS) detection, transformation, and geodesic calculations."""

import math
from typing import Optional, Tuple
import numpy as np
import pyproj
from pyproj import CRS, Transformer, Geod
import shapely
from shapely.geometry.base import BaseGeometry

from app.core.exceptions import CRSTransformationError


class CRSService:
    """Handles CRS inspection, dynamic UTM zone selection, reprojection, and geodesic computations."""

    def __init__(self):
        self.geod = Geod(ellps="WGS84")

    @staticmethod
    def parse_crs(crs_input: Optional[str]) -> CRS:
        """Parses a CRS string, WKT, or authority code into a pyproj.CRS object."""
        if not crs_input or crs_input.strip() == "":
            return CRS.from_epsg(4326)
        try:
            return CRS.from_user_input(crs_input.strip())
        except Exception:
            # Fallback to WGS84 if unrecognizable
            return CRS.from_epsg(4326)

    @staticmethod
    def get_utm_epsg_for_coordinates(lon: float, lat: float) -> int:
        """
        Determines the optimal Universal Transverse Mercator (UTM) or Polar Stereographic
        EPSG code for a given longitude and latitude in WGS84.
        """
        # Handle polar regions with Universal Polar Stereographic (UPS)
        if lat > 84.0:
            return 32661  # WGS 84 / UPS North
        if lat < -80.0:
            return 32761  # WGS 84 / UPS South

        # Standard UTM Zone calculation: zones 1 to 60 (each 6 degrees wide)
        zone = int(math.floor((lon + 180.0) / 6.0)) + 1
        zone = max(1, min(60, zone))

        # Northern hemisphere: EPSG 32601 - 32660
        # Southern hemisphere: EPSG 32701 - 32760
        if lat >= 0:
            return 32600 + zone
        else:
            return 32700 + zone

    def select_projected_crs(self, geom: BaseGeometry, source_crs: CRS) -> CRS:
        """
        Chooses an appropriate metric projected coordinate system for a geometry.
        If already projected in linear meters, returns source CRS.
        If geographic (e.g. EPSG:4326), computes centroid and selects optimal UTM zone.
        """
        if source_crs.is_projected:
            return source_crs

        # For geographic coordinates, extract centroid to find optimal UTM zone
        try:
            # If source is not EPSG:4326, project centroid to EPSG:4326 first
            centroid = geom.centroid
            lon, lat = centroid.x, centroid.y
            
            if source_crs.to_epsg() != 4326:
                transformer_to_4326 = Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)
                lon, lat = transformer_to_4326.transform(lon, lat)

            utm_epsg = self.get_utm_epsg_for_coordinates(lon, lat)
            return CRS.from_epsg(utm_epsg)
        except Exception as e:
            # Fallback to World Mercator (EPSG:3395) or standard UTM zone 1
            return CRS.from_epsg(3857)

    def reproject_geometry(
        self, geom: BaseGeometry, source_crs: CRS, target_crs: CRS
    ) -> BaseGeometry:
        """Reprojects a Shapely geometry from source_crs to target_crs."""
        if source_crs == target_crs or source_crs.equals(target_crs):
            return geom

        try:
            transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)

            def _reproject_coords(coords):
                x, y = transformer.transform(coords[..., 0], coords[..., 1])
                return np.column_stack([x, y])

            return shapely.transform(geom, _reproject_coords)
        except Exception as e:
            raise CRSTransformationError(f"Failed to reproject geometry from {source_crs} to {target_crs}: {str(e)}")

    def compute_geodesic_polygon(self, geom: BaseGeometry) -> Tuple[float, float]:
        """
        Computes the ellipsoidal geodesic area (m²) and perimeter (m) on the WGS84 ellipsoid
        for a polygon in geographic coordinates (lon, lat).
        """
        try:
            area, perimeter = self.geod.geometry_area_perimeter(geom)
            return abs(area), abs(perimeter)
        except Exception:
            return 0.0, 0.0

    def compute_geodesic_length(self, geom: BaseGeometry) -> float:
        """
        Computes the ellipsoidal geodesic length (m) on the WGS84 ellipsoid
        for a linestring in geographic coordinates (lon, lat).
        """
        try:
            length = self.geod.geometry_length(geom)
            return abs(length)
        except Exception:
            return 0.0


crs_service = CRSService()
