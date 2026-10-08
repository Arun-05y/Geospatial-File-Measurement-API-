"""Unit tests for Coordinate Reference System (CRS) selection and reprojection."""

import pytest
from pyproj import CRS
from shapely.geometry import Polygon, LineString

from app.services.crs_service import crs_service


def test_utm_zone_calculation_northern_hemisphere():
    # Minneapolis, MN (lon: -93.2650, lat: 44.9778) -> UTM Zone 15N -> EPSG:32615
    epsg = crs_service.get_utm_epsg_for_coordinates(-93.2650, 44.9778)
    assert epsg == 32615


def test_utm_zone_calculation_southern_hemisphere():
    # Sydney, Australia (lon: 151.2093, lat: -33.8688) -> UTM Zone 56S -> EPSG:32756
    epsg = crs_service.get_utm_epsg_for_coordinates(151.2093, -33.8688)
    assert epsg == 32756


def test_utm_zone_calculation_polar():
    # Arctic (lat > 84) -> UPS North (EPSG:32661)
    epsg_north = crs_service.get_utm_epsg_for_coordinates(10.0, 85.0)
    assert epsg_north == 32661

    # Antarctic (lat < -80) -> UPS South (EPSG:32761)
    epsg_south = crs_service.get_utm_epsg_for_coordinates(10.0, -82.0)
    assert epsg_south == 32761


def test_select_projected_crs_for_geographic():
    poly = Polygon([[-93.265, 44.977], [-93.261, 44.977], [-93.261, 44.974], [-93.265, 44.974], [-93.265, 44.977]])
    source_crs = CRS.from_epsg(4326)
    proj_crs = crs_service.select_projected_crs(poly, source_crs)

    assert proj_crs.is_projected
    assert proj_crs.to_epsg() == 32615


def test_reproject_geometry_metric_accuracy():
    # In geographic degrees, polygon coordinates produce tiny numbers like 0.00001
    # Reprojecting to UTM produces realistic metric dimensions (e.g. hundreds of meters, thousands of m²)
    poly = Polygon([[-93.265, 44.977], [-93.261, 44.977], [-93.261, 44.974], [-93.265, 44.974], [-93.265, 44.977]])
    source_crs = CRS.from_epsg(4326)
    target_crs = CRS.from_epsg(32615)

    projected_geom = crs_service.reproject_geometry(poly, source_crs, target_crs)

    # In degrees, poly.area is ~0.000012
    assert poly.area < 0.001
    # In meters, projected area should be approximately 100,000 m² (10 hectares)
    assert projected_geom.area > 50000
    assert projected_geom.area < 200000


def test_geodesic_calculations():
    poly = Polygon([[-93.265, 44.977], [-93.261, 44.977], [-93.261, 44.974], [-93.265, 44.974], [-93.265, 44.977]])
    area, perimeter = crs_service.compute_geodesic_polygon(poly)
    assert area > 50000
    assert perimeter > 1000

    line = LineString([[-93.265, 44.977], [-93.261, 44.977]])
    length = crs_service.compute_geodesic_length(line)
    assert length > 250
