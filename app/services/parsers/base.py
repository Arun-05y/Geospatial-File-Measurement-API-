"""Base interface and data classes for geospatial file parsers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List
from pyproj import CRS
from shapely.geometry.base import BaseGeometry


@dataclass
class ParsedFeature:
    """Internal representation of a parsed geospatial feature."""
    feature_id: Any
    geometry_type: str
    geometry_geojson: dict[str, Any]
    shapely_geom: BaseGeometry
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedDataset:
    """Container for parsed features and dataset metadata."""
    crs: CRS
    crs_str: str
    features: List[ParsedFeature]


class BaseParser(ABC):
    """Abstract base class for geospatial file parsers."""

    @abstractmethod
    def parse(self, file_path: Path) -> ParsedDataset:
        """Parses the geospatial file at file_path and returns a ParsedDataset."""
        pass
