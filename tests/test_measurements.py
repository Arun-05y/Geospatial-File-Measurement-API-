"""Unit tests for geometry measurement calculation engine."""

import pytest
from pyproj import CRS
from shapely.geometry import Polygon, LineString, Point, GeometryCollection

from app.services.measurement import measurement_engine


def test_polygon_measurement_area_and_units():
    # Square polygon in degrees
    poly = Polygon([[-93.265, 44.977], [-93.261, 44.977], [-93.261, 44.974], [-93.265, 44.974], [-93.265, 44.977]])
    source_crs = CRS.from_epsg(4326)

    meas = measurement_engine.calculate_measurements(poly, source_crs, "Polygon")

    assert meas.measurement_status == "calculated"
    assert meas.area_sq_meters is not None
    assert meas.area_sq_meters > 50000
    assert meas.area_sq_km is not None
    assert meas.area_hectares is not None
    assert meas.area_acres is not None
    assert meas.perimeter_meters is not None
    assert meas.projected_crs == "EPSG:32615"
    assert meas.geodesic_area_sq_meters is not None


def test_linestring_measurement_length():
    line = LineString([[-93.270, 44.970], [-93.265, 44.975], [-93.260, 44.980]])
    source_crs = CRS.from_epsg(4326)

    meas = measurement_engine.calculate_measurements(line, source_crs, "LineString")

    assert meas.measurement_status == "calculated"
    assert meas.length_meters is not None
    assert meas.length_meters > 1000
    assert meas.length_km is not None
    assert meas.area_sq_meters is None  # LineString has no area
    assert meas.projected_crs == "EPSG:32615"


def test_point_measurement_graceful_handling():
    pt = Point(-93.265, 44.977)
    source_crs = CRS.from_epsg(4326)

    meas = measurement_engine.calculate_measurements(pt, source_crs, "Point")

    # Point requires no measurement and must not crash
    assert meas.measurement_status == "not_applicable"
    assert meas.area_sq_meters is None
    assert meas.length_meters is None
    assert "Point geometry" in meas.notes


def test_unsupported_geometry_graceful_handling():
    # GeometryCollection is not a supported single-metric geometry
    gc = GeometryCollection([Point(0, 0), LineString([(0, 0), (1, 1)])])
    source_crs = CRS.from_epsg(4326)

    meas = measurement_engine.calculate_measurements(gc, source_crs, "GeometryCollection")

    assert meas.measurement_status == "unsupported_geometry"
    assert meas.area_sq_meters is None
    assert meas.length_meters is None
    assert "not supported" in meas.notes
