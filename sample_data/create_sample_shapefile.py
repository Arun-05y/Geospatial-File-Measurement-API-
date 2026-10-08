"""Generates sample shapefile components (.shp, .shx, .dbf, .prj) and packages them into sample_shapefile.zip."""

from pathlib import Path
import zipfile
import shapefile

def generate_shapefile():
    output_dir = Path(__file__).resolve().parent
    base_name = "sample_parcels"
    shp_path = output_dir / f"{base_name}.shp"
    zip_path = output_dir / "sample_shapefile.zip"

    # Create Shapefile Writer for Polygons
    w = shapefile.Writer(str(output_dir / base_name), shapeType=shapefile.POLYGON)

    # Define fields (attributes)
    w.field("NAME", "C", size=50)
    w.field("PARCEL_ID", "N", size=10)
    w.field("ZONING", "C", size=20)
    w.field("VALUATION", "F", size=12, decimal=2)

    # Feature 1: Parcel 101 in Minneapolis (lon, lat in EPSG:4326)
    poly1 = [
        [-93.2680, 44.9780],
        [-93.2640, 44.9780],
        [-93.2640, 44.9750],
        [-93.2680, 44.9750],
        [-93.2680, 44.9780],
    ]
    w.poly([poly1])
    w.record(NAME="Commercial Lot A", PARCEL_ID=101, ZONING="Commercial", VALUATION=450000.50)

    # Feature 2: Parcel 102
    poly2 = [
        [-93.2635, 44.9780],
        [-93.2600, 44.9780],
        [-93.2600, 44.9750],
        [-93.2635, 44.9750],
        [-93.2635, 44.9780],
    ]
    w.poly([poly2])
    w.record(NAME="Residential Lot B", PARCEL_ID=102, ZONING="Residential", VALUATION=285000.00)

    # Close and write .shp, .shx, .dbf
    w.close()

    # Create WGS84 (.prj) file
    wgs84_wkt = (
        'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],'
        'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
    )
    prj_path = output_dir / f"{base_name}.prj"
    prj_path.write_text(wgs84_wkt, encoding="utf-8")

    # Package into sample_shapefile.zip
    companion_extensions = [".shp", ".shx", ".dbf", ".prj"]
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for ext in companion_extensions:
            file_to_pack = output_dir / f"{base_name}{ext}"
            if file_to_pack.exists():
                zf.write(file_to_pack, arcname=f"{base_name}{ext}")

    print(f"Successfully generated {zip_path}")

if __name__ == "__main__":
    generate_shapefile()
