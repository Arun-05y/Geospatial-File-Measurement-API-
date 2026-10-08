"""In-memory and file-based repository for tracking uploaded files and processed measurements."""

from datetime import datetime
from threading import Lock
from typing import Dict, List, Optional, Tuple

from app.models.schemas import (
    FileInfoResponse,
    FileMeasurementsResponse,
    FileStatus,
)


class FileRepository:
    """Thread-safe storage repository for uploaded geospatial files and their measurements."""

    def __init__(self):
        self._lock = Lock()
        self._files: Dict[str, FileInfoResponse] = {}
        self._measurements: Dict[str, FileMeasurementsResponse] = {}

    def save(
        self,
        file_info: FileInfoResponse,
        measurements: Optional[FileMeasurementsResponse] = None,
    ) -> None:
        """Saves or updates file metadata and measurements."""
        with self._lock:
            self._files[file_info.id] = file_info
            if measurements:
                self._measurements[file_info.id] = measurements

    def update_status(
        self, file_id: str, status: FileStatus, error_message: Optional[str] = None
    ) -> None:
        """Updates status of an existing file."""
        with self._lock:
            if file_id in self._files:
                current = self._files[file_id]
                updated = current.model_copy(
                    update={"status": status, "error_message": error_message}
                )
                self._files[file_id] = updated

    def get_file(self, file_id: str) -> Optional[FileInfoResponse]:
        """Retrieves file metadata by unique ID."""
        with self._lock:
            return self._files.get(file_id)

    def get_measurements(self, file_id: str) -> Optional[FileMeasurementsResponse]:
        """Retrieves calculated measurements by file ID."""
        with self._lock:
            return self._measurements.get(file_id)

    def list_files(self, skip: int = 0, limit: int = 50) -> Tuple[int, List[FileInfoResponse]]:
        """Returns total count and paginated list of uploaded files."""
        with self._lock:
            all_files = list(self._files.values())
            # Sort newest first
            all_files.sort(
                key=lambda f: f.uploaded_at or datetime.min, reverse=True
            )
            return len(all_files), all_files[skip : skip + limit]

    def delete(self, file_id: str) -> bool:
        """Deletes file metadata and associated measurements."""
        with self._lock:
            removed_info = self._files.pop(file_id, None)
            self._measurements.pop(file_id, None)
            return removed_info is not None

    def clear(self) -> None:
        """Clears all records (useful for testing)."""
        with self._lock:
            self._files.clear()
            self._measurements.clear()


repository = FileRepository()
