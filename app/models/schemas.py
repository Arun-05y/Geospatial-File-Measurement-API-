"""Pydantic schemas and data models for geospatial measurements and API responses."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class FileStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class MeasurementDetail(BaseModel):
    """Detailed measurements for a single geometry."""
    measurement_status: str = Field(
        ...,
        description="Calculation status: 'calculated', 'not_applicable' (for Point), or 'unsupported_geometry'"
    )
    # Area measurements (for Polygons)
    area_sq_meters: Optional[float] = Field(None, description="Area in square meters (m²)")
    area_sq_km: Optional[float] = Field(None, description="Area in square kilometers (km²)")
    area_hectares: Optional[float] = Field(None, description="Area in hectares (ha)")
    area_acres: Optional[float] = Field(None, description="Area in acres")
    
    # Boundary/Perimeter measurements (for Polygons)
    perimeter_meters: Optional[float] = Field(None, description="Boundary perimeter in meters (m)")
    perimeter_km: Optional[float] = Field(None, description="Boundary perimeter in kilometers (km)")

    # Length measurements (for LineStrings)
    length_meters: Optional[float] = Field(None, description="Length in meters (m)")
    length_km: Optional[float] = Field(None, description="Length in kilometers (km)")
    
    # Geodesic metrics computed on WGS84 ellipsoid
    geodesic_area_sq_meters: Optional[float] = Field(None, description="Ellipsoidal geodesic area in m²")
    geodesic_length_meters: Optional[float] = Field(None, description="Ellipsoidal geodesic length in meters")
    
    # Projected CRS used for calculation
    projected_crs: Optional[str] = Field(None, description="Projected coordinate system used (e.g. EPSG:32633 UTM)")
    notes: Optional[str] = Field(None, description="Additional notes or error reason if unsupported")


class FeatureItem(BaseModel):
    """Represents an extracted geospatial feature."""
    feature_id: Any = Field(..., description="Feature ID or sequential index")
    geometry_type: str = Field(..., description="Geometry type: Polygon, LineString, Point, etc.")
    geometry: dict[str, Any] = Field(..., description="GeoJSON geometry representation")
    crs: str = Field(..., description="Feature source coordinate reference system")
    properties: dict[str, Any] = Field(default_factory=dict, description="Feature attributes/properties")
    measurements: Optional[MeasurementDetail] = Field(None, description="Calculated geometric measurements")


class FileInfoResponse(BaseModel):
    """Metadata and processing status for an uploaded file."""
    id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original uploaded filename")
    feature_count: int = Field(..., description="Total number of extracted features")
    crs: str = Field(..., description="Detected coordinate reference system")
    status: FileStatus = Field(..., description="Processing status (e.g. COMPLETED)")
    uploaded_at: Optional[datetime] = Field(None, description="Timestamp of file upload")
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")
    error_message: Optional[str] = Field(None, description="Error explanation if status is FAILED")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "abc123",
                "filename": "survey.kml",
                "feature_count": 120,
                "crs": "EPSG:4326",
                "status": "COMPLETED"
            }
        }
    }


class MeasurementSummary(BaseModel):
    """Summary of measurements across all features in a file."""
    total_features: int = 0
    polygon_count: int = 0
    linestring_count: int = 0
    point_count: int = 0
    unsupported_count: int = 0
    total_area_sq_meters: float = 0.0
    total_area_sq_km: float = 0.0
    total_area_hectares: float = 0.0
    total_length_meters: float = 0.0
    total_length_km: float = 0.0
    projected_crs_used: list[str] = Field(default_factory=list)


class FileMeasurementsResponse(BaseModel):
    """Response returned by GET /api/files/{id}/measurements/"""
    file_id: str
    filename: str
    source_crs: str
    summary: MeasurementSummary
    features: list[FeatureItem]


class FileListResponse(BaseModel):
    """Paginated or listed uploaded files."""
    total: int
    files: list[FileInfoResponse]


class HealthResponse(BaseModel):
    status: str
    version: str
    app: str
