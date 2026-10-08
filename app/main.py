from fastapi import FastAPI, UploadFile, File, HTTPException
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile
import shutil
import shapefile
from shapely.geometry import (
    Point,
    LineString,
    Polygon,
    shape
)
from pyproj import Transformer

app = FastAPI()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@app.get("/")
def root():
    return {"message": "Geospatial File Measurement API is running"}


@app.post("/api/files/")
async def upload_file(file: UploadFile = File(...)):
    filename = Path(file.filename).name
    file_path = UPLOAD_DIR / filename

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    return {
        "filename": filename,
        "message": "File uploaded and saved successfully"
    }


def read_kml(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()

    namespace = {
        "kml": "http://www.opengis.net/kml/2.2"
    }

    features = []

    for index, placemark in enumerate(
        root.findall(".//kml:Placemark", namespace)
    ):
        name = placemark.find("kml:name", namespace)

        name_value = (
            name.text if name is not None else f"Feature {index}"
        )

        point = placemark.find(".//kml:Point", namespace)
        line = placemark.find(".//kml:LineString", namespace)
        polygon = placemark.find(".//kml:Polygon", namespace)

        geometry = None

        if point is not None:
            coordinates = point.find(
                "kml:coordinates", namespace
            )

            if coordinates is not None:
                values = coordinates.text.strip().split(",")

                geometry = Point(
                    float(values[0]),
                    float(values[1])
                )

        elif line is not None:
            coordinates = line.find(
                "kml:coordinates", namespace
            )

            if coordinates is not None:
                points = []

                for coordinate in coordinates.text.strip().split():
                    values = coordinate.split(",")

                    points.append(
                        (
                            float(values[0]),
                            float(values[1])
                        )
                    )

                geometry = LineString(points)

        elif polygon is not None:
            coordinates = polygon.find(
                ".//kml:outerBoundaryIs/"
                "kml:LinearRing/kml:coordinates",
                namespace
            )

            if coordinates is not None:
                points = []

                for coordinate in coordinates.text.strip().split():
                    values = coordinate.split(",")

                    points.append(
                        (
                            float(values[0]),
                            float(values[1])
                        )
                    )

                geometry = Polygon(points)

        if geometry is not None:
            features.append({
                "id": index,
                "geometry_type": geometry.geom_type,
                "geometry": geometry.__geo_interface__,
                "crs": "EPSG:4326",
                "properties": {
                    "name": name_value
                }
            })

    return features


def read_shapefile(zip_path):
    extract_dir = UPLOAD_DIR / zip_path.stem
    extract_dir.mkdir(exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_dir)

    shp_files = list(extract_dir.rglob("*.shp"))

    if not shp_files:
        raise ValueError(
            "ZIP file does not contain a .shp file"
        )

    shp_path = shp_files[0]

    reader = shapefile.Reader(str(shp_path))

    fields = [
        field[0]
        for field in reader.fields[1:]
    ]

    features = []

    for index, record_shape in enumerate(reader.iterShapeRecords()):
        geometry = shape(record_shape.shape.__geo_interface__)

        properties = dict(
            zip(fields, record_shape.record)
        )

        features.append({
            "id": index,
            "geometry_type": geometry.geom_type,
            "geometry": geometry.__geo_interface__,
            "crs": "EPSG:4326",
            "properties": properties
        })

    return features


@app.get("/api/files/{filename}")
def get_file(filename: str):
    filename = Path(filename).name
    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    try:
        if file_path.suffix.lower() == ".kml":
            features = read_kml(file_path)

        elif file_path.suffix.lower() == ".zip":
            features = read_shapefile(file_path)

        else:
            raise HTTPException(
                status_code=400,
                detail="Only KML and ZIP Shapefile files are supported"
            )

        return {
            "filename": filename,
            "feature_count": len(features),
            "features": features
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to read file: {str(e)}"
        )


def calculate_measurements(features):
    measurements = []

    for feature in features:
        geometry_type = feature["geometry_type"]
        geometry_data = feature["geometry"]

        geometry = shape(geometry_data)

        if geometry_type == "Point":
            measurements.append({
                "id": feature["id"],
                "geometry_type": "Point",
                "measurement": None
            })

        elif geometry_type == "LineString":
            transformer = Transformer.from_crs(
                "EPSG:4326",
                "EPSG:32644",
                always_xy=True
            )

            projected_points = []

            for lon, lat in geometry.coords:
                x, y = transformer.transform(lon, lat)
                projected_points.append((x, y))

            projected_geometry = LineString(projected_points)

            measurements.append({
                "id": feature["id"],
                "geometry_type": "LineString",
                "length_meters": round(
                    projected_geometry.length,
                    2
                )
            })

        elif geometry_type == "Polygon":
            transformer = Transformer.from_crs(
                "EPSG:4326",
                "EPSG:32644",
                always_xy=True
            )

            projected_points = []

            for lon, lat in geometry.exterior.coords:
                x, y = transformer.transform(lon, lat)
                projected_points.append((x, y))

            projected_geometry = Polygon(projected_points)

            measurements.append({
                "id": feature["id"],
                "geometry_type": "Polygon",
                "area_square_meters": round(
                    projected_geometry.area,
                    2
                )
            })

    return measurements


@app.get("/api/files/{filename}/measurements/")
def get_measurements(filename: str):
    filename = Path(filename).name
    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    try:
        if file_path.suffix.lower() == ".kml":
            features = read_kml(file_path)

        elif file_path.suffix.lower() == ".zip":
            features = read_shapefile(file_path)

        else:
            raise HTTPException(
                status_code=400,
                detail="Only KML and ZIP Shapefile files are supported"
            )

        measurements = calculate_measurements(features)

        return {
            "filename": filename,
            "measurements": measurements
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to calculate measurements: {str(e)}"
        )