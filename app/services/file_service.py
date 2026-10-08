"""Service orchestrating file ingestion, parsing, and measurement calculations."""

from datetime import datetime
from pathlib import Path
import uuid
from fastapi import UploadFile

from app.config import settings
from app.core.exceptions import InvalidFileError, ResourceNotFoundError
from app.models.schemas import (
    FeatureItem,
    FileInfoResponse,
    FileMeasurementsResponse,
    FileStatus,
    MeasurementSummary,
)
from app.services.measurement import measurement_engine
from app.services.parsers.kml_parser import KMLParser
from app.services.parsers.shapefile_parser import ShapefileParser
from app.storage.repository import repository


class FileService:
    """Coordinates file uploads, parser selection, geometry measurements, and data persistence."""

    def __init__(self):
        self.shapefile_parser = ShapefileParser()
        self.kml_parser = KMLParser()

    async def process_upload(self, upload_file: UploadFile) -> FileInfoResponse:
        """Validates, stores, parses, and computes measurements for an uploaded geospatial file."""
        filename = upload_file.filename or "unknown_file"
        file_ext = Path(filename).suffix.lower()

        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise InvalidFileError(
                f"Unsupported file format '{file_ext}'. Allowed formats: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )

        file_id = uuid.uuid4().hex[:10]
        saved_path = settings.UPLOAD_DIR / f"{file_id}_{filename}"

        # Write uploaded file to disk asynchronously with size check
        size_bytes = 0
        try:
            with open(saved_path, "wb") as out_file:
                while chunk := await upload_file.read(1024 * 64):
                    size_bytes += len(chunk)
                    if size_bytes > settings.MAX_FILE_SIZE_BYTES:
                        raise InvalidFileError(
                            f"File size exceeds maximum allowable limit of {settings.MAX_FILE_SIZE_BYTES / (1024 * 1024):.0f}MB."
                        )
                    out_file.write(chunk)
        except Exception:
            if saved_path.exists():
                saved_path.unlink()
            raise

        if size_bytes == 0:
            if saved_path.exists():
                saved_path.unlink()
            raise InvalidFileError("Uploaded file is empty.")

        # Create initial record
        file_info = FileInfoResponse(
            id=file_id,
            filename=filename,
            feature_count=0,
            crs=settings.DEFAULT_CRS,
            status=FileStatus.PROCESSING,
            uploaded_at=datetime.utcnow(),
            file_size_bytes=size_bytes,
        )
        repository.save(file_info)

        # Parse file based on extension
        try:
            if file_ext == ".zip":
                dataset = self.shapefile_parser.parse(saved_path)
            elif file_ext == ".kml":
                dataset = self.kml_parser.parse(saved_path)
            else:
                raise InvalidFileError(f"No parser available for {file_ext}")

            # Compute measurements for all features
            features: list[FeatureItem] = []
            summary = MeasurementSummary(total_features=len(dataset.features))
            projected_crs_set = set()

            for item in dataset.features:
                measurement = measurement_engine.calculate_measurements(
                    geom=item.shapely_geom,
                    source_crs=dataset.crs,
                    geometry_type=item.geometry_type,
                )

                norm_type = item.geometry_type.upper()
                if "POLYGON" in norm_type:
                    summary.polygon_count += 1
                    if measurement.area_sq_meters is not None:
                        summary.total_area_sq_meters += measurement.area_sq_meters
                        summary.total_area_sq_km += measurement.area_sq_km or 0.0
                        summary.total_area_hectares += measurement.area_hectares or 0.0
                elif "LINE" in norm_type:
                    summary.linestring_count += 1
                    if measurement.length_meters is not None:
                        summary.total_length_meters += measurement.length_meters
                        summary.total_length_km += measurement.length_km or 0.0
                elif "POINT" in norm_type:
                    summary.point_count += 1
                else:
                    summary.unsupported_count += 1

                if measurement.projected_crs:
                    projected_crs_set.add(measurement.projected_crs)

                features.append(
                    FeatureItem(
                        feature_id=item.feature_id,
                        geometry_type=item.geometry_type,
                        geometry=item.geometry_geojson,
                        crs=dataset.crs_str,
                        properties=item.properties,
                        measurements=measurement,
                    )
                )

            # Round totals for summary
            summary.total_area_sq_meters = round(summary.total_area_sq_meters, 4)
            summary.total_area_sq_km = round(summary.total_area_sq_km, 6)
            summary.total_area_hectares = round(summary.total_area_hectares, 6)
            summary.total_length_meters = round(summary.total_length_meters, 4)
            summary.total_length_km = round(summary.total_length_km, 6)
            summary.projected_crs_used = sorted(list(projected_crs_set))

            measurements_resp = FileMeasurementsResponse(
                file_id=file_id,
                filename=filename,
                source_crs=dataset.crs_str,
                summary=summary,
                features=features,
            )

            # Update file info to COMPLETED
            completed_info = file_info.model_copy(
                update={
                    "feature_count": len(features),
                    "crs": dataset.crs_str,
                    "status": FileStatus.COMPLETED,
                }
            )
            repository.save(completed_info, measurements_resp)
            return completed_info

        except Exception as e:
            repository.update_status(file_id, FileStatus.FAILED, error_message=str(e))
            raise

    def get_file_info(self, file_id: str) -> FileInfoResponse:
        """Retrieves metadata for an uploaded file."""
        info = repository.get_file(file_id)
        if not info:
            raise ResourceNotFoundError(f"File with ID '{file_id}' was not found.")
        return info

    def get_file_measurements(self, file_id: str) -> FileMeasurementsResponse:
        """Retrieves feature measurements for an uploaded file."""
        self.get_file_info(file_id)  # Validate existence
        measurements = repository.get_measurements(file_id)
        if not measurements:
            raise ResourceNotFoundError(f"Measurements for file ID '{file_id}' are not available.")
        return measurements

    def list_files(self, skip: int = 0, limit: int = 50) -> tuple[int, list[FileInfoResponse]]:
        """Lists uploaded files with pagination."""
        return repository.list_files(skip=skip, limit=limit)

    def delete_file(self, file_id: str) -> bool:
        """Deletes file metadata and record."""
        return repository.delete(file_id)


file_service = FileService()
