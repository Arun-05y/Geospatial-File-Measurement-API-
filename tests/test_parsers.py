"""Unit tests for Shapefile and KML parsers."""

from pathlib import Path
import pytest

from app.core.exceptions import CorruptedArchiveError, InvalidFileError
from app.services.parsers.kml_parser import KMLParser
from app.services.parsers.shapefile_parser import ShapefileParser


def test_kml_parser_polygons(sample_kml_path: Path):
    parser = KMLParser()
    dataset = parser.parse(sample_kml_path)

    assert dataset.crs_str == "EPSG:4326"
    assert len(dataset.features) == 2
    for f in dataset.features:
        assert f.geometry_type == "Polygon"
        assert f.properties.get("crop") in ("Soybean", "Corn")
        assert f.shapely_geom.is_valid


def test_kml_parser_lines(sample_lines_kml_path: Path):
    parser = KMLParser()
    dataset = parser.parse(sample_lines_kml_path)

    assert len(dataset.features) == 2
    assert any(f.properties.get("material") == "Steel" for f in dataset.features)
    assert all(f.geometry_type == "LineString" for f in dataset.features)


def test_kml_parser_points(sample_points_kml_path: Path):
    parser = KMLParser()
    dataset = parser.parse(sample_points_kml_path)

    assert len(dataset.features) == 2
    assert all(f.geometry_type == "Point" for f in dataset.features)


def test_shapefile_parser_zip(sample_shapefile_zip_path: Path):
    parser = ShapefileParser()
    dataset = parser.parse(sample_shapefile_zip_path)

    assert len(dataset.features) == 2
    assert all(f.geometry_type == "Polygon" for f in dataset.features)
    # Check attributes extracted from .dbf
    assert any(f.properties.get("NAME") == "Commercial Lot A" for f in dataset.features)
    assert any(f.properties.get("ZONING") == "Residential" for f in dataset.features)


def test_shapefile_parser_invalid_zip(tmp_path: Path):
    fake_zip = tmp_path / "corrupt.zip"
    fake_zip.write_text("not a real zip")

    parser = ShapefileParser()
    with pytest.raises(InvalidFileError):
        parser.parse(fake_zip)


def test_shapefile_parser_missing_companion_files(tmp_path: Path):
    import zipfile
    bad_zip = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad_zip, "w") as zf:
        zf.writestr("test.shp", b"dummy shp")
        # Missing .shx and .dbf

    parser = ShapefileParser()
    with pytest.raises(CorruptedArchiveError):
        parser.parse(bad_zip)
