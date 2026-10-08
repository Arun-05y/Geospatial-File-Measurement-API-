# Geospatial File Measurement API (GFM)

A production-grade backend service built with **FastAPI**, **Shapely**, **PyProj**, and **PyShp** that ingests geospatial vector files (**Shapefile `.zip`** and **OGC KML `.kml`**), parses vector features, dynamically transforms geographic coordinates to metric projected coordinate systems, and calculates high-precision geometric measurements (polygon areas, linestring lengths, and graceful point handling).

---

## 🌟 Key Features

- **Multi-Format Ingestion**: Supports `.zip` containing ESRI Shapefiles (`.shp`, `.shx`, `.dbf`, `.prj`) and OGC KML (`.kml`) files.
- **Accurate CRS Handling**: Geographic coordinates in angular degrees (e.g., `EPSG:4326`) are never used directly for area or length. Features are dynamically transformed to their optimal metric **UTM projection** based on feature centroids, with polar fallback to **UPS**.
- **Dual Metric Verification**: Computes metric planar projected measurements alongside **WGS84 ellipsoidal geodesic measurements** via `pyproj.Geod`.
- **Supported Geometries & Measurements**:
  - **Polygon / MultiPolygon**: Area ($m^2$, $km^2$, hectares, acres) and Perimeter ($m$, $km$).
  - **LineString / MultiLineString**: Length ($m$, $km$, miles).
  - **Point / MultiPoint**: Gracefully handled with coordinates recorded (`not_applicable` status, zero crash).
  - **Unsupported Types**: Handled gracefully (`unsupported_geometry`) with informative notes rather than failing the request.
- **Interactive Web Dashboard**: Built-in Leaflet.js interactive map at `/` with drag-and-drop file upload, real-time metrics, and feature popups.
- **Production Hardened**: Guards against **Zip Slip** path traversal, **Zip Bomb** resource exhaustion, and XML **XXE / entity expansion attacks** using `defusedxml`.

---

## 📋 API Specification

