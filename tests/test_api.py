"""API integration tests for Geospatial File Measurement endpoints."""

from pathlib import Path
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    response = client.get("/api/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_upload_kml_and_get_info(client: TestClient, sample_kml_path: Path):
    # Upload KML file
    with open(sample_kml_path, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("sample_polygons.kml", f, "application/vnd.google-earth.kml+xml")},
        )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["filename"] == "sample_polygons.kml"
    assert data["feature_count"] == 2
    assert data["crs"] == "EPSG:4326"
    assert data["status"] == "COMPLETED"

    file_id = data["id"]

    # Retrieve File Information via GET /api/files/{id}/
    info_resp = client.get(f"/api/files/{file_id}/")
    assert info_resp.status_code == 200
    info_data = info_resp.json()
    assert info_data["id"] == file_id
    assert info_data["filename"] == "sample_polygons.kml"
    assert info_data["feature_count"] == 2
    assert info_data["crs"] == "EPSG:4326"
    assert info_data["status"] == "COMPLETED"


def test_get_measurements_polygon_kml(client: TestClient, sample_kml_path: Path):
    with open(sample_kml_path, "rb") as f:
        up_resp = client.post(
            "/api/files/",
            files={"file": ("sample_polygons.kml", f, "application/vnd.google-earth.kml+xml")},
        )
    file_id = up_resp.json()["id"]

    # Get measurements
    meas_resp = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_resp.status_code == 200
    meas_data = meas_resp.json()

    assert meas_data["file_id"] == file_id
    assert meas_data["summary"]["total_features"] == 2
    assert meas_data["summary"]["polygon_count"] == 2
    assert meas_data["summary"]["total_area_sq_meters"] > 0
    assert "EPSG:32615" in meas_data["summary"]["projected_crs_used"]

    # Check each feature's measurement fields
    features = meas_data["features"]
    assert len(features) == 2
    for feat in features:
        assert feat["geometry_type"] == "Polygon"
        assert feat["crs"] == "EPSG:4326"
        assert "geometry" in feat
        assert "properties" in feat
        m = feat["measurements"]
        assert m["measurement_status"] == "calculated"
        assert m["area_sq_meters"] > 10000
        assert m["perimeter_meters"] > 100
        assert m["projected_crs"] == "EPSG:32615"


def test_get_measurements_lines_kml(client: TestClient, sample_lines_kml_path: Path):
    with open(sample_lines_kml_path, "rb") as f:
        up_resp = client.post(
            "/api/files/",
            files={"file": ("sample_lines.kml", f, "application/vnd.google-earth.kml+xml")},
        )
    file_id = up_resp.json()["id"]

    meas_resp = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_resp.status_code == 200
    meas_data = meas_resp.json()

    assert meas_data["summary"]["linestring_count"] == 2
    assert meas_data["summary"]["total_length_meters"] > 0

    feat0 = meas_data["features"][0]
    assert feat0["geometry_type"] == "LineString"
    assert feat0["measurements"]["length_meters"] > 1000


def test_get_measurements_points_kml(client: TestClient, sample_points_kml_path: Path):
    with open(sample_points_kml_path, "rb") as f:
        up_resp = client.post(
            "/api/files/",
            files={"file": ("sample_points.kml", f, "application/vnd.google-earth.kml+xml")},
        )
    file_id = up_resp.json()["id"]

    meas_resp = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_resp.status_code == 200
    meas_data = meas_resp.json()

    assert meas_data["summary"]["point_count"] == 2
    # Verify points do not crash and report not_applicable
    for f in meas_data["features"]:
        assert f["geometry_type"] == "Point"
        assert f["measurements"]["measurement_status"] == "not_applicable"
        assert f["measurements"]["area_sq_meters"] is None
        assert f["measurements"]["length_meters"] is None


def test_upload_shapefile_zip(client: TestClient, sample_shapefile_zip_path: Path):
    with open(sample_shapefile_zip_path, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("sample_shapefile.zip", f, "application/zip")},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "sample_shapefile.zip"
    assert data["feature_count"] == 2
    assert data["status"] == "COMPLETED"

    file_id = data["id"]
    meas_resp = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_resp.status_code == 200
    meas_data = meas_resp.json()
    assert len(meas_data["features"]) == 2
    assert meas_data["features"][0]["properties"]["NAME"] == "Commercial Lot A"


def test_list_and_delete_files(client: TestClient, sample_kml_path: Path):
    with open(sample_kml_path, "rb") as f:
        up_resp = client.post(
            "/api/files/",
            files={"file": ("sample_polygons.kml", f, "application/vnd.google-earth.kml+xml")},
        )
    file_id = up_resp.json()["id"]

    # List files
    list_resp = client.get("/api/files/")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    # Delete file
    del_resp = client.delete(f"/api/files/{file_id}/")
    assert del_resp.status_code == 204

    # Subsequent GET should return 404
    get_resp = client.get(f"/api/files/{file_id}/")
    assert get_resp.status_code == 404


def test_unsupported_file_extension(client: TestClient):
    response = client.post(
        "/api/files/",
        files={"file": ("document.txt", b"plain text", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["message"]


def test_empty_file_upload(client: TestClient):
    response = client.post(
        "/api/files/",
        files={"file": ("empty.kml", b"", "application/vnd.google-earth.kml+xml")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["message"]


def test_nonexistent_file_id_returns_404(client: TestClient):
    response = client.get("/api/files/nonexistent_id/")
    assert response.status_code == 404
