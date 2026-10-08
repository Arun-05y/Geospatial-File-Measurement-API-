"""API endpoints for geospatial file upload, inspection, and measurement extraction."""

from fastapi import APIRouter, File, Query, UploadFile, status
from app.models.schemas import (
    FileInfoResponse,
    FileListResponse,
    FileMeasurementsResponse,
)
from app.services.file_service import file_service

router = APIRouter(prefix="/files", tags=["Files"])


@router.post(
    "/",
    response_model=FileInfoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and process a geospatial file",
    description="Upload a .zip (containing a Shapefile) or a .kml file. Extracts vector features and computes measurements.",
)
async def upload_file(
    file: UploadFile = File(..., description="Geospatial file (.zip Shapefile or .kml)")
) -> FileInfoResponse:
    """Uploads and processes a geospatial file."""
    return await file_service.process_upload(file)


@router.get(
    "/{file_id}/",
    response_model=FileInfoResponse,
    summary="Get file information",
    description="Returns metadata and status for an uploaded file, matching the required specification format.",
)
async def get_file_info(file_id: str) -> FileInfoResponse:
    """Returns metadata for an uploaded file."""
    return file_service.get_file_info(file_id)


@router.get(
    "/{file_id}/measurements/",
    response_model=FileMeasurementsResponse,
    summary="Get file measurements",
    description="Returns area, length, and geometric measurements for all features in the file.",
)
async def get_file_measurements(file_id: str) -> FileMeasurementsResponse:
    """Returns measurements for features in the uploaded file."""
    return file_service.get_file_measurements(file_id)


@router.get(
    "/",
    response_model=FileListResponse,
    summary="List uploaded files",
    description="Returns a paginated list of all uploaded geospatial files.",
)
async def list_files(
    skip: int = Query(0, ge=0, description="Offset"),
    limit: int = Query(50, ge=1, le=100, description="Limit"),
) -> FileListResponse:
    """Lists all uploaded files."""
    total, files = file_service.list_files(skip=skip, limit=limit)
    return FileListResponse(total=total, files=files)


@router.delete(
    "/{file_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an uploaded file",
    description="Removes an uploaded file, its metadata, and calculated measurements.",
)
async def delete_file(file_id: str):
    """Deletes an uploaded file."""
    file_service.delete_file(file_id)
    return None