### Endpoint Overview

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/files/` | Uploads and processes a `.zip` Shapefile or `.kml` file. |
| `GET` | `/api/files/{id}/` | Returns metadata and status for an uploaded file. |
| `GET` | `/api/files/{id}/measurements/` | Returns feature-level and summary measurements. |
| `GET` | `/api/files/` | Lists all uploaded files (supports pagination: `skip`, `limit`). |
| `DELETE` | `/api/files/{id}/` | Deletes an uploaded file and clears cached measurements. |
| `GET` | `/api/health/` | Health check and version status. |
| `GET` | `/docs` | Interactive Swagger UI. |
| `GET` | `/` | Interactive Web Dashboard with Leaflet Map. |

---

### Request & Response Examples

#### 1. Upload Geospatial File
`POST /api/files/`

**cURL Request:**
```bash
curl -X POST "http://127.0.0.1:8000/api/files/" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@sample_data/sample_polygons.kml"
```

**Response (`201 Created`):**
```json
{
  "id": "e4587ba210",
  "filename": "sample_polygons.kml",
  "feature_count": 2,
  "crs": "EPSG:4326",
  "status": "COMPLETED",
  "uploaded_at": "2026-10-08T03:15:30.123456",
  "file_size_bytes": 1420,
  "error_message": null
}
```

---

#### 2. Get File Information
`GET /api/files/{id}/`

**cURL Request:**
```bash
curl -X GET "http://127.0.0.1:8000/api/files/e4587ba210/"
```

**Response (`200 OK`):**
```json
{
  "id": "e4587ba210",
  "filename": "sample_polygons.kml",
  "feature_count": 2,
  "crs": "EPSG:4326",
  "status": "COMPLETED"
}
```

---

#### 3. Get File Measurements
`GET /api/files/{id}/measurements/`

**cURL Request:**
```bash
curl -X GET "http://127.0.0.1:8000/api/files/e4587ba210/measurements/"
```

**Response (`200 OK`):**
```json
{
  "file_id": "e4587ba210",
  "filename": "sample_polygons.kml",
  "source_crs": "EPSG:4326",
  "summary": {
    "total_features": 2,
    "polygon_count": 2,
    "linestring_count": 0,
    "point_count": 0,
    "unsupported_count": 0,
    "total_area_sq_meters": 236748.12,
    "total_area_sq_km": 0.236748,
    "total_area_hectares": 23.6748,
    "total_length_meters": 0.0,
    "total_length_km": 0.0,
    "projected_crs_used": ["EPSG:32615"]
  },
  "features": [
    {
      "feature_id": "North Field Alpha",
      "geometry_type": "Polygon",
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [-93.265, 44.9778],
            [-93.261, 44.9778],
            [-93.261, 44.974],
            [-93.265, 44.974],
            [-93.265, 44.9778]
          ]
        ]
      },
      "crs": "EPSG:4326",
      "properties": {
        "crop": "Soybean",
        "farmer": "J. Smith"
      },
      "measurements": {
        "measurement_status": "calculated",
        "area_sq_meters": 133589.62,
        "area_sq_km": 0.13359,
        "area_hectares": 13.359,
        "area_acres": 33.0107,
        "perimeter_meters": 1464.32,
        "perimeter_km": 1.4643,
        "geodesic_area_sq_meters": 133572.84,
        "geodesic_length_meters": null,
        "projected_crs": "EPSG:32615",
        "notes": "Calculated in WGS 84 / UTM zone 15N"
      }
    }
  ]
}
```

---

## 🏗️ Architecture

```
GFM/
├── app/
│   ├── main.py                     # FastAPI application entrypoint & middleware
│   ├── config.py                   # App configuration & environment constraints
│   ├── api/
│   │   ├── router.py               # Aggregated API router
│   │   └── v1/
│   │       ├── files.py            # POST /files/, GET /files/{id}/, GET measurements
│   │       └── health.py           # Health check endpoint
│   ├── core/
│   │   ├── exceptions.py        # Domain-specific exceptions
│   │   └── error_handlers.py    # Standardized JSON error response handlers
│   ├── models/
│   │   └── schemas.py           # Pydantic v2 schemas for files and measurements
│   ├── services/
│   │   ├── crs_service.py       # UTM zone calculation, reprojection & geodesics
│   │   ├── measurement.py       # Geometric measurement engine (Polygons, Lines, Points)
│   │   ├── file_service.py      # Upload pipeline orchestration
│   │   └── parsers/
│   │       ├── base.py          # Abstract parser interface
│   │       ├── shapefile_parser.py # Safe zipped shapefile parser
│   │       └── kml_parser.py    # Secure OGC KML parser
│   ├── storage/
│   │   └── repository.py        # Thread-safe repository for file metadata
│   └── static/
│       ├── index.html           # Leaflet-powered interactive web dashboard
│       └── app.js               # Frontend map rendering and upload handler
├── sample_data/                 # Test files (KML polygons, lines, points, and zipped shapefile)
├── tests/                       # Complete pytest suite (26 passing tests)
├── Dockerfile                   # Multi-stage container definition
├── docker-compose.yml           # Local container orchestration
└── requirements.txt             # Locked Python dependencies
```

---

### Pipeline Flow

```
+--------------------+
|  Client Upload     |  (.zip Shapefile or .kml)
+---------+----------+
          |
          v
+---------+----------+
|  Validation Layer  |  (Extension, size check, safe file extraction)
+---------+----------+
          |
          v
+---------+----------+
|  Parser Selection  |---> [.zip] -> ShapefileParser (pyshp + .prj detection)
+--------------------+---> [.kml] -> KMLParser (defusedxml Placemark walker)
          |
          v
+---------+----------+
| Vector Extraction  |  Extracts Feature ID, Geometry Type, Coordinates, Properties
+---------+----------+
          |
          v
+---------+----------+
|  CRS Engine        |  Detects geographic CRS (e.g. EPSG:4326)
+---------+----------+  Computes centroid -> Determines optimal UTM Zone (326xx / 327xx)
          |
          v
+---------+----------+
| Measurement Engine |  Reprojects to metric space:
+---------+----------+  - Polygon: Area (m², km², ha, acres) & Perimeter (m, km)
          |             - LineString: Length (m, km)
          |             - Point: Graceful not_applicable
          v
