def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_ready(client):
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "connected"}

def test_404_not_found(client):
    response = client.get("/api/v1/non-existent-endpoint")
    assert response.status_code == 404
    json_data = response.json()
    assert json_data["message"] == "Resource Not Found"
    assert json_data["status_code"] == 404
