"""KML (.kml) parser using defusedxml, shapely, and pyproj."""

from pathlib import Path
import re
from typing import Any, List, Optional, Tuple
from pyproj import CRS
from shapely.geometry import (
    Point,
    LineString,
    Polygon,
    MultiPolygon,
    MultiLineString,
    GeometryCollection,
    mapping,
)
from shapely.geometry.base import BaseGeometry
from xml.etree.ElementTree import Element
import defusedxml.ElementTree as dET

from app.config import settings
from app.core.exceptions import InvalidFileError, ParsingError
from app.services.parsers.base import BaseParser, ParsedDataset, ParsedFeature


class KMLParser(BaseParser):
    """Parses OGC KML files into structured features and geometries."""

    def parse(self, file_path: Path) -> ParsedDataset:
        try:
            tree = dET.parse(str(file_path))
            root = tree.getroot()
        except Exception as e:
            raise InvalidFileError(f"Failed to parse XML content in KML file: {str(e)}")

        # KML by OGC specification standard is EPSG:4326 (WGS84 lon, lat)
        crs = CRS.from_epsg(4326)
        crs_str = settings.DEFAULT_CRS

        features: List[ParsedFeature] = []
        placemark_index = 0

        # Traverse all elements to find Placemarks
        for elem in root.iter():
            local_tag = self._get_local_tag(elem.tag)
            if local_tag == "Placemark":
                parsed = self._parse_placemark(elem, placemark_index)
                if parsed:
                    features.append(parsed)
                    placemark_index += 1

        if not features:
            # Fallback: check if geometries exist directly without Placemark wrapper
            direct_features = self._parse_orphan_geometries(root, placemark_index)
            features.extend(direct_features)

        return ParsedDataset(crs=crs, crs_str=crs_str, features=features)

    @staticmethod
    def _get_local_tag(tag: str) -> str:
        """Strips XML namespace from tag name."""
        return tag.split("}")[-1] if "}" in tag else tag

    def _parse_placemark(self, elem: Element, index: int) -> Optional[ParsedFeature]:
        """Extracts metadata and geometry from a <Placemark> element."""
        props: dict[str, Any] = {}
        geom: Optional[BaseGeometry] = None
        placemark_id = elem.attrib.get("id")

        for child in elem:
            tag = self._get_local_tag(child.tag)
            if tag == "name" and child.text:
                props["name"] = child.text.strip()
            elif tag == "description" and child.text:
                props["description"] = child.text.strip()
            elif tag == "ExtendedData":
                props.update(self._parse_extended_data(child))
            elif tag in ("Point", "LineString", "Polygon", "MultiGeometry", "LinearRing"):
                geom = self._parse_geometry_element(child)

        if geom is None or geom.is_empty:
            return None

        feature_id = placemark_id or props.get("name") or index

        return ParsedFeature(
            feature_id=feature_id,
            geometry_type=geom.geom_type,
            geometry_geojson=mapping(geom),
            shapely_geom=geom,
            properties=props,
        )

    def _parse_orphan_geometries(self, root: Element, start_index: int) -> List[ParsedFeature]:
        """Parses any root-level or unparented geometries in the KML."""
        features: List[ParsedFeature] = []
        idx = start_index
        for child in root.iter():
            tag = self._get_local_tag(child.tag)
            if tag in ("Polygon", "LineString", "Point"):
                parent_tag = self._get_local_tag(child.attrib.get("parent", ""))
                # If geometry parsed, construct feature
                geom = self._parse_geometry_element(child)
                if geom and not geom.is_empty:
                    features.append(
                        ParsedFeature(
                            feature_id=idx,
                            geometry_type=geom.geom_type,
                            geometry_geojson=mapping(geom),
                            shapely_geom=geom,
                            properties={},
                        )
                    )
                    idx += 1
        return features

    def _parse_extended_data(self, elem: Element) -> dict[str, Any]:
        """Extracts key-value attributes from <ExtendedData>."""
        data: dict[str, Any] = {}
        for child in elem.iter():
            tag = self._get_local_tag(child.tag)
            if tag == "Data":
                name = child.attrib.get("name")
                for sub in child:
                    if self._get_local_tag(sub.tag) == "value" and sub.text:
                        data[name] = sub.text.strip()
            elif tag == "SimpleData":
                name = child.attrib.get("name")
                if name and child.text:
                    data[name] = child.text.strip()
        return data

    def _parse_geometry_element(self, elem: Element) -> Optional[BaseGeometry]:
        """Parses geometry elements into Shapely BaseGeometry."""
        tag = self._get_local_tag(elem.tag)

        if tag == "Point":
            coords = self._extract_coordinates(elem)
            if coords:
                return Point(coords[0][0], coords[0][1])

        elif tag == "LineString":
            coords = self._extract_coordinates(elem)
            if len(coords) >= 2:
                return LineString([(c[0], c[1]) for c in coords])

        elif tag == "Polygon":
            return self._parse_polygon_element(elem)

        elif tag == "LinearRing":
            coords = self._extract_coordinates(elem)
            if len(coords) >= 3:
                return Polygon([(c[0], c[1]) for c in coords])

        elif tag == "MultiGeometry":
            sub_geoms: List[BaseGeometry] = []
            for sub in elem:
                sub_g = self._parse_geometry_element(sub)
                if sub_g and not sub_g.is_empty:
                    sub_geoms.append(sub_g)
            if not sub_geoms:
                return None

            # Attempt to homogenize into MultiPolygon or MultiLineString if appropriate
            all_poly = all(isinstance(g, Polygon) for g in sub_geoms)
            if all_poly:
                return MultiPolygon(sub_geoms)

            all_lines = all(isinstance(g, LineString) for g in sub_geoms)
            if all_lines:
                return MultiLineString(sub_geoms)

            return GeometryCollection(sub_geoms)

        return None

    def _parse_polygon_element(self, poly_elem: Element) -> Optional[Polygon]:
        """Parses <Polygon> with outer and inner boundary linear rings."""
        outer_coords: List[Tuple[float, float]] = []
        inner_rings: List[List[Tuple[float, float]]] = []

        for child in poly_elem:
            tag = self._get_local_tag(child.tag)
            if tag == "outerBoundaryIs":
                for ring in child:
                    if self._get_local_tag(ring.tag) == "LinearRing":
                        raw_c = self._extract_coordinates(ring)
                        outer_coords = [(c[0], c[1]) for c in raw_c]
            elif tag == "innerBoundaryIs":
                for ring in child:
                    if self._get_local_tag(ring.tag) == "LinearRing":
                        raw_c = self._extract_coordinates(ring)
                        if len(raw_c) >= 3:
                            inner_rings.append([(c[0], c[1]) for c in raw_c])

        if len(outer_coords) >= 3:
            return Polygon(shell=outer_coords, holes=inner_rings)
        return None

    def _extract_coordinates(self, elem: Element) -> List[Tuple[float, ...]]:
        """Finds <coordinates> text and parses whitespace and comma separated coordinates."""
        coords: List[Tuple[float, ...]] = []
        for child in elem.iter():
            if self._get_local_tag(child.tag) == "coordinates" and child.text:
                text = child.text.strip()
                # Split tuples separated by whitespace/newlines
                tuples = re.split(r"\s+", text)
                for t in tuples:
                    if not t.strip():
                        continue
                    parts = t.strip().split(",")
                    if len(parts) >= 2:
                        try:
                            lon = float(parts[0])
                            lat = float(parts[1])
                            alt = float(parts[2]) if len(parts) > 2 else 0.0
                            coords.append((lon, lat, alt))
                        except ValueError:
                            continue
        return coords