+---------+----------+
| Persistence & API  |  Stores result -> Returns structured JSON response
+--------------------+
```

---

## 🧭 CRS Handling Strategy

Geographic coordinate systems (such as `EPSG:4326` WGS84) represent points on an angular ellipsoid in decimal degrees $(\lambda, \phi)$. Direct Euclidean calculations on degrees produce completely distorted and meaningless numbers ($1^\circ \text{ lon}$ at the equator is $\approx 111.32\text{ km}$, while at $60^\circ\text{N}$ it is only $\approx 55.80\text{ km}$).

To solve this accurately:
1. **Dynamic UTM Zone Selection**:
   For any geographic geometry, we evaluate its centroid $(\text{lon}, \text{lat})$. The Universal Transverse Mercator (UTM) zone is calculated via:
   $$\text{Zone} = \left\lfloor \frac{\text{lon} + 180}{6} \right\rfloor + 1$$
   - Northern hemisphere ($\text{lat} \ge 0$): $\text{EPSG} = 32600 + \text{Zone}$
   - Southern hemisphere ($\text{lat} < 0$): $\text{EPSG} = 32700 + \text{Zone}$
2. **Polar Fallback (UPS)**:
   For latitudes above $84^\circ\text{N}$ or below $-80^\circ\text{S}$, standard UTM is undefined; the system automatically falls back to **Universal Polar Stereographic** (EPSG:32661 / EPSG:32761).
3. **Reprojection via PyProj**:
   Using `pyproj.Transformer.from_crs(source_crs, target_crs, always_xy=True)` and Shapely's modern vectorized coordinate transform, geometries are reprojected into conformal metric coordinates where Euclidean distance is measured in linear meters.
4. **Secondary Geodesic Verification**:
   We also evaluate `pyproj.Geod(ellps="WGS84")` to calculate true ellipsoidal surface area and geodesic lengths, accommodating the Earth's curvature directly.

---

## 💡 Design Decisions & Alternatives Considered

| Decision | Chosen Solution | Alternative Considered | Rationale |
|---|---|---|---|
| **Framework** | **FastAPI** | Django + DRF | FastAPI provides high-speed async I/O, native Pydantic v2 schemas, automated OpenAPI/Swagger generation, and low container footprint. |
| **Geospatial Stack** | **Shapely + PyProj + PyShp + DefusedXML** | OS-level GDAL / Fiona / GeoPandas | Compiling GDAL C-extensions on Windows/Docker frequently causes DLL hell and bloated images. `pyshp` (pure Python) + precompiled `shapely`/`pyproj` wheels install instantaneously, have 0 external C-library dependency issues, and provide top-tier performance. |
| **Projection Choice** | **Dynamic UTM Zone** | Web Mercator (EPSG:3857) | Web Mercator severely distorts surface area towards the poles (Greenland appears the size of Africa). UTM provides conformal metric projection with scale distortion below 0.1%. |
| **KML Parsing** | **defusedxml + ElementTree** | Standard xml.etree / fastkml | Protects against XML external entity (XXE) attacks and Billion Laughs vulnerabilities while providing fast, reliable parsing across inconsistent KML namespaces. |
| **Archive Security** | **Zip Slip + Bomb Filtering** | Direct unzip | Inspects every entry path in zip archives to prevent directory traversal and enforces a 200MB uncompressed limit. |

---

## 🚀 Setup & Local Execution

### Prerequisites
- Python 3.10+
- Git

### 1. Clone & Set Up Virtual Environment

```bash
# Clone the repository
git clone <repo-url>
cd GFM

# Create and activate virtual environment
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Application

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Interactive Swagger Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Interactive Web Dashboard**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

### 3. Run Automated Tests

```bash
pytest -v
```
All **26 unit and integration tests** will execute and verify parsers, CRS transformations, geometry measurements, and REST endpoints.

---

## 🐳 Docker Deployment

To build and run with Docker:

```bash
docker build -t gfm-api .
docker run -p 8000:8000 gfm-api
```

Or using Docker Compose:

```bash
docker-compose up --build
```

---

## 🧠 Key Learnings & Future Scope

### Key Learnings
1. **Projection Distortion Realities**: Degree-based calculations are fundamentally invalid for metric measurement. Selecting an appropriate metric coordinate system requires inspecting feature location and extent; UTM zone selection offers the optimal balance between accuracy and local conformal preservation.
2. **KML Namespace Variations**: Real-world KML files from Google Earth, ArcGIS, and QGIS frequently use differing or undeclared XML namespaces (`kml/2.2`, `kml/2.0`, etc.). Stripping namespaces during tag inspection prevents silent parsing failures.
3. **Archive Security**: Supporting `.zip` uploads requires rigorous Zip Slip and Zip Bomb safeguards to prevent path traversal and memory denial-of-service in production.

### Future Scope
1. **Asynchronous Background Processing (Celery & Redis)**: For multi-gigabyte shapefiles or complex multi-million feature datasets, offload processing to asynchronous background workers with webhook notifications.
2. **Raster Measurement Support**: Extend the API to support GeoTIFF / DEM raster files to measure surface elevation statistics, slope, aspect, and 3D surface area.
3. **Topological Validation and Auto-Repair**: Integrate `shapely.validation.make_valid` to automatically heal self-intersecting polygon geometries (bowtie polygons, sliver gaps) before computing areas.
4. **Cloud-Native Storage & PostGIS Integration**: Enable streaming direct uploads to Amazon S3 / Google Cloud Storage and indexing vector features in PostgreSQL / PostGIS.
