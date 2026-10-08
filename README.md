# Geospatial File Measurement API

A FastAPI-based backend for uploading and processing geospatial files such as KML and zipped Shapefiles.

## Features

- Upload KML files
- Upload zipped Shapefiles
- Extract geospatial features
- Return geometry type, geometry, CRS, and properties
- Calculate:
  - Polygon area in square meters
  - LineString length in meters
  - Point measurement as null
- Transform geographic coordinates (EPSG:4326) to a projected CRS before measurement
- REST API endpoints
- Error handling
- Automated tests using pytest

## Tech Stack

- Python
- FastAPI
- Shapely
- PyProj
- PyShp
- Uvicorn
- Pytest

## API Endpoints

### Upload File

```http
POST /api/files/