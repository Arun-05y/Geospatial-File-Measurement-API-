"""Shapefile (.zip) parser using pyshp, shapely, and pyproj."""

import datetime
from pathlib import Path
import tempfile
import zipfile
from typing import Any
import pyproj
from pyproj import CRS
import shapefile
from shapely.geometry import shape as to_shapely_shape

from app.config import settings
from app.core.exceptions import CorruptedArchiveError, InvalidFileError, ParsingError
from app.services.parsers.base import BaseParser, ParsedDataset, ParsedFeature


class ShapefileParser(BaseParser):
    """Parses zipped ESRI Shapefiles safely into structured features."""

    MAX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024  # 200 MB zip-bomb limit

    def parse(self, file_path: Path) -> ParsedDataset:
        if not zipfile.is_zipfile(file_path):
            raise InvalidFileError(f"File '{file_path.name}' is not a valid ZIP archive.")

        with tempfile.TemporaryDirectory(prefix="gfm_shp_") as temp_dir:
            extract_path = Path(temp_dir)
            self._safe_extract_zip(file_path, extract_path)

            shp_files = list(extract_path.rglob("*.shp")) + list(extract_path.rglob("*.SHP"))
            if not shp_files:
                raise CorruptedArchiveError("ZIP archive must contain at least one .shp file.")

            # Pick the primary shapefile
            target_shp = shp_files[0]
            base_stem = target_shp.stem
            parent_dir = target_shp.parent

            # Verify companion files
            dbf_file = parent_dir / f"{base_stem}.dbf"
            if not dbf_file.exists():
                dbf_file = parent_dir / f"{base_stem}.DBF"
            if not dbf_file.exists():
                raise CorruptedArchiveError(f"Shapefile '{target_shp.name}' is missing companion .dbf file.")

            shx_file = parent_dir / f"{base_stem}.shx"
            if not shx_file.exists():
                shx_file = parent_dir / f"{base_stem}.SHX"
            if not shx_file.exists():
                raise CorruptedArchiveError(f"Shapefile '{target_shp.name}' is missing companion .shx file.")

            # Parse projection from .prj if present
            crs, crs_str = self._detect_crs(parent_dir, base_stem)

            # Read features using shapefile.Reader
            features = self._read_features(target_shp)

            return ParsedDataset(crs=crs, crs_str=crs_str, features=features)

    def _safe_extract_zip(self, zip_path: Path, target_dir: Path) -> None:
        """Extracts ZIP archive while guarding against Zip Slip and Zip Bomb attacks."""
        total_size = 0
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.infolist():
                # Protect against Zip Slip directory traversal
                member_path = (target_dir / member.filename).resolve()
                if not str(member_path).startswith(str(target_dir.resolve())):
                    raise CorruptedArchiveError(f"Unsafe file path detected in ZIP: {member.filename}")

                # Protect against Zip Bomb
                total_size += member.file_size
                if total_size > self.MAX_UNCOMPRESSED_BYTES:
                    raise CorruptedArchiveError("ZIP uncompressed size exceeds allowable threshold (200MB).")

                zf.extract(member, target_dir)

    def _detect_crs(self, parent_dir: Path, base_stem: str) -> tuple[CRS, str]:
        """Detects CRS from .prj file or falls back to default EPSG:4326."""
        prj_path = parent_dir / f"{base_stem}.prj"
        if not prj_path.exists():
            prj_path = parent_dir / f"{base_stem}.PRJ"

        if prj_path.exists():
            try:
                prj_wkt = prj_path.read_text(encoding="utf-8", errors="ignore").strip()
                if prj_wkt:
                    crs = CRS.from_user_input(prj_wkt)
                    epsg_code = crs.to_epsg()
                    crs_str = f"EPSG:{epsg_code}" if epsg_code else (crs.to_string() or "PROJCS/GEOGCS")
                    return crs, crs_str
            except Exception:
                pass

        # Default fallback
        return CRS.from_epsg(4326), settings.DEFAULT_CRS

    def _read_features(self, shp_path: Path) -> list[ParsedFeature]:
        """Reads shapefile records and constructs ParsedFeature models."""
        features: list[ParsedFeature] = []
        try:
            with shapefile.Reader(str(shp_path)) as sf:
                for idx, shape_rec in enumerate(sf.iterShapeRecords()):
                    try:
                        geo_dict = shape_rec.shape.__geo_interface__
                        if not geo_dict or not geo_dict.get("type"):
                            continue

                        shapely_geom = to_shapely_shape(geo_dict)
                        geom_type = shapely_geom.geom_type

                        # Extract attributes and serialize types
                        raw_props = shape_rec.record.as_dict()
                        clean_props = self._sanitize_properties(raw_props)

                        feature_id = clean_props.get("id") or clean_props.get("ID") or clean_props.get("FID") or idx

                        features.append(
                            ParsedFeature(
                                feature_id=feature_id,
                                geometry_type=geom_type,
                                geometry_geojson=geo_dict,
                                shapely_geom=shapely_geom,
                                properties=clean_props,
                            )
                        )
                    except Exception as feat_err:
                        # Log and skip corrupted single record instead of failing entire file
                        continue
        except Exception as e:
            raise ParsingError(f"Failed to read shapefile records: {str(e)}")

        return features

    @staticmethod
    def _sanitize_properties(props: dict[str, Any]) -> dict[str, Any]:
        """Ensures all property dictionary values are JSON serializable."""
        clean = {}
        for k, v in props.items():
            if isinstance(v, (datetime.date, datetime.datetime)):
                clean[k] = v.isoformat()
            elif isinstance(v, bytes):
                clean[k] = v.decode("utf-8", errors="replace")
            else:
                clean[k] = v
        return clean
