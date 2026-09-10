from app.main import app


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_cloud_run_routes_avoid_reserved_z_suffix():
    reserved_paths = [
        route.path for route in app.routes if getattr(route, "path", "").endswith("z")
    ]
    assert reserved_paths == []


def test_metrics(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "python_gc_objects_collected_total" in response.text
