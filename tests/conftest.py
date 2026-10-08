"""Pytest fixtures for Geospatial File Measurement API tests."""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.storage.repository import repository


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_repository():
    """Ensures repository is clean before and after each test."""
    repository.clear()
    yield
    repository.clear()


@pytest.fixture
def sample_kml_path() -> Path:
    return Path(__file__).resolve().parent.parent / "sample_data" / "sample_polygons.kml"


@pytest.fixture
def sample_lines_kml_path() -> Path:
    return Path(__file__).resolve().parent.parent / "sample_data" / "sample_lines.kml"


@pytest.fixture
def sample_points_kml_path() -> Path:
    return Path(__file__).resolve().parent.parent / "sample_data" / "sample_points.kml"


@pytest.fixture
def sample_shapefile_zip_path() -> Path:
    return Path(__file__).resolve().parent.parent / "sample_data" / "sample_shapefile.zip"
