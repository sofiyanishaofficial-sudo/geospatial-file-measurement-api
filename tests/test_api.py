from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Geospatial File Measurement API is running"


def test_kml_file():
    response = client.get("/api/files/test.kml")

    assert response.status_code == 200

    data = response.json()

    assert data["feature_count"] == 3
    assert len(data["features"]) == 3


def test_kml_measurements():
    response = client.get("/api/files/test.kml/measurements/")

    assert response.status_code == 200

    data = response.json()

    assert len(data["measurements"]) == 3

    assert data["measurements"][0]["geometry_type"] == "Point"
    assert data["measurements"][0]["measurement"] is None

    assert data["measurements"][1]["geometry_type"] == "LineString"
    assert data["measurements"][1]["length_meters"] > 0

    assert data["measurements"][2]["geometry_type"] == "Polygon"
    assert data["measurements"][2]["area_square_meters"] > 0


def test_shapefile():
    response = client.get(
        "/api/files/test_polygons_shapefile.zip"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["feature_count"] == 2
    assert len(data["features"]) == 2


def test_shapefile_measurements():
    response = client.get(
        "/api/files/test_polygons_shapefile.zip/measurements/"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["measurements"]) == 2

    for measurement in data["measurements"]:
        assert measurement["geometry_type"] == "Polygon"
        assert measurement["area_square_meters"] > 0


def test_file_not_found():
    response = client.get(
        "/api/files/not_found.kml"
    )

    assert response.status_code == 404


def test_unsupported_file():
    response = client.get(
        "/api/files/test.txt"
    )

    assert response.status_code == 404