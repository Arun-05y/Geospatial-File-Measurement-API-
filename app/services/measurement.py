"""Service for computing geometric and geodesic measurements on vector features."""

from typing import Tuple
from shapely.geometry.base import BaseGeometry
from pyproj import CRS

from app.models.schemas import MeasurementDetail
from app.services.crs_service import crs_service


class MeasurementEngine:
    """Calculates metric area, perimeter, and length using projected CRS transformations and geodesics."""

    SQ_METERS_TO_SQ_KM = 1e-6
    SQ_METERS_TO_HECTARES = 1e-4
    SQ_METERS_TO_ACRES = 0.000247105381

    METERS_TO_KM = 0.001

    @classmethod
    def calculate_measurements(
        cls,
        geom: BaseGeometry,
        source_crs: CRS,
        geometry_type: str,
    ) -> MeasurementDetail:
        """
        Calculates measurements for a given Shapely geometry based on its type.
        Gracefully handles unsupported types and points.
        """
        if geom is None or geom.is_empty:
            return MeasurementDetail(
                measurement_status="empty_geometry",
                notes="Geometry is empty or invalid.",
            )

        norm_type = geometry_type.upper()

        # 1. Point / MultiPoint
        if "POINT" in norm_type:
            return MeasurementDetail(
                measurement_status="not_applicable",
                notes="Point geometry: area and length measurements are not applicable.",
            )

        # 2. Polygon / MultiPolygon
        if "POLYGON" in norm_type:
            try:
                # Determine projected metric CRS (e.g. UTM)
                projected_crs = crs_service.select_projected_crs(geom, source_crs)
                projected_geom = crs_service.reproject_geometry(geom, source_crs, projected_crs)

                area_m2 = round(abs(projected_geom.area), 4)
                perimeter_m = round(abs(projected_geom.length), 4)

                # Ellipsoidal Geodesic measurement if source is geographic WGS84
                geo_area = None
                if source_crs.is_geographic:
                    ga, _ = crs_service.compute_geodesic_polygon(geom)
                    geo_area = round(ga, 4)

                return MeasurementDetail(
                    measurement_status="calculated",
                    area_sq_meters=area_m2,
                    area_sq_km=round(area_m2 * cls.SQ_METERS_TO_SQ_KM, 6),
                    area_hectares=round(area_m2 * cls.SQ_METERS_TO_HECTARES, 6),
                    area_acres=round(area_m2 * cls.SQ_METERS_TO_ACRES, 6),
                    perimeter_meters=perimeter_m,
                    perimeter_km=round(perimeter_m * cls.METERS_TO_KM, 6),
                    geodesic_area_sq_meters=geo_area,
                    projected_crs=f"EPSG:{projected_crs.to_epsg()}" if projected_crs.to_epsg() else str(projected_crs.name),
                    notes=f"Calculated in {projected_crs.name or str(projected_crs.to_epsg())}",
                )
            except Exception as e:
                return MeasurementDetail(
                    measurement_status="calculation_error",
                    notes=f"Error calculating polygon measurement: {str(e)}",
                )

        # 3. LineString / MultiLineString
        if "LINESTRING" in norm_type or "LINE" in norm_type:
            try:
                # Determine projected metric CRS (e.g. UTM)
                projected_crs = crs_service.select_projected_crs(geom, source_crs)
                projected_geom = crs_service.reproject_geometry(geom, source_crs, projected_crs)

                length_m = round(abs(projected_geom.length), 4)

                # Ellipsoidal Geodesic length if source is geographic WGS84
                geo_length = None
                if source_crs.is_geographic:
                    gl = crs_service.compute_geodesic_length(geom)
                    geo_length = round(gl, 4)

                return MeasurementDetail(
                    measurement_status="calculated",
                    length_meters=length_m,
                    length_km=round(length_m * cls.METERS_TO_KM, 6),
                    geodesic_length_meters=geo_length,
                    projected_crs=f"EPSG:{projected_crs.to_epsg()}" if projected_crs.to_epsg() else str(projected_crs.name),
                    notes=f"Calculated in {projected_crs.name or str(projected_crs.to_epsg())}",
                )
            except Exception as e:
                return MeasurementDetail(
                    measurement_status="calculation_error",
                    notes=f"Error calculating linestring measurement: {str(e)}",
                )

        # 4. Graceful handling for unsupported geometry types (e.g. GeometryCollection)
        return MeasurementDetail(
            measurement_status="unsupported_geometry",
            notes=f"Geometry type '{geometry_type}' is not supported for measurement calculation.",
        )


measurement_engine = MeasurementEngine()
